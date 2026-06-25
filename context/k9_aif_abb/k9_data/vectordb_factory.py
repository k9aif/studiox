# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""VectorDB Factory — config-driven provider selection for vector stores."""

import importlib
import logging
from threading import Lock
from typing import Any, Dict, Type

from k9_aif_abb.k9_data.base_vectordb import BaseVectorDB

log = logging.getLogger("VectorDBFactory")


class VectorDBFactory:

    _registry: Dict[str, Type[Any]] = {}
    _lock = Lock()
    _bootstrapped = False

    def __init__(self, *args, **kwargs):
        raise RuntimeError("VectorDBFactory is static — use from_config() or create()")

    @staticmethod
    def _ensure_defaults() -> None:
        if VectorDBFactory._bootstrapped:
            return
        with VectorDBFactory._lock:
            if VectorDBFactory._bootstrapped:
                return
            from k9_aif_abb.k9_data.adapters.chromadb_adapter import ChromaDBAdapter
            from k9_aif_abb.k9_data.adapters.milvus_adapter import MilvusAdapter
            from k9_aif_abb.k9_data.adapters.qdrant_adapter import QdrantAdapter
            from k9_aif_abb.k9_data.adapters.pgvector_adapter import PgVectorAdapter
            VectorDBFactory._registry["chromadb"] = ChromaDBAdapter
            VectorDBFactory._registry["milvus"] = MilvusAdapter
            VectorDBFactory._registry["qdrant"] = QdrantAdapter
            VectorDBFactory._registry["pgvector"] = PgVectorAdapter
            VectorDBFactory._bootstrapped = True

    @staticmethod
    def register(name: str, cls: Type[BaseVectorDB]) -> None:
        VectorDBFactory._ensure_defaults()
        with VectorDBFactory._lock:
            VectorDBFactory._registry[name.lower()] = cls

    @staticmethod
    def create(config: Dict[str, Any] = None) -> BaseVectorDB:
        VectorDBFactory._ensure_defaults()
        cfg = config or {}
        provider = cfg.get("vectordb", {}).get("provider", "chromadb").lower()
        log.info("[VectorDBFactory] Creating provider: %s", provider)

        cls = VectorDBFactory._registry.get(provider)
        if cls:
            return cls(config=cfg)

        raise ValueError(f"Unknown VectorDB provider: {provider}. Registered: {list(VectorDBFactory._registry.keys())}")

    @staticmethod
    def from_config(cfg: dict) -> BaseVectorDB:
        """Legacy method — supports both registry and importlib-based loading."""
        VectorDBFactory._ensure_defaults()
        vdb_cfg = cfg.get("vectordb", {}) or {}
        provider = vdb_cfg.get("provider", "").lower()

        if provider in VectorDBFactory._registry:
            return VectorDBFactory._registry[provider](config=cfg)

        module = vdb_cfg.get("module")
        class_name = vdb_cfg.get("class")
        if module and class_name:
            mod = importlib.import_module(module)
            cls = getattr(mod, class_name)
            return cls(cfg)

        return VectorDBFactory.create(cfg)
