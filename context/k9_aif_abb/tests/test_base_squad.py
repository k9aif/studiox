# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

import unittest

from k9_aif_abb.k9_squad.base_squad import BaseSquad


class DummyAgent:
    def execute(self, context):
        return {
            "agent_ran": True,
            "input_seen": context.get("input"),
            "squad_seen": context.get("squad_id"),
        }


class SecondDummyAgent:
    def execute(self, context):
        return {
            "second_agent_ran": True,
            "previous_result_seen": context.get("dummy", {}).get("agent_ran"),
        }


class DummyOrchestrator:
    pass


class DummyMonitor:
    def __init__(self):
        self.started = False
        self.ended = False

    def on_squad_start(self, squad_id):
        self.started = True
        self.started_squad_id = squad_id

    def on_squad_end(self, squad_id):
        self.ended = True
        self.ended_squad_id = squad_id


class TestBaseSquad(unittest.TestCase):

    def test_base_squad_run_returns_result_dict(self):
        squad = BaseSquad(
            squad_id="test_squad",
            agents=[DummyAgent()],
            orchestrator=DummyOrchestrator(),
        )
        squad.flow = [
            {"agent": "DummyAgent", "result_key": "dummy"}
        ]

        result = squad.run({"input": "value"})

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["squad_id"], "test_squad")
        self.assertTrue(result["dummy"]["agent_ran"])
        self.assertEqual(result["dummy"]["input_seen"], "value")
        self.assertEqual(result["dummy"]["squad_seen"], "test_squad")

    def test_base_squad_accumulates_context_between_agents(self):
        squad = BaseSquad(
            squad_id="test_squad",
            agents=[DummyAgent(), SecondDummyAgent()],
            orchestrator=DummyOrchestrator(),
        )
        squad.flow = [
            {"agent": "DummyAgent", "result_key": "dummy"},
            {"agent": "SecondDummyAgent", "result_key": "second"},
        ]

        result = squad.run({"input": "value"})

        self.assertTrue(result["dummy"]["agent_ran"])
        self.assertTrue(result["second"]["second_agent_ran"])
        self.assertTrue(result["second"]["previous_result_seen"])

    def test_base_squad_context_overrides_are_applied(self):
        squad = BaseSquad(
            squad_id="test_squad",
            agents=[DummyAgent()],
            orchestrator=DummyOrchestrator(),
        )
        squad.flow = [
            {
                "agent": "DummyAgent",
                "result_key": "dummy",
                "context": {"input": "override_value"},
            }
        ]

        result = squad.run({"input": "original_value"})

        self.assertEqual(result["dummy"]["input_seen"], "override_value")

    def test_base_squad_monitor_hooks_are_called(self):
        monitor = DummyMonitor()

        squad = BaseSquad(
            squad_id="test_squad",
            agents=[DummyAgent()],
            orchestrator=DummyOrchestrator(),
            monitor=monitor,
        )
        squad.flow = [
            {"agent": "DummyAgent", "result_key": "dummy"}
        ]

        squad.run({"input": "value"})

        self.assertTrue(monitor.started)
        self.assertTrue(monitor.ended)
        self.assertEqual(monitor.started_squad_id, "test_squad")
        self.assertEqual(monitor.ended_squad_id, "test_squad")

    def test_base_squad_defaults(self):
        squad = BaseSquad(
            squad_id="test_squad",
            agents=[],
            orchestrator=DummyOrchestrator(),
        )

        self.assertEqual(squad.squad_id, "test_squad")
        self.assertEqual(squad.agents, [])
        self.assertEqual(squad.description, "")
        self.assertEqual(squad.flow, [])
        self.assertEqual(squad.metadata, {})

    def test_base_squad_raises_when_flow_missing(self):
        squad = BaseSquad(
            squad_id="test_squad",
            agents=[DummyAgent()],
            orchestrator=DummyOrchestrator(),
        )

        with self.assertRaises(RuntimeError):
            squad.run({"input": "value"})

    def test_base_squad_raises_when_required_agent_missing(self):
        squad = BaseSquad(
            squad_id="test_squad",
            agents=[],
            orchestrator=DummyOrchestrator(),
        )
        squad.flow = [
            {"agent": "DummyAgent", "result_key": "dummy"}
        ]

        with self.assertRaises(RuntimeError):
            squad.run({"input": "value"})


if __name__ == "__main__":
    unittest.main()