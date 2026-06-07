# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from abc import ABC, abstractmethod
from typing import Dict, Any
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent


class BaseRulesAgent(BaseAgent, ABC):
    """
    ABB: Abstract base class for rules engine agents.
    Subclasses implement evaluate_rules() to call a concrete engine (ODM, Drools, etc.).
    """

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config or {})

    @abstractmethod
    def evaluate_rules(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate rules against the request and return modified/enriched output."""
        ...

    def execute(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"[{self.__class__.__name__}] Executing rules check")
        return self.evaluate_rules(request)