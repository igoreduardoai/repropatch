"""Advisory Patch Auditor on Meta's open-weight Muse Spark Open, served by Baseten.

Role: AFTER a candidate is final and the independent evaluator has produced a
verdict, a second model from a different provider (open weights, not the repair
model) reads the diff, the frozen reproduction test and the evaluator result and
writes a structured opinion: patch scope, overfitting risk, likely regressions,
and a review/accept recommendation.

Boundaries (enforced in code and tests):
- Advisory only. The returned opinion is attached beside the report; it never
  changes status, verdict, `verified` or evaluation fields.
- Never runs before the verdict, and its output is never fed back to the repair
  agent (no second attempt).
- No silent fallback: without BASETEN_API_KEY the auditor is DISABLED and every
  output is labeled so. No retries on 429/5xx; the error is recorded instead.
- The API key is read from the server environment only and never placed in
  results, events, logs or artifacts.
- Spend goes to a SEPARATE ledger (default cap US$3) so Meta API accounting is
  untouched. Cost uses Baseten's public list price; it is an estimate, not an invoice.
"""
from decimal import Decimal
from pathlib import Path
import json
import os
import uuid
import httpx
from .budget import Budget, micro_to_usd
from .verify import redact

PROVIDER = "baseten"
MODEL = "meta-models/muse-spark-open-1026"
LABEL = "baseten:muse-spark-open-1026"
BASE_URL = "https://inference.baseten.co/v1"
# Baseten Model API list price for Muse Spark Open, USD per 1M tokens,
# https://www.baseten.co/library/muse-spark-open/ (checked 2026-10-27).
# Listed for slug meta-models/muse-spark-open; the dated -1026 slug is assumed
# to share it. Estimate only: not reconciled with a Baseten invoice.
PRICE = {"input": Decimal("1.25"), "cached_input": Decimal("0.15"), "output": Decimal("4.25"),
         "source": "https://www.baseten.co/library/muse-spark-open/", "checked": "2026-10-27"}
RECOMMENDATIONS = {"accept", "review"}
LEVELS = {"low", "medium", "high"}
MAX_INPUT_CHARS = 60_000

class AuditorError(RuntimeError): pass
class AuditorDisabled(AuditorError): pass

SYSTEM = """You are an independent, skeptical code-review auditor. A different AI agent
wrote a patch to fix a reported bug. A separate harness already ran a frozen
reproduction test and other checks and produced a verdict. You CANNOT change that
verdict and you are not asked to re-run anything. Judge only from the material shown.
Return ONLY a JSON object with exactly these keys:
{"patch_scope": "<what the patch changes, 1-3 sentences>",
 "scope_assessment": "minimal" | "proportionate" | "broader_than_needed",
 "overfitting_risk": "low" | "medium" | "high",
 "overfitting_reason": "<why: does the patch special-case the test or fix the general behavior?>",
 "likely_regressions": ["<concrete behavior that could break, or empty list>"],
 "recommendation": "accept" | "review",
 "rationale": "<2-4 sentences>",
 "confidence": "low" | "medium" | "high"}
Say "review" whenever a human should look before merging. Do not invent test results."""

def status(env=None) -> dict:
    env = os.environ if env is None else env
    enabled = bool(env.get("BASETEN_API_KEY"))
    return {"enabled": enabled, "provider": LABEL, "role": "advisory_patch_auditor",
            "reason": None if enabled else "BASETEN_API_KEY missing from server environment; auditor disabled"}

def disabled_opinion(reason: str) -> dict:
    return {"auditor": LABEL, "advisory": True, "status": "DISABLED", "reason": reason, "opinion": None}

