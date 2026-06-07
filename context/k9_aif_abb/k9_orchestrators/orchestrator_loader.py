"""
K9-AIF ABB: Orchestrator Loader

Provides a reusable architecture-level loader for resolving and creating
orchestrators from configuration.

ABB responsibility:
- define standard orchestrator loading behavior
- resolve orchestrator classes
- instantiate orchestrators
- optionally attach squads using SquadLoader

Do NOT put domain-specific insurance logic here.
Do NOT put Kafka topic handling here.
"""

from typing import Any, Dict, Optional, Type

from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator
from k9_aif_abb.k9_squad.squad_loader import SquadLoader


class OrchestratorLoader:
    """
    ABB-level loader for creating orchestrator instances from configuration.

    This mirrors the role of SquadLoader for squads.
    Concrete SBBs may provide configuration loading, YAML parsing, registry
    setup, and runtime wiring.
    """

    def __init__(
        self,
        registry: Optional[Dict[str, Type[BaseOrchestrator]]] = None,
        squad_loader: Optional[SquadLoader] = None,
    ):
        self.registry = registry or {}
        self.squad_loader = squad_loader

    def register(self, orchestrator_type: str, orchestrator_cls: Type[BaseOrchestrator]) -> None:
        """
        Register an orchestrator implementation class.
        """
        self.registry[orchestrator_type] = orchestrator_cls

    def load(self, orchestrator_config: Dict[str, Any]) -> BaseOrchestrator:
        """
        Create an orchestrator from config.

        Expected minimal config:

        {
            "id": "claims_orchestrator",
            "type": "claims",
            "name": "Claims Orchestrator",
            "squads": [...]
        }
        """
        orchestrator_type = orchestrator_config.get("type")

        if not orchestrator_type:
            raise ValueError("orchestrator_config must include 'type'")

        if orchestrator_type not in self.registry:
            raise ValueError(f"No orchestrator registered for type: {orchestrator_type}")

        orchestrator_cls = self.registry[orchestrator_type]

        squads = []
        if self.squad_loader and orchestrator_config.get("squads"):
            squads = [
                self.squad_loader.load(squad_config)
                for squad_config in orchestrator_config.get("squads", [])
            ]

        return orchestrator_cls(
            config=orchestrator_config,
            squads=squads,
        )