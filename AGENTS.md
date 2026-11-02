# ReproPatch — instructions for coding agents

## Goal
Build and ship the approved ReproPatch MVP. Do not restart project selection.
Read README.md, CODEX_TASK.md and docs/ARCHITECTURE.md first.

## Truth and scope
- The user reported a successful $0.014 Meta smoke test using muse-wonder-1.0.
  Do not ask them to repeat the same access question or paste their key in chat.
- Use Meta Model API online. Codex may develop the product. Do not replace the
  product's inference with OpenAI/Anthropic silently.
- Local model downloads, health workflows, farm material and other projects are
  out of scope. No billing/subscription SaaS, team management or marketing site.
- UI copy is English for the hackathon. Operator handoff/report is Portuguese.
- FIXTURE is not LIVE. Every fixture screen/artifact must remain explicitly labeled.
- No invented case URLs, model metrics, sales claims, winner probabilities or
  assertions that a simulation is production validation.
- Tests in this package are infrastructure tests, not real-model evaluations.

## Budget
- Approval in this conversation is for implementing this project and the
  previously scoped pilot: maximum $24 incremental Meta usage, $3 per model run.
- Do not spend above that, rely on cache discounts, or auto-retry uncertain bills.
- The adapter must reserve before sending, settle actual usage, count reasoning
  inside output_tokens only once, and stop on an accounting mismatch.
- No hosted web-search/subagent tools in the budgeted MVP: each actual model
  iteration must remain visible to our ledger.
- No new paid hosting subscription, paid dataset or domain purchase without
  explicit approval. Free/local deployment can proceed.

## Security invariants
- Never execute uploaded repositories or model-written code directly on the host.
- Never mount the Docker socket, Meta key, operator token, home directory or
  maintainer tests into an agent workspace.
- Work from a detached allowed commit WITHOUT later git history or reference PR.
- Network deny by default; public browser targets require a reviewed allowlist.
- W1 source writes require a confirmed correct assertion failure and a frozen test.
- A syntax error, timeout, missing module or broken browser is NOT reproduction.
- The frozen test is checked externally; a test file inside a writable repo alone
  is not sufficient enforcement.
- Hidden evaluator runs only after candidate finalization; no results flow back.
- Read-only tests do not alone prove independence: isolate evaluator process and
  verify fail-before / pass-reference before accepting a real benchmark case.
- Deny .env/.git/hidden/oracle paths, traversal, symlinks, oversized files and
  unreviewed commands. Do not send raw secrets or hidden reasoning to the UI.
- No auto-merge, no production writes, no unrequested external messages.

## Implementation quality
- Keep one API + one worker and SQLite WAL for the MVP. Do not add five services.
- Preserve the TypeScript UI and its visual design unless a concrete need arises.
- Respect the API contracts; add tests for modifications.
- Prefer reviewed stdlib / existing dependencies over new frameworks.
- Persist events, test hashes, candidate hashes, status, usage and error reasons.
- Finish statuses distinguish VERIFIED, REJECTED, NOT_REPRODUCED, BLOCKED,
  BUDGET_EXCEEDED, CANCELLED and ERROR. Never catch an error and mark VERIFIED.
- W0 is a competent baseline with the same model, tools, context and spending cap.
- Preserve unsuccessful attempts. Four cases are a feasibility pilot, not proof
  of statistical superiority.

## Git / release
- Confirm gh auth identity; do not infer the account from older projects.
- Default new repo private until explicit public release after security review.
- Keep secrets, uploads, hidden evaluations and runtime artifacts out of Git.
- Make honest commits as work progresses. Never backdate or fabricate history.
- Public hackathon code must include original contribution / prior-work disclosure.
- Do not modify other repositories or load unrelated personal files.

## Required verification
python -m pytest -q
npm run typecheck
npm run build
Inspect desktop and mobile with Playwright.
Then test live only in the verified sandbox and within the approved budget.

Final handoff: URLs actually created, commit SHA, test counts, actual model spend,
what is LIVE vs FIXTURE, measured results, remaining blockers. No future promises.
