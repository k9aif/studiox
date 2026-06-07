# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_factories/governance_factory.py

from typing import Type, Dict, Any
from threading import Lock
import logging

class GovernanceFactory:
    """Static Factory - provisions compliance, ethics, and rule engines."""

    _registry: Dict[str, Type[Any]] = {}
    _bootstrapped = False
    _lock = Lock()
    logger = logging.getLogger("GovernanceFactory")

    def __init__(self, *args, **kwargs):
        raise RuntimeError("GovernanceFactory is static and cannot be instantiated")

    @staticmethod
    def register(name: str, gov_cls: Type[Any]) -> None:
        with GovernanceFactory._lock:
            GovernanceFactory._registry[name] = gov_cls
            GovernanceFactory.logger.debug(f"Registered governance module '{name}'")

    @staticmethod
    def get(name: str, **kwargs: Any):
        try:
            cls = GovernanceFactory._registry[name]
            return cls(**kwargs)
        except KeyError:
            raise ValueError(f"Unknown governance module: {name}")

    @staticmethod
    def bootstrap() -> None:
        if GovernanceFactory._bootstrapped:
            return
        GovernanceFactory._bootstrapped = True
        GovernanceFactory.logger.info("[Factory] Bootstrapped GovernanceFactory")