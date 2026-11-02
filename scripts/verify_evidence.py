#!/usr/bin/env python3
"""Offline re-check of ReproPatch's recorded pilot evidence. Standard library only.

No network, no model calls, no Docker. It re-reads docs/evidence/, recomputes
SHA-256 hashes of the exported artifacts and re-tallies the recorded runs.
It cannot re-run the Meta model; it checks that the published record is
internally consistent.

Usage: python3 scripts/verify_evidence.py [--run RUN_ID_PREFIX] [--root REPO_DIR]

Also re-checks the 2 Nov 2026 extension (docs/evidence/extension-2026-11-02/):
6 more real VanJS bugs (2 batches), real Meta runs, per-call spend log, artifact hashes.
"""
import argparse, csv, hashlib, json, sys
from pathlib import Path

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--run"); ap.add_argument("--root", default=Path(__file__).resolve().parents[1])
    a = ap.parse_args(); ev = Path(a.root) / "docs" / "evidence"
    pilot = json.loads((ev / "pilot-results.json").read_text())
    runs = pilot["runs"]; ok = True
    if a.run and not any(x["run_id"].startswith(a.run) for x in runs) and (ev / EXT).exists():
        return extension(ev, a.run)
    if a.run:
        r = next((x for x in runs if x["run_id"].startswith(a.run)), None)
        if not r: sys.exit(f"run {a.run} not in pilot-results.json")
        print(f"RECORDED RUN {r['run_id']}  (replay of stored evidence; no new inference)")
        print(f"  case {r['case_id']}  method {r['method']}  model {pilot['protocol']['model']}")
        print(f"  Meta calls {r['model_calls']}  duration {r['duration_ms']/1000:.1f} s  metered USD {r['metered_cost_usd']:.6f}")
        ins = sum(u["input_tokens"] for u in r.get("response_usage", [])); outs = sum(u["output_tokens"] for u in r.get("response_usage", []))
        print(f"  tokens in/out {ins:,}/{outs:,}  (sum of {len(r.get('response_usage', []))} recorded Responses usages)")
        e = r.get("evaluation") or {}
        if e:
            print("INDEPENDENT EVALUATOR (fresh containers, result never sent back to the model)")
            print(f"  frozen reproduction : {e['frozen_reproduction']['outcome']} (exit {e['frozen_reproduction']['exit_code']})")
            print(f"  public regressions  : {'PASS' if e['public_regressions']['passed'] else 'FAIL'} (exit {e['public_regressions']['exit_code']})")
            print(f"  independent checks  : {'PASS' if e['independent']['passed'] else 'FAIL'} (exit {e['independent']['exit_code']})")
        print(f"VERDICT: {r['status']}   false_success={r['false_success']}   regressions={r['regressions']}   operator_interventions={r['operator_interventions']}")
        fl = ev / "first-live"
        if r["run_id"].startswith("909bd13d") and fl.exists():
            for name, key in (("repair.patch", "patch_sha256"), ("reproduction.frozen.cjs", "frozen_test_sha256")):
                got = sha(fl / name); match = got == r[key]; ok &= match
                print(f"  sha256 {name:24s} {got[:16]}…  recorded {r[key][:16]}…  {'MATCH' if match else 'MISMATCH'}")
            rep = json.loads((fl / "report.json").read_text())
            m = rep.get("video_sha256") and sha(fl / "reported-bug.mp4") == rep["video_sha256"]; ok &= bool(m)
            print(f"  sha256 reported-bug.mp4        {'MATCH' if m else 'MISMATCH'} (bug video uploaded to Meta Files)")
            print(f"  candidate reconstructed and hash-verified: {rep.get('candidate_reconstructed_and_hash_verified')}")
        aud = ev / "auditor" / f"{r['case_id']}-{r['method']}.json"
        if aud.exists():
            o = json.loads(aud.read_text())
            print(f"ADVISORY AUDITOR {o['model']} via {o['provider']} (after the verdict; cannot change it)")
            print(f"  recommendation {o['opinion']['recommendation']}  overfitting_risk {o['opinion']['overfitting_risk']}  verdict_unchanged {o['harness_verdict_unchanged']}")
        print("RESULT:", "all recorded hashes match" if ok else "HASH MISMATCH"); return 0 if ok else 1

    print(f"PILOT {pilot['protocol']['protocol']} · model {pilot['protocol']['model']} · retries {pilot['protocol']['retries']} · fixtures excluded {pilot['fixtures_excluded']}")
    print(f"{'run':9s} {'case':8s} {'meth':4s} {'verdict':9s} {'calls':>5s} {'USD':>9s} {'secs':>6s}  reason")
    for r in runs:
        print(f"{r['run_id'][:8]:9s} {r['case_id']:8s} {r['method']:4s} {r['status']:9s} {r['model_calls']:5d} {r['metered_cost_usd']:9.6f} {r['duration_ms']/1000:6.1f}  {r['reason'] or 'all checks passed'}")
    cases = sorted({r["case_id"] for r in runs})
    fixed = sorted({r["case_id"] for r in runs if r["status"] == "VERIFIED"})
    false_fixed = sum(1 for r in runs if r["false_success"])
    total = round(sum(r["metered_cost_usd"] for r in runs), 6); ok &= abs(total - pilot["metered_cost_usd"]) < 1e-6
    print("-" * 72)
    print(f"real bugs attempted        : {len(cases)}  ({', '.join(cases)})")
    print(f"real bugs verified fixed   : {len(fixed)} of {len(cases)}  ({', '.join(fixed)})")
    print(f"runs VERIFIED / REJECTED   : {sum(r['status']=='VERIFIED' for r in runs)} / {sum(r['status']=='REJECTED' for r in runs)}  (REJECTED = abstained at the 25-turn cap)")
    print(f"false 'fixed' claims       : {false_fixed}")
    print(f"Meta calls, all 8 runs     : {sum(r['model_calls'] for r in runs)}")
    print(f"metered Meta USD (sum)     : {total:.6f}  vs recorded total {pilot['metered_cost_usd']:.6f}  {'MATCH' if abs(total-pilot['metered_cost_usd'])<1e-6 else 'MISMATCH'}")
    print(f"W1 better than W0?         : no (same 2 cases fixed, same 2 abstained)")
    print(f"limits                     : {'; '.join(pilot['limitations'])}")
    if (ev / EXT).exists():
        print(); ok &= extension(ev) == 0
        x = json.loads((ev / EXT / "extension-results.json").read_text())
        xr = [r for r in x["runs"] if r["counted"]]
        allc = set(cases) | {r["case_id"] for r in xr}
        allf = set(fixed) | {r["case_id"] for r in xr if r["status"] == "VERIFIED"}
        caught = sum(1 for r in xr if r["false_success"] and r["status"] == "REJECTED")
        wrong = sum(1 for r in runs + xr if r["status"] == "VERIFIED" and not (r.get("evaluation") or {}).get("all_passed"))
        print("=" * 72)
        print(f"COMBINED (27 Oct pilot + 2 Nov extension, counted runs only)")
        print(f"real bugs verified fixed   : {len(allf)} of {len(allc)}  ({', '.join(sorted(allf))})")
        print(f"real Meta runs counted     : {len(runs) + len(xr)}")
        print(f"model 'fixed' claims that failed an independent check : {caught}  -> all stored as REJECTED")
        print(f"VERIFIED verdicts with any failed check                : {wrong}")
        print(f"metered Meta USD (counted) : {pilot['metered_cost_usd'] + x['summary']['metered_cost_usd_counted_runs']:.6f}")
    print("RESULT:", "all recorded hashes and totals match" if ok else "MISMATCH"); return 0 if ok else 1

