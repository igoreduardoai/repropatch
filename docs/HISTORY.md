# Repository history note

This public repository is a fresh, single-commit export of ReproPatch's private
development repository. All work was done during the Meta Global AI Developer
Hackathon (26 Oct to 4 Nov 2026). The private history has 15 commits, all dated
27 Oct 2026 (US Central time), listed below for reference. The full history can be
shown to the organizers on request.

The export adds, on top of the last private commit (`e377d65`), work also done during
the event window (2 Nov 2026): `scripts/verify_evidence.py` (offline re-check of the
recorded evidence), `scripts/demo_offline.sh`, the static replay page in
`docs/replay/` (a replay of a recorded run; it calls no model), this note and the
"At a glance" block in the README, and the 2 Nov 2026 extension (3 more real VanJS bugs, 8 real Meta runs, 6 counted) in `docs/evidence/extension-2026-11-02/`. No result recorded on 27 Oct was changed.

| private commit | date (CDT) | message |
|---|---|---|
| `57d775c` | 2026-10-27 14:37 | Initialize ReproPatch MVP and evidence-first harness |
| `61c7de9` | 2026-10-27 14:37 | Preserve starter tests and resolved frontend dependency lock |
| `368b516` | 2026-10-27 14:42 | Document provenance and license; scan Meta credentials and Git history |
| `ca23546` | 2026-10-27 14:46 | Add pinned sandbox browser build and reviewed test profile commands |
| `3dfed0f` | 2026-10-27 14:47 | Make browser test profile independent of dispatcher environment |
| `2671fe4` | 2026-10-27 14:50 | Preserve workbench design while rendering live attempts and approved cases |
| `ac5ede1` | 2026-10-27 14:52 | Add reviewed case registry, Docker sandbox gateway, live runner and independent evaluator |
| `f4de16c` | 2026-10-27 14:56 | Verify real Chromium and isolate model tests from mutable source workspaces |
| `e255ebb` | 2026-10-27 15:16 | Complete authenticated MVP and record the real eight-run Meta pilot |
| `073211e` | 2026-10-27 15:17 | Include sanitized output of the first independent evaluation |
| `b81905c` | 2026-10-27 15:19 | Disclose account-level hosted CI blocker without claiming remote test success |
| `295c822` | 2026-10-27 15:50 | docs: use a generic data path in the deploy notes |
| `d4cab76` | 2026-10-27 16:26 | docs: add hackathon submission summary to README |
| `f5ea7c6` | 2026-10-27 16:54 | Add advisory patch auditor on Meta's open-weight Muse Spark Open (Baseten) |
| `e377d65` | 2026-10-27 17:04 | Disclose that all work, including the starter kit, was built during the hackathon |
