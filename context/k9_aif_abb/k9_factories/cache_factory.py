# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_factories/cache_factory.py

"""
CacheFactory — static factory for cache backends.

Pre-registered adapters: in_memory (default), redis.

YAML config::

    cache:
      provider: in_memory      # in_memory | redis  (default: in_memory)
      # redis-specific keys when provider: redis
      redis_host: 192.168.1.98
      redis_port: 6379
      redis_db: 0
      key_prefix: k9aif:

Usage::

    from k9_aif_abb.k9_factories.cache_factory import CacheFactory

    cache = CacheFactory.create(config)
    cache.set("result:claim-001", payload, ttl=300)
    cached = cache.get("result:claim-001")
"""

from threading import Lock
from typing import Any, Dict, Type
import logging

log = logging.getLogger("CacheFactory")


class CacheFactory:
    """Static Factory — provisions cache backends."""

    _registry: Dict[str, Type[Any]] = {}
    _lock = Lock()
    _bootstrapped = False

    def __init__(self, *args, **kwargs):
        raise RuntimeError("CacheFactory is static and cannot be instantiated")

    @staticmethod
    def _ensure_defaults() -> None:
        if CacheFactory._bootstrapped:
            return
        with CacheFactory._lock:
            if CacheFactory._bootstrapped:
                return
            from k9_aif_abb.k9_cache.adapters.in_memory_adapter import InMemoryAdapter
            from k9_aif_abb.k9_cache.adapters.redis_adapter      import RedisAdapter

            CacheFactory._registry.update({
                "in_memory": InMemoryAdapter,
                "redis":     RedisAdapter,
            })
            CacheFactory._bootstrapped = True
            log.info("[Factory] Bootstrapped CacheFactory")

    @staticmethod
    def register(name: str, cls: Type[Any]) -> None:
        """Register a custom cache adapter."""
        CacheFactory._ensure_defaults()
        with CacheFactory._lock:
            CacheFactory._registry[name.lower()] = cls
            log.debug("[Factory] Registered cache adapter '%s'", name)

    @staticmethod
    def get(name: str, config: Dict[str, Any] = None):
        """Return an instance of the named cache adapter."""
        CacheFactory._ensure_defaults()
        cls = CacheFactory._registry.get(name.lower())
        if not cls:
            raise ValueError(f"Unknown cache provider: {name}")
        return cls(config=config or {})

    @staticmethod
    def create(config: Dict[str, Any] = None):
        """
        Create a cache from config.

        Reads ``config["cache"]["provider"]`` (default: ``"in_memory"``).
        """
        CacheFactory._ensure_defaults()
        cfg      = config or {}
        provider = cfg.get("cache", {}).get("provider", "in_memory").lower()
        log.info("[Factory] Creating cache: %s", provider)
        return CacheFactory.get(provider, config=cfg)
