# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
EmbeddingServiceFactory — config-driven provider selection for embedding services.

YAML config::

    vectordb:
      embedding_provider: ollama          # ollama (default)
      embedding_model: nomic-embed-text   # model name on the provider
      embedding_endpoint: http://localhost:11434

Usage::

    from k9_aif_abb.k9_factories.embedding_factory import EmbeddingServiceFactory

    svc = EmbeddingServiceFactory.create(config)
    vec = svc.embed("K9-AIF is an agentic framework")
"""

from threading import Lock
from typing import Any, Dict, Type
import logging

from k9_aif_abb.k9_core.inference.base_embedding_service import BaseEmbeddingService

log = logging.getLogger("EmbeddingServiceFactory")


class EmbeddingServiceFactory:
    """Static factory — provisions embedding service backends."""

    _registry: Dict[str, Type[BaseEmbeddingService]] = {}
    _lock = Lock()
    _bootstrapped = False

    def __init__(self, *args, **kwargs):
        raise RuntimeError("EmbeddingServiceFactory is static — use create()")

    @staticmethod
    def _ensure_defaults() -> None:
        if EmbeddingServiceFactory._bootstrapped:
            return
        with EmbeddingServiceFactory._lock:
            if EmbeddingServiceFactory._bootstrapped:
                return
            from k9_aif_abb.k9_data.embedding.ollama_embedding_service import OllamaEmbeddingService
            EmbeddingServiceFactory._registry["ollama"] = OllamaEmbeddingService
            EmbeddingServiceFactory._bootstrapped = True

    @staticmethod
    def register(name: str, cls: Type[BaseEmbeddingService]) -> None:
        EmbeddingServiceFactory._ensure_defaults()
        with EmbeddingServiceFactory._lock:
            EmbeddingServiceFactory._registry[name.lower()] = cls

    @staticmethod
    def create(config: Dict[str, Any] = None) -> BaseEmbeddingService:
        EmbeddingServiceFactory._ensure_defaults()
        cfg = config or {}
        provider = cfg.get("vectordb", {}).get("embedding_provider", "ollama").lower()
        log.info("[Factory] Creating embedding service: %s", provider)
        cls = EmbeddingServiceFactory._registry.get(provider)
        if not cls:
            raise ValueError(
                f"Unknown embedding provider: {provider}. "
                f"Registered: {list(EmbeddingServiceFactory._registry.keys())}"
            )
        return cls(config=cfg)
