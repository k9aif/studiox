# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""RedisSessionStore — distributed session store backed by Redis."""

import json
import logging
from typing import Any, Dict, List, Optional

from k9_aif_abb.k9_core.session.base_session_store import BaseSessionStore
from k9_aif_abb.k9_core.session.k9_session import K9Session, SessionStatus

log = logging.getLogger("RedisSessionStore")


class RedisSessionStore(BaseSessionStore):
    """
    Redis-backed session store for distributed / multi-process deployments.

    Requires: pip install redis

    Config keys (under session.redis):
        host: localhost
        port: 6379
        db: 0
        key_prefix: k9aif:session:
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._config = (config or {}).get("session", {}).get("redis", {})
        self._prefix = self._config.get("key_prefix", "k9aif:session:")
        self._client = None  # lazy init

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            import redis  # type: ignore
            self._client = redis.Redis(
                host=self._config.get("host", "localhost"),
                port=int(self._config.get("port", 6379)),
                db=int(self._config.get("db", 0)),
                decode_responses=True,
            )
        except ImportError as exc:
            raise RuntimeError("pip install redis required for RedisSessionStore") from exc

    def _key(self, session_id: str) -> str:
        return f"{self._prefix}{session_id}"

    def get(self, session_id: str) -> Optional[K9Session]:
        self._ensure_client()
        raw = self._client.get(self._key(session_id))
        if raw is None:
            return None
        return K9Session.from_dict(json.loads(raw))

    def save(self, session: K9Session) -> None:
        self._ensure_client()
        self._client.setex(
            self._key(session.session_id),
            session.ttl,
            json.dumps(session.to_dict()),
        )

    def delete(self, session_id: str) -> None:
        self._ensure_client()
        self._client.delete(self._key(session_id))

    def exists(self, session_id: str) -> bool:
        self._ensure_client()
        return bool(self._client.exists(self._key(session_id)))

    def list_active(self) -> List[K9Session]:
        # Redis SCAN is expensive — not supported for list_active at scale
        return []
