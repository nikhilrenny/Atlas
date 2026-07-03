"""SQLite persistence for Phase 10 agent runs, steps, and scheduled jobs.
Same shape as memory/store.py -- one file, sqlite3 stdlib, no new dependency.
"""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[3] / "data" / "agents.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agent_runs (
                id          TEXT PRIMARY KEY,
                goal        TEXT NOT NULL,
                status      TEXT NOT NULL,   -- pending | running | done | failed
                error       TEXT,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agent_steps (
                id          TEXT PRIMARY KEY,
                run_id      TEXT NOT NULL,
                idx         INTEGER NOT NULL,
                action      TEXT NOT NULL,   -- tool | browse | lookup
                target      TEXT NOT NULL,
                params      TEXT NOT NULL,   -- JSON
                status      TEXT NOT NULL,   -- pending | running | done | failed | skipped
                result      TEXT,            -- JSON, set on done
                error       TEXT,
                started_at  TEXT,
                finished_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_steps_run ON agent_steps(run_id, idx);

            CREATE TABLE IF NOT EXISTS scheduled_jobs (
                id           TEXT PRIMARY KEY,
                goal         TEXT NOT NULL,
                recurrence   TEXT NOT NULL,  -- JSON: {"type":"interval","minutes":N} | {"type":"daily","at":"HH:MM"}
                enabled      INTEGER NOT NULL DEFAULT 1,
                next_run_at  TEXT NOT NULL,
                last_run_at  TEXT,
                created_at   TEXT NOT NULL
            );
        """)


# --- Runs ---

def create_run(goal: str) -> str:
    rid = uuid.uuid4().hex[:16]
    now = _now()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO agent_runs (id, goal, status, created_at, updated_at) VALUES (?,?,?,?,?)",
            (rid, goal, "pending", now, now),
        )
    return rid


def update_run_status(run_id: str, status: str, error: str | None = None):
    with _get_conn() as conn:
        conn.execute(
            "UPDATE agent_runs SET status=?, error=?, updated_at=? WHERE id=?",
            (status, error, _now(), run_id),
        )


def get_run(run_id: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM agent_runs WHERE id=?", (run_id,)).fetchone()
    if not row:
        return None
    run = dict(row)
    run["steps"] = list_steps(run_id)
    return run


def list_runs(limit: int = 50) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# --- Steps ---

def add_step(run_id: str, idx: int, action: str, target: str, params: dict) -> str:
    sid = uuid.uuid4().hex[:16]
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO agent_steps (id, run_id, idx, action, target, params, status) VALUES (?,?,?,?,?,?,?)",
            (sid, run_id, idx, action, target, json.dumps(params), "pending"),
        )
    return sid


def update_step(step_id: str, status: str, result: dict | None = None, error: str | None = None, started: bool = False, finished: bool = False):
    fields = ["status=?"]
    values = [status]
    if started:
        fields.append("started_at=?")
        values.append(_now())
    if finished:
        fields.append("finished_at=?")
        values.append(_now())
    if result is not None:
        fields.append("result=?")
        values.append(json.dumps(result, default=str))
    if error is not None:
        fields.append("error=?")
        values.append(error)
    values.append(step_id)
    with _get_conn() as conn:
        conn.execute(f"UPDATE agent_steps SET {', '.join(fields)} WHERE id=?", values)


def list_steps(run_id: str) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_steps WHERE run_id=? ORDER BY idx ASC", (run_id,)
        ).fetchall()
    steps = []
    for r in rows:
        d = dict(r)
        d["params"] = json.loads(d["params"]) if d["params"] else {}
        if d.get("result"):
            try:
                d["result"] = json.loads(d["result"])
            except Exception:
                pass
        steps.append(d)
    return steps


# --- Scheduled jobs ---

def create_schedule(goal: str, recurrence: dict, next_run_at: str) -> str:
    jid = uuid.uuid4().hex[:16]
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO scheduled_jobs (id, goal, recurrence, enabled, next_run_at, created_at) VALUES (?,?,?,1,?,?)",
            (jid, goal, json.dumps(recurrence), next_run_at, _now()),
        )
    return jid


def list_schedules() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM scheduled_jobs ORDER BY created_at DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["recurrence"] = json.loads(d["recurrence"])
        d["enabled"] = bool(d["enabled"])
        out.append(d)
    return out


def due_schedules(now_iso: str) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM scheduled_jobs WHERE enabled=1 AND next_run_at<=?", (now_iso,)
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["recurrence"] = json.loads(d["recurrence"])
        out.append(d)
    return out


def mark_schedule_ran(job_id: str, next_run_at: str):
    with _get_conn() as conn:
        conn.execute(
            "UPDATE scheduled_jobs SET last_run_at=?, next_run_at=? WHERE id=?",
            (_now(), next_run_at, job_id),
        )


def delete_schedule(job_id: str) -> bool:
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM scheduled_jobs WHERE id=?", (job_id,))
    return cur.rowcount > 0


def set_schedule_enabled(job_id: str, enabled: bool) -> bool:
    with _get_conn() as conn:
        cur = conn.execute("UPDATE scheduled_jobs SET enabled=? WHERE id=?", (1 if enabled else 0, job_id))
    return cur.rowcount > 0
