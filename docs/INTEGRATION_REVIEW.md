# Codex independent review and exercised corrections

Reviewed base 9c80340...9bbfb1c (committed/untracked diff), not unrelated repos.
Objections in the executor handoff (resolved on main, not an approval stamp):
- blocker, gateway.py:181: a model-written Node repro ran in the mutable agent
  workspace and could edit sources before W1 freeze. Moved it to fresh containers
  with root-owned read-only files; actual Docker tests reject write and rename.
- major, sandbox_runtime/dispatch.mjs:46: ESM import ignored NODE_PATH and actual
  Chromium acceptance failed. Fixed createRequire and initial navigation;
  all four real cases then passed browser smoke.
- major, opscli.py:42: any baseline nonzero was accepted. Require classified
  ASSERTION_FAILED, never syntax/setup/timeout; reference must classify PASS.
- major, recovery: a crashed RESERVED request needed UNKNOWN+halt before new
  calls. Added exclusive-worker recovery and tests; API also honors ledger halt.
Also reconciled actual usage, added real-run UI states and guarded missing fields.
Final infrastructure: 104 pytest pass, tsc/build pass, HTTP desktop/mobile pass.
Eight real Meta attempts: 4 VERIFIED, 4 abstentions; USD 3.332222 reconciled.
No model reruns, public release, production changes or upstream merge.
