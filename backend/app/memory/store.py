"""SQLite + ChromaDB memory store for Atlas.

SQLite is the primary store -- always available, structured queries, no external deps.
ChromaDB adds semantic search via nomic-embed-text embeddings; it degrades gracefully
if Ollama is unavailable (search falls back to SQLite LIKE queries).

Schema:
  memories    -- all memory records (id, type, content, data JSON, tags, timestamps)
  preferences -- inferred/explicit user preferences (key, value, confidence, source)
"""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[3] / "data" / "memory.db"
CHROMA_PATH = Path(__file__).resolve().parents[3] / "data" / "chroma_memory"

MEMORY_TYPES = ("preference", "lookup", "tool_execution", "page_visit")


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
            CREATE TABLE IF NOT EXISTS memories (
                id         TEXT PRIMARY KEY,
                type       TEXT NOT NULL,
                content    TEXT NOT NULL,
                data       TEXT NOT NULL,
                tags       TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memories_type    ON memories(type);
            CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);

            CREATE TABLE IF NOT EXISTS preferences (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source     TEXT DEFAULT 'inferred',
                updated_at TEXT NOT NULL
            );
        """)


# --- ChromaDB (optional semantic layer) ---

def _get_chroma_collection():
    try:
        import chromadb
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        return client.get_or_create_collection("atlas_memories")
    except Exception:
        return None


# --- Memory CRUD ---

def add_memory(type_: str, content: str, data: dict, tags: list[str] | None = None) -> str:
    mid = uuid.uuid4().hex[:16]
    now = _now()
    tag_str = ",".join(tags or [])
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO memories (id, type, content, data, tags, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (mid, type_, content, json.dumps(data), tag_str, now, now),
        )
    return mid


def get_memory(mid: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM memories WHERE id=?", (mid,)).fetchone()
    return _row_to_dict(row) if row else None


def delete_memory(mid: str) -> bool:
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM memories WHERE id=?", (mid,))
    coll = _get_chroma_collection()
    if coll:
        try:
            coll.delete(ids=[mid])
        except Exception:
            pass
    return cur.rowcount > 0


def list_memories(type_: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    with _get_conn() as conn:
        if type_:
            rows = conn.execute(
                "SELECT * FROM memories WHERE type=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (type_, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def keyword_search(query: str, limit: int = 5) -> list[dict]:
    like = f"%{query}%"
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM memories WHERE content LIKE ? OR tags LIKE ? ORDER BY created_at DESC LIMIT ?",
            (like, like, limit),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def semantic_search(query_embedding: list[float], limit: int = 5) -> list[dict]:
    coll = _get_chroma_collection()
    if coll is None:
        return []
    try:
        results = coll.query(query_embeddings=[query_embedding], n_results=limit)
        ids = results["ids"][0] if results["ids"] else []
        if not ids:
            return []
        with _get_conn() as conn:
            placeholders = ",".join("?" * len(ids))
            rows = conn.execute(
                f"SELECT * FROM memories WHERE id IN ({placeholders})", ids
            ).fetchall()
        id_order = {mid: i for i, mid in enumerate(ids)}
        return sorted([_row_to_dict(r) for r in rows], key=lambda r: id_order.get(r["id"], 99))
    except Exception:
        return []


def add_embedding(mid: str, content: str, embedding: list[float]):
    coll = _get_chroma_collection()
    if coll is None:
        return
    try:
        coll.upsert(ids=[mid], documents=[content], embeddings=[embedding])
    except Exception:
        pass


# --- Preferences ---

def set_preference(key: str, value: str, confidence: float = 1.0, source: str = "inferred"):
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO preferences (key, value, confidence, source, updated_at)
               VALUES (?,?,?,?,?)
               ON CONFLICT(key) DO UPDATE SET
                 value=excluded.value, confidence=excluded.confidence,
                 source=excluded.source, updated_at=excluded.updated_at""",
            (key, value, confidence, source, _now()),
        )


def get_preferences() -> dict[str, dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM preferences").fetchall()
    return {r["key"]: {"value": r["value"], "confidence": r["confidence"], "source": r["source"]} for r in rows}


def get_preference(key: str) -> str | None:
    with _get_conn() as conn:
        row = conn.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def count_memories(type_: str) -> int:
    with _get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as n FROM memories WHERE type=?", (type_,)).fetchone()
    return row["n"] if row else 0


def clear_all(type_: str | None = None) -> int:
    """Deletes all memory rows (optionally scoped to one type). Used by the Settings
    panel's 'clear memory' action. Also wipes the matching ChromaDB collection when
    clearing everything, since per-id deletion there isn't worth the round-trips."""
    with _get_conn() as conn:
        if type_:
            cur = conn.execute("DELETE FROM memories WHERE type=?", (type_,))
        else:
            cur = conn.execute("DELETE FROM memories")
    if not type_:
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            client.delete_collection("atlas_memories")
        except Exception:
            pass
    return cur.rowcount


# --- Helpers ---

def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    try:
        d["data"] = json.loads(d["data"])
    except Exception:
        pass
    d["tags"] = [t for t in d.get("tags", "").split(",") if t]
    return d