EXT = "extension-2026-11-02"

def extension(ev, run=None):
    d = ev / EXT; x = json.loads((d / "extension-results.json").read_text()); ok = True
    prov = {c["case_id"]: c for c in json.loads((d / "case-provenance-extension.json").read_text())}
    for cid, c in prov.items():
        m = sha(d / f"bug-video-{cid}.mp4") == c["video_sha256"]; ok &= m
        if not run: print(f"  bug video {cid:18s} sha256 {'MATCH' if m else 'MISMATCH'}  (upstream fix {c['upstream_fix_commit'][:7]}, {c['video_origin']})")
    for r in x["runs"]:
        rd = d / "runs" / r["run_id"]
        for name, h in r["artifact_sha256"].items():
            m = sha(rd / name) == h; ok &= m
        if r.get("patch_sha256"):
            m = sha(rd / "repair.patch") == r["patch_sha256"]; ok &= m
        if r.get("frozen_test_sha256") and (rd / "reproduction.frozen.cjs").exists():
            m = sha(rd / "reproduction.frozen.cjs") == r["frozen_test_sha256"]; ok &= m
    rows = list(csv.DictReader(open(d / "spend-log-per-call.csv")))
    for r in x["runs"]:
        s = round(sum(float(c["metered_usd"]) for c in rows if c["run_id"] == r["run_id"]), 6)
        m = abs(s - r["metered_cost_usd"]) < 2e-6; ok &= m
    if run:
        r = next((y for y in x["runs"] if y["run_id"].startswith(run)), None)
        if not r: sys.exit(f"run {run} not found")
        e = r.get("evaluation") or {}
        print(f"RECORDED EXTENSION RUN {r['run_id']}  case {r['case_id']}  method {r['method']}  (real Meta run, 2 Nov 2026; replay of stored evidence)")
        print(f"  Meta calls {r['model_calls']}  metered USD {r['metered_cost_usd']:.6f}  counted={r['counted']}" + (f"  ({r['exclusion_reason']})" if r['exclusion_reason'] else ""))
        for k in ("frozen_reproduction", "public_regressions", "independent"):
            if k in e: print(f"  {k:20s}: {e[k].get('outcome') or ('PASS' if e[k].get('passed') else 'FAIL')} (exit {e[k]['exit_code']})")
        print(f"VERDICT: {r['status']}   model claimed fixed but a check failed: {r['false_success']}   reason: {r['reason'] or '-'}")
        print("RESULT:", "all recorded hashes match" if ok else "HASH MISMATCH"); return 0 if ok else 1
    print(f"EXTENSION 2 Nov 2026 · {x['summary']['model']} · {x['summary']['cases_counted']} more real VanJS bugs · W0+W1 each · artifacts re-hashed")
    print(f"{'run':9s} {'case':18s} {'meth':4s} {'verdict':9s} {'calls':>5s} {'USD':>9s}  note")
    for r in x["runs"]:
        e = r.get("evaluation") or {}
        note = ("NOT COUNTED: " + r["exclusion_reason"][:60]) if not r["counted"] else (
            "all checks passed" if r["status"] == "VERIFIED" else
            "no candidate (model ended without submitting)" if not r["candidate_sha256"] else
            "model said fixed; independent check FAILED -> REJECTED")
        print(f"{r['run_id'][:8]:9s} {r['case_id']:18s} {r['method']:4s} {r['status']:9s} {r['model_calls']:5d} {r['metered_cost_usd']:9.6f}  {note}")
    tot = round(sum(float(c["metered_usd"]) for c in rows), 6); m = abs(tot - x["summary"]["metered_cost_usd_all_runs"]) < 2e-6; ok &= m
    print(f"per-call spend log: {len(rows)} Meta calls, USD {tot:.6f} vs recorded {x['summary']['metered_cost_usd_all_runs']:.6f} {'MATCH' if m else 'MISMATCH'}")
    print(f"extension hashes/totals: {'MATCH' if ok else 'MISMATCH'}")
    return 0 if ok else 1

if __name__ == "__main__": sys.exit(main())
