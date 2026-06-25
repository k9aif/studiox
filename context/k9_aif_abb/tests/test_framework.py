# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework
#
# test_framework.py — consolidated framework stability test
#
# Covers the key contracts changed or added in this release:
#   1. Governance pipeline  (pipeline.py + require_governance)
#   2. BaseAgent            (enforce_governance, apply_pre/post_governance)
#   3. ChatAgentABB         (sync execute, correct attribute names)
#   4. BaseSquad            (regression — squad execution still works)
#   5. AgentRegistry        (regression — register / get / create)
#   6. k9_utils.llm_invoke  (importable, callback registration)
#
# Run:
#   pytest k9_aif_abb/tests/test_framework.py -v

import asyncio
import inspect
import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# ─── 1. Governance pipeline ────────────────────────────────────────────────────

from k9_aif_abb.k9_core.governance.pipeline import (
    GovernanceConfigError,
    NoopGovernance,
    require_governance,
)


class RealGovernance:
    """Minimal concrete governance used across tests."""
    def pre_process(self, payload: dict, ctx=None) -> dict:
        payload["_governed"] = True
        return payload

    def post_process(self, payload: dict, ctx=None) -> dict:
        payload["_post_governed"] = True
        return payload


class TestRequireGovernance:

    def test_passes_through_real_governance(self):
        gov = RealGovernance()
        assert require_governance(gov) is gov

    def test_returns_noop_with_warning_in_dev(self, caplog):
        with patch.dict(os.environ, {"K9_ENV": "development"}):
            result = require_governance(None)
        assert isinstance(result, NoopGovernance)
        assert any("NOT safe for production" in r.message for r in caplog.records)

    def test_returns_noop_with_warning_in_test(self, caplog):
        with patch.dict(os.environ, {"K9_ENV": "test"}):
            result = require_governance(None)
        assert isinstance(result, NoopGovernance)

    def test_returns_noop_but_logs_error_in_production(self, caplog):
        with patch.dict(os.environ, {"K9_ENV": "production"}):
            result = require_governance(None)
        assert isinstance(result, NoopGovernance)
        assert any(r.levelname == "ERROR" for r in caplog.records)

    def test_env_arg_takes_precedence_over_envvar(self):
        # explicit env="development" wins even if K9_ENV=production
        with patch.dict(os.environ, {"K9_ENV": "production"}):
            result = require_governance(None, env="development")
        assert isinstance(result, NoopGovernance)

    def test_noop_pre_process_is_passthrough(self):
        gov = NoopGovernance()
        payload = {"key": "value"}
        assert gov.pre_process(payload) is payload

    def test_noop_post_process_is_passthrough(self):
        gov = NoopGovernance()
        payload = {"key": "value"}
        assert gov.post_process(payload) is payload


# ─── 2. BaseAgent ──────────────────────────────────────────────────────────────

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent


class MinimalAgent(BaseAgent):
    """Minimal concrete agent for testing BaseAgent contracts."""
    layer = "Test Agent"

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"done": True}


class TestBaseAgentInit:

    def test_init_with_real_governance(self):
        gov = RealGovernance()
        agent = MinimalAgent(governance=gov)
        assert agent.governance is gov

    def test_init_without_governance_in_dev_uses_noop(self):
        with patch.dict(os.environ, {"K9_ENV": "development"}):
            agent = MinimalAgent()
        assert isinstance(agent.governance, NoopGovernance)

    def test_init_without_governance_in_production_uses_noop_but_logs(self, caplog):
        with patch.dict(os.environ, {"K9_ENV": "production"}):
            agent = MinimalAgent()
        assert isinstance(agent.governance, NoopGovernance)
        assert any(r.levelname == "ERROR" for r in caplog.records)

    def test_logger_is_named_after_class(self):
        gov = RealGovernance()
        agent = MinimalAgent(governance=gov)
        assert agent.logger.name == "MinimalAgent"


