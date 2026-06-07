# SPDX-License-Identifier: Apache-2.0
# k9x_studio — agent YAML/global config merge helper
#
# Mirrors the AgentLoader pattern the generator scaffolds into every
# generated K9-AIF app (see backend/services/scaffold_service.py):
# agent.yaml (behavior: role/goal/instructions/model) wins on key
# collision over the global config.yaml (infrastructure: inference,
# postgres, governance, ...).

import re
from pathlib import Path
from typing import Any, Dict

import yaml

_YAML_DIR = Path(__file__).resolve().parent / "yaml"

_CAMEL_BOUNDARY_1 = re.compile(r'(.)([A-Z][a-z]+)')
_CAMEL_BOUNDARY_2 = re.compile(r'([a-z0-9])([A-Z])')


def _to_snake(agent_name: str) -> str:
    s = _CAMEL_BOUNDARY_1.sub(r'\1_\2', agent_name)
    s = _CAMEL_BOUNDARY_2.sub(r'\1_\2', s)
    return s.lower()


class AgentConfigLoader:
    """Loads agents/yaml/<snake_case>.yaml and merges it over the global config."""

    def __init__(self, yaml_dir: Path = _YAML_DIR):
        self._dir = Path(yaml_dir)
        self._cache: Dict[str, dict] = {}

    def _load(self, agent_name: str) -> dict:
        if agent_name not in self._cache:
            path = self._dir / f"{_to_snake(agent_name)}.yaml"
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    self._cache[agent_name] = yaml.safe_load(f) or {}
            else:
                self._cache[agent_name] = {}
        return self._cache[agent_name]

    def merge_with_global(self, agent_name: str, global_config: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(global_config)
        merged.update(self._load(agent_name))
        return merged
