"""Blind pre-merge review: can Meta's open-weight Muse Spark Open spot an incomplete patch
WITHOUT seeing the hidden independent checks?

For every recorded run that produced a candidate patch, the auditor gets the bug report,
the final patch, the frozen reproduction test, the agent's claim, and ONLY the results the
agent itself could see (frozen reproduction + public regressions). The independent verdict
is withheld. We then compare its accept/review call with the harness verdict.

No Docker, no Meta API call, no new repair. Patch and frozen-test hashes are checked against
the recorded results before any call. Requires BASETEN_API_KEY (never printed). Own ledger,
US$3 cap. Output: docs/evidence/auditor-blind-2026-11-02/.
"""
from pathlib import Path
import hashlib, json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from repropatch.auditor import PatchAuditor, AuditorDisabled, AuditorError, LABEL  # noqa: E402

EXT = ROOT / "docs/evidence/extension-2026-11-02"
OUT = ROOT / "docs/evidence/auditor-blind-2026-11-02"

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def records():
    cases = {c["case_id"]: c for c in json.loads((ROOT / "docs/evidence/case-provenance.json").read_text())}
    cases.update({c["case_id"]: c for c in json.loads((EXT / "case-provenance-extension.json").read_text())})
    pilot = {r["run_id"]: r for r in json.loads((ROOT / "docs/evidence/pilot-results.json").read_text())["runs"]}
    fl = json.loads((ROOT / "docs/evidence/first-live/report.json").read_text())
    if fl.get("run_id") in pilot:
        yield ROOT / "docs/evidence/first-live", pilot[fl["run_id"]], cases, True
    for r in json.loads((EXT / "extension-results.json").read_text())["runs"]:
        if r.get("counted") and r.get("patch_sha256"):
            yield EXT / "runs" / r["run_id"], r, cases, r["counted"]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        auditor = PatchAuditor(ROOT / ".data/auditor-blind-ledger.sqlite3", "3.00")
    except AuditorDisabled as exc:
        print(f"DISABLED: {exc}"); return 2
    rows = []
    try:
        for d, rec, cases, counted in records():
            patch = d / "repair.patch"; frozen = next(d.glob("reproduction.frozen.*"), None)
            if not patch.exists() or sha(patch) != rec["patch_sha256"] or (frozen and sha(frozen) != rec["frozen_test_sha256"]):
                print(f"SKIP {d.name}: missing artifact or hash mismatch"); continue
            report = json.loads((d / "report.json").read_text())
            ev = rec["evaluation"]
            visible = {"frozen_reproduction": ev.get("frozen_reproduction"), "public_regressions": ev.get("public_regressions"),
                       "independent": "WITHHELD for this blind review. Judge the patch itself; do not assume it passed or failed."}
            case = cases[rec["case_id"]]
            try:
                audit = auditor.audit("blind-" + rec["run_id"], case, patch.read_text(),
                                      frozen.read_text() if frozen else None, visible, report.get("agent_claim"))
            except AuditorError as exc:
                print(f"ERROR {rec['case_id']}-{rec['method']}: {exc}"); rows.append({"run_id": rec["run_id"], "case_id": rec["case_id"],
                      "method": rec["method"], "harness_verdict": rec["status"], "auditor_error": str(exc)}); continue
            op = audit["opinion"]
            doc = {"mode": "BLIND review on recorded artifacts: independent verdict withheld from the auditor (no new repair, no Meta API call)",
                   "auditor": LABEL, "case_id": rec["case_id"], "method": rec["method"], "run_id": rec["run_id"],
                   "harness_verdict": rec["status"], "harness_verdict_unchanged": True, "shown_to_auditor": visible,
                   "inputs": {"patch_sha256": rec["patch_sha256"], "frozen_test_sha256": rec["frozen_test_sha256"]}, **audit}
            (OUT / f"{rec['case_id']}-{rec['method']}.json").write_text(json.dumps(doc, indent=2) + "\n")
            u = audit["usage"]
            rows.append({"run_id": rec["run_id"], "case_id": rec["case_id"], "method": rec["method"], "harness_verdict": rec["status"],
                         "auditor_recommendation": op["recommendation"], "overfitting_risk": op["overfitting_risk"],
                         "confidence": op["confidence"], "prompt_tokens": u["prompt_tokens"], "completion_tokens": u["completion_tokens"],
                         "estimated_cost_usd": u["estimated_cost_usd"]})
            print(f"{rec['case_id']}-{rec['method']}: harness={rec['status']} auditor={op['recommendation']} risk={op['overfitting_risk']} est=${u['estimated_cost_usd']}")
        ok = [r for r in rows if "auditor_recommendation" in r]
        def n(v, rec): return sum(1 for r in ok if r["harness_verdict"] == v and r["auditor_recommendation"] == rec)
        summary = {"date": "2026-11-02", "auditor": LABEL, "patches_audited": len(ok), "errors": len(rows) - len(ok),
                   "harness_VERIFIED": {"auditor_accept": n("VERIFIED", "accept"), "auditor_review": n("VERIFIED", "review")},
                   "harness_REJECTED_after_model_said_fixed": {"auditor_accept": n("REJECTED", "accept"), "auditor_review": n("REJECTED", "review")},
                   "ledger": auditor.ledger.summary(),
                   "limits": "Tiny sample from one library; the auditor never sees the hidden checks; advisory only, never changes a verdict."}
        (OUT / "summary.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2) + "\n")
        print(json.dumps(summary, indent=1))
    finally:
        auditor.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
