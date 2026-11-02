"""Persisted, conservative request reservations, in integer micro-dollars.

Reserve full uncached counted input + max output before inference. Unknown
billing after a timeout keeps the reservation charged; never silently retry.
A pricing/usage mismatch HALTS future calls, not a promise to override billing.
"""
from decimal import Decimal
from pathlib import Path
from .store import Store, now

class BudgetExceeded(RuntimeError): pass
class UsageMismatch(RuntimeError): pass

def usd_to_micro(value) -> int:
    return int(Decimal(str(value))*1_000_000)

def micro_to_usd(value: int) -> float:
    return float(Decimal(value)/1_000_000)

class Budget:
    def __init__(self, db: Path, batch_cap="24.00", run_cap="3.00"):
        self.store=Store(db)
        self.batch_cap=usd_to_micro(batch_cap)
        self.run_cap=usd_to_micro(run_cap)
        with self.store.connection() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS spend(
              id TEXT PRIMARY KEY, run_id TEXT NOT NULL, reserved INTEGER NOT NULL,
              charged INTEGER NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS budget_flags(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            """)

    def reserve(self, request_id: str, run_id: str, input_tokens: int, max_output: int,
                input_rate=Decimal("4"), output_rate=Decimal("20")):
        if input_tokens<0 or max_output<=0: raise ValueError("Invalid token limits")
        amount=int((Decimal(input_tokens)*input_rate+Decimal(max_output)*output_rate).to_integral_value(rounding="ROUND_CEILING"))
        with self.store.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            if c.execute("SELECT 1 FROM budget_flags WHERE key='halted'").fetchone():
                raise BudgetExceeded("Ledger halted after unknown/mismatched usage")
            if c.execute("SELECT 1 FROM spend WHERE id=?",(request_id,)).fetchone():
                raise ValueError("Request already reserved; do not send twice")
            total=c.execute("SELECT COALESCE(SUM(charged),0) FROM spend").fetchone()[0]
            used=c.execute("SELECT COALESCE(SUM(charged),0) FROM spend WHERE run_id=?",(run_id,)).fetchone()[0]
            if total+amount>self.batch_cap or used+amount>self.run_cap:
                raise BudgetExceeded("Call reservation exceeds run or batch budget")
            c.execute("INSERT INTO spend VALUES(?,?,?,?,?,?)",(request_id,run_id,amount,amount,"RESERVED",now()))
        return amount

    def settle(self, request_id: str, input_tokens: int, output_tokens: int, cached_tokens=0,
               input_rate=Decimal("4"), output_rate=Decimal("20"), cache_rate=Decimal("0.20")):
        if not 0<=cached_tokens<=input_tokens or output_tokens<0:
            self.halt("invalid_usage");raise UsageMismatch("Invalid usage counters")
        amount=int((Decimal(input_tokens-cached_tokens)*input_rate+Decimal(cached_tokens)*cache_rate+Decimal(output_tokens)*output_rate).to_integral_value(rounding="ROUND_CEILING"))
        exceeded=False
        with self.store.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            row=c.execute("SELECT * FROM spend WHERE id=?",(request_id,)).fetchone()
            if not row or row["state"]!="RESERVED": raise ValueError("No unsettled reservation")
            exceeded=amount>row["reserved"]
            c.execute("UPDATE spend SET charged=?,state='SETTLED' WHERE id=?",(amount,request_id))
            if exceeded:c.execute("INSERT OR REPLACE INTO budget_flags VALUES('halted','usage_exceeded_reservation')")
        if exceeded:raise UsageMismatch("Actual usage exceeded reservation; stop and reconcile billing")
        return amount

    def halt(self, reason: str):
        with self.store.connection() as c:
            c.execute("INSERT OR REPLACE INTO budget_flags VALUES('halted',?)",(reason,))

    def unknown(self, request_id: str):
        with self.store.connection() as c:
            c.execute("UPDATE spend SET state='UNKNOWN' WHERE id=? AND state='RESERVED'",(request_id,))
            c.execute("INSERT OR REPLACE INTO budget_flags VALUES('halted','request_billing_unknown')")

    def recover_inflight(self):
        """Call only while holding the exclusive worker lock, after a restart."""
        with self.store.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            count=c.execute("SELECT COUNT(*) FROM spend WHERE state='RESERVED'").fetchone()[0]
            if count:
                c.execute("UPDATE spend SET state='UNKNOWN' WHERE state='RESERVED'")
                c.execute("INSERT OR REPLACE INTO budget_flags VALUES('halted','interrupted_request_billing_unknown')")
        return count

    def run_spend(self, run_id: str):
        with self.store.connection() as c:
            r=c.execute("SELECT COALESCE(SUM(charged),0) committed,COALESCE(SUM(CASE WHEN state='SETTLED' THEN charged ELSE 0 END),0) settled,"
                        "COUNT(*) calls,COALESCE(SUM(state='UNKNOWN'),0) unknown FROM spend WHERE run_id=?",(run_id,)).fetchone()
        return {"committed_usd":micro_to_usd(r["committed"]),"settled_usd":micro_to_usd(r["settled"]),
                "model_calls":r["calls"],"unknown_calls":r["unknown"]}

    def summary(self):
        with self.store.connection() as c:
            row=c.execute("SELECT COALESCE(SUM(charged),0) total,COALESCE(SUM(CASE WHEN state='SETTLED' THEN charged ELSE 0 END),0) settled FROM spend").fetchone()
            halted=c.execute("SELECT value FROM budget_flags WHERE key='halted'").fetchone()
        return {"cap_usd":micro_to_usd(self.batch_cap),"committed_usd":micro_to_usd(row["total"]),
                "settled_usd":micro_to_usd(row["settled"]),"halted":halted[0] if halted else None,
                "scope":"This ledger only; it does not include other API clients or account charges."}
