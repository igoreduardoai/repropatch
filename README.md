# ReproPatch
### Show the bug. Keep the proof.

> **At a glance**
> - **Judge in 2 minutes:** https://igoreduardoai.github.io/repropatch/ (scoreboard of every counted run, the bug videos, and in-browser playback of the live-run recordings; recorded evidence, no model calls)
> - **Result:** 8 of 14 real VanJS bugs verified fixed by Meta `muse-wonder-1.0` in 28 counted real runs. 4 times the model said "fixed" with an incomplete patch; the independent check caught all 4 (REJECTED), so 0 wrong "fixed" verdicts. The other 11 non-verified runs ended without a candidate and stay REJECTED. USD 7.14 metered.
> - **Why it matters:** a second model is not proof. Meta's open-weight Muse Spark Open, reviewing the same patches blind, accepted all 4 incomplete ones; only the executed hidden checks caught them ([docs/evidence/auditor-blind-2026-11-02/](docs/evidence/auditor-blind-2026-11-02/)).
> - **Live runs, recorded (2 Nov 2026):** [docs/evidence/extension-2026-11-02/live-runs/](docs/evidence/extension-2026-11-02/live-runs/) (terminal recordings of all 22 runs on 2 Nov)
> - **Demo video (≤3 min, narration: Igor's own voice, cloned with ElevenLabs):** https://youtu.be/r4RFmpX63TI (recorded before the last two batches, so it shows 3 of 7 bugs; the numbers above are current)
> - **Replay of a recorded run (no model calls):** [docs/replay/](docs/replay/) · hosted: https://igoreduardoai.github.io/repropatch/replay/
> - **Check it offline in 1 command (standard library, no keys, under a second):** `python3 scripts/verify_evidence.py` (recomputes hashes and tallies from [docs/evidence/](docs/evidence/))
> - **Validation and limits:** [VALIDATION.md](VALIDATION.md) · License: MIT

## Hackathon submission

**Meta Global AI Developer Hackathon (Cerebral Valley x Meta) · Indie track · solo (Igor Eduardo)**

- **What it does:** turns a bug video into a reproduction, freezes it as a hashed
  test outside the agent workspace, lets Meta `muse-wonder-1.0` patch the code
  through function tools in a Docker sandbox, then runs an independent evaluator
  once, in fresh containers, with checks the agent cannot read.
- **Meta tooling:** Meta Model API Responses with `muse-wonder-1.0`; the bug MP4 is
  uploaded to Meta Files and attached as `input_file`; an agentic loop of 11
  externally executed function tools (code, real Chromium browser, reproduction,
  freeze, patch, public regressions, submit); every request is token-counted with
  `/responses/input_tokens` and reserved in a spend ledger before it is sent.
- **Honest pilot result:** 8 real runs on 4 historical VanJS bugs (MIT). W0 and W1
  both VERIFIED VanJS 389 and 401; both abstained at the 25-turn limit on 411 and
  464 (kept as REJECTED, never counted as fixes). **No W1 superiority observed.**
  Metered Meta usage USD 3.332222 total, largest run USD 0.864264. Details:
  [VALIDATION.md](VALIDATION.md) and [docs/evidence/](docs/evidence/).
- **Extension, 2 Nov 2026 (10 more real bugs, 20 counted runs, 4 batches):** cases built from real
  VanJS fixes (upstream commits 915f0e2, 52a3696, c9f2dd4, c93a153, 5d97cff, 17d5ce5, fc3ee4c, acb8ba8,
  1c580f0, 84f30ae), bug videos recorded on the pre-fix code, independent checks adapted from each fix's
  upstream tests. Verified: vanX.compact (W0, W1), vanX.raw (W0, W1), property bindings after removal
  (W0, W1), function fields (W1), array length after pop (W1), reactive proxy crash (W0). Caught: 4 runs
  where the model said "Fixed" and its own reproduction and the public tests passed, but the independent
  check failed (SVG link W0 and W1, vanX.replace W1, function fields W0) → REJECTED. No candidate (25-turn
  cap or ended): VanX list truncation (W0, W1), vanX.replace W0, vanX.replace shorter array (W0, W1),
  array length after pop W0, reactive proxy crash W1. USD 3.812283 for the 20 counted runs; 2 more runs
  (USD 0.346883) are excluded because our own public test was wrong, then fixed and re-run. Every Meta
  call: [spend-log-per-call.csv](docs/evidence/extension-2026-11-02/spend-log-per-call.csv).
- **Open-weight advisory auditor:** after the verdict is final, Meta's open-weight
  **Muse Spark Open** (`meta-models/muse-spark-open-1026`, served by Baseten's
  OpenAI-compatible API) reads the patch, the frozen test and the evaluator result
  and writes a structured opinion: scope, overfitting risk, likely regressions,
  accept/review. It runs on a different provider and model than the repair agent,
  is opt-in (`REPROPATCH_ENABLE_AUDITOR=true` + `BASETEN_API_KEY`; no key means
  DISABLED, labeled), has its own US$3 ledger and **never changes VERIFIED/REJECTED**.
  Measured so far: 2 real calls on recorded artifacts, no new repair. On the real
  VanJS 389 W0 fix it said *accept* (low overfitting risk); on a hand-written,
  deliberately overfit control patch it said *review* (high risk). That is one real
  patch and one planted control: it shows the auditor works end to end, not that
  it is accurate. 5,171 tokens, about US$0.015 at Baseten list price (estimate, not
  invoice). See [docs/evidence/auditor/](docs/evidence/auditor/).
- **Blind review experiment (2 Nov):** the same open-weight auditor reviewed the 10 exported
  final patches with the independent verdict withheld. It said *accept* to all 10, including
  the 4 incomplete patches the hidden checks rejected (10 calls, ≈US$0.08). That is why
  ReproPatch decides on executed checks, not on a model's opinion.
  [docs/evidence/auditor-blind-2026-11-02/](docs/evidence/auditor-blind-2026-11-02/).
- **Demo video:** https://youtu.be/r4RFmpX63TI · **Replay page:** [docs/replay/](docs/replay/) ([hosted](https://igoreduardoai.github.io/repropatch/replay/)) (replay of recorded run 909bd13d; calls no model)
- **Runs locally** (Python, Node, Docker); there is no hosted live inference: the [judge page](https://igoreduardoai.github.io/repropatch/) and the replay show recorded runs. 121
  pytest tests: 104 passed on the Mac before the auditor (with Docker); on 2 Nov all
  121 passed on a clean checkout on the Linux build box, including the 8 real-Docker tests. Hosted CI is
  blocked by a GitHub account restriction (see below). See [Run locally](#run-locally).
- **Built during the hackathon only:** every line of ReproPatch was created during
  the event; Git history starts on 27 October 2026 and no pre-event code is
  included. That covers the starter build kit (workbench design, queue, scripted
  fixture, 42 tests), generated during the event with an AI assistant and imported
  as the first commit, and everything built on it: the live Meta engine, sandbox
  gateway, independent evaluator, ledger, pilot and advisory auditor. Only
  open-source dependencies (VanJS as pilot target, Playwright, FastAPI, TypeScript,
  etc.) and the Meta/Baseten APIs are external. MIT ([LICENSE](LICENSE),
  [NOTICE](NOTICE), [WORK_DISCLOSURE.md](docs/WORK_DISCLOSURE.md)).

An authenticated workbench for **video → reproduction → frozen test → patch →
independent evaluation**, using Meta `muse-wonder-1.0`. The original TypeScript
workbench is preserved. One FastAPI process, one separate worker, SQLite WAL.

## What actually runs

- The labeled pagination **FIXTURE** remains scripted, costs zero, and never
  enters model metrics. W0 is rejected; W1 passes its executed fixture checks.
- LIVE uses reviewed public-source snapshots, a real Chromium browser in Docker,
  Meta function calls and an independent evaluator in fresh containers after
  candidate finalization. There is no fixture fallback.
- Model-written tests run against root-owned, read-only sources in separate
  containers. W1 cannot edit source through tools until its reproduction fails
  for the expected assertion on baseline and passes against reference behavior.
- Sources, videos and manifests are hashed. The frozen test is stored outside
  every agent workspace. Final source snapshots and patches are hashed as well.
- The ledger reserves before sending, reconciles reported usage without counting
  reasoning twice, and halts on unknown billing (including interrupted requests).
  Limits are $3/run and $24/batch, across this persistent ledger only.

The real pilot uses four historical VanJS bugs (MIT), with independently recorded
videos and **operator-authored** private checks, not maintainer-authored tests.
Results and limitations are recorded in `docs/evidence/` when exported. A successful
run means only that its executed checks passed. Abstentions and failures remain
visible; a four-case pilot is not evidence of general superiority.

## Run locally

Python 3.11+, Node.js 22+, and Docker for LIVE execution:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e '.[dev]'
npm ci
npm run build
.venv/bin/python scripts/setup.py
bash scripts/start_local.sh
```

Open `http://127.0.0.1:8000`. Sign in with the operator token generated by setup.
The Meta credential belongs in the private `.env` (`META_MODEL_API_KEY`); never in
web assets, target containers, Git or chat. Setup preserves an existing `.env`.

## Reviewed LIVE cases

Build the reviewed browser image before accepting a case:

```bash
docker build -t repropatch-browser:pilot-v4 deploy/sandbox
```

Cases live in `.data/cases/` (excluded from Git). See
[CASE_REGISTRY.md](docs/CASE_REGISTRY.md) for the manifest and snapshot contract.
Reference trees and independent tests must stay outside agent snapshots. No
arbitrary repository URL, shell command or host path is accepted from the UI.

```bash
.venv/bin/python -m repropatch.opscli cases
.venv/bin/python -m repropatch.opscli accept --case CASE_ID
# Stop the ordinary worker first; the CLI holds its exclusive lock.
.venv/bin/python -m repropatch.opscli run --case CASE_ID --method W1 \
  --video /absolute/path/reproduction.mp4 --approve-paid-run
```

Accepting a case executes the baseline/reference checks and actual Chromium.
Public LIVE remains disabled until the operator has exercised the complete
model path and sets `REPROPATCH_ENABLE_LIVE=true`. Signed case acceptance and the
spend ledger are checked again on every run. Unknown billing blocks new calls.

## Verification

```bash
.venv/bin/python -m pytest -q
npm run typecheck
npm run build
.venv/bin/python scripts/check_ui_http.py
.venv/bin/python scripts/check_secrets.py --history
```

`test_docker_live.py` executes real containers when the local test image
`node:22-bookworm-slim` exists. Infrastructure tests are not model effectiveness
results. [VALIDATION.md](VALIDATION.md) distinguishes them from the real pilot.

## Deployment and release

The authenticated deployment uses this Mac's persistent SQLite/files and a free,
temporary HTTPS tunnel. It requires the Mac and local processes online; it is
not permanent hosted infrastructure. See [DEPLOY.md](docs/DEPLOY.md).

The repository is public for the hackathon submission. Secret, license and
work-disclosure reviews were run before publication; no upstream merge is automatic.
See [WORK_DISCLOSURE.md](docs/WORK_DISCLOSURE.md), LICENSE and NOTICE. The starter
build kit (created during the hackathon) and its original validation are preserved
in Git and [STARTER_VALIDATION.md](docs/STARTER_VALIDATION.md).
