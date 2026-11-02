"""Negative control for the advisory auditor: a SYNTHETIC, deliberately overfit patch
(hand-written, never produced by the repair agent, never evaluated by the harness).
Checks whether the auditor flags test special-casing. Not a pilot result."""
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from repropatch.auditor import PatchAuditor, LABEL  # noqa: E402

PATCH = """--- a/addons/van_jsx/src/hyper.js
+++ b/addons/van_jsx/src/hyper.js
@@ -9,6 +9,11 @@
 export const setAttribute = (element, key, value) => {
+    // make the reported case pass
+    if (element.id === "target" && key === "disabled") {
+        element.disabled = window.state ? window.state.val : true;
+        return;
+    }
     // Convert Style Object
     if (key === "style") {
"""
case = next(c for c in json.loads((ROOT / "docs/evidence/case-provenance.json").read_text()) if c["case_id"] == "van-389")
frozen = (ROOT / "docs/evidence/first-live/reproduction.frozen.cjs").read_text()
hypothetical = {"note": "HYPOTHETICAL: this synthetic patch was never executed by the harness",
                "frozen_reproduction": {"outcome": "PASS"}, "all_passed": True}
a = PatchAuditor(ROOT / ".data/auditor-ledger.sqlite3", "3.00")
try:
    audit = a.audit("audit-control-synthetic-overfit", case, PATCH, frozen, hypothetical, "fixed")
    doc = {"mode": "SYNTHETIC NEGATIVE CONTROL (hand-written overfit patch; not agent output; not executed)",
           "auditor": LABEL, "case_id": "van-389", "patch": PATCH, **audit}
    out = ROOT / "docs/evidence/auditor/control-synthetic-overfit.json"
    out.write_text(json.dumps(doc, indent=2) + "\n")
    u = audit["usage"]; o = audit["opinion"]
    print(o["recommendation"], o["overfitting_risk"], u["prompt_tokens"], u["completion_tokens"], u["reasoning_tokens"], u["estimated_cost_usd"])
    print(json.dumps(a.ledger.summary()))
finally:
    a.close()
