# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
Tests for Cache ABB (Phase 1 — InMemoryAdapter and CacheFactory).

No external services required.
"""

import time
import threading
import pytest

from k9_aif_abb.k9_core.cache.base_cache import BaseCache
from k9_aif_abb.k9_cache.adapters.in_memory_adapter import InMemoryAdapter
from k9_aif_abb.k9_factories.cache_factory import CacheFactory


# ── BaseCache contract ────────────────────────────────────────────────────────

def test_base_is_abstract():
    with pytest.raises(TypeError):
        BaseCache()  # type: ignore


# ── InMemoryAdapter ───────────────────────────────────────────────────────────

def test_set_and_get():
    cache = InMemoryAdapter()
    cache.set("k", "v")
    assert cache.get("k") == "v"


def test_get_missing_returns_none():
    cache = InMemoryAdapter()
    assert cache.get("nope") is None


def test_delete():
    cache = InMemoryAdapter()
    cache.set("k", "v")
    cache.delete("k")
    assert cache.get("k") is None


def test_delete_nonexistent_noop():
    cache = InMemoryAdapter()
    cache.delete("ghost")    # should not raise


def test_clear():
    cache = InMemoryAdapter()
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_exists_true():
    cache = InMemoryAdapter()
    cache.set("k", "v")
    assert cache.exists("k") is True


def test_exists_false():
    cache = InMemoryAdapter()
    assert cache.exists("missing") is False


def test_ttl_expiry():
    cache = InMemoryAdapter()
    cache.set("k", "v", ttl=1)
    assert cache.get("k") == "v"
    time.sleep(1.05)
    assert cache.get("k") is None


def test_ttl_none_does_not_expire():
    cache = InMemoryAdapter()
    cache.set("k", "permanent")
    time.sleep(0.05)
    assert cache.get("k") == "permanent"


def test_max_size_evicts_oldest():
    cache = InMemoryAdapter(config={"cache": {"max_size": 3}})
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    cache.set("d", 4)    # should evict "a"
    assert cache.get("a") is None
    assert cache.get("d") == 4


def test_thread_safety():
    cache = InMemoryAdapter()
    errors = []

    def writer(n):
        try:
            for i in range(100):
                cache.set(f"key-{n}-{i}", i)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(t,)) for t in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors


# ── CacheFactory ──────────────────────────────────────────────────────────────

def test_factory_default_is_in_memory():
    cache = CacheFactory.create({})
    assert isinstance(cache, InMemoryAdapter)


def test_factory_explicit_in_memory():
    cache = CacheFactory.create({"cache": {"provider": "in_memory"}})
    assert isinstance(cache, InMemoryAdapter)


def test_factory_unknown_provider():
    with pytest.raises(ValueError, match="Unknown cache provider"):
        CacheFactory.create({"cache": {"provider": "no_such_backend"}})


def test_factory_get():
    cache = CacheFactory.get("in_memory")
    assert isinstance(cache, InMemoryAdapter)


def test_factory_register_custom():
    class DummyCache(BaseCache):
        def __init__(self, config=None): pass

        def get(self, key):     return "dummy"
        def set(self, key, v, ttl=None): pass
        def delete(self, key):  pass
        def clear(self):        pass

    CacheFactory.register("dummy_cache", DummyCache)
    cache = CacheFactory.create({"cache": {"provider": "dummy_cache"}})
    assert cache.get("x") == "dummy"
