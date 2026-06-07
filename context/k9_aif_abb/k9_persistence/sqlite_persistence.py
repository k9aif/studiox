# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from __future__ import annotations
import sqlite3
import threading
import json
from pathlib import Path
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.persistence.base_persistence import BasePersistence

class SQLitePersistence(BasePersistence):
    """SBB: SQLite persistence for durable state storage (persistent connection)."""

    def __init__(self, db_path: str | Path = "k9_aif_state.db", monitor=None):
        super().__init__(name="SQLitePersistence", monitor=monitor)
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()
        import atexit
        atexit.register(self.close)  # guarantee closure on exit

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS states (
                key TEXT PRIMARY KEY,
                state TEXT
            )
        """)
        self.conn.commit()

        #  NEW: resolve absolute path for full visibility
        abs_path = self.db_path.resolve()
        self.logger.info(f"[{self.layer}:{self.name}] Initialized SQLite DB at {abs_path}")

    # --- CRUD methods using the single shared connection ---
    def save_state(self, key: str, state: Dict[str, Any]) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO states (key, state) VALUES (?, ?)",
                (key, json.dumps(state)),
            )
            self.conn.commit()
        self.logger.debug(f"[{self.layer}:{self.name}] Saved state for key={key}")

    def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            cur = self.conn.execute("SELECT state FROM states WHERE key=?", (key,))
            row = cur.fetchone()
            return json.loads(row[0]) if row else None

    def update_state(self, key: str, state: Dict[str, Any]) -> None:
        current = self.load_state(key) or {}
        current.update(state)
        self.save_state(key, current)
        self.logger.debug(f"[{self.layer}:{self.name}] Updated state for key={key}")

    def delete_state(self, key: str) -> None:
        with self._lock:
            self.conn.execute("DELETE FROM states WHERE key=?", (key,))
            self.conn.commit()
        self.logger.debug(f"[{self.layer}:{self.name}] Deleted state for key={key}")

    def close(self):
        """Gracefully close SQLite connection."""
        try:
            if self.conn:
                abs_path = self.db_path.resolve()
                self.conn.close()
                self.conn = None
                self.logger.info(f"[{self.layer}:{self.name}] Closed SQLite DB at {abs_path}")
        except Exception as e:
            self.logger.warning(f"[{self.layer}:{self.name}] Failed to close DB: {e}")