class TestEnforceGovernance:

    def test_passes_silently_with_real_governance(self):
        gov = RealGovernance()
        agent = MinimalAgent(governance=gov)
        agent.enforce_governance()  # must not raise

    def test_warns_but_does_not_raise_in_dev_with_noop(self, caplog):
        with patch.dict(os.environ, {"K9_ENV": "development"}):
            agent = MinimalAgent()
            agent.enforce_governance()  # must not raise
        assert any("WARNING" in r.levelname or "NoopGovernance" in r.message
                   for r in caplog.records)

    def test_raises_permission_error_in_production_with_noop(self):
        with patch.dict(os.environ, {"K9_ENV": "production"}):
            agent = MinimalAgent()
        with patch.dict(os.environ, {"K9_ENV": "production"}):
            with pytest.raises(PermissionError, match="enforce_governance"):
                agent.enforce_governance()

    def test_raises_permission_error_in_staging_with_noop(self):
        with patch.dict(os.environ, {"K9_ENV": "staging"}):
            agent = MinimalAgent()
            with pytest.raises(PermissionError):
                agent.enforce_governance()


class TestApplyGovernance:

    def test_apply_pre_governance_calls_pre_process(self):
        gov = RealGovernance()
        agent = MinimalAgent(governance=gov)
        payload = {"x": 1}
        result = asyncio.get_event_loop().run_until_complete(
            agent.apply_pre_governance(payload)
        )
        assert result["_governed"] is True

    def test_apply_post_governance_calls_post_process(self):
        gov = RealGovernance()
        agent = MinimalAgent(governance=gov)
        payload = {"x": 1}
        result = asyncio.get_event_loop().run_until_complete(
            agent.apply_post_governance(payload)
        )
        assert result["_post_governed"] is True

    def test_apply_pre_governance_handles_async_governance(self):
        class AsyncGovernance:
            async def pre_process(self, payload, ctx=None):
                payload["_async"] = True
                return payload
            async def post_process(self, payload, ctx=None):
                return payload

        agent = MinimalAgent(governance=AsyncGovernance())
        payload = {}
        result = asyncio.get_event_loop().run_until_complete(
            agent.apply_pre_governance(payload)
        )
        assert result["_async"] is True


class TestPublishEvent:

    def test_publish_event_calls_message_bus(self):
        bus = MagicMock()
        gov = RealGovernance()
        agent = MinimalAgent(governance=gov, message_bus=bus)
        agent.publish_event({"type": "TestEvent"})
        bus.publish.assert_called_once()

    def test_publish_event_calls_monitor(self):
        monitor = MagicMock()
        gov = RealGovernance()
        agent = MinimalAgent(governance=gov, monitor=monitor)
        agent.publish_event({"type": "TestEvent"})
        monitor.record_event.assert_called_once()

    def test_publish_event_works_without_bus_or_monitor(self):
        gov = RealGovernance()
        agent = MinimalAgent(governance=gov)
        agent.publish_event({"type": "TestEvent"})  # must not raise


# ─── 3. ChatAgentABB ───────────────────────────────────────────────────────────

from k9_aif_abb.k9_agents.chat.chat_agent_abb import ChatAgentABB


class TestChatAgentABB:

    def test_execute_is_synchronous(self):
        gov = RealGovernance()
        agent = ChatAgentABB(governance=gov)
        result = agent.execute({"message": "hello"})
        assert not inspect.iscoroutine(result), "execute() must be sync, not async"

    def test_execute_returns_reply_dict(self):
        gov = RealGovernance()
        agent = ChatAgentABB(governance=gov)
        result = agent.execute({"message": "hello"})
        assert "reply" in result
        assert isinstance(result["reply"], str)

    def test_execute_missing_message_returns_warn(self):
        gov = RealGovernance()
        agent = ChatAgentABB(governance=gov)
        result = agent.execute({})
        assert "reply" in result
        assert "[WARN]" in result["reply"]

    def test_execute_empty_payload_returns_warn(self):
        gov = RealGovernance()
        agent = ChatAgentABB(governance=gov)
        result = agent.execute({})
        assert "[WARN]" in result["reply"]

    def test_execute_governance_failure_returns_warn(self):
        with patch.dict(os.environ, {"K9_ENV": "production"}):
            agent = ChatAgentABB()  # NoopGovernance — enforce_governance will raise
        with patch.dict(os.environ, {"K9_ENV": "production"}):
            result = agent.execute({"message": "hello"})
        assert "[WARN]" in result["reply"]

    def test_execute_publishes_to_message_bus(self):
        bus = MagicMock()
        gov = RealGovernance()
        agent = ChatAgentABB(governance=gov, message_bus=bus)
        agent.execute({"message": "hello"})
        assert bus.publish.called

    def test_execute_works_without_message_bus(self):
        gov = RealGovernance()
        agent = ChatAgentABB(governance=gov)
        result = agent.execute({"message": "hello"})
        assert "reply" in result  # must not raise

    def test_uses_message_bus_not_messaging_attribute(self):
        gov = RealGovernance()
        agent = ChatAgentABB(governance=gov)
        assert hasattr(agent, "message_bus")
        assert not hasattr(agent, "messaging")


