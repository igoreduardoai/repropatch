# Reviewed case registry and live gate

Only cases registered here can run live. The API, UI and worker accept a `case_id`
and a previously uploaded video; they never accept URLs, host paths or commands.
No real case is registered in this repository: `REPROPATCH_CASES_DIR` (default
`<data_dir>/cases`, outside Git) starts empty and live stays blocked.

## Directory layout (one directory per case; `case_id` = `[a-z0-9-]{3,63}` = dir name)
```
<case_id>/manifest.json        reviewed manifest, schema_version 2 (template: evaluation/case-manifest.template.json)
<case_id>/snapshot/            sanitized tree at base_commit: no .git, no history, no solution, no symlinks
<case_id>/private/reference/   full tree WITH the reference fix (harness only: test sensitivity + acceptance)
<case_id>/private/evaluator/   maintainer tests (copied to profile.evaluator.dest in fresh evaluator containers only)
<case_id>/acceptance.json      signed evidence written by `opscli accept`
```
`snapshot` is the only tree an agent container ever receives. `private/*` never enters the agent container.

## manifest.json fields
`case_id,title,repository_url(https),license,base_commit(40-hex),video_origin(original_issue|independently_recorded_reproduction),
video_sha256,expected_behavior,sandbox_image_id(sha256:… image ID),editable_paths(dir prefixes ending "/"),
protocol_version,methods=["W0","W1"],model="muse-wonder-1.0",profile`. `TBD`/placeholders are rejected.

`profile` (all commands are argv lists run with no shell, cwd `/workspace/repo`, never model-chosen):
- `repro.path` – the ONE test file the agent may write (e.g. `tests/repro.spec.js`); `repro.argv` runs it.
- `public_regressions.argv` – optional; public tests already inside `snapshot`.
- `serve.argv/url/ready_timeout_s` – starts the app inside the sandbox; `url` must be loopback `http://127.0.0.1:PORT/`. Required for acceptance (browser smoke).
- `evaluator.dest/argv` – maintainer tests are placed under `dest/`; exit 0 = pass.
- `failure_pattern` – regex the expected assertion failure output must match (e.g. `expect\(.*toHaveText`). Output containing infra markers (SyntaxError, Cannot find module, browser launch, net::ERR, `Test timeout of`, `page.goto: …`, …) or a process timeout is never a valid reproduction, even if the pattern matches.

## Sandbox image contract (built by the operator, no Meta key inside)
Debian/Ubuntu-based, contains: `node`, `tar`, `mkdir`, Playwright + Chromium, and the case's JS deps (e.g. `/opt/deps/node_modules`, `NODE_PATH` and `PATH` set in the image `ENV`; `playwright` importable via `NODE_PATH`). Runs as uid 65534 with read-only rootfs and tmpfs `/workspace`, `/tmp` and `HOME=/tmp/home`. Chromium is launched with `--no-sandbox` (the container is the boundary). Reference it by immutable image ID (`docker image inspect --format '{{.Id}}'`), not by tag. Docker bridges/`--network none` only; the Docker socket is never mounted.

## Acceptance (live stays blocked until it exists and matches current bytes)
`REPROPATCH_ACCEPTANCE_KEY=<≥16 chars> python -m repropatch.opscli accept --case ID` runs, in fresh containers, the maintainer tests on `snapshot` (must fail) and on `reference` (must pass), plus a browser smoke (serve + Chromium screenshot). It writes `acceptance.json` signed with HMAC-SHA256 over: manifest, snapshot, reference and evaluator tree hashes, image ID and results. Any later byte change, wrong key or image drift ⇒ not accepted. `GET /api/config` reports `live_enabled` only when `REPROPATCH_ENABLE_LIVE=true` AND an accepted case exists; `POST /api/runs mode=live` returns 409/400 otherwise, and the worker re-checks everything (including the uploaded video hash equal to `video_sha256`) before the first model call.

## Operator CLI (P0, independent of the API flag)
`python -m repropatch.opscli cases | accept --case ID | sweep | run --case ID --method W0|W1 --video PATH --approve-paid-run`.
`run` needs acceptance, `META_MODEL_API_KEY` in the operator environment and the explicit flag; it holds the worker lock; the ledger enforces $3/run and $24 total. Everything it does is recorded as a normal run (events, hashes, usage).

## Protocol facts enforced in code
Agent container: no network, no mounts, read-only rootfs, tmpfs workspace, caps dropped, `docker cp`-free tar streams, fixed dispatcher. Reproduction freeze = fresh baseline container fails with `failure_pattern` AND fresh reference container passes, then bytes hashed to `data/frozen/<run>/` (outside any workspace). W1 `write_source/apply_patch` need that freeze. `submit_candidate` extracts the editable-tree diff host-side and ends all tools. The evaluator (frozen test + public + maintainer tests) runs once, each in its own fresh container, and results are never returned to the model. `operator_interventions` is recorded as 0: automatic confirmation only, no operator review step exists yet.

## Known limits
Docker is not multi-tenant isolation; use a dedicated worker host. Playwright/Chromium paths are covered by code review and the dispatcher syntax check only until a real image is accepted. Screenshots are stored as evidence; only text snapshots are returned to the model. Cancel is cooperative (between tool calls/model calls); a running sandbox command ends at its timeout.
