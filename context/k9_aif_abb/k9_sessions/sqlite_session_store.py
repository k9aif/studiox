# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""SQLiteSessionStore — file-backed session store, survives restarts."""

import json
import logging
import os
import sqlite3
from threading import Lock
from typing import Any, Dict, List, Optional

from k9_aif_abb.k9_core.session.base_session_store import BaseSessionStore
from k9_aif_abb.k9_core.session.k9_session import K9Session, SessionStatus

log = logging.getLogger("SQLiteSessionStore")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS k9_sessions (
    session_id   TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    last_active  TEXT NOT NULL,
    ttl          INTEGER NOT NULL,
    context      TEXT NOT NULL DEFAULT '{}',
    metadata     TEXT NOT NULL DEFAULT '{}',
    status       TEXT NOT NULL DEFAULT 'active'
)
"""


class SQLiteSessionStore(BaseSessionStore):
    """
    SQLite-backed session store — survives process restarts.

    Config keys (under session.sqlite):
        db_path: /tmp/k9_sessions.db
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = (config or {}).get("session", {}).get("sqlite", {})
        self._db_path = cfg.get("db_path", "/tmp/k9_sessions.db")
        self._lock = Lock()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(_CREATE_TABLE)
            conn.commit()

    def get(self, session_id: str) -> Optional[K9Session]:
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT * FROM k9_sessions WHERE session_id = ?", (session_id,)
                ).fetchone()
        if row is None:
            return None
        return self._row_to_session(row)

    def save(self, session: K9Session) -> None:
        d = session.to_dict()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO k9_sessions
                       (session_id, user_id, created_at, last_active,
                        ttl, context, metadata, status)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        d["session_id"], d["user_id"],
                        d["created_at"], d["last_active"],
                        d["ttl"],
                        json.dumps(d["context"]),
                        json.dumps(d["metadata"]),
                        d["status"],
                    ),
                )
                conn.commit()

    def delete(self, session_id: str) -> None:
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "DELETE FROM k9_sessions WHERE session_id = ?", (session_id,)
                )
                conn.commit()

    def exists(self, session_id: str) -> bool:
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT 1 FROM k9_sessions WHERE session_id = ?", (session_id,)
                ).fetchone()
        return row is not None

    def list_active(self) -> List[K9Session]:
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT * FROM k9_sessions WHERE status = 'active'"
                ).fetchall()
        return [self._row_to_session(r) for r in rows]

    @staticmethod
    def _row_to_session(row) -> K9Session:
        return K9Session.from_dict({
            "session_id":  row[0],
            "user_id":     row[1],
            "created_at":  row[2],
            "last_active": row[3],
            "ttl":         row[4],
            "context":     json.loads(row[5]),
            "metadata":    json.loads(row[6]),
            "status":      row[7],
        })
