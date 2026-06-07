# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_factories/connector_factory.py

from typing import Type, Dict, Any
from threading import Lock
import logging

class ConnectorFactory:
    """Static Factory - provisions integration connectors (Appian, MCP, APIs)."""

    _registry: Dict[str, Type[Any]] = {}
    _bootstrapped = False
    _lock = Lock()
    logger = logging.getLogger("ConnectorFactory")

    def __init__(self, *args, **kwargs):
        raise RuntimeError("ConnectorFactory is static and cannot be instantiated")

    @staticmethod
    def register(name: str, connector_cls: Type[Any]) -> None:
        with ConnectorFactory._lock:
            ConnectorFactory._registry[name] = connector_cls
            ConnectorFactory.logger.debug(f"Registered connector '{name}'")

    @staticmethod
    def get(name: str, **kwargs: Any):
        try:
            cls = ConnectorFactory._registry[name]
            return cls(**kwargs)
        except KeyError:
            raise ValueError(f"Unknown connector: {name}")

    @staticmethod
    def bootstrap() -> None:
        if ConnectorFactory._bootstrapped:
            return
        ConnectorFactory._bootstrapped = True
        ConnectorFactory.logger.info("[Factory] Bootstrapped ConnectorFactory")