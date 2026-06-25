# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
InMemoryAdapter — default thread-safe in-process cache.

Zero dependencies.  Suitable for single-process use, unit tests, and local
development.  Does NOT persist across restarts or share state between processes.

TTL is enforced at ``get()`` time (lazy expiry) to avoid background threads.

YAML config::

    cache:
      provider: in_memory            # default when 'cache' block is absent
      max_size: 1000                 # optional soft cap (oldest entry evicted)

SBB extension::

    class AppCache(InMemoryAdapter):
        def get(self, key):
            # add domain-specific metrics, e.g. Prometheus counter
            value = super().get(key)
            CACHE_HITS.inc() if value is not None else CACHE_MISSES.inc()
            return value
"""

import time
import threading
from typing import Any, Dict, Optional, Tuple

from k9_aif_abb.k9_core.cache.base_cache import BaseCache


class InMemoryAdapter(BaseCache):
    """Thread-safe in-memory cache with optional TTL and size cap."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config   = config or {}
        self._max_size = self._config.get("cache", {}).get("max_size", 0)
        # _store: key → (value, expires_at or None)
        self._store: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._lock  = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at is not None and time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = (time.monotonic() + ttl) if ttl is not None else None
        with self._lock:
            if self._max_size and len(self._store) >= self._max_size and key not in self._store:
                # Evict the oldest entry (insertion order in Python 3.7+)
                oldest = next(iter(self._store))
                del self._store[oldest]
            self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
