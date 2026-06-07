# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_factories/model_router_factory.py

import logging
from typing import Dict, Any

from k9_aif_abb.k9_factories.llm_factory import LLMFactory
from k9_aif_abb.k9_inference.catalog.model_catalog import ModelCatalog
from k9_aif_abb.k9_inference.routers.base_model_router import BaseModelRouter
from k9_aif_abb.k9_inference.routers.default_model_router import DefaultModelRouter
from k9_aif_abb.k9_inference.routers.k9_model_router import K9ModelRouter

from k9_aif_abb.k9_core.persistence.base_persistence import MemoryPersistence
from k9_aif_abb.k9_storage.sqlite_database_storage import SQLiteDatabaseStorage
from k9_aif_abb.k9_storage.postgres_database_storage import PostgresDatabaseStorage
from k9_aif_abb.k9_storage.routing_state_store import RoutingStateStore


class ModelRouterFactory:
    """
    K9-AIF Factory ABB - ModelRouterFactory
    ---------------------------------------
    Responsible for provisioning model router instances.

    Responsibilities:
      - read inference router config
      - build model catalog
      - build router persistence backend
      - instantiate configured router implementation
      - cache router instances if needed
    """

    _instances: Dict[str, BaseModelRouter] = {}
    logger = logging.getLogger("ModelRouterFactory")

    @classmethod
    def get_router(cls, config: Dict[str, Any]) -> BaseModelRouter:
        """
        Return a configured model router instance.

        Expected config patterns:
          1. Nested:
             inference:
               router:
                 type: k9_model_router
               model_catalog:
                 ...
          2. Flattened:
             router:
               type: k9_model_router
             model_catalog:
               ...
        """
        cfg = cls._normalize_config(config)

        inf_cfg = cfg.get("inference", {})
        router_cfg = inf_cfg.get("router", {})
        router_type = (router_cfg.get("type") or "k9").lower()

        if not LLMFactory.is_bootstrapped():
            LLMFactory.bootstrap(config)

        persistence_cfg = router_cfg.get("persistence", {})
        provider = (persistence_cfg.get("provider") or "sqlite").lower()
        enabled = persistence_cfg.get("enabled", True)
        cache_key = f"{router_type}:{enabled}:{provider}"

        if cache_key in cls._instances:
            return cls._instances[cache_key]

        catalog = cls._build_catalog(cfg)

        if router_type in ("k9", "k9_model_router"):
            state_store = cls._build_router_state_store(cfg)
            router = K9ModelRouter(
                catalog=catalog,
                config=cfg,
                state_store=state_store,
            )

        elif router_type == "default":
            default_alias = router_cfg.get("default_model_alias", "general")
            router = DefaultModelRouter(default_alias)

        else:
            raise ValueError(f"Unsupported router type: {router_type}")

        cls._instances[cache_key] = router
        cls.logger.info("Router ready -> %s", router.__class__.__name__)
        return router

    @classmethod
    def _build_router_state_store(cls, config: Dict[str, Any]) -> RoutingStateStore:
        """
        Build router state store based on inference.router.persistence config.
        """
        inf_cfg = config.get("inference", {})
        router_cfg = inf_cfg.get("router", {})
        persistence_cfg = router_cfg.get("persistence", {})

        enabled = persistence_cfg.get("enabled", True)
        provider = (persistence_cfg.get("provider") or "sqlite").lower()

        if not enabled:
            cls.logger.info(
                "Model router persistence disabled; using MemoryPersistence."
            )
            storage = MemoryPersistence()

        elif provider == "sqlite":
            sqlite_cfg = persistence_cfg.get("sqlite", {})
            db_path = sqlite_cfg.get("db_path", "./runtime/k9_model_router.db")
            cls.logger.info(
                "Model router persistence provider -> sqlite (%s)",
                db_path,
            )
            storage = SQLiteDatabaseStorage(db_path=db_path)

        elif provider == "postgres":
            cls.logger.info("Model router persistence provider -> postgres")
            storage = PostgresDatabaseStorage(config=config)

        elif provider == "memory":
            cls.logger.info("Model router persistence provider -> memory")
            storage = MemoryPersistence()

        else:
            raise ValueError(
                f"Unsupported model router persistence provider: {provider}"
            )

        return RoutingStateStore(storage)

    @classmethod
    def _normalize_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize flattened config to inference.* shape.
        """
        if "inference" not in config and any(
            k in config for k in ("router", "model_catalog", "llm_factory")
        ):
            return {
                "inference": {
                    "router": config.get("router", {}),
                    "model_catalog": config.get("model_catalog", {}),
                    "llm_factory": config.get("llm_factory", {}),
                },
                "postgres": config.get("postgres", {}),
            }

        return config

    @classmethod
    def _build_catalog(cls, config: Dict[str, Any]) -> ModelCatalog:
        """
        Build ModelCatalog from config.

        Preferred config:
          inference:
            model_catalog:
              default_model: general
              models:
                general:
                  provider: ollama
                  llm_ref: general
                  capabilities: [chat]
                confidential:
                  provider: watsonx
                  llm_ref: secure_general
                  capabilities: [confidential]

        Fallback:
          derive minimal catalog from inference.llm_factory.models
        """
        inf_cfg = config.get("inference", {})
        catalog_cfg = inf_cfg.get("model_catalog", {})

        if not catalog_cfg:
            llm_cfg = inf_cfg.get("llm_factory", {})
            llm_models = llm_cfg.get("models", {}) or {}

            derived_models = {
                alias: {
                    "provider": llm_cfg.get("provider", "ollama"),
                    "llm_ref": alias,
                    "capabilities": [alias],
                }
                for alias in llm_models
            }

            default_model = (
                "general"
                if "general" in derived_models
                else next(iter(derived_models), None)
            )

            catalog_cfg = {
                "default_model": default_model,
                "models": derived_models,
            }

            cls.logger.info(
                "[ModelRouterFactory] model_catalog missing; "
                "derived minimal catalog from llm_factory.models"
            )

        return ModelCatalog(catalog_cfg)

    @classmethod
    def reset(cls) -> None:
        cls._instances.clear()
        cls.logger.info("ModelRouterFactory reset complete.")