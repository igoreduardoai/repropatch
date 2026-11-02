# Advisory auditor evidence

Model: `meta-models/muse-spark-open-1026` (Meta open weights) via Baseten's
OpenAI-compatible API. Label in events/ledger: `baseten:muse-spark-open-1026`.

| File | Input | Recommendation | Overfitting risk | Tokens in/out (reasoning) |
|---|---|---|---|---|
| `van-389-W0.json` | Real recorded patch, frozen test and evaluator result of run 909bd13d (hashes checked) | accept | low | 1367 / 1431 (1265) |
| `control-synthetic-overfit.json` | Hand-written overfit patch, never executed, labeled hypothetical | review | high | 813 / 1560 (1349) |

Cost: about US$0.015 for both calls at Baseten's public list price
(US$1.25 input, US$0.15 cached input, US$4.25 output per 1M tokens,
https://www.baseten.co/library/muse-spark-open/, checked 2026-10-27; listed for
`meta-models/muse-spark-open`, assumed identical for the dated slug). Estimate only,
not reconciled with a Baseten invoice. No Meta API credit was used.

Limits: advisory only; one open model; one real patch plus one easy planted control.
This shows the integration works, not that the auditor is accurate. The other three
VERIFIED patches are not exported in this repository and were not audited here.
