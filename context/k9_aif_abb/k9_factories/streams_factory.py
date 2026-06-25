# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
StreamsFactory — static factory for K9 enterprise context fabric providers.

Pre-registered providers: in_memory (default, zero deps), kafka.

YAML config::

    streams:
      enabled: false            # false by default — opt-in, zero impact on existing code
      provider: in_memory       # in_memory (default) | kafka
      window:
        max_events:  500        # max events retained in context window
        ttl_seconds: 86400      # event TTL in seconds (24h default)
      kafka:
        bootstrap_servers: "${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
        security_protocol: PLAINTEXT

Usage::

    from k9_aif_abb.k9_factories.streams_factory import StreamsFactory

    fabric = StreamsFactory.create_fabric(config)   # None when disabled
    window = StreamsFactory.create_window(config)   # None when disabled
"""

import logging
from threading import Lock
from typing import Any, Dict, Optional, Type

log = logging.getLogger("StreamsFactory")


class StreamsFactory:
    """Static factory for K9 enterprise context fabric and context window providers."""

    _fabric_registry: Dict[str, Type[Any]] = {}
    _window_registry: Dict[str, Type[Any]] = {}
    _lock = Lock()
    _bootstrapped = False

    def __init__(self, *args, **kwargs) -> None:
        raise RuntimeError("StreamsFactory is static and cannot be instantiated")

    @staticmethod
    def _ensure_defaults() -> None:
        if StreamsFactory._bootstrapped:
            return
        with StreamsFactory._lock:
            if StreamsFactory._bootstrapped:
                return
            from k9_aif_abb.k9_streams.in_memory_stream import (
                InMemoryContextWindow,
                InMemoryEventFabric,
            )
            StreamsFactory._fabric_registry["in_memory"] = InMemoryEventFabric
            StreamsFactory._window_registry["in_memory"] = InMemoryContextWindow
            StreamsFactory._bootstrapped = True
            log.info("[Factory] Bootstrapped StreamsFactory")

    @staticmethod
    def register_fabric(name: str, cls: Type[Any]) -> None:
        """Register a custom BaseEventFabric implementation."""
        StreamsFactory._ensure_defaults()
        with StreamsFactory._lock:
            StreamsFactory._fabric_registry[name.lower()] = cls

    @staticmethod
    def register_window(name: str, cls: Type[Any]) -> None:
        """Register a custom BaseContextWindow implementation."""
        StreamsFactory._ensure_defaults()
        with StreamsFactory._lock:
            StreamsFactory._window_registry[name.lower()] = cls

    @staticmethod
    def create_fabric(config: Optional[Dict[str, Any]] = None):
        """
        Create a BaseEventFabric from config, or return None if streams are disabled.

        Returns None when config["streams"]["enabled"] is false or absent.
        All stream hooks in Router/Orchestrator are guarded — zero impact on
        existing code when streams are disabled.
        """
        StreamsFactory._ensure_defaults()
        cfg = config or {}
        streams_cfg = cfg.get("streams", {})

        if not streams_cfg.get("enabled", False):
            log.debug("[Factory] Streams disabled — returning None")
            return None

        provider = streams_cfg.get("provider", "in_memory").lower()

        if provider == "kafka" and "kafka" not in StreamsFactory._fabric_registry:
            try:
                from k9_aif_abb.k9_streams.kafka_stream import KafkaEventFabric
                StreamsFactory._fabric_registry["kafka"] = KafkaEventFabric
            except ImportError as exc:
                raise RuntimeError(
                    "pip install k9-aif[kafka] required for streams.provider: kafka"
                ) from exc

        cls = StreamsFactory._fabric_registry.get(provider)
        if not cls:
            raise ValueError(f"Unknown stream fabric provider: {provider}")

        log.info("[Factory] Creating event fabric: provider=%s", provider)
        return cls(config=cfg)

    @staticmethod
    def create_window(config: Optional[Dict[str, Any]] = None):
        """
        Create a BaseContextWindow from config, or return None if streams are disabled.
        """
        StreamsFactory._ensure_defaults()
        cfg = config or {}
        streams_cfg = cfg.get("streams", {})

        if not streams_cfg.get("enabled", False):
            return None

        window_provider = streams_cfg.get("window_provider", "in_memory").lower()
        cls = StreamsFactory._window_registry.get(window_provider) \
            or StreamsFactory._window_registry.get("in_memory")

        log.info("[Factory] Creating context window: provider=%s", window_provider)
        return cls(config=cfg)
