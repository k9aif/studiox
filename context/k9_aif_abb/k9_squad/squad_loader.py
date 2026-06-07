# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from pathlib import Path
from typing import Dict, Any

import yaml

from .base_squad import BaseSquad
from .squad_monitor import DefaultSquadMonitor


class SquadLoader:
    """
    Loads K9-AIF squad definitions from YAML and builds BaseSquad objects.

    Squads are decoupled from orchestrators — squad YAML lists only agents
    and flow steps. The orchestrator that calls ``_load_squad()`` owns the
    association; it is never stored in the squad YAML.

    Expected YAML shape:

    squads:
      claims_intake:
        description: Example claims intake squad
        agents:
          - IntakeAgent
          - ExtractionAgent
          - ValidationAgent
        flow:
          - agent: IntakeAgent
            result_key: intake
          - agent: ExtractionAgent
            result_key: extraction
          - agent: ValidationAgent
            result_key: validation
    """

    def __init__(self, agent_registry, orchestrator_registry=None, monitor_cls=DefaultSquadMonitor):
        """
        Args:
            agent_registry:
                Registry object that supports either:
                  - create(name)
                  - get(name) -> class
            orchestrator_registry:
                Ignored — retained for backwards compatibility only.
                Orchestrator association is managed by the calling orchestrator,
                not stored in squad YAML.
            monitor_cls:
                Monitor class to attach by default to each squad.
        """
        self.agent_registry = agent_registry
        self.monitor_cls = monitor_cls

    def load(self, path: str | Path) -> Dict[str, BaseSquad]:
        """
        Load all squads from a YAML file.

        Returns:
            Dict[str, BaseSquad]: mapping of squad_id to BaseSquad instance
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Squad config file not found: {path}")

        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        squads_cfg = data.get("squads")
        if not squads_cfg:
            raise ValueError(f"No 'squads' section found in {path}")

        loaded_squads: Dict[str, BaseSquad] = {}

        for squad_id, cfg in squads_cfg.items():
            loaded_squads[squad_id] = self._build_squad(squad_id, cfg)

        return loaded_squads

    def load_one(self, path: str | Path, squad_id: str) -> BaseSquad:
        """
        Load a single squad by ID from a YAML file.
        """
        squads = self.load(path)
        if squad_id not in squads:
            available = ", ".join(sorted(squads.keys())) or "none"
            raise KeyError(
                f"Squad '{squad_id}' not found in config. Available squads: {available}"
            )
        return squads[squad_id]

    def _build_squad(self, squad_id: str, cfg: Dict[str, Any]) -> BaseSquad:
        """
        Build a BaseSquad instance from one squad config block.
        """
        if not isinstance(cfg, dict):
            raise ValueError(f"Squad '{squad_id}' configuration must be a mapping/dictionary.")

        agent_names = cfg.get("agents", [])
        if not agent_names:
            raise ValueError(f"Squad '{squad_id}' must define at least one agent")

        agents = [self._create_agent(agent_name, squad_id) for agent_name in agent_names]
        monitor = self.monitor_cls() if self.monitor_cls else None

        squad = BaseSquad(
            squad_id=squad_id,
            agents=agents,
            monitor=monitor,
        )

        squad.description = cfg.get("description", "")
        squad.flow = cfg.get("flow", [])
        squad.metadata = cfg

        return squad

    def _create_agent(self, agent_name: str, squad_id: str):
        """
        Create an agent instance using the provided registry.

        Supports:
          - registry.create(name)
          - registry.get(name) -> class
        """
        try:
            if hasattr(self.agent_registry, "create"):
                return self.agent_registry.create(agent_name)

            if hasattr(self.agent_registry, "get"):
                agent_cls = self.agent_registry.get(agent_name)
                return agent_cls()

            raise TypeError(
                "Agent registry must implement either 'create(name)' "
                "or 'get(name) -> class'"
            )

        except Exception as e:
            raise ValueError(
                f"Failed to create agent '{agent_name}' for squad '{squad_id}': {e}"
            ) from e