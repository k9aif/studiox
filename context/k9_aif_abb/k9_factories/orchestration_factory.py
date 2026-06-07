# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# Factory ABB for orchestration layer
# File: k9_aif_abb/k9_factories/orchestration_factory.py

import logging
from typing import Dict, Optional, Type
from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator


class OrchestrationFactory:
    """
    ABB - OrchestrationFactory
    --------------------------
    Provides singleton lifecycle management for all orchestrators
    (ExperienceOrchestrator, WeatherAssistOrchestrator, etc.)

    Responsibilities:
      - Register orchestrator classes.
      - Ensure only one instance per orchestrator type exists.
      - Retrieve orchestrators via `.get(name)` for reuse.
    """

    _registry: Dict[str, Type[BaseOrchestrator]] = {}
    _instances: Dict[str, BaseOrchestrator] = {}
    _bootstrapped = False
    logger = logging.getLogger("OrchestrationFactory")

    # -----------------------------------------------------------
    # Bootstrapping (optional, safe to call many times)
    # -----------------------------------------------------------
    @classmethod
    def bootstrap(cls, config: Optional[dict] = None):
        """Prepare factory; can register default orchestrators here."""
        if cls._bootstrapped:
            return
        cls._bootstrapped = True
        cls.logger.info("[Factory] Bootstrapped OrchestrationFactory")

    # -----------------------------------------------------------
    # Registration
    # -----------------------------------------------------------
    @classmethod
    def register(cls, name: str, orchestrator_cls: Type[BaseOrchestrator]):
        """Register an orchestrator class by name."""
        cls._registry[name] = orchestrator_cls
        cls.logger.info(f"[Factory] Registered orchestrator: {name}")

    # -----------------------------------------------------------
    # Retrieval
    # -----------------------------------------------------------
    @classmethod
    def get(cls, name: str, config: Optional[dict] = None) -> Optional[BaseOrchestrator]:
        """Retrieve or create a singleton orchestrator by name."""
        if name in cls._instances:
            return cls._instances[name]

        orch_cls = cls._registry.get(name)
        if not orch_cls:
            cls.logger.error(f"[Factory] Orchestrator not registered: {name}")
            return None

        instance = orch_cls(config=config)
        cls._instances[name] = instance
        cls.logger.info(f"[Factory] Created singleton orchestrator: {name}")
        return instance

    # -----------------------------------------------------------
    # Introspection
    # -----------------------------------------------------------
    @classmethod
    def list(cls) -> Dict[str, str]:
        return {k: v.__name__ for k, v in cls._registry.items()}