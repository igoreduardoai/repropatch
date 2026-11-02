"""Run the advisory Patch Auditor over ALREADY RECORDED pilot artifacts.

No Docker, no Meta API call, no new repair. Each input directory must contain the
recorded repair.patch, reproduction.frozen.* and report.json; hashes are checked
against docs/evidence/pilot-results.json before any Baseten call. Output goes to
docs/evidence/auditor/<case>-<method>.json. Requires BASETEN_API_KEY in the
environment (never printed). Spend is capped by a separate ledger (default US$3).
"""
from pathlib import Path
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from repropatch.auditor import PatchAuditor, AuditorDisabled, LABEL  # noqa: E402

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main(dirs):
    pilot = {r["run_id"]: r for r in json.loads((ROOT / "docs/evidence/pilot-results.json").read_text())["runs"]}
    cases = {c["case_id"]: c for c in json.loads((ROOT / "docs/evidence/case-provenance.json").read_text())}
    out_dir = ROOT / "docs/evidence/auditor"; out_dir.mkdir(parents=True, exist_ok=True)
    try:
        auditor = PatchAuditor(ROOT / ".data/auditor-ledger.sqlite3", "3.00")
    except AuditorDisabled as exc:
        print(f"DISABLED: {exc}"); return 2
    try:
        for d in map(Path, dirs):
            report = json.loads((d / "report.json").read_text())
            rec = pilot[report["run_id"]]
            patch = d / "repair.patch"; frozen = next(d.glob("reproduction.frozen.*"), None)
            if sha(patch) != rec["patch_sha256"] or (frozen and sha(frozen) != rec["frozen_test_sha256"]):
                print(f"SKIP {d}: hash mismatch with pilot-results.json"); continue
            case = cases[rec["case_id"]]
            audit = auditor.audit("audit-" + rec["run_id"], case, patch.read_text(),
                                  frozen.read_text() if frozen else None, rec["evaluation"], report.get("agent_claim"))
            doc = {"mode": "LIVE call on recorded artifacts (no new repair, no Meta API call)",
                   "auditor": LABEL, "case_id": rec["case_id"], "method": rec["method"], "pilot_run_id": rec["run_id"],
                   "harness_verdict": rec["status"], "harness_verdict_unchanged": True,
                   "inputs": {"patch_sha256": rec["patch_sha256"], "frozen_test_sha256": rec["frozen_test_sha256"],
                              "evaluation": rec["evaluation"]},
                   **audit}
            name = f"{rec['case_id']}-{rec['method']}.json"
            (out_dir / name).write_text(json.dumps(doc, indent=2) + "\n")
            u = audit["usage"]
            print(f"{name}: {audit['opinion']['recommendation']} risk={audit['opinion']['overfitting_risk']} "
                  f"in={u['prompt_tokens']} out={u['completion_tokens']} reasoning={u['reasoning_tokens']} est=${u['estimated_cost_usd']}")
        print("ledger:", json.dumps(auditor.ledger.summary()))
    finally:
        auditor.close()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or [str(ROOT / "docs/evidence/first-live")]))
