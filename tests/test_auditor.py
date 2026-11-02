"""Advisory Patch Auditor (Baseten, Muse Spark Open). Mocked HTTP only; no network."""
import json
import httpx
import pytest
from repropatch import auditor as A
from repropatch.store import Store

FAKE_KEY = "bt-test-SENTINEL-not-a-real-key-0123456789"
CASE = {"title": "Disabled state does not update", "expected_behavior": "button enables when state becomes false"}
PATCH = "--- a/src/x.js\n+++ b/src/x.js\n@@ -1 +1 @@\n-old\n+new\n"
EVAL = {"frozen_reproduction": {"outcome": "PASS"}, "public_regressions": {"passed": True},
        "independent": {"passed": True}, "all_passed": True}
GOOD = {"patch_scope": "Changes attribute handling.", "scope_assessment": "broader_than_needed",
        "overfitting_risk": "low", "overfitting_reason": "General fix.", "likely_regressions": ["style strings"],
        "recommendation": "review", "rationale": "Broad change.", "confidence": "medium"}

def ok_response(content=None, usage=None):
    return httpx.Response(200, json={"id": "chatcmpl_1", "model": A.MODEL,
        "choices": [{"message": {"role": "assistant", "content": json.dumps(GOOD) if content is None else content}}],
        "usage": usage or {"prompt_tokens": 1000, "completion_tokens": 400, "prompt_tokens_details": {"cached_tokens": 0},
                           "completion_tokens_details": {"reasoning_tokens": 300}}})

def make(tmp_path, handler, cap="3.00"):
    return A.PatchAuditor(tmp_path / "aud.sqlite3", cap, api_key=FAKE_KEY, transport=httpx.MockTransport(handler))

def test_missing_key_is_disabled_and_labeled(tmp_path, monkeypatch):
    monkeypatch.delenv("BASETEN_API_KEY", raising=False)
    with pytest.raises(A.AuditorDisabled):
        A.PatchAuditor(tmp_path / "aud.sqlite3")
    st = A.status({})
    assert st["enabled"] is False and "disabled" in st["reason"] and st["provider"] == "baseten:muse-spark-open-1026"
    assert A.disabled_opinion(st["reason"])["status"] == "DISABLED"

def test_request_shape_usage_and_cost(tmp_path):
    seen = []
    def handler(req):
        seen.append((req.url, req.headers.get("authorization"), json.loads(req.content)));return ok_response()
    aud = make(tmp_path, handler)
    out = aud.audit("run1", CASE, PATCH, "test()", EVAL, "fixed")
    url, auth, body = seen[0]
    assert str(url) == "https://inference.baseten.co/v1/chat/completions"
    assert auth == "Bearer " + FAKE_KEY and body["model"] == "meta-models/muse-spark-open-1026"
    assert out["status"] == "COMPLETED" and out["advisory"] is True and out["opinion"]["recommendation"] == "review"
    # 1000*1.25 + 400*4.25 micro-dollars; reasoning is inside completion tokens, not added again.
    assert out["usage"]["estimated_cost_usd"] == pytest.approx(0.00295)
    assert out["usage"]["reasoning_tokens"] == 300 and "not invoice-verified" in out["usage"]["cost_basis"]
    assert aud.ledger.summary()["settled_usd"] == pytest.approx(0.00295)
    aud.close()

@pytest.mark.parametrize("code", [429, 500, 503])
def test_rate_limit_and_server_errors_fail_without_retry(tmp_path, code):
    calls = []
    def handler(req):
        calls.append(1);return httpx.Response(code, json={"error": "x"})
    aud = make(tmp_path, handler)
    with pytest.raises(A.AuditorError, match=f"auditor_http_{code}_no_retry"):
        aud.audit("run1", CASE, PATCH, None, EVAL)
    assert len(calls) == 1 and aud.ledger.summary()["halted"]
    aud.close()

@pytest.mark.parametrize("content", ["not json", "[]", json.dumps({**GOOD, "recommendation": "merge_now"}),
                                     json.dumps({k: v for k, v in GOOD.items() if k != "rationale"}),
                                     json.dumps({**GOOD, "overfitting_risk": "none"})])
def test_malformed_response_rejected(tmp_path, content):
    aud = make(tmp_path, lambda req: ok_response(content))
    with pytest.raises(A.AuditorError):
        aud.audit("run1", CASE, PATCH, None, EVAL)
    aud.close()

def test_missing_usage_halts_ledger(tmp_path):
    aud = make(tmp_path, lambda req: httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(GOOD)}}]}))
    with pytest.raises(A.AuditorError, match="usage"):
        aud.audit("run1", CASE, PATCH, None, EVAL)
    assert aud.ledger.summary()["halted"]
    aud.close()

def test_cost_cap_blocks_before_request(tmp_path):
    calls = []
    aud = make(tmp_path, lambda req: calls.append(1) or ok_response(), cap="0.001")
    from repropatch.budget import BudgetExceeded
    with pytest.raises(BudgetExceeded):
        aud.audit("run1", CASE, PATCH, None, EVAL)
    assert calls == []
    aud.close()