# ─── 4. BaseSquad — regression ─────────────────────────────────────────────────

from k9_aif_abb.k9_squad.base_squad import BaseSquad


class DummySquadAgent:
    def execute(self, context):
        return {"ran": True, "saw": context.get("input")}


class DummyOrchestrator:
    pass


class TestBaseSquadRegression:

    def _make_squad(self, agents=None):
        squad = BaseSquad(
            squad_id="test",
            agents=agents or [DummySquadAgent()],
            orchestrator=DummyOrchestrator(),
        )
        squad.flow = [{"agent": "DummySquadAgent", "result_key": "step1"}]
        return squad

    def test_run_returns_completed_status(self):
        result = self._make_squad().run({"input": "x"})
        assert result["status"] == "completed"

    def test_run_includes_agent_result(self):
        result = self._make_squad().run({"input": "x"})
        assert result["step1"]["ran"] is True
        assert result["step1"]["saw"] == "x"

    def test_run_raises_without_flow(self):
        squad = BaseSquad(
            squad_id="test",
            agents=[DummySquadAgent()],
            orchestrator=DummyOrchestrator(),
        )
        with pytest.raises(RuntimeError):
            squad.run({"input": "x"})

    def test_run_raises_with_missing_agent(self):
        squad = BaseSquad(
            squad_id="test",
            agents=[],
            orchestrator=DummyOrchestrator(),
        )
        squad.flow = [{"agent": "DummySquadAgent", "result_key": "step1"}]
        with pytest.raises(RuntimeError):
            squad.run({"input": "x"})


class ContextCapturingAgent:
    """Records whatever context it receives so tests can inspect it."""
    def execute(self, context):
        return {"received_keys": sorted(context.keys()), "received": dict(context)}


class TestSquadContextKeys:

    def test_no_context_keys_passes_everything(self):
        a1 = DummySquadAgent()
        a2 = ContextCapturingAgent()
        squad = BaseSquad(squad_id="t", agents=[a1, a2])
        squad.flow = [
            {"agent": "DummySquadAgent", "result_key": "step1"},
            {"agent": "ContextCapturingAgent", "result_key": "step2"},
        ]
        result = squad.run({"input": "x"})
        assert "step1" in result["step2"]["received_keys"]

    def test_context_keys_filters_upstream_results(self):
        a1 = DummySquadAgent()
        a2 = ContextCapturingAgent()
        squad = BaseSquad(squad_id="t", agents=[a1, a2])
        squad.flow = [
            {"agent": "DummySquadAgent", "result_key": "step1"},
            {"agent": "ContextCapturingAgent", "result_key": "step2", "context_keys": []},
        ]
        result = squad.run({"input": "x"})
        assert "step1" not in result["step2"]["received_keys"]
        assert "input" in result["step2"]["received_keys"]

    def test_context_keys_includes_named_upstream_keys(self):
        a1 = DummySquadAgent()
        a2 = ContextCapturingAgent()
        squad = BaseSquad(squad_id="t", agents=[a1, a2])
        squad.flow = [
            {"agent": "DummySquadAgent", "result_key": "step1"},
            {"agent": "ContextCapturingAgent", "result_key": "step2", "context_keys": ["step1"]},
        ]
        result = squad.run({"input": "x"})
        assert "step1" in result["step2"]["received_keys"]
        assert "input" in result["step2"]["received_keys"]

    def test_context_keys_always_includes_original_payload(self):
        a1 = DummySquadAgent()
        a2 = ContextCapturingAgent()
        squad = BaseSquad(squad_id="t", agents=[a1, a2])
        squad.flow = [
            {"agent": "DummySquadAgent", "result_key": "step1"},
            {"agent": "ContextCapturingAgent", "result_key": "step2", "context_keys": ["step1"]},
        ]
        result = squad.run({"input": "x", "claim_id": "C001"})
        received = result["step2"]["received_keys"]
        assert "input" in received
        assert "claim_id" in received
        assert "squad_id" in received


