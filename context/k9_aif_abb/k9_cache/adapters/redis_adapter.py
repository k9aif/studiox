# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
RedisAdapter — Redis / Valkey / Redis-compatible cache adapter.

Requires the ``redis`` package::

    pip install redis

YAML config::

    cache:
      provider: redis
      redis_host: 192.168.1.98       # default: localhost
      redis_port: 6379               # default: 6379
      redis_db: 0                    # default: 0
      key_prefix: k9aif:             # optional prefix for all keys

Redis password comes from environment only (REDIS_PASSWORD) — never config.yaml.

SBB extension::

    class ClusterRedisAdapter(RedisAdapter):
        def _make_client(self):
            from redis.cluster import RedisCluster
            return RedisCluster(host=self._host, port=self._port)
"""

import logging
import os
from typing import Any, Dict, Optional

from k9_aif_abb.k9_core.cache.base_cache import BaseCache

log = logging.getLogger(__name__)


class RedisAdapter(BaseCache):
    """Cache adapter backed by Redis / Valkey."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config  = config or {}
        cfg           = self._config.get("cache", self._config)
        self._host    = cfg.get("redis_host", "localhost")
        self._port    = int(cfg.get("redis_port", 6379))
        self._db      = int(cfg.get("redis_db", 0))
        self._prefix  = cfg.get("key_prefix", "")
        # Password from env only
        self._password = os.environ.get("REDIS_PASSWORD") or None
        self._client  = None

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            import redis  # type: ignore
            self._client = redis.Redis(
                host=self._host,
                port=self._port,
                db=self._db,
                password=self._password,
                decode_responses=True,
            )
            # Verify connectivity
            self._client.ping()
            log.info("[RedisAdapter] connected to %s:%s db=%s", self._host, self._port, self._db)
        except ImportError as exc:
            raise RuntimeError(
                "redis package required for RedisAdapter: pip install redis"
            ) from exc

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}" if self._prefix else key

    def get(self, key: str) -> Optional[Any]:
        self._ensure_client()
        return self._client.get(self._key(key))

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._ensure_client()
        if ttl is not None:
            self._client.setex(self._key(key), ttl, str(value))
        else:
            self._client.set(self._key(key), str(value))

    def delete(self, key: str) -> None:
        self._ensure_client()
        self._client.delete(self._key(key))

    def clear(self) -> None:
        self._ensure_client()
        if self._prefix:
            keys = self._client.keys(f"{self._prefix}*")
            if keys:
                self._client.delete(*keys)
        else:
            self._client.flushdb()
