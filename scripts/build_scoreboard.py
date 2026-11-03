#!/usr/bin/env python3
"""Build docs/scoreboard.json (read by the GitHub Pages landing page docs/index.html)
from the recorded evidence in docs/evidence/. Standard library only, no network, no model calls."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; EV = ROOT / "docs" / "evidence"; EXT = EV / "extension-2026-11-02"
pilot = json.loads((EV / "pilot-results.json").read_text())
prov = {c["case_id"]: c for c in json.loads((EV / "case-provenance.json").read_text())}
ext = json.loads((EXT / "extension-results.json").read_text())
xprov = {c["case_id"]: c for c in json.loads((EXT / "case-provenance-extension.json").read_text())}
PR = {"van-389": 389, "van-401": 401, "van-411": 411, "van-464": 464}
blind = {}
bd = EV / "auditor-blind-2026-11-02"
for f in sorted(bd.glob("*.json")):
    if f.name == "summary.json": continue
    d = json.loads(f.read_text()); blind[f.stem] = (d.get("opinion") or {}).get("recommendation")
def why(r):
    if r["status"] == "VERIFIED": return "Frozen reproduction, public regressions and independent check all passed"
    if r.get("candidate_sha256"): return 'Model said "Fixed"; its own reproduction and the public tests passed; the independent check FAILED'
    return {"turn_limit": "Stopped at the 25-turn cap without a candidate"}.get(r.get("reason"), "Ended without a candidate (" + str(r.get("reason")) + ")")
cases = {}
def add(cid, meta, src, link, video, r, batch):
    c = cases.setdefault(cid, {"case_id": cid, "title": meta.get("title"), "upstream": link, "source": src, "bug_video": video, "batch": batch, "runs": {}})
    cast = EXT / "live-runs" / f"live-run-{cid}-{r['method']}.cast"
    c["runs"][r["method"]] = {"run_id": r["run_id"], "status": r["status"], "why": why(r), "model_calls": r["model_calls"],
        "usd": r["metered_cost_usd"], "patch_sha256": r.get("patch_sha256"), "frozen_test_sha256": r.get("frozen_test_sha256"),
        "cast": f"evidence/extension-2026-11-02/live-runs/{cast.name}" if cast.exists() else None,
        "blind_review": blind.get(f"{cid}-{r['method']}"),
        "all_checks_passed": (r.get("evaluation") or {}).get("all_passed")}
for r in pilot["runs"]:
    n = PR[r["case_id"]]
    add(r["case_id"], prov[r["case_id"]], "VanJS PR", f"https://github.com/vanjs-org/van/pull/{n}", None, r, "pilot 27 Oct 2026")
for r in ext["runs"]:
    if not r["counted"]: continue
    p = xprov[r["case_id"]]; sha = p["upstream_fix_commit"]
    add(r["case_id"], p, "upstream fix", f"https://github.com/vanjs-org/van/commit/{sha}", f"evidence/extension-2026-11-02/bug-video-{r['case_id']}.mp4", r, "extension 2 Nov 2026")
allruns = [x for c in cases.values() for x in c["runs"].values()]
out = {"generated_from": ["docs/evidence/pilot-results.json", "docs/evidence/extension-2026-11-02/extension-results.json"],
  "model": "muse-wonder-1.0", "bugs": len(cases), "bugs_verified": sum(1 for c in cases.values() if any(x["status"] == "VERIFIED" for x in c["runs"].values())),
  "runs_counted": len(allruns), "verified_runs": sum(1 for x in allruns if x["status"] == "VERIFIED"),
  "false_fixed_caught": sum(1 for x in allruns if x["status"] != "VERIFIED" and x["patch_sha256"]),
  "no_candidate_runs": sum(1 for x in allruns if x["status"] != "VERIFIED" and not x["patch_sha256"]),
  "wrong_verified": sum(1 for x in allruns if x["status"] == "VERIFIED" and x["all_checks_passed"] is not True), "usd_counted": round(sum(x["usd"] for x in allruns), 6),
  "w0_bugs_verified": sum(1 for c in cases.values() if c["runs"].get("W0", {}).get("status") == "VERIFIED"),
  "w1_bugs_verified": sum(1 for c in cases.values() if c["runs"].get("W1", {}).get("status") == "VERIFIED"),
  "cases": list(cases.values())}
(ROOT / "docs" / "scoreboard.json").write_text(json.dumps(out, indent=1))
print({k: v for k, v in out.items() if k != "cases"})
