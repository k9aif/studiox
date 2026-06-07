from k9_aif_abb.k9_orchestrators.orchestrator_loader import OrchestratorLoader
from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator


class DummyOrchestrator(BaseOrchestrator):
    def __init__(self, config, squads=None):
        self.config = config
        self.squads = squads or []

    def execute_flow(self, payload):
        return {
            "orchestrator_id": self.config["id"],
            "squad_count": len(self.squads),
        }


def test_orchestrator_loader_basic():
    loader = OrchestratorLoader()
    loader.register("dummy", DummyOrchestrator)

    config = {
        "id": "test_orchestrator",
        "type": "dummy",
        "name": "Test Orchestrator",
    }

    orch = loader.load(config)

    assert isinstance(orch, DummyOrchestrator)
    assert orch.config["id"] == "test_orchestrator"
    assert orch.squads == []


def test_orchestrator_loader_missing_type():
    loader = OrchestratorLoader()

    try:
        loader.load({"id": "bad"})
        assert False
    except ValueError as e:
        assert "must include 'type'" in str(e)


def test_orchestrator_loader_unregistered_type():
    loader = OrchestratorLoader()

    try:
        loader.load({"id": "bad", "type": "unknown"})
        assert False
    except ValueError as e:
        assert "No orchestrator registered" in str(e)