# ─── 5. AgentRegistry — regression ────────────────────────────────────────────

from k9_aif_abb.k9_agents.registry.agent_registry import AgentRegistry


class DummyRegistryAgent:
    pass


class TestAgentRegistryRegression:

    def test_register_and_retrieve(self):
        reg = AgentRegistry()
        reg.register("DummyRegistryAgent", DummyRegistryAgent)
        assert reg.get("DummyRegistryAgent") is DummyRegistryAgent

    def test_create_returns_instance(self):
        reg = AgentRegistry()
        reg.register("DummyRegistryAgent", DummyRegistryAgent)
        assert isinstance(reg.create("DummyRegistryAgent"), DummyRegistryAgent)

    def test_exists(self):
        reg = AgentRegistry()
        reg.register("DummyRegistryAgent", DummyRegistryAgent)
        assert reg.exists("DummyRegistryAgent") is True
        assert reg.exists("Missing") is False

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError):
            AgentRegistry().get("Missing")

    def test_register_empty_name_raises(self):
        with pytest.raises(ValueError):
            AgentRegistry().register("", DummyRegistryAgent)

    def test_register_none_class_raises(self):
        with pytest.raises(ValueError):
            AgentRegistry().register("X", None)


# ─── 6. k9_utils.llm_invoke ────────────────────────────────────────────────────

class TestLlmInvokeUtility:

    def test_importable_from_k9_utils(self):
        from k9_aif_abb.k9_utils.llm_invoke import llm_invoke, register_trace_callback
        assert callable(llm_invoke)
        assert callable(register_trace_callback)

    def test_register_trace_callback_stores_fn(self):
        import k9_aif_abb.k9_utils.llm_invoke as mod
        original = mod._trace_callback
        try:
            cb = MagicMock()
            mod.register_trace_callback(cb)
            assert mod._trace_callback is cb
        finally:
            mod._trace_callback = original

    def test_callback_is_called_on_successful_invoke(self):
        import k9_aif_abb.k9_utils.llm_invoke as mod
        from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
        from k9_aif_abb.k9_inference.models.inference_response import InferenceResponse

        original = mod._trace_callback
        try:
            cb = MagicMock()
            mod.register_trace_callback(cb)

            mock_resp = MagicMock(spec=InferenceResponse)
            mock_resp.output = "Hello world"
            mock_resp.model_alias = "test-model"
            mock_resp.provider = "ollama"
            mock_resp.latency_ms = 42
            mock_resp.token_usage = {"prompt": 10, "completion": 5}

            with patch("k9_aif_abb.k9_utils.llm_invoke.ModelRouterFactory") as mock_factory:
                mock_router = MagicMock()
                mock_router.invoke.return_value = mock_resp
                mock_factory.get_router.return_value = mock_router

                req = InferenceRequest(prompt="test", task_type="general")
                mod.llm_invoke({}, req)

            cb.assert_called_once()
            event = cb.call_args[0][0]
            assert event["type"] == "LLMCall"
            assert event["model"] == "test-model"
        finally:
            mod._trace_callback = original

    def test_raises_on_warn_response(self):
        import k9_aif_abb.k9_utils.llm_invoke as mod
        from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
        from k9_aif_abb.k9_inference.models.inference_response import InferenceResponse

        mock_resp = MagicMock(spec=InferenceResponse)
        mock_resp.output = "[WARN] connection refused"
        mock_resp.model_alias = "test-model"

        with patch("k9_aif_abb.k9_utils.llm_invoke.ModelRouterFactory") as mock_factory:
            mock_router = MagicMock()
            mock_router.invoke.return_value = mock_resp
            mock_factory.get_router.return_value = mock_router

            req = InferenceRequest(prompt="test", task_type="general")
            with pytest.raises(RuntimeError, match="LLM backend unavailable"):
                mod.llm_invoke({}, req)
