# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_core/inference/provider_registry.py

import logging
from typing import Dict, Type

from k9_aif_abb.k9_core.inference.base_provider_adapter import BaseProviderAdapter

log = logging.getLogger("ProviderAdapterRegistry")


class ProviderAdapterRegistry:
    """
    K9-AIF Inference ABB — ProviderAdapterRegistry
    ------------------------------------------------
    Central registry that maps backend/provider names to adapter classes.

    OOB adapters (ollama, openai, openai-compatible) are registered
    automatically on first use. Custom adapters can be registered by
    solution code before LLMFactory.bootstrap() is called — no changes
    to LLMFactory or any other ABB component are required.

    Usage (SBB custom adapter):
        from k9_aif_abb.k9_core.inference.provider_registry import ProviderAdapterRegistry
        ProviderAdapterRegistry.register("watsonx", WatsonxProviderAdapter)
    """

    _adapters: Dict[str, Type[BaseProviderAdapter]] = {}
    _defaults_loaded: bool = False

    @classmethod
    def register(cls, backend: str, adapter_cls: Type[BaseProviderAdapter]) -> None:
        """Register a provider adapter under the given backend name."""
        key = backend.lower().strip()
        cls._adapters[key] = adapter_cls
        log.debug("Registered provider adapter: %s -> %s", key, adapter_cls.__name__)

    @classmethod
    def resolve(cls, backend: str) -> BaseProviderAdapter:
        """
        Return an adapter instance for the given backend name.
        Raises ValueError with an actionable message if not found.
        """
        if not cls._defaults_loaded:
            cls._load_defaults()

        key = backend.lower().strip()
        adapter_cls = cls._adapters.get(key)
        if adapter_cls is None:
            available = ", ".join(sorted(cls._adapters.keys()))
            raise ValueError(
                f"No provider adapter registered for backend '{backend}'. "
                f"Available: [{available}]. "
                f"Register a custom adapter with ProviderAdapterRegistry.register()."
            )
        return adapter_cls()

    @classmethod
    def _load_defaults(cls) -> None:
        """Lazily register the OOB adapters to avoid circular imports at module load."""
        from k9_aif_abb.k9_core.inference.ollama_provider_adapter import OllamaProviderAdapter
        from k9_aif_abb.k9_core.inference.openai_provider_adapter import OpenAIProviderAdapter

        cls._adapters.setdefault("ollama", OllamaProviderAdapter)
        cls._adapters.setdefault("openai", OpenAIProviderAdapter)
        cls._adapters.setdefault("openai-compatible", OpenAIProviderAdapter)
        cls._defaults_loaded = True
        log.debug("Default provider adapters loaded: ollama, openai, openai-compatible")

    @classmethod
    def reset(cls) -> None:
        """Clear all registrations. Used in tests."""
        cls._adapters.clear()
        cls._defaults_loaded = False
