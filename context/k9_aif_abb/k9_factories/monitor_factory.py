# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_factories/monitor_factory.py

from typing import Any, Dict, Type, List
from threading import Lock
import logging
from k9_aif_abb.k9_utils.config_loader import load_config
from k9_aif_abb.k9_core.monitoring.monitor_server import MonitorServer


class MonitorFactory:
    """Static Factory - provisions Monitor backends and unified MonitorServer."""

    _registry: Dict[str, Type[Any]] = {}
    _bootstrapped = False
    _lock = Lock()
    logger = logging.getLogger("MonitorFactory")

    def __init__(self, *args, **kwargs):
        raise RuntimeError("MonitorFactory is static and cannot be instantiated")

    @staticmethod
    def register(name: str, monitor_cls: Type[Any]) -> None:
        with MonitorFactory._lock:
            MonitorFactory._registry[name] = monitor_cls
            MonitorFactory.logger.debug(f"Registered monitor backend '{name}'")

    @staticmethod
    def get(name: str, **kwargs: Any):
        try:
            cls = MonitorFactory._registry[name]
            return cls(**kwargs)
        except KeyError:
            raise ValueError(f"Unknown monitor backend: {name}")

    @staticmethod
    def bootstrap() -> None:
        if MonitorFactory._bootstrapped:
            return
        MonitorFactory._bootstrapped = True
        MonitorFactory.logger.info("[Factory] Bootstrapped MonitorFactory")

    @staticmethod
    def load_from_config() -> MonitorServer:
        cfg = load_config("k9_aif_abb/config/config.yaml")
        monitor_defs = cfg.get("monitors", [])
        common_tags = cfg.get("common_tags", {"app": "K9-AIF"})
        monitors: List[Any] = []
        for entry in monitor_defs:
            module_name, class_name = entry["class"].rsplit(".", 1)
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            MonitorFactory.register(entry["name"], cls)
            params = entry.get("params", {})
            monitors.append(cls(**params))
        return MonitorServer(monitors=monitors, common_tags=common_tags)

    # ------------------------------------------------------------------
    # [OK] New method: entry point for bootstrap_all()
    # ------------------------------------------------------------------
    @staticmethod
    def create(config) -> MonitorServer:
        """
        Entry point used by bootstrap_all().
        Reuses the existing load_from_config() logic, or falls back
        to a default MonitorServer if no config is found.
        """
        try:
            return MonitorFactory.load_from_config()
        except Exception as e:
            MonitorFactory.logger.warning(
                f"MonitorFactory.create() fallback: {e}. Using default MonitorServer."
            )
            return MonitorServer(monitors=[], common_tags={"app": "K9-AIF"})