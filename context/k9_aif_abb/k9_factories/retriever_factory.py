# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type

from k9_aif_abb.k9_core.retrieval.base_retriever import BaseRetriever


class RetrieverFactory:
    """
    Config-driven factory for retriever instances.

    Pattern:
      - bootstrap(config)
      - register(alias, retriever_cls)
      - get(alias)
    """

    _instances: Dict[str, BaseRetriever] = {}
    _registry: Dict[str, Type[BaseRetriever]] = {}
    _cfg: Dict[str, Any] = {}
    _bootstrapped: bool = False

    @classmethod
    def bootstrap(cls, config: Optional[Dict[str, Any]] = None) -> None:
        config = config or {}
        cls._cfg = config.get("retrieval", {})
        cls._bootstrapped = True
        logging.getLogger("RetrieverFactory").info(
            "[RetrieverFactory] Bootstrapped"
        )

    @classmethod
    def register(cls, alias: str, retriever_cls: Type[BaseRetriever]) -> None:
        if not issubclass(retriever_cls, BaseRetriever):
            raise TypeError(
                f"Retriever '{alias}' must inherit from BaseRetriever"
            )
        cls._registry[alias] = retriever_cls

    @classmethod
    def get(cls, alias: Optional[str] = None) -> BaseRetriever:
        if not cls._bootstrapped:
            raise RuntimeError(
                "RetrieverFactory.get() called before bootstrap()."
            )

        log = logging.getLogger("RetrieverFactory")

        alias = alias or cls._cfg.get("default_retriever", "k9")

        if alias in cls._instances:
            return cls._instances[alias]

        retriever_cls = cls._registry.get(alias)
        if not retriever_cls:
            raise KeyError(
                f"Retriever alias '{alias}' is not registered."
            )

        instance = retriever_cls(config=cls._cfg)
        cls._instances[alias] = instance
        log.info("[RetrieverFactory] Created retriever '%s'", alias)
        return instance

    @classmethod
    def reset(cls) -> None:
        cls._instances.clear()
        cls._registry.clear()
        cls._cfg = {}
        cls._bootstrapped = False