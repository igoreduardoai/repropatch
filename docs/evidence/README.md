# Actual execution evidence

- `pilot-results.json`: all eight actual attempts, response usage IDs, costs and
  hashes; includes four abstentions, no retries or fixtures.
- `case-provenance.json`: public source commits, video origins and manifest hashes.
- `first-live/`: first actual complete repair, frozen model test, patch, candidate
  hash, original bug video, browser screenshot, independent log and MIT attribution.
- `recorded-live-trace-walkthrough.mp4`: replay navigation of real stored traces,
  patch, evidence and evaluation; this is NOT a newly executed inference or a
  recording of the entire 80-second first repair. No speed-up is applied.
- PNGs: actual final HTTP UI states, not generated mockups.
- `auditor/`: advisory opinions from Meta's open-weight Muse Spark Open (Baseten),
  produced by `scripts/audit_recorded.py` on the recorded first-live artifacts and
  by `scripts/audit_control.py` on a labeled synthetic control. Real API calls on
  stored artifacts; no new repair, no Meta API call; verdicts unchanged.

Independent assertion bodies and reference source trees are deliberately not
published. They were operator-authored and executed privately, not represented
as upstream maintainer tests. Raw runtime traces and SQLite remain private in
`.data/`. Repository visibility is still private; these files are prepared for
public release after review.

## extension-2026-11-02/ (real Meta runs, 2 Nov 2026)

- `extension-results.json`: all 8 attempts (6 counted, 2 excluded with the reason), usage per response, hashes, evaluator results.
- `spend-log-per-call.csv`: every Meta call (response ID, tokens, metered USD).
- `case-provenance-extension.json`: upstream fix commits, manifest/snapshot/reference/evaluator tree hashes, video hashes.
- `runs/<run_id>/`: patch, frozen reproduction test, evaluator log, report.
- `bug-video-*.mp4`: the bug videos sent to Meta Files (recorded by us on the pre-fix code).
- `case-tests/`: the demo page, public test and independent check of each case (independent checks adapted from upstream VanJS tests, MIT), plus the broken v1 public test kept for transparency.
- `live-runs/`: asciinema recordings of all 8 live runs, and MP4 renders of two (idle gaps over 1.5 s compressed).
- `tooling/`: the scripts used to build the cases, record the videos, follow and export the runs.
