# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""InMemorySessionStore — default session store, no external dependencies."""

from threading import Lock
from typing import Any, Dict, List, Optional

from k9_aif_abb.k9_core.session.base_session_store import BaseSessionStore
from k9_aif_abb.k9_core.session.k9_session import K9Session, SessionStatus


class InMemorySessionStore(BaseSessionStore):
    """
    Thread-safe in-memory session store.

    Default store — zero dependencies. State is lost on restart.
    Use for development, testing, and single-process deployments.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._store: Dict[str, K9Session] = {}
        self._lock = Lock()

    def get(self, session_id: str) -> Optional[K9Session]:
        with self._lock:
            return self._store.get(session_id)

    def save(self, session: K9Session) -> None:
        with self._lock:
            self._store[session.session_id] = session

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._store.pop(session_id, None)

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._store

    def list_active(self) -> List[K9Session]:
        with self._lock:
            return [
                s for s in self._store.values()
                if s.status == SessionStatus.ACTIVE
            ]