def _clip(text: str, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + f"\n[... truncated {len(text) - limit} chars]"

def build_prompt(case: dict, patch: str, frozen_test: str | None, evaluation: dict, agent_claim: str | None) -> str:
    parts = [
        "## Reported bug\nTitle: " + str(case.get("title", "")) + "\nExpected behavior: " + str(case.get("expected_behavior", "")),
        "## Final patch (unified diff, written by the repair agent)\n```diff\n" + _clip(patch, 30_000) + "\n```",
        "## Frozen reproduction test (written by the agent before the fix and locked by hash)\n```js\n"
        + (_clip(frozen_test, 12_000) if frozen_test else "(none frozen in this method)") + "\n```",
        "## Harness verdict (independent evaluator; final and not yours to change)\n```json\n"
        + json.dumps(evaluation, indent=1, sort_keys=True)[:4_000] + "\n```",
        "## Agent claim\n" + str(agent_claim or "(none)"),
    ]
    return _clip("\n\n".join(parts), MAX_INPUT_CHARS)

def scrub(text: str, secrets=()) -> str:
    for value in secrets:
        if value:
            text = text.replace(value, "[redacted]")
    return redact(text)

def validate(raw: str, secrets=()) -> dict:
    try:
        data = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise AuditorError("auditor_response_not_json") from exc
    if not isinstance(data, dict):
        raise AuditorError("auditor_response_not_object")
    required = {"patch_scope": str, "scope_assessment": str, "overfitting_risk": str, "overfitting_reason": str,
                "likely_regressions": list, "recommendation": str, "rationale": str, "confidence": str}
    for key, kind in required.items():
        if not isinstance(data.get(key), kind):
            raise AuditorError(f"auditor_response_missing_{key}")
    if data["recommendation"] not in RECOMMENDATIONS:
        raise AuditorError("auditor_response_bad_recommendation")
    if data["overfitting_risk"] not in LEVELS or data["confidence"] not in LEVELS:
        raise AuditorError("auditor_response_bad_level")
    if not all(isinstance(x, str) for x in data["likely_regressions"]):
        raise AuditorError("auditor_response_bad_regressions")
    return {k: (scrub(v, secrets) if isinstance(v, str) else [scrub(x, secrets) for x in v]) for k, v in data.items() if k in required}

class PatchAuditor:
    def __init__(self, ledger_db: Path, cap_usd="3.00", api_key=None, transport=None, max_tokens=6000):
        self._key = api_key or os.getenv("BASETEN_API_KEY")
        if not self._key:
            raise AuditorDisabled("BASETEN_API_KEY missing from server environment; auditor disabled")
        self.max_tokens = max_tokens
        self.ledger = Budget(ledger_db, cap_usd, cap_usd)
        self.client = httpx.Client(base_url=BASE_URL, timeout=httpx.Timeout(240, connect=15),
                                   headers={"Authorization": f"Bearer {self._key}"},
                                   transport=transport, follow_redirects=False)

    def __repr__(self):
        return f"PatchAuditor(provider={LABEL!r})"

    def close(self):
        self.client.close()

    def _rates(self):
        # Budget stores micro-dollars; USD per 1M tokens == micro-dollars per token.
        return PRICE["input"], PRICE["output"], PRICE["cached_input"]

    def audit(self, run_id: str, case: dict, patch: str, frozen_test: str | None,
              evaluation: dict, agent_claim: str | None = None) -> dict:
        if not patch or not patch.strip():
            raise AuditorError("empty_patch_not_audited")
        prompt = build_prompt(case, patch, frozen_test, evaluation, agent_claim)
        payload = {"model": MODEL, "max_tokens": self.max_tokens, "response_format": {"type": "json_object"},
                   "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
        # No token-count endpoint: reserve conservatively (>= 1 token per 2 chars + overhead).
        reserve_in = (len(SYSTEM) + len(prompt)) // 2 + 512
        inr, outr, cacher = self._rates()
        request_id = uuid.uuid4().hex
        self.ledger.reserve(request_id, run_id, reserve_in, self.max_tokens, inr, outr)
        try:
            r = self.client.post("/chat/completions", json=payload)
        except httpx.HTTPError as exc:
            self.ledger.unknown(request_id)
            raise AuditorError(f"auditor_transport_{type(exc).__name__}") from None
        if r.status_code == 429 or r.status_code >= 500:
            # Provider declined/failed: record it, no automatic retry.
            self.ledger.unknown(request_id)
            raise AuditorError(f"auditor_http_{r.status_code}_no_retry")
        if r.status_code >= 400:
            self.ledger.unknown(request_id)
            raise AuditorError(f"auditor_http_{r.status_code}")
        try:
            data = r.json()
            usage = data["usage"]
            pin, pout = usage["prompt_tokens"], usage["completion_tokens"]
            if not isinstance(pin, int) or not isinstance(pout, int):
                raise KeyError("usage")
        except (ValueError, KeyError, TypeError):
            self.ledger.unknown(request_id)
            raise AuditorError("auditor_usage_missing") from None
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
        reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
        # completion_tokens already includes reasoning tokens; never add them twice.
        charged = self.ledger.settle(request_id, pin, pout, cached, inr, outr, cacher)
        usage_out = {"prompt_tokens": pin, "completion_tokens": pout, "cached_tokens": cached,
                     "reasoning_tokens": reasoning,
                     "estimated_cost_usd": micro_to_usd(charged),
                     "cost_basis": f"Baseten list price {PRICE['input']}/{PRICE['cached_input']}/{PRICE['output']} USD per 1M "
                                   f"input/cached/output tokens ({PRICE['source']}, checked {PRICE['checked']}); estimate, not invoice-verified"}
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise AuditorError("auditor_response_missing_content") from None
        opinion = validate(content, (self._key,))
        return {"auditor": LABEL, "model": data.get("model") or MODEL, "provider": PROVIDER, "advisory": True,
                "status": "COMPLETED", "response_id": data.get("id"), "opinion": opinion, "usage": usage_out,
                "note": "Advisory opinion from a different provider/model than the repair agent. It does not change the harness verdict."}

def attach(report: dict, audit: dict) -> dict:
    """Return a copy of report with the audit beside it. Verdict fields are never touched."""
    out = dict(report)
    out["advisory_audit"] = audit
    return out

def run_after_verdict(store, settings, rid: str, case: dict, report: dict, frozen_test: str | None, env=None):
    """Live-runner hook: called only after the terminal verdict is persisted."""
    env = os.environ if env is None else env
    if env.get("REPROPATCH_ENABLE_AUDITOR", "false").lower() != "true":
        store.event(rid, "Patch auditor not enabled (REPROPATCH_ENABLE_AUDITOR != true).", "info",
                    {"auditor": LABEL, "status": "NOT_ENABLED"})
        return None
    st = status(env)
    if not st["enabled"]:
        store.event(rid, "Patch auditor DISABLED: no Baseten key in server environment.", "warning",
                    {"auditor": LABEL, "status": "DISABLED"})
        return disabled_opinion(st["reason"])
    auditor = None
    try:
        auditor = PatchAuditor(settings.data_dir / "auditor-ledger.sqlite3",
                               env.get("REPROPATCH_AUDITOR_CAP_USD", "3.00"), api_key=env.get("BASETEN_API_KEY"))
        audit = auditor.audit(rid, case, report.get("patch", ""), frozen_test, report.get("evaluation", {}),
                              report.get("agent_claim"))
        store.event(rid, "Advisory patch audit recorded (verdict unchanged).", "info",
                    {"auditor": LABEL, "status": "COMPLETED", "recommendation": audit["opinion"]["recommendation"],
                     **{k: audit["usage"][k] for k in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "estimated_cost_usd")}})
        return audit
    except Exception as exc:
        reason = scrub(str(exc), (env.get("BASETEN_API_KEY"),))[:200]
        store.event(rid, "Advisory patch audit failed; verdict unchanged.", "warning",
                    {"auditor": LABEL, "status": "ERROR", "reason": reason})
        return {"auditor": LABEL, "advisory": True, "status": "ERROR", "reason": reason, "opinion": None}
    finally:
        if auditor:
            auditor.close()
