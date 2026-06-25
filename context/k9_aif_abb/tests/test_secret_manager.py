# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
Tests for Secret Manager ABB (Phase 1 — env adapter and factory).

No external services required — all tests use the env adapter.
"""

import os
import pytest

from k9_aif_abb.k9_core.security.base_secret_manager import BaseSecretManager
from k9_aif_abb.k9_security.adapters.env_adapter import EnvSecretAdapter
from k9_aif_abb.k9_factories.security_factory import SecretManagerFactory


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure test env vars are isolated."""
    monkeypatch.delenv("K9_TEST_SECRET", raising=False)
    monkeypatch.delenv("K9_MISSING",     raising=False)


# ── BaseSecretManager contract ────────────────────────────────────────────────

def test_base_is_abstract():
    with pytest.raises(TypeError):
        BaseSecretManager()  # type: ignore


def test_get_many_partial(monkeypatch):
    monkeypatch.setenv("K9_TEST_SECRET", "hello")
    adapter = EnvSecretAdapter()
    result = adapter.get_many(["K9_TEST_SECRET", "K9_MISSING"])
    assert result == {"K9_TEST_SECRET": "hello"}


def test_exists_true(monkeypatch):
    monkeypatch.setenv("K9_TEST_SECRET", "hello")
    adapter = EnvSecretAdapter()
    assert adapter.exists("K9_TEST_SECRET") is True


def test_exists_false():
    adapter = EnvSecretAdapter()
    assert adapter.exists("K9_MISSING") is False


# ── EnvSecretAdapter ──────────────────────────────────────────────────────────

def test_env_get_present(monkeypatch):
    monkeypatch.setenv("K9_TEST_SECRET", "mysecret")
    adapter = EnvSecretAdapter()
    assert adapter.get("K9_TEST_SECRET") == "mysecret"


def test_env_get_missing():
    adapter = EnvSecretAdapter()
    with pytest.raises(KeyError):
        adapter.get("K9_MISSING")


def test_env_get_empty_string(monkeypatch):
    monkeypatch.setenv("K9_TEST_SECRET", "")
    adapter = EnvSecretAdapter()
    with pytest.raises(KeyError):
        adapter.get("K9_TEST_SECRET")


# ── SecretManagerFactory ──────────────────────────────────────────────────────

def test_factory_default_is_env():
    sm = SecretManagerFactory.create({})
    assert isinstance(sm, EnvSecretAdapter)


def test_factory_explicit_env():
    sm = SecretManagerFactory.create({"secrets": {"provider": "env"}})
    assert isinstance(sm, EnvSecretAdapter)


def test_factory_unknown_provider():
    with pytest.raises(ValueError, match="Unknown secret manager"):
        SecretManagerFactory.create({"secrets": {"provider": "nonexistent_xyz"}})


def test_factory_get_env():
    sm = SecretManagerFactory.get("env")
    assert isinstance(sm, EnvSecretAdapter)


def test_factory_register_custom():
    class DummyAdapter(BaseSecretManager):
        def __init__(self, config=None): pass

        def get(self, key):
            return "dummy"

    SecretManagerFactory.register("dummy_test", DummyAdapter)
    sm = SecretManagerFactory.create({"secrets": {"provider": "dummy_test"}})
    assert sm.get("anything") == "dummy"
