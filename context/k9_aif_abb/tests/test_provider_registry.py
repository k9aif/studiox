# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# Tests: ProviderAdapterRegistry + provider adapters + LLMFactory dispatch

import os
import pytest
from unittest.mock import patch, MagicMock

from k9_aif_abb.k9_core.inference.provider_registry import ProviderAdapterRegistry
from k9_aif_abb.k9_core.inference.base_provider_adapter import BaseProviderAdapter
from k9_aif_abb.k9_core.inference.ollama_provider_adapter import OllamaProviderAdapter
from k9_aif_abb.k9_core.inference.openai_provider_adapter import OpenAIProviderAdapter
from k9_aif_abb.k9_core.inference.ollama_llm import OllamaLLM
from k9_aif_abb.k9_core.inference.openai_llm import OpenAILLM
from k9_aif_abb.k9_factories.llm_factory import LLMFactory


# ── ProviderAdapterRegistry ────────────────────────────────────────────────

class TestProviderAdapterRegistry:

    def setup_method(self):
        ProviderAdapterRegistry.reset()

    def test_defaults_loaded_on_first_resolve(self):
        adapter = ProviderAdapterRegistry.resolve("ollama")
        assert isinstance(adapter, OllamaProviderAdapter)

    def test_openai_backend_resolves(self):
        adapter = ProviderAdapterRegistry.resolve("openai")
        assert isinstance(adapter, OpenAIProviderAdapter)

    def test_openai_compatible_backend_resolves(self):
        adapter = ProviderAdapterRegistry.resolve("openai-compatible")
        assert isinstance(adapter, OpenAIProviderAdapter)

    def test_unknown_backend_raises_valueerror(self):
        with pytest.raises(ValueError, match="No provider adapter registered"):
            ProviderAdapterRegistry.resolve("nonexistent-provider")

    def test_custom_adapter_registration(self):
        class CustomAdapter(BaseProviderAdapter):
            provider_name = "custom"
            def create_llm(self, model_name, factory_cfg, extra_kwargs):
                return MagicMock()

        ProviderAdapterRegistry.register("custom", CustomAdapter)
        adapter = ProviderAdapterRegistry.resolve("custom")
        assert isinstance(adapter, CustomAdapter)

    def test_register_does_not_affect_other_backends(self):
        class AnotherAdapter(BaseProviderAdapter):
            provider_name = "another"
            def create_llm(self, model_name, factory_cfg, extra_kwargs):
                return MagicMock()

        ProviderAdapterRegistry.register("another", AnotherAdapter)
        # Ollama still resolves correctly
        adapter = ProviderAdapterRegistry.resolve("ollama")
        assert isinstance(adapter, OllamaProviderAdapter)


# ── OllamaProviderAdapter ──────────────────────────────────────────────────

class TestOllamaProviderAdapter:

    def test_creates_ollama_llm(self):
        adapter = OllamaProviderAdapter()
        factory_cfg = {"base_url": "http://localhost:11434"}
        llm = adapter.create_llm("llama3.2:1b", factory_cfg, {})
        assert isinstance(llm, OllamaLLM)
        assert llm.model == "llama3.2:1b"
        assert llm.host == "http://localhost:11434"

    def test_default_base_url(self):
        adapter = OllamaProviderAdapter()
        llm = adapter.create_llm("llama3.2:1b", {}, {})
        assert llm.host == "http://localhost:11434"

    def test_extra_kwargs_forwarded(self):
        adapter = OllamaProviderAdapter()
        llm = adapter.create_llm("llama3.2:1b", {}, {"temperature": 0.1})
        assert llm.kwargs.get("temperature") == 0.1


# ── OpenAIProviderAdapter ──────────────────────────────────────────────────

