# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

import pytest

from k9_aif_abb.k9_agents.registry.agent_registry import AgentRegistry


class DummyAgent:
    pass


def test_register_and_get_agent():
    registry = AgentRegistry()
    registry.register("DummyAgent", DummyAgent)

    agent_cls = registry.get("DummyAgent")
    assert agent_cls is DummyAgent


def test_create_agent():
    registry = AgentRegistry()
    registry.register("DummyAgent", DummyAgent)

    agent = registry.create("DummyAgent")
    assert isinstance(agent, DummyAgent)


def test_exists():
    registry = AgentRegistry()
    registry.register("DummyAgent", DummyAgent)

    assert registry.exists("DummyAgent") is True
    assert registry.exists("MissingAgent") is False


def test_list():
    registry = AgentRegistry()
    registry.register("DummyAgent", DummyAgent)

    items = registry.list()
    assert "DummyAgent" in items
    assert items["DummyAgent"] is DummyAgent


def test_get_unknown_agent_raises():
    registry = AgentRegistry()

    with pytest.raises(KeyError, match="Agent 'MissingAgent' is not registered"):
        registry.get("MissingAgent")


def test_register_invalid_name_raises():
    registry = AgentRegistry()

    with pytest.raises(ValueError, match="Agent name must be a non-empty string"):
        registry.register("", DummyAgent)


def test_register_none_class_raises():
    registry = AgentRegistry()

    with pytest.raises(ValueError, match="cannot be None"):
        registry.register("DummyAgent", None)