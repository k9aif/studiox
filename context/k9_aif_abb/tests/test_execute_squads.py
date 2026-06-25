# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework — Tests for BaseOrchestrator.execute_squads()

import unittest
from typing import Any, Dict

from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator
from k9_aif_abb.k9_squad.base_squad import BaseSquad


def _make_agent_class(name):
    """Create a named agent class dynamically so BaseSquad's __class__.__name__ lookup works."""
    def execute(self, context):
        return {"agent": name, "ran": True, "input": context.get("input")}
    return type(name, (), {"execute": execute})


class _TestGovernance:
    def pre_process(self, payload, ctx=None):
        return payload
    def post_process(self, payload, ctx=None):
        return payload


class _ConcreteOrchestrator(BaseOrchestrator):
    layer = "TestOrchestrator"

    def execute_flow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {}


def _make_squad(squad_id, agent_name="DummyAgent"):
    cls = _make_agent_class(agent_name)
    agent = cls()
    squad = BaseSquad(squad_id=squad_id, agents=[agent])
    squad.flow = [{"agent": agent_name, "result_key": "result"}]
    return squad


class TestExecuteSquads(unittest.TestCase):

    def test_single_squad_sequential(self):
        orch = _ConcreteOrchestrator(config={}, governance=_TestGovernance())
        squad = _make_squad("SquadA", "AgentA")
        results = orch.execute_squads([squad], {"input": "hello"})

        self.assertIn("SquadA", results)
        self.assertEqual(results["SquadA"]["status"], "completed")
        self.assertTrue(results["SquadA"]["result"]["ran"])

    def test_multiple_squads_sequential(self):
        orch = _ConcreteOrchestrator(config={}, governance=_TestGovernance())
        squad_a = _make_squad("SquadA", "AgentA")
        squad_b = _make_squad("SquadB", "AgentB")
        results = orch.execute_squads([squad_a, squad_b], {"input": "test"})

        self.assertEqual(len(results), 2)
        self.assertIn("SquadA", results)
        self.assertIn("SquadB", results)
        self.assertEqual(results["SquadA"]["status"], "completed")
        self.assertEqual(results["SquadB"]["status"], "completed")

    def test_multiple_squads_parallel(self):
        orch = _ConcreteOrchestrator(config={}, governance=_TestGovernance())
        squad_a = _make_squad("SquadA", "AgentA")
        squad_b = _make_squad("SquadB", "AgentB")
        results = orch.execute_squads(
            [squad_a, squad_b], {"input": "parallel"}, parallel=True,
        )

        self.assertEqual(len(results), 2)
        self.assertIn("SquadA", results)
        self.assertIn("SquadB", results)
        self.assertEqual(results["SquadA"]["status"], "completed")
        self.assertEqual(results["SquadB"]["status"], "completed")

    def test_empty_squads_returns_empty(self):
        orch = _ConcreteOrchestrator(config={}, governance=_TestGovernance())
        results = orch.execute_squads([], {"input": "none"})
        self.assertEqual(results, {})

    def test_parallel_single_squad_runs_sequentially(self):
        orch = _ConcreteOrchestrator(config={}, governance=_TestGovernance())
        squad = _make_squad("Solo", "SoloAgent")
        results = orch.execute_squads([squad], {"input": "solo"}, parallel=True)

        self.assertEqual(len(results), 1)
        self.assertIn("Solo", results)

    def test_parallel_isolates_payload(self):
        """Each parallel squad gets its own copy of the payload."""
        orch = _ConcreteOrchestrator(config={}, governance=_TestGovernance())
        squad_a = _make_squad("SquadA", "AgentA")
        squad_b = _make_squad("SquadB", "AgentB")
        payload = {"input": "shared", "mutable_list": [1, 2]}

        results = orch.execute_squads(
            [squad_a, squad_b], payload, parallel=True,
        )

        self.assertEqual(results["SquadA"]["result"]["input"], "shared")
        self.assertEqual(results["SquadB"]["result"]["input"], "shared")

    def test_parallel_handles_squad_failure(self):
        """A failing squad should not crash the others."""
        orch = _ConcreteOrchestrator(config={}, governance=_TestGovernance())
        good_squad = _make_squad("GoodSquad", "GoodAgent")

        bad_squad = BaseSquad(squad_id="BadSquad", agents=[])
        bad_squad.flow = [{"agent": "MissingAgent", "result_key": "x"}]

        results = orch.execute_squads(
            [good_squad, bad_squad], {"input": "test"}, parallel=True,
        )

        self.assertEqual(results["GoodSquad"]["status"], "completed")
        self.assertEqual(results["BadSquad"]["status"], "failed")
        self.assertIn("error", results["BadSquad"])


if __name__ == "__main__":
    unittest.main()
