# ReproPatch replay page (static)

**Replay of a recorded run.** This page calls no model and executes no code. It loads the
evidence recorded on 27 Oct 2026 (`data/`, copied unchanged from `docs/evidence/`) and replays
run `909bd13d` (Meta `muse-wonder-1.0`, VanJS 389) plus the 8-run pilot table.

Run offline: `python3 -m http.server 8799` in this folder, then open http://127.0.0.1:8799/.
Host anywhere static (GitHub Pages from `docs/replay/`, Vercel static, Netlify). No build step,
no secrets, no API keys.

**Update 2 Nov 2026:** also loads `data/extension-results.json` (3 more real VanJS bugs, 8 real Meta runs, 6 counted)
and shows two terminal recordings of live runs (`data/live-run-*.mp4`, idle gaps over 1.5 s compressed). Still no model calls on this page.
