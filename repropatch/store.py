"""SQLite WAL queue and audit trail; one worker for this MVP.

A claim is atomic. Crashed runs become ERROR, never VERIFIED. There is no
implicit replay of a possibly billed request after worker restart.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
import uuid
from .models import Stage, TERMINAL

def now():
    return datetime.now(timezone.utc).isoformat()

ALLOWED = {
    "QUEUED": {"PREFLIGHT", "CANCELLED"},
    "PREFLIGHT": {"REPRODUCING", "BLOCKED", "ERROR", "CANCELLED"},
    "REPRODUCING": {"FROZEN", "PATCHING", "NOT_REPRODUCED", "REJECTED", "BLOCKED", "BUDGET_EXCEEDED", "ERROR", "CANCELLED"},
    "FROZEN": {"PATCHING", "REJECTED", "BLOCKED", "BUDGET_EXCEEDED", "ERROR", "CANCELLED"},
    "PATCHING": {"VERIFYING", "REJECTED", "BLOCKED", "BUDGET_EXCEEDED", "ERROR", "CANCELLED"},
    "VERIFYING": {"VERIFIED", "REJECTED", "ERROR", "CANCELLED"},
}

class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript("""
            CREATE TABLE IF NOT EXISTS runs(
              id TEXT PRIMARY KEY, title TEXT NOT NULL, case_id TEXT NOT NULL,
              method TEXT NOT NULL, mode TEXT NOT NULL, status TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              payload TEXT NOT NULL, result TEXT, idempotency_key TEXT UNIQUE,
              cancel_requested INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
              at TEXT NOT NULL, stage TEXT NOT NULL, kind TEXT NOT NULL,
              message TEXT NOT NULL, data TEXT NOT NULL,
              FOREIGN KEY(run_id) REFERENCES runs(id)
            );
            CREATE TABLE IF NOT EXISTS artifacts(
              id TEXT PRIMARY KEY, run_id TEXT NOT NULL, name TEXT NOT NULL,
              path TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL,
              content_type TEXT NOT NULL, created_at TEXT NOT NULL,
              UNIQUE(run_id,name), FOREIGN KEY(run_id) REFERENCES runs(id)
            );
            CREATE TABLE IF NOT EXISTS uploads(
              id TEXT PRIMARY KEY, path TEXT NOT NULL, original_name TEXT NOT NULL,
              size INTEGER NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL
            );
            """)

    @contextmanager
    def connection(self):
        c = sqlite3.connect(self.path, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback(); raise
        finally:
            c.close()

    @staticmethod
    def decode(row):
        if row is None: return None
        result = dict(row)
        for field in ["payload", "result", "data"]:
            if field in result and result[field] is not None:
                result[field] = json.loads(result[field])
        return result

    def create(self, payload: dict, key: str | None = None):
        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            if key:
                existing = c.execute("SELECT * FROM runs WHERE idempotency_key=?", (key,)).fetchone()
                if existing:
                    decoded = self.decode(existing)
                    if decoded["payload"] != payload:
                        raise ValueError("Idempotency key already used with different input")
                    return decoded
            rid = uuid.uuid4().hex
            timestamp = now()
            c.execute("INSERT INTO runs(id,title,case_id,method,mode,status,created_at,updated_at,payload,idempotency_key) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (rid, payload["title"], payload["case_id"], payload["method"], payload["mode"], "QUEUED", timestamp, timestamp, json.dumps(payload), key))
            c.execute("INSERT INTO events(run_id,at,stage,kind,message,data) VALUES(?,?,?,?,?,?)",
                (rid,timestamp,"QUEUED","info","Run queued; no result has been measured yet.","{}"))
        return self.get(rid)

    def get(self, rid):
        with self.connection() as c:
            return self.decode(c.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone())

    def list(self):
        with self.connection() as c:
            return [self.decode(r) for r in c.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT 100")]

    def claim(self):
        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT * FROM runs WHERE status='QUEUED' ORDER BY created_at LIMIT 1").fetchone()
            if not row: return None
            c.execute("UPDATE runs SET status='PREFLIGHT',updated_at=? WHERE id=?", (now(), row["id"]))
            c.execute("INSERT INTO events(run_id,at,stage,kind,message,data) VALUES(?,?,?,?,?,?)",
                (row["id"],now(),"PREFLIGHT","info","Worker claimed the run.","{}"))
            result = self.decode(row);result["status"]="PREFLIGHT"
            return result

    def event(self, rid, message, kind="info", data=None):
        row = self.get(rid)
        if not row: raise KeyError(rid)
        with self.connection() as c:
            c.execute("INSERT INTO events(run_id,at,stage,kind,message,data) VALUES(?,?,?,?,?,?)",
                (rid, now(), row["status"], kind, message, json.dumps(data or {})))

    def transition(self, rid, stage: Stage | str, message: str, result=None):
        stage = str(stage)
        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT status FROM runs WHERE id=?", (rid,)).fetchone()
            if not row: raise KeyError(rid)
            old = row["status"]
            if stage not in ALLOWED.get(old, set()):
                raise ValueError(f"Illegal transition: {old} -> {stage}")
            c.execute("UPDATE runs SET status=?,updated_at=?,result=COALESCE(?,result) WHERE id=?",
                (stage,now(),None if result is None else json.dumps(result),rid))
            c.execute("INSERT INTO events(run_id,at,stage,kind,message,data) VALUES(?,?,?,?,?,?)",
                (rid,now(),stage,"success" if stage=="VERIFIED" else "info",message,"{}"))

    def events(self, rid, after=0):
        with self.connection() as c:
            return [self.decode(r) for r in c.execute("SELECT * FROM events WHERE run_id=? AND id>? ORDER BY id",(rid,after))]

    def cancel(self, rid):
        row = self.get(rid)
        if not row: raise KeyError(rid)
        if row["status"] in TERMINAL: return row
        with self.connection() as c:
            c.execute("UPDATE runs SET cancel_requested=1 WHERE id=?",(rid,))
        if row["status"]=="QUEUED": self.transition(rid,"CANCELLED","Cancelled before execution.")
        return self.get(rid)

    def cancelled(self, rid):
        return bool(self.get(rid)["cancel_requested"])

    def fail_interrupted(self):
        with self.connection() as c:
            rows=c.execute("SELECT id,status FROM runs WHERE status IN ('PREFLIGHT','REPRODUCING','FROZEN','PATCHING','VERIFYING')").fetchall()
        for row in rows:
            self.transition(row["id"],"ERROR","Worker restarted. Execution interrupted; no automatic rerun.",
                {"reason":"worker_interrupted", "verified":False})

    def artifacts(self, rid):
        with self.connection() as c:
            return [dict(r) for r in c.execute("SELECT * FROM artifacts WHERE run_id=? ORDER BY created_at",(rid,))]
