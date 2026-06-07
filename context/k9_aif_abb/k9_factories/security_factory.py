# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_factories/security_factory.py

from typing import Type, Dict, Any
from threading import Lock
import logging

class SecurityFactory:
    """Static Factory - provisions encryption, IAM, and access control modules."""

    _registry: Dict[str, Type[Any]] = {}
    _bootstrapped = False
    _lock = Lock()
    logger = logging.getLogger("SecurityFactory")

    def __init__(self, *args, **kwargs):
        raise RuntimeError("SecurityFactory is static and cannot be instantiated")

    @staticmethod
    def register(name: str, sec_cls: Type[Any]) -> None:
        with SecurityFactory._lock:
            SecurityFactory._registry[name] = sec_cls
            SecurityFactory.logger.debug(f"Registered security backend '{name}'")

    @staticmethod
    def get(name: str, **kwargs: Any):
        try:
            cls = SecurityFactory._registry[name]
            return cls(**kwargs)
        except KeyError:
            raise ValueError(f"Unknown security backend: {name}")

    @staticmethod
    def bootstrap() -> None:
        if SecurityFactory._bootstrapped:
            return
        SecurityFactory._bootstrapped = True
        SecurityFactory.logger.info("[Factory] Bootstrapped SecurityFactory")