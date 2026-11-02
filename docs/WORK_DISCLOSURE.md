# Work and evidence disclosure

**Everything in this repository was built during the hackathon.** The event
window is 26 Oct - 4 Nov 2026; the Git history starts on 27 Oct 2026 (first
commit 14:37 CT). No code written before 26 Oct 2026 is included, and no older
history was imported.

- **Starter build kit (commits 57d775c, 61c7de9):** the TypeScript workbench
  design, FastAPI API, SQLite queue, accounting adapter, scripted pagination
  FIXTURE, its 42 tests and deployment templates. It was generated during the
  event, in a brainstorming session with an AI assistant, and imported as the
  first commits. It is labeled "starter" only because it was the first step of
  this build, not because it existed before the event.
- **Built on top of it, from 27 Oct 2026:** the live Meta engine (Responses loop,
  Files video upload, token counting), the Docker sandbox gateway and its tools,
  the browser image, the reviewed case registry, the frozen-test protocol, the
  independent evaluator, the spend ledger, the 8-run VanJS pilot with evidence,
  and the advisory auditor (`repropatch/auditor.py`).
- **Third-party components** (VanJS as pilot target, MIT; Playwright/Chromium;
  TypeScript; FastAPI and other Python packages; Node.js) are open-source
  dependencies listed in NOTICE. They are not claimed as our work.
- Commit dates are not modified. Commit authorship was normalized to the public
  account before publication.

Codex develops/reviews and a local Claude Code executor implements bounded
tasks. The runtime repair model is Meta Wonder. No coding assistant's output is
represented as a paid Meta repair result.

The advisory auditor was added on 27 October 2026, after the pilot. Its model is
Meta's open-weight Muse Spark Open served by Baseten (credits granted to the
author). Its opinions are not part of the pilot metrics and never change a
verdict. The negative-control patch in `docs/evidence/auditor/` is hand-written
by the operator, not produced by any model run.

Fixtures remain labeled FIXTURE, make zero model calls, and never enter the
live pilot. Public VanJS bug recordings are independently recorded reproductions,
not videos authored by the original maintainers. Independent assertions authored
for this pilot are not described as maintainer-authored tests.

This repository is preparation for submission. Public release and competition
submission are separate from deployment. No auto-merge or changes to upstream
projects or production are authorized by the repair workflow.
