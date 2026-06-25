# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
k9_cache — Cache adapter implementations for K9-AIF.

Adapters live in ``k9_cache/adapters/``.
The contract is defined in ``k9_core/cache/base_cache.py``.
The factory is ``k9_factories/cache_factory.py``.

Typical import::

    from k9_aif_abb.k9_factories.cache_factory import CacheFactory

    cache = CacheFactory.create(config)
    cache.set("key", value, ttl=300)
    value = cache.get("key")
"""