class TestOpenAIProviderAdapter:

    def test_creates_openai_llm_via_api_key_env(self):
        adapter = OpenAIProviderAdapter()
        factory_cfg = {"api_key_env": "TEST_OPENAI_KEY"}
        with patch.dict(os.environ, {"TEST_OPENAI_KEY": "sk-test-123"}):
            llm = adapter.create_llm("gpt-4o-mini", factory_cfg, {})
        assert isinstance(llm, OpenAILLM)
        assert llm.model == "gpt-4o-mini"

    def test_creates_grok_llm_with_base_url(self):
        adapter = OpenAIProviderAdapter()
        factory_cfg = {
            "api_key_env": "GROK_API_KEY",
            "base_url": "https://api.x.ai/v1",
        }
        with patch.dict(os.environ, {"GROK_API_KEY": "xai-test-456"}):
            llm = adapter.create_llm("grok-3-mini", factory_cfg, {})
        assert isinstance(llm, OpenAILLM)
        assert llm.model == "grok-3-mini"

    def test_missing_api_key_env_raises(self):
        adapter = OpenAIProviderAdapter()
        factory_cfg = {"api_key_env": "MISSING_KEY_XYZ"}
        clean_env = {k: v for k, v in os.environ.items() if k != "MISSING_KEY_XYZ"}
        with patch.dict(os.environ, clean_env, clear=True):
            with pytest.raises(EnvironmentError, match="MISSING_KEY_XYZ"):
                adapter.create_llm("gpt-4o", factory_cfg, {})

    def test_legacy_api_key_with_env_placeholder(self):
        adapter = OpenAIProviderAdapter()
        factory_cfg = {"api_key": "${MY_API_KEY}"}
        with patch.dict(os.environ, {"MY_API_KEY": "sk-legacy-789"}):
            llm = adapter.create_llm("gpt-4o-mini", factory_cfg, {})
        assert isinstance(llm, OpenAILLM)

    def test_implicit_openai_api_key_fallback(self):
        adapter = OpenAIProviderAdapter()
        factory_cfg = {}  # no api_key_env or api_key
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-implicit"}):
            llm = adapter.create_llm("gpt-4o-mini", factory_cfg, {})
        assert isinstance(llm, OpenAILLM)

    def test_no_key_at_all_raises(self):
        adapter = OpenAIProviderAdapter()
        factory_cfg = {}
        clean_env = {k: v for k, v in os.environ.items()
                     if k not in ("OPENAI_API_KEY", "GROK_API_KEY")}
        with patch.dict(os.environ, clean_env, clear=True):
            with pytest.raises(EnvironmentError, match="api_key_env"):
                adapter.create_llm("gpt-4o-mini", factory_cfg, {})


# ── LLMFactory dispatch via registry ──────────────────────────────────────

class TestLLMFactoryProviderDispatch:

    def setup_method(self):
        LLMFactory.reset()
        ProviderAdapterRegistry.reset()

    def _ollama_config(self):
        return {
            "inference": {
                "llm_factory": {
                    "backend": "ollama",
                    "base_url": "http://localhost:11434",
                    "models": {
                        "general": {"model": "llama3.2:1b", "temperature": 0.3}
                    },
                }
            }
        }

    def _openai_config(self, env_var="OPENAI_API_KEY"):
        return {
            "inference": {
                "llm_factory": {
                    "backend": "openai",
                    "api_key_env": env_var,
                    "models": {
                        "general": {"model": "gpt-4o-mini", "temperature": 0.3}
                    },
                }
            }
        }

    def _grok_config(self):
        return {
            "inference": {
                "llm_factory": {
                    "backend": "openai-compatible",
                    "base_url": "https://api.x.ai/v1",
                    "api_key_env": "GROK_API_KEY",
                    "models": {
                        "general": {"model": "grok-3-mini", "temperature": 0.3}
                    },
                }
            }
        }

    def test_ollama_backend_creates_ollama_llm(self):
        LLMFactory.bootstrap(self._ollama_config())
        llm = LLMFactory.get("general")
        assert isinstance(llm, OllamaLLM)

    def test_openai_backend_creates_openai_llm(self):
        LLMFactory.bootstrap(self._openai_config())
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            llm = LLMFactory.get("general")
        assert isinstance(llm, OpenAILLM)
        assert llm.model == "gpt-4o-mini"

    def test_grok_backend_creates_openai_llm_with_base_url(self):
        LLMFactory.bootstrap(self._grok_config())
        with patch.dict(os.environ, {"GROK_API_KEY": "xai-test"}):
            llm = LLMFactory.get("general")
        assert isinstance(llm, OpenAILLM)
        assert llm.model == "grok-3-mini"

    def test_llm_instances_are_cached(self):
        LLMFactory.bootstrap(self._ollama_config())
        a = LLMFactory.get("general")
        b = LLMFactory.get("general")
        assert a is b

    def test_custom_adapter_used_by_factory(self):
        """Future provider: register custom adapter, factory uses it automatically."""
        class FakeLLM(OllamaLLM):
            pass

        class FakeAdapter(BaseProviderAdapter):
            provider_name = "fake"
            def create_llm(self, model_name, factory_cfg, extra_kwargs):
                return FakeLLM(host="http://fake", model=model_name)

        ProviderAdapterRegistry.register("fake", FakeAdapter)
        cfg = {
            "inference": {
                "llm_factory": {
                    "backend": "fake",
                    "models": {"general": {"model": "fake-model"}},
                }
            }
        }
        LLMFactory.bootstrap(cfg)
        llm = LLMFactory.get("general")
        assert isinstance(llm, FakeLLM)

    def test_public_api_unchanged(self):
        """Verify existing public surface: bootstrap, get, get_model, reset."""
        LLMFactory.bootstrap(self._ollama_config())
        assert LLMFactory.is_bootstrapped()
        assert LLMFactory.get_model("general") == "llama3.2:1b"
        llm = LLMFactory.get("general")
        assert llm is not None
        LLMFactory.reset()
        assert not LLMFactory.is_bootstrapped()
