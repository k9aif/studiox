# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_factories/persistence_factory.py
#
# PersistenceFactory - static factory for governed persistence backends
# Supports: SQLite, ChromaDB, and pluggable future providers.

from typing import Any, Dict, Type
from threading import Lock
import logging

from k9_aif_abb.k9_persistence.sqlite_persistence import SQLitePersistence
from k9_aif_abb.k9_persistence.chromadb_persistence import ChromaDBPersistence


class PersistenceFactory:
    """Static Factory - provisions persistence backends (SQLite, ChromaDB, etc.)."""

    _registry: Dict[str, Type[Any]] = {
        "sqlite": SQLitePersistence,
        "chromadb": ChromaDBPersistence,
    }
    _bootstrapped = False
    _lock = Lock()
    logger = logging.getLogger("PersistenceFactory")

    def __init__(self, *args, **kwargs):
        raise RuntimeError("PersistenceFactory is static and cannot be instantiated")

    # ------------------------------------------------------------------
    @staticmethod
    def register(name: str, cls: Type[Any]) -> None:
        """Register a new persistence backend class."""
        with PersistenceFactory._lock:
            PersistenceFactory._registry[name.lower()] = cls
            PersistenceFactory.logger.debug(f"[Factory] Registered persistence backend '{name}'")

    # ------------------------------------------------------------------
    @staticmethod
    def get(name: str, **kwargs: Any):
        """Retrieve an instance of a registered persistence backend."""
        cls = PersistenceFactory._registry.get(name.lower())
        if not cls:
            raise ValueError(f"Unknown persistence backend: {name}")
        instance = cls(**kwargs)
        PersistenceFactory.logger.info(f"[Factory] Activated {name}")
        return instance

    # ------------------------------------------------------------------
    @staticmethod
    def create(config: Dict[str, Any], monitor=None):
        """
        Create a governed persistence backend from ABB or SBB config.
        Supports vectordb.backend, vectordb.provider, or legacy persistence blocks.
        """
        try:
            vectordb_cfg = config.get("vectordb", {})

            store = (
                vectordb_cfg.get("backend")               
                or vectordb_cfg.get("provider")           
                or (config.get("persistence", [{}])[0].get("name")
                    if isinstance(config.get("persistence"), list)
                    else config.get("persistence", {}).get("backend"))
                or "sqlite"
            ).lower()

            PersistenceFactory.logger.info(f"[Factory] Creating persistence for provider: {store}")

            if store not in PersistenceFactory._registry:
                raise ValueError(f"Persistence provider '{store}' not registered")

            cls = PersistenceFactory._registry[store]
            instance = cls(config=config, monitor=monitor)
            PersistenceFactory.logger.info(f"[Factory] Created {store} persistence backend")
            return instance

        except Exception as e:
            PersistenceFactory.logger.error(f"[Factory] Failed to create persistence backend: {e}")
            return None

    # ------------------------------------------------------------------
    @staticmethod
    def bootstrap() -> None:
        """Bootstrap factory (called once during system initialization)."""
        if PersistenceFactory._bootstrapped:
            return
        PersistenceFactory._bootstrapped = True
        PersistenceFactory.logger.info("[Factory] Bootstrapped PersistenceFactory")