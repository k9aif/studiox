# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
BaseCache — ABB abstract contract for caching.

Inheritance hierarchy::

    BaseCache                       (contract — ABB, this file)
      └── InMemoryAdapter           (default: thread-safe dict, no TTL)
      └── RedisAdapter              (Redis / Redis-compatible, TTL-aware)
      └── MyCache                   (SBB — extend for domain/infra-specific cache)

Overrideable surface
--------------------
``get(key)``         — **abstract** — return value or ``None`` on miss.
``set(key, value)``  — **abstract** — store value, optional TTL seconds.
``delete(key)``      — **abstract** — remove key; no-op if absent.
``clear()``          — **abstract** — flush all entries.
``exists(key)``      — optional; default calls ``get()`` and checks for None.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseCache(ABC):
    """
    ABB contract for key/value caching across any cache backend.

    Minimal SBB implementation::

        class MyCache(BaseCache):
            def get(self, key):   return _store.get(key)
            def set(self, key, value, ttl=None): _store[key] = value
            def delete(self, key): _store.pop(key, None)
            def clear(self): _store.clear()
    """

    # ── Abstract — implement in every adapter ─────────────────────────────────

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Return cached value or ``None`` on a miss."""
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store *value* under *key*.

        Args:
            ttl: expiry in seconds; ``None`` means no expiry.
                 Adapters that do not support TTL may ignore this parameter.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove *key*; no-op if the key does not exist."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Flush all entries from the cache."""
        raise NotImplementedError

    # ── Optional override ─────────────────────────────────────────────────────

    def exists(self, key: str) -> bool:
        """Return True if *key* is present in the cache."""
        return self.get(key) is not None
