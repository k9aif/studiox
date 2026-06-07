# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_factories/mcp_client_connection_factory.py

from typing import Dict, Type, Any
from threading import Lock
import logging

class MCPClientConnectionFactory:
    """Static Factory - provisions Model Context Protocol (MCP) client connectors."""

    _registry: Dict[str, Type[Any]] = {}
    _bootstrapped = False
    _lock = Lock()
    logger = logging.getLogger("MCPClientConnectionFactory")

    def __init__(self, *args, **kwargs):
        raise RuntimeError("MCPClientConnectionFactory is static and cannot be instantiated")

    @staticmethod
    def register(name: str, conn_cls: Type[Any]) -> None:
        with MCPClientConnectionFactory._lock:
            MCPClientConnectionFactory._registry[name] = conn_cls
            MCPClientConnectionFactory.logger.debug(f"Registered MCP client '{name}'")

    @staticmethod
    def get(name: str, **kwargs: Any):
        try:
            cls = MCPClientConnectionFactory._registry[name]
            return cls(**kwargs)
        except KeyError:
            raise ValueError(f"Unknown MCP client: {name}")

    @staticmethod
    def bootstrap() -> None:
        if MCPClientConnectionFactory._bootstrapped:
            return
        MCPClientConnectionFactory._bootstrapped = True
        MCPClientConnectionFactory.logger.info("[Factory] Bootstrapped MCPClientConnectionFactory")