# Validation — 27 October and 2 November 2026

The validation of the starter build kit (created during the hackathon, first
commit 27 Oct 2026) is preserved in docs/STARTER_VALIDATION.md.
This file records the implementation and execution on the user's Mac.

- Initial starter: 42 pytest tests passed; TypeScript typecheck/build passed.
- Existing app exercised via actual HTTP: fixture W0 REJECTED, W1 VERIFIED,
  both zero Meta calls and excluded from model metrics. Original traces retained.
- Final full pytest run: 104 passed, one dependency deprecation warning.
- npm typecheck and build passed; actual HTTPS Playwright desktop 1440×1100 and
  mobile 390×844 passed login, trace, patch, evidence, evaluation and modal checks;
  no page errors or horizontal page overflow.
- Real Docker tests inspect no network/host mounts/socket/credentials, read-only
  root, non-root execution and resource limits. Additional tests demonstrate that
  model tests cannot overwrite source or rename the protected snapshot.
- All four registered cases passed actual Chromium acceptance, intended assertion
  failure before repair and passing reference behavior before paid inference.
- Eight independent Meta runs, fixed source/video/configuration and counterbalanced
  W0/W1 order. No paid automatic retry and no fixture fallback.

| Public case | W0 | W1 |
|---|---|---|
| VanJS 389 | VERIFIED | VERIFIED |
| VanJS 401 | VERIFIED | VERIFIED |
| VanJS 411 | Abstained at 25 turns | Abstained at 25 turns |
| VanJS 464 | Abstained at 25 turns | Abstained at 25 turns |

Abstentions are stored as REJECTED with reason `turn_limit`; they were never
submitted to the independent evaluator. They are not counted as evaluated passes,
regression-free results or successful repairs. No superiority of W1 was observed.

Metered Meta usage: **USD 3.332222** total; largest run **USD 0.864264**.
All reservations settled, zero UNKNOWN. The export independently recomputes
per-response costs (including actual cached tokens, reasoning counted once) and
matches the persistent ledger exactly. These are usage-based costs at the verified
Meta rates, not an independently checked account invoice or cash balance.
Pricing source: https://dev.meta.ai/docs/pricing-rate-limits (checked 27 Oct 2026).

First actual repair: run `909bd13d4455456ea81635153cd91dab`, VanJS 389 W0.
17 Meta calls, USD 0.194311. The candidate passes frozen reproduction, public
regressions and operator-authored independent checks in separate fresh containers.
The exported patch reconstructs the exact candidate hash. Raw usage IDs, frozen
hash, patch, video and screenshots are included in docs/evidence/.

The HTTPS deployment returned health 200, unauthenticated API 401 and authenticated
API 200. It reports eight live runs, four paired cases and four accepted live
case manifests. Fixtures remain separate. No upstream/production change or merge.

Limitations: four related historical cases, limited private assertions (not
maintainer tests), possible training familiarity, strict patch-application errors,
no statistical superiority claim, no hostile multi-tenant validation, temporary
Mac-dependent deployment. Public repository visibility/submission has not changed.

## Extension — 2 November 2026 (Linux build box, Docker 27.5.1)

Three more real VanJS bugs, built from upstream fixes and accepted by the same signed
case gate (independent checks fail on the pre-fix tree, pass on the upstream fix,
browser smoke passes). Bug videos were recorded by us on the pre-fix code
(`independently_recorded_reproduction`). Independent checks were adapted by us from
the tests the maintainers added in each fix commit; they were not run by the maintainers.

| Case (upstream fix) | W0 | W1 |
|---|---|---|
| vanx-compact-063 (c9f2dd4) | VERIFIED | VERIFIED |
| van-setter-161-v2 (52a3696) | REJECTED: model said "Fixed"; frozen repro + public PASS; independent FAIL | same |
| vanx-truncate-915 (915f0e2, committed 1 Nov 2026) | REJECTED: no candidate | REJECTED: no candidate |

The SVG-link patches keyed the setter cache by namespace, which fixes the symptom in
the video, but missed the same cache bug for custom elements, which the upstream test
covers. Two earlier runs on `van-setter-161` are **excluded**: our public test expected
`color: red` but the browser serializes `color: red;`, so it failed even on the upstream
fix. We fixed the test (`van-setter-161-v2`, re-accepted) and re-ran both methods.

Metered Meta usage: USD 1.020792 for the 6 counted runs, USD 1.367675 for all 8;
143 calls, each in `docs/evidence/extension-2026-11-02/spend-log-per-call.csv`, recomputed
from recorded usage and matching the ledger exactly. Hard cap for this session:
USD 8 batch / USD 3 per run, enforced by the ledger. Not an invoice; the account
balance could not be read through the API.

### Extension batches 2 and 3 — 2 November 2026, evening (same box, same caps)

Three more real VanJS bugs, built and accepted the same way (signed case gate; bug videos
recorded by us on the pre-fix code; independent checks adapted from the upstream tests).

| Case (upstream fix) | W0 | W1 |
|---|---|---|
| vanx-replace-c93 (c93a153, committed 31 Oct 2026) | REJECTED: no candidate (ended after a truncated turn) | REJECTED: model said "Fixed"; frozen repro + public PASS; independent FAIL |
| vanx-funcfield-5d9 (5d97cff) | REJECTED: model said "Fixed"; frozen repro + public PASS; independent FAIL | VERIFIED |
| vanx-raw-356 (17d5ce5) | VERIFIED | VERIFIED |

What the independent checks caught: the `vanx-replace-c93` W1 patch sorts correctly but still
overwrites a reused object when a new item is inserted before it (expected `C,B`, got `C,C`);
the `vanx-funcfield-5d9` W0 patch handles direct assignment of a function field but not
`vanX.replace` (expected `ghi`, got `def`). Metered Meta usage for these 6 runs: USD 1.106210,
100 calls (in the same per-call log). Ledger total for 2 Nov: USD 2.473885, 243 calls,
14 runs (12 counted), under the USD 8 batch cap.

### Combined (27 Oct pilot + 2 Nov extension, counted runs only)

- **5 of 10 real bugs verified fixed** (VanJS 389, 401, vanx-compact-063, vanx-funcfield-5d9,
  vanx-raw-356) in **20 counted real Meta runs**.
- **4 times the model said "Fixed" with an incomplete patch**; all 4 failed an independent
  check and were stored as REJECTED. **No VERIFIED verdict has any failed check.**
- 7 runs ended without a candidate (stored as REJECTED, never as fixes).
- W1 verified 5 bugs and W0 verified 4. That is one bug on ten cases: not evidence of superiority.
- Metered Meta usage for counted runs: USD 5.459224 (pilot 3.332222 + extension 2.127002).
- Re-check offline: `python3 scripts/verify_evidence.py`.

### Blind open-weight review (2 Nov 2026)

Muse Spark Open (Meta open weights, via Baseten) reviewed the 10 exported final patches
**without** the independent verdict. It recommended *accept* for all 10, including the 4 that
the executed checks rejected. Details: `docs/evidence/auditor-blind-2026-11-02/`.
10 calls, about USD 0.08 at list price (estimate).

### Test suite, 2 November 2026 (Linux build box, Docker 27.5.1)

Clean checkout of the public repository plus the 2 Nov scripts: **121 passed**, including the
8 real-Docker sandbox tests (run with sudo for Docker socket access on this box).

## Hosted CI pending

GitHub Actions did not start any job step because of an account-level billing / spending-limit restriction reported by GitHub. No hosted test result is claimed. No payment, quota increase or paid runner was configured. The local 104-test suite and real HTTPS checks above were executed successfully.
