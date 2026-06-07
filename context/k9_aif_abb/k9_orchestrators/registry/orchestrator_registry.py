# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from typing import Dict, Type, Optional

class OrchestratorRegistry:
    """
    Registry for K9-AIF orchestrator implementations.

    Maps orchestrator aliases (for example: 'framework', 'diagnostic')
    to concrete orchestrator classes.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Type] = {}

    def register(self, name: str, orchestrator_cls: Type) -> None:
        """
        Register an orchestrator class under a logical name.
        """
        if not name or not isinstance(name, str):
            raise ValueError("Orchestrator name must be a non-empty string.")

        if orchestrator_cls is None:
            raise ValueError(f"Orchestrator class for '{name}' cannot be None.")

        self._registry[name] = orchestrator_cls

    def get(self, name: str) -> Type:
        """
        Return the registered orchestrator class for the given name.
        """
        if name not in self._registry:
            available = ", ".join(sorted(self._registry.keys())) or "none"
            raise KeyError(
                f"Orchestrator '{name}' is not registered. Available: {available}"
            )
        return self._registry[name]

    def create(self, name: str, *args, **kwargs):
        """
        Create an orchestrator instance from a registered name.
        """
        orchestrator_cls = self.get(name)
        return orchestrator_cls(*args, **kwargs)

    def list(self) -> Dict[str, Type]:
        """
        Return a copy of the current orchestrator registry.
        """
        return dict(self._registry)

    def exists(self, name: str) -> bool:
        return name in self._registry
    