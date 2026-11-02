# Blind open-weight review (2 Nov 2026)

Question: if a second model reviews the patch, without the hidden checks, would it catch
the incomplete fixes that the executed independent checks caught?

- Reviewer: Meta's open-weight **Muse Spark Open** (`meta-models/muse-spark-open-1026`) via
  Baseten's OpenAI-compatible API, same advisory auditor code as `repropatch/auditor.py`.
- Input per patch: bug title and expected behavior, the final patch, the frozen reproduction
  test, the agent's claim, and only the results the agent itself saw (frozen reproduction and
  public regressions). The independent verdict was **withheld**.
- Patches: the 10 final patches whose artifacts are exported in this repository (pilot run
  909bd13d plus every counted 2 Nov run with a candidate). Hashes were checked against the
  recorded results before each call. Script: `scripts/audit_blind.py`.

| Harness verdict (executed checks) | Reviewer said accept | Reviewer said review |
|---|---|---|
| VERIFIED (6 patches) | 6 | 0 |
| REJECTED after the model said "Fixed" (4 patches) | 4 | 0 |

The executed hidden checks caught 4 of 4 incomplete patches. The blind reviewer caught 0 of 4
and rated all ten "low" overfitting risk. Two examples of what the hidden checks found:
`vanx-replace-c93` W1 sorted correctly but still overwrote a reused object when a new item was
inserted before it (expected `C,B`, got `C,C`); `vanx-funcfield-5d9` W0 fixed direct assignment
of a function field but not `vanX.replace` (expected `ghi`, got `def`).

Cost: 10 calls, USD 0.083631 at Baseten list price (estimate, separate ledger, not an invoice;
Baseten partner credits, no Meta API credit). Per-patch outputs are in this folder; totals in
`summary.json`.

Limits: 10 patches from one library; one reviewer model and one prompt; the reviewer may do
better with more context or tools. This result says a second model's opinion did not replace
executed checks here; it does not say the reviewer is useless. It is advisory and never changes
a verdict.
