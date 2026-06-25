# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
k9_cache.adapters — Cache adapter implementations.

Available adapters::

    in_memory → InMemoryAdapter   (default: thread-safe dict, no TTL enforcement)
    redis     → RedisAdapter      (Redis / Valkey / Redis-compatible, TTL-aware)

Typical import::

    from k9_aif_abb.k9_cache.adapters.in_memory_adapter import InMemoryAdapter
"""

from k9_aif_abb.k9_cache.adapters.in_memory_adapter import InMemoryAdapter
from k9_aif_abb.k9_cache.adapters.redis_adapter import RedisAdapter

__all__ = ["InMemoryAdapter", "RedisAdapter"]