def test_auditor_never_changes_verdict(tmp_path):
    report = {"status": "REJECTED", "verified": False, "evaluation": {**EVAL, "all_passed": False}, "patch": PATCH}
    before = json.loads(json.dumps(report))
    aud = make(tmp_path, lambda req: ok_response(json.dumps({**GOOD, "recommendation": "accept"})))
    out = A.attach(report, aud.audit("run1", CASE, PATCH, None, report["evaluation"]))
    assert report == before
    assert {k: out[k] for k in before} == before and out["advisory_audit"]["opinion"]["recommendation"] == "accept"
    aud.close()

def _run(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    run = store.create({"case_id": "c", "method": "W1", "mode": "live", "title": "t", "expected_behavior": "e"}, None)
    class S: data_dir = tmp_path
    return store, S, run["id"]

def _settings(path):
    path.mkdir(exist_ok=True)
    class S: data_dir = path
    return S

def test_hook_not_enabled_and_disabled_paths(tmp_path):
    store, S, rid = _run(tmp_path)
    assert A.run_after_verdict(store, S, rid, CASE, {"patch": PATCH}, None, env={}) is None
    out = A.run_after_verdict(store, S, rid, CASE, {"patch": PATCH}, None, env={"REPROPATCH_ENABLE_AUDITOR": "true"})
    assert out["status"] == "DISABLED"
    kinds = [e["data"]["status"] for e in store.events(rid) if "auditor" in (e["data"] or {})]
    assert kinds == ["NOT_ENABLED", "DISABLED"]

def test_key_never_in_events_errors_or_results(tmp_path, monkeypatch, caplog):
    store, S, rid = _run(tmp_path)
    env = {"REPROPATCH_ENABLE_AUDITOR": "true", "BASETEN_API_KEY": FAKE_KEY}
    # Error path whose provider message echoes the key must still not leak it.
    def boom(req): return httpx.Response(500, text="bad key " + FAKE_KEY)
    real = A.PatchAuditor.__init__
    def patched(self, db, cap="3.00", api_key=None, transport=None, max_tokens=6000):
        real(self, db, cap, api_key=api_key, transport=httpx.MockTransport(boom), max_tokens=max_tokens)
    monkeypatch.setattr(A.PatchAuditor, "__init__", patched)
    err = A.run_after_verdict(store, S, rid, CASE, {"patch": PATCH, "evaluation": EVAL}, None, env=env)
    def ok(req): return ok_response(json.dumps({**GOOD, "rationale": "the key is " + FAKE_KEY + " api_key=" + FAKE_KEY}))
    monkeypatch.setattr(A.PatchAuditor, "__init__", lambda self, db, cap="3.00", api_key=None, transport=None, max_tokens=6000:
                        real(self, db, cap, api_key=api_key, transport=httpx.MockTransport(ok), max_tokens=max_tokens))
    # Fresh ledger: the 500 above correctly halted the first one.
    good = A.run_after_verdict(store, _settings(tmp_path / "fresh"), rid, CASE, {"patch": PATCH, "evaluation": EVAL}, None, env=env)
    blob = json.dumps([err, good, store.events(rid)], default=str) + caplog.text + repr(A.PatchAuditor(tmp_path / "x", api_key=FAKE_KEY))
    assert err["status"] == "ERROR" and good["status"] == "COMPLETED", good
    assert "[redacted]" in good["opinion"]["rationale"]
    assert FAKE_KEY not in blob

def test_config_exposes_auditor_status_without_key(tmp_path, monkeypatch):
    monkeypatch.setenv("BASETEN_API_KEY", FAKE_KEY)
    from fastapi.testclient import TestClient
    from repropatch.api import create_app
    from repropatch.config import Settings
    (tmp_path / "d").mkdir()
    c = TestClient(create_app(Settings(data_dir=tmp_path / "d", auth_token="tok")))
    r = c.get("/api/config", headers={"Authorization": "Bearer tok"})
    assert r.json()["advisory_auditor"]["enabled"] is True and FAKE_KEY not in r.text

from test_live import env, submit, W1_GOOD  # noqa: E402,F401  (reuse live fixtures)

def test_live_runner_attaches_audit_after_verdict_without_changing_it(env, monkeypatch):
    monkeypatch.setenv("REPROPATCH_ENABLE_AUDITOR", "true")
    monkeypatch.setenv("BASETEN_API_KEY", FAKE_KEY)
    real = A.PatchAuditor.__init__
    seen = []
    def handler(req):
        seen.append(json.loads(req.content));return ok_response(json.dumps({**GOOD, "recommendation": "review"}))
    monkeypatch.setattr(A.PatchAuditor, "__init__", lambda self, db, cap="3.00", api_key=None, transport=None, max_tokens=6000:
                        real(self, db, cap, api_key=api_key, transport=httpx.MockTransport(handler), max_tokens=max_tokens))
    s, store, budget, reg, case = env
    row, rt, client = submit(env, "W1", W1_GOOD)
    assert row["status"] == "VERIFIED" and row["result"]["verified"] is True and "advisory_audit" not in row["result"]
    names = {a["name"] for a in store.artifacts(row["id"])}
    assert "advisory-audit.json" in names and len(seen) == 1
    # Meta spend ledger untouched by the auditor (separate ledger file).
    assert row["result"]["model_calls"] == 5
    assert FAKE_KEY not in json.dumps(store.events(row["id"]))
