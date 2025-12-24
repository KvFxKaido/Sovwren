# path: sovwren/persistence.py
# Python 3.10+
#
# v0.2 PARKED: Full conversation persistence layer (Code Pilot design)
#
# This module provides comprehensive session persistence including:
# - Full session lifecycle (begin -> messages -> events -> end)
# - Project + Node tracking (models as guests)
# - Context snapshots per turn (RAG retrieval logging)
# - Bookmarks with integrity hashes
# - JSON export for portability
#
# For v0.1, we use the simpler protocol_events table in database.py.
# This module is the upgrade path for v0.2.

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional


# ---- Data types -------------------------------------------------------------

Role = Literal["steward", "node", "system"]
Band = Literal["None", "Low", "Medium", "High", "Critical"]
EventKind = Literal[
    "consent_checkpoint",
    "rupture_logged",
    "bookmark",
    "state_changed",
    "context_transition",
]


@dataclass(frozen=True)
class NodeInfo:
    name: str
    provider: str
    model: str
    meta: Dict[str, Any] | None = None


@dataclass(frozen=True)
class SessionState:
    lens: Literal["Blue", "Red", "Purple", "Clear"] | None = None
    mode: Literal["Workshop", "Sanctuary", "Mixed"] | None = None
    idleness: bool | None = None
    energy: Literal["Low", "Medium", "High", "Fragile", "Conserving", "Steady"] | None = None
    note: str | None = None  # why: preserve human context when it matters


# ---- Persistence core -------------------------------------------------------

