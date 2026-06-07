# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from typing import Dict, Type


class AgentRegistry:
    """
    Registry for K9-AIF agent implementations.

    Maps agent aliases to concrete agent classes.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Type] = {}

    def register(self, name: str, agent_cls: Type) -> None:
        """
        Register an agent class under a logical name.
        """
        if not name or not isinstance(name, str):
            raise ValueError("Agent name must be a non-empty string.")

        if agent_cls is None:
            raise ValueError(f"Agent class for '{name}' cannot be None.")

        self._registry[name] = agent_cls

    def get(self, name: str) -> Type:
        """
        Return the registered agent class for the given name.
        """
        if name not in self._registry:
            available = ", ".join(sorted(self._registry.keys())) or "none"
            raise KeyError(
                f"Agent '{name}' is not registered. Available: {available}"
            )
        return self._registry[name]

    def create(self, name: str, *args, **kwargs):
        """
        Create an agent instance from a registered name.
        """
        agent_cls = self.get(name)
        return agent_cls(*args, **kwargs)

    def list(self) -> Dict[str, Type]:
        """
        Return a copy of the current agent registry.
        """
        return dict(self._registry)

    def exists(self, name: str) -> bool:
        """
        Return True if the agent name is registered.
        """
        return name in self._registry