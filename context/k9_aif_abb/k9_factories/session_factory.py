# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
SessionFactory — static factory for session store backends.

Pre-registered stores: redis (default), in_memory, sqlite.

YAML config::

    session:
      provider: redis          # redis (default) | in_memory | sqlite
      ttl: 3600                # session TTL in seconds (default: 3600)

      # Redis — when provider: redis
      redis:
        host: localhost
        port: 6379
        db: 0
        key_prefix: k9aif:session:

      # SQLite — when provider: sqlite
      sqlite:
        db_path: /tmp/k9_sessions.db

Usage::

    from k9_aif_abb.k9_factories.session_factory import SessionFactory
    from k9_aif_abb.k9_core.session import K9SessionManager

    manager = SessionFactory.create_manager(config)
    # pass manager to BaseRouter / BaseOrchestrator at construction
"""

from threading import Lock
from typing import Any, Dict, Type
import logging

log = logging.getLogger("SessionFactory")


class SessionFactory:
    """Static factory — provisions session store backends and K9SessionManager."""

    _registry: Dict[str, Type[Any]] = {}
    _lock = Lock()
    _bootstrapped = False

    def __init__(self, *args, **kwargs) -> None:
        raise RuntimeError("SessionFactory is static and cannot be instantiated")

    @staticmethod
    def _ensure_defaults() -> None:
        if SessionFactory._bootstrapped:
            return
        with SessionFactory._lock:
            if SessionFactory._bootstrapped:
                return
            from k9_aif_abb.k9_sessions.in_memory_session_store import InMemorySessionStore
            from k9_aif_abb.k9_sessions.redis_session_store import RedisSessionStore
            from k9_aif_abb.k9_sessions.sqlite_session_store import SQLiteSessionStore

            SessionFactory._registry.update({
                "in_memory": InMemorySessionStore,
                "redis":     RedisSessionStore,
                "sqlite":    SQLiteSessionStore,
            })
            SessionFactory._bootstrapped = True
            log.info("[Factory] Bootstrapped SessionFactory")

    @staticmethod
    def register(name: str, cls: Type[Any]) -> None:
        SessionFactory._ensure_defaults()
        with SessionFactory._lock:
            SessionFactory._registry[name.lower()] = cls
            log.debug("[Factory] Registered session store '%s'", name)

    @staticmethod
    def get_store(name: str, config: Dict[str, Any] = None):
        SessionFactory._ensure_defaults()
        cls = SessionFactory._registry.get(name.lower())
        if not cls:
            raise ValueError(f"Unknown session store provider: {name}")
        return cls(config=config or {})

    @staticmethod
    def create_manager(config: Dict[str, Any] = None):
        """
        Create a K9SessionManager from config, or return None if disabled.

        Returns None (session disabled) when:
        - no ``session`` key in config
        - ``config["session"]["enabled"]`` is false or missing

        Nothing in BaseRouter or BaseOrchestrator is affected when None is
        returned — all session hooks are guarded and become no-ops.

        YAML config::

            session:
              enabled: true          # false by default — opt-in
              provider: in_memory    # in_memory | redis | sqlite
              ttl: 3600
        """
        from k9_aif_abb.k9_core.session.k9_session_manager import K9SessionManager

        SessionFactory._ensure_defaults()
        cfg = config or {}
        session_cfg = cfg.get("session", {})

        if not session_cfg.get("enabled", False):
            log.debug("[Factory] Session management disabled — returning None")
            return None

        provider = session_cfg.get("provider", "redis").lower()
        ttl = int(session_cfg.get("ttl", 3600))

        log.info("[Factory] Creating session manager: provider=%s ttl=%s", provider, ttl)
        store = SessionFactory.get_store(provider, config=cfg)
        return K9SessionManager(store=store, default_ttl=ttl)
