# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_factories/router_factory.py

from typing import Type, Dict, Any
from threading import Lock
import logging


class RouterFactory:
    """
    K9-AIF Factory ABB - RouterFactory
    ----------------------------------
    Static factory that provisions orchestration routers and flow dispatchers.
    - Non-instantiable by design.
    - Ensures thread-safe registration.
    - Central registry for all router SBBs.
    """

    _registry: Dict[str, Type[Any]] = {}
    _bootstrapped = False
    _lock = Lock()
    logger = logging.getLogger("RouterFactory")

    def __init__(self, *args, **kwargs):
        raise RuntimeError("RouterFactory is static and cannot be instantiated")

    # ------------------------------------------------------------------
    # Bootstrap lifecycle
    # ------------------------------------------------------------------
    @staticmethod
    def bootstrap() -> None:
        """Initialize the factory (once per runtime)."""
        with RouterFactory._lock:
            if RouterFactory._bootstrapped:
                return
            RouterFactory._bootstrapped = True
            RouterFactory.logger.info("[Factory] Bootstrapped RouterFactory")

    # ------------------------------------------------------------------
    # Registration and retrieval
    # ------------------------------------------------------------------
    @staticmethod
    def register(name: str, router_cls: Type[Any]) -> None:
        """Register a router class under a symbolic name."""
        with RouterFactory._lock:
            RouterFactory._registry[name] = router_cls
            RouterFactory.logger.debug(f"[Factory] Registered router '{name}'")

    @staticmethod
    def get(name: str, **kwargs: Any):
        """Retrieve and instantiate a registered router."""
        try:
            cls = RouterFactory._registry[name]
            instance = cls(**kwargs)
            RouterFactory.logger.debug(f"[Factory] Provisioned router '{name}'")
            return instance
        except KeyError:
            raise ValueError(f"Unknown router: {name}")

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------
    @staticmethod
    def list_registered() -> Dict[str, str]:
        """Return a summary of registered routers."""
        return {name: cls.__name__ for name, cls in RouterFactory._registry.items()}