class SovwrenDB:
    """
    Minimal, append-oriented SQLite wrapper.

    Why: Keep this boring and explicit. No ORM to avoid hidden migrations.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES)
        self._conn.row_factory = sqlite3.Row
        self._apply_pragmas()
        self._migrate()

    # -- public API -----------------------------------------------------------

    def begin_session(
        self,
        project_root: str | Path,
        node: NodeInfo,
        initial_state: SessionState | None = None,
    ) -> int:
        with self._tx() as cur:
            project_id = self._ensure_project(cur, Path(project_root))
            node_id = self._ensure_node(cur, node)
            cur.execute(
                """
                INSERT INTO sessions(project_id, node_id, started_at, lens, mode, idleness, energy, note)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    node_id,
                    _utcnow(),
                    getattr(initial_state, "lens", None),
                    getattr(initial_state, "mode", None),
                    _bool(initial_state.idleness) if initial_state else None,
                    getattr(initial_state, "energy", None),
                    getattr(initial_state, "note", None),
                ),
            )
            session_id = int(cur.lastrowid)

            if initial_state:
                self.log_event(
                    session_id,
                    kind="state_changed",
                    by="system",
                    payload=_state_payload(initial_state),
                )
        return session_id

    def end_session(self, session_id: int) -> None:
        with self._tx() as cur:
            cur.execute(
                "UPDATE sessions SET ended_at = ? WHERE id = ? AND ended_at IS NULL",
                (_utcnow(), session_id),
            )

    def append_message(
        self,
        session_id: int,
        role: Role,
        content: str,
        *,
        tokens_est: Optional[int] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> int:
        with self._tx() as cur:
            cur.execute(
                """
                INSERT INTO messages(session_id, role, content, tokens_est, meta_json, created_at)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    role,
                    content,
                    tokens_est,
                    json.dumps(meta or {}),
                    _utcnow(),
                ),
            )
            return int(cur.lastrowid)

    def log_event(
        self,
        session_id: int,
        *,
        kind: EventKind,
        by: Literal["steward", "node", "system"],
        payload: Dict[str, Any] | None = None,
    ) -> int:
        with self._tx() as cur:
            cur.execute(
                """
                INSERT INTO events(session_id, kind, by_who, payload_json, created_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (session_id, kind, by, json.dumps(payload or {}), _utcnow()),
            )
            return int(cur.lastrowid)

    def record_context(
        self,
        session_id: int,
        *,
        turn_id: int,
        band: Band,
        retrieved_files: Iterable[str] | None,
        approx_tokens_conv: Optional[int],
        approx_tokens_ret: Optional[int],
    ) -> int:
        """
        Why: Visibility over accuracy. Bands prevent false precision.
        """
        with self._tx() as cur:
            cur.execute(
                """
                INSERT INTO context_snapshots(
                    session_id, turn_id, band, retrieved_files_json,
                    approx_tokens_conv, approx_tokens_ret, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    turn_id,
                    band,
                    json.dumps(list(retrieved_files or [])),
                    approx_tokens_conv,
                    approx_tokens_ret,
                    _utcnow(),
                ),
            )
            # also emit a context_transition event when band is not "None"
            if band and band != "None":
                self.log_event(
                    session_id,
                    kind="context_transition",
                    by="system",
                    payload={
                        "turn_id": turn_id,
                        "band": band,
                        "retrieved_files": list(retrieved_files or []),
                    },
                )
            return int(cur.lastrowid)

    def update_state(self, session_id: int, **updates: Any) -> None:
        """
        Allowed keys: lens, mode, idleness, energy, note.
        Emits a state_changed event with the diff.
        """
        allowed = {"lens", "mode", "idleness", "energy", "note"}
        diff = {k: updates[k] for k in updates.keys() & allowed if updates[k] is not None}
        if not diff:
            return
        sets = ", ".join(f"{k} = :{k}" for k in diff)
        diff["session_id"] = session_id
        with self._tx() as cur:
            cur.execute(
                f"UPDATE sessions SET {sets} WHERE id = :session_id",
                diff,
            )
        self.log_event(
            session_id,
            kind="state_changed",
            by="steward",  # default assumption; adjust at call site when Node toggles
            payload=diff,
        )

    def save_ticket(
        self,
        session_id: int,
        *,
        seed_excerpt: str,
        summary: str,
        participants: Iterable[str],
        status: Literal["open", "in-progress", "resolved"] = "open",
        integrity_sha256: Optional[str] = None,
    ) -> int:
        with self._tx() as cur:
            cur.execute(
                """
                INSERT INTO tickets(
                    session_id, seed_excerpt, summary, participants_json, status,
                    integrity_sha256, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    seed_excerpt,
                    summary,
                    json.dumps(list(participants)),
                    status,
                    integrity_sha256,
                    _utcnow(),
                ),
            )
            ticket_id = int(cur.lastrowid)
        self.log_event(
            session_id,
            kind="bookmark",
            by="steward",
            payload={"bookmark_id": ticket_id},
        )
        return ticket_id

    def export_session_json(self, session_id: int) -> Dict[str, Any]:
        with self._tx() as cur:
            cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            s = cur.fetchone()
            if not s:
                raise ValueError(f"Session {session_id} not found")
            cur.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
            messages = [dict(row) for row in cur.fetchall()]
            cur.execute("SELECT * FROM events WHERE session_id = ? ORDER BY id ASC", (session_id,))
            events = [dict(row) for row in cur.fetchall()]
            cur.execute("SELECT * FROM context_snapshots WHERE session_id = ? ORDER BY id ASC", (session_id,))
            ctx = [dict(row) for row in cur.fetchall()]
            cur.execute("SELECT * FROM tickets WHERE session_id = ? ORDER BY id ASC", (session_id,))
            tickets = [dict(row) for row in cur.fetchall()]
        return {
            "session": dict(s),
            "messages": messages,
            "events": events,
            "context": ctx,
            "tickets": tickets,
            "exported_at": _utcnow(),
            "version": 1,
        }

    # -- internals ------------------------------------------------------------

    def _apply_pragmas(self) -> None:
        cur = self._conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA foreign_keys=ON;")
        cur.execute("PRAGMA busy_timeout=5000;")
        cur.close()

    def _migrate(self) -> None:
        cur = self._conn.cursor()
        cur.execute("PRAGMA user_version;")
        (ver,) = cur.fetchone()
        if ver == 0:
            self._create_schema(cur)
            cur.execute("PRAGMA user_version=1;")
        cur.close()
        self._conn.commit()

    def _create_schema(self, cur: sqlite3.Cursor) -> None:
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
              id INTEGER PRIMARY KEY,
              root_path TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS nodes (
              id INTEGER PRIMARY KEY,
              name TEXT NOT NULL,
              provider TEXT NOT NULL,
              model TEXT NOT NULL,
              meta_json TEXT,
              UNIQUE(name, provider, model)
            );

            CREATE TABLE IF NOT EXISTS sessions (
              id INTEGER PRIMARY KEY,
              project_id INTEGER NOT NULL REFERENCES projects(id),
              node_id INTEGER NOT NULL REFERENCES nodes(id),
              started_at TEXT NOT NULL,
              ended_at TEXT,
              lens TEXT,
              mode TEXT,
              idleness INTEGER,
              energy TEXT,
              note TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
              id INTEGER PRIMARY KEY,
              session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              tokens_est INTEGER,
              meta_json TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY,
              session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
              kind TEXT NOT NULL,
              by_who TEXT NOT NULL,
              payload_json TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS context_snapshots (
              id INTEGER PRIMARY KEY,
              session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
              turn_id INTEGER NOT NULL,
              band TEXT NOT NULL,
              retrieved_files_json TEXT NOT NULL,
              approx_tokens_conv INTEGER,
              approx_tokens_ret INTEGER,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tickets (
              id INTEGER PRIMARY KEY,
              session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
              seed_excerpt TEXT NOT NULL,
              summary TEXT NOT NULL,
              participants_json TEXT NOT NULL,
              status TEXT NOT NULL,
              integrity_sha256 TEXT,
              created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
            CREATE INDEX IF NOT EXISTS idx_ctx_session ON context_snapshots(session_id);
            """
        )

    def _ensure_project(self, cur: sqlite3.Cursor, root: Path) -> int:
        cur.execute("SELECT id FROM projects WHERE root_path = ?", (str(root),))
        row = cur.fetchone()
        if row:
            return int(row[0])
        cur.execute(
            "INSERT INTO projects(root_path, created_at) VALUES(?, ?)",
            (str(root), _utcnow()),
        )
        return int(cur.lastrowid)

    def _ensure_node(self, cur: sqlite3.Cursor, node: NodeInfo) -> int:
        cur.execute(
            "SELECT id FROM nodes WHERE name=? AND provider=? AND model=?",
            (node.name, node.provider, node.model),
        )
        row = cur.fetchone()
        if row:
            return int(row[0])
        cur.execute(
            "INSERT INTO nodes(name, provider, model, meta_json) VALUES(?, ?, ?, ?)",
            (node.name, node.provider, node.model, json.dumps(node.meta or {})),
        )
        return int(cur.lastrowid)

    @contextmanager
    def _tx(self):
        cur = self._conn.cursor()
        try:
            yield cur
        except Exception:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()
        finally:
            cur.close()

    def close(self) -> None:
        self._conn.close()


# ---- helpers ----------------------------------------------------------------

def _utcnow() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _bool(v: Optional[bool]) -> Optional[int]:
    return None if v is None else int(bool(v))


def _state_payload(state: SessionState) -> Dict[str, Any]:
    return {k: getattr(state, k) for k in ("lens", "mode", "idleness", "energy", "note") if getattr(state, k) is not None}


# ---- tiny manual test -------------------------------------------------------

if __name__ == "__main__":
    # Minimal CLI smoke test (run: python -m sovwren.persistence)
    db = SovwrenDB(Path.cwd() / ".sovwren" / "sovwren.db")
    sess = db.begin_session(
        project_root=Path.cwd(),
        node=NodeInfo(name="Sovwren", provider="LM Studio", model="ministral-3-8b-reasoning-2512"),
        initial_state=SessionState(lens="Blue", mode="Workshop", idleness=False, energy="Steady"),
    )
    db.append_message(sess, "steward", "Hey")
    db.append_message(sess, "node", "Hi. Idle presence available.")
    db.log_event(sess, kind="consent_checkpoint", by="steward", payload={"note": "slow down"})
    db.record_context(sess, turn_id=3, band="Low", retrieved_files=["MYTH ENGINE - Living Document (v1.7).md"], approx_tokens_conv=3200, approx_tokens_ret=1100)
    db.update_state(sess, idleness=True)  # state_changed event emitted
    tid = db.save_ticket(sess, seed_excerpt="...", summary="Pattern: context transitions feel sharp", participants=["Shawn", "Sovwren"], status="open")
    print(json.dumps(db.export_session_json(sess), indent=2))
    db.end_session(sess)
    db.close()
