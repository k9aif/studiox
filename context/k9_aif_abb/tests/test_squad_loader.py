# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from pathlib import Path

import pytest
import yaml

from k9_aif_abb.k9_squad.base_squad import BaseSquad
from k9_aif_abb.k9_squad.squad_loader import SquadLoader


class DummyAgentA:
    def execute(self, context):
        return context


class DummyAgentB:
    def execute(self, context):
        return context


class DummyAgentRegistry:
    def __init__(self):
        self._registry = {
            "DummyAgentA": DummyAgentA,
            "DummyAgentB": DummyAgentB,
        }

    def create(self, name):
        if name not in self._registry:
            raise KeyError(f"Agent '{name}' not registered")
        return self._registry[name]()


def write_yaml(tmp_path: Path, content: dict) -> Path:
    path = tmp_path / "example_squads.yaml"
    path.write_text(yaml.safe_dump(content), encoding="utf-8")
    return path


def test_load_single_squad(tmp_path):
    yaml_path = write_yaml(
        tmp_path,
        {
            "squads": {
                "claims_intake": {
                    "description": "Test squad",
                    "agents": ["DummyAgentA", "DummyAgentB"],
                    "flow": [
                        {"agent": "DummyAgentA", "result_key": "a"},
                        {"agent": "DummyAgentB", "result_key": "b"},
                    ],
                }
            }
        },
    )

    loader = SquadLoader(agent_registry=DummyAgentRegistry())

    squads = loader.load(yaml_path)

    assert "claims_intake" in squads

    squad = squads["claims_intake"]
    assert isinstance(squad, BaseSquad)
    assert squad.squad_id == "claims_intake"
    assert len(squad.agents) == 2
    assert isinstance(squad.agents[0], DummyAgentA)
    assert isinstance(squad.agents[1], DummyAgentB)
    assert squad.description == "Test squad"
    # Squads do not carry an orchestrator reference — decoupled by design
    assert not hasattr(squad, "orchestrator") or squad.orchestrator is None


def test_load_multiple_squads(tmp_path):
    yaml_path = write_yaml(
        tmp_path,
        {
            "squads": {
                "squad_one": {
                    "agents": ["DummyAgentA"],
                    "flow": [{"agent": "DummyAgentA", "result_key": "a"}],
                },
                "squad_two": {
                    "agents": ["DummyAgentB"],
                    "flow": [{"agent": "DummyAgentB", "result_key": "b"}],
                },
            }
        },
    )

    loader = SquadLoader(agent_registry=DummyAgentRegistry())

    squads = loader.load(yaml_path)

    assert set(squads.keys()) == {"squad_one", "squad_two"}
    assert len(squads["squad_one"].agents) == 1
    assert len(squads["squad_two"].agents) == 1


def test_load_one_squad_by_id(tmp_path):
    yaml_path = write_yaml(
        tmp_path,
        {
            "squads": {
                "claims_intake": {
                    "agents": ["DummyAgentA"],
                    "flow": [{"agent": "DummyAgentA", "result_key": "a"}],
                }
            }
        },
    )

    loader = SquadLoader(agent_registry=DummyAgentRegistry())

    squad = loader.load_one(yaml_path, "claims_intake")

    assert squad.squad_id == "claims_intake"
    assert len(squad.agents) == 1
    assert isinstance(squad.agents[0], DummyAgentA)


def test_missing_squads_section_raises_error(tmp_path):
    yaml_path = write_yaml(tmp_path, {"not_squads": {}})

    loader = SquadLoader(agent_registry=DummyAgentRegistry())

    with pytest.raises(ValueError, match="No 'squads' section found"):
        loader.load(yaml_path)


def test_squad_without_orchestrator_field_loads_fine(tmp_path):
    """Squads must NOT have an orchestrator: field — decoupled by design."""
    yaml_path = write_yaml(
        tmp_path,
        {
            "squads": {
                "decoupled_squad": {
                    "agents": ["DummyAgentA"],
                    "flow": [{"agent": "DummyAgentA", "result_key": "a"}],
                }
            }
        },
    )

    loader = SquadLoader(agent_registry=DummyAgentRegistry())
    squad = loader.load_one(yaml_path, "decoupled_squad")
    assert squad.squad_id == "decoupled_squad"


def test_missing_agents_raises_error(tmp_path):
    yaml_path = write_yaml(
        tmp_path,
        {
            "squads": {
                "bad_squad": {
                    "agents": [],
                    "flow": [],
                }
            }
        },
    )

    loader = SquadLoader(agent_registry=DummyAgentRegistry())

    with pytest.raises(ValueError, match="must define at least one agent"):
        loader.load(yaml_path)


def test_unknown_agent_raises_error(tmp_path):
    yaml_path = write_yaml(
        tmp_path,
        {
            "squads": {
                "bad_squad": {
                    "agents": ["UnknownAgent"],
                    "flow": [{"agent": "UnknownAgent", "result_key": "x"}],
                }
            }
        },
    )

    loader = SquadLoader(agent_registry=DummyAgentRegistry())

    with pytest.raises(ValueError, match="Failed to create agent 'UnknownAgent'"):
        loader.load(yaml_path)


def test_backwards_compat_orchestrator_registry_ignored(tmp_path):
    """orchestrator_registry kwarg is accepted for backwards compat but ignored."""
    yaml_path = write_yaml(
        tmp_path,
        {
            "squads": {
                "squad_one": {
                    "agents": ["DummyAgentA"],
                    "flow": [{"agent": "DummyAgentA", "result_key": "a"}],
                }
            }
        },
    )

    loader = SquadLoader(
        agent_registry=DummyAgentRegistry(),
        orchestrator_registry=object(),  # anything — must be ignored
    )

    squad = loader.load_one(yaml_path, "squad_one")
    assert squad.squad_id == "squad_one"
