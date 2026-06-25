# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""K9SessionManager — session lifecycle orchestrator."""

import logging
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.session.k9_session import K9Session, SessionStatus
from k9_aif_abb.k9_core.session.base_session_store import BaseSessionStore


class K9SessionManager:
    """
    ABB session lifecycle manager.

    Sits at the Router boundary. On every inbound payload:
    - No session_id → on_session_start() → new session, UUID auto-generated
    - session_id present → on_session_get() → retrieve and enrich

    After squad execution the Orchestrator calls on_session_update() to
    persist context changes back to the store.

    SBBs choose the store (InMemory, Redis, SQLite) via SessionFactory.
    """

    def __init__(
        self,
        store: BaseSessionStore,
        default_ttl: int = 3600,
    ) -> None:
        self._store = store
        self._default_ttl = default_ttl
        self.logger = logging.getLogger(self.__class__.__name__)

    def on_session_start(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> K9Session:
        session = K9Session(
            user_id=user_id,
            ttl=self._default_ttl,
            metadata=metadata or {},
        )
        self._store.save(session)
        self.logger.info(
            "[K9SessionManager] Started session %s for user %s",
            session.session_id, user_id,
        )
        return session

    def on_session_get(self, session_id: str) -> Optional[K9Session]:
        if not session_id:
            return None
        session = self._store.get(session_id)
        if session is None:
            self.logger.debug("[K9SessionManager] Session not found: %s", session_id)
            return None
        if session.is_expired():
            self.on_session_expire(session_id)
            return None
        session.touch()
        self._store.save(session)
        return session

    def on_session_update(
        self,
        session_id: str,
        context_delta: Dict[str, Any],
    ) -> Optional[K9Session]:
        session = self.on_session_get(session_id)
        if session is None:
            return None
        session.context.update(context_delta)
        self._store.save(session)
        return session

    def on_session_expire(self, session_id: str) -> None:
        session = self._store.get(session_id)
        if session:
            session.status = SessionStatus.EXPIRED
            self._store.save(session)
            self.logger.info("[K9SessionManager] Session expired: %s", session_id)

    def on_session_destroy(self, session_id: str) -> None:
        self._store.delete(session_id)
        self.logger.info("[K9SessionManager] Session destroyed: %s", session_id)

    def extract_session_id(self, payload: Dict[str, Any]) -> Optional[str]:
        return payload.get("session_id") or None

    def enrich_payload(
        self,
        session: Optional[K9Session],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Attach session_id and session_context to the payload."""
        if session is None:
            return payload
        enriched = dict(payload)
        enriched["session_id"] = session.session_id
        enriched["session_context"] = dict(session.context)
        enriched["session_user_id"] = session.user_id
        return enriched
