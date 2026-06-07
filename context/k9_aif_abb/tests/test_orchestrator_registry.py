# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

import pytest

from k9_aif_abb.k9_orchestrators.registry.orchestrator_registry import OrchestratorRegistry


class DummyOrchestrator:
    def execute(self, squad, context):
        return context


def test_register_and_get_orchestrator():
    registry = OrchestratorRegistry()
    registry.register("dummy", DummyOrchestrator)

    orch_cls = registry.get("dummy")
    assert orch_cls is DummyOrchestrator


def test_create_orchestrator():
    registry = OrchestratorRegistry()
    registry.register("dummy", DummyOrchestrator)

    orch = registry.create("dummy")
    assert isinstance(orch, DummyOrchestrator)


def test_exists():
    registry = OrchestratorRegistry()
    registry.register("dummy", DummyOrchestrator)

    assert registry.exists("dummy") is True
    assert registry.exists("missing") is False


def test_list():
    registry = OrchestratorRegistry()
    registry.register("dummy", DummyOrchestrator)

    items = registry.list()

    assert "dummy" in items
    assert items["dummy"] is DummyOrchestrator


def test_get_unknown_orchestrator_raises():
    registry = OrchestratorRegistry()

    with pytest.raises(KeyError, match="Orchestrator 'missing' is not registered"):
        registry.get("missing")


def test_register_invalid_name_raises():
    registry = OrchestratorRegistry()

    with pytest.raises(ValueError, match="Orchestrator name must be a non-empty string"):
        registry.register("", DummyOrchestrator)


def test_register_none_class_raises():
    registry = OrchestratorRegistry()

    with pytest.raises(ValueError, match="cannot be None"):
        registry.register("dummy", None)