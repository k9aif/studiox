# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
Tests for K9CriticActorAgent (OOB concrete implementation).

llm_invoke is patched at the module level so no LLM or network is required.
All tests are fully offline.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from k9_aif_abb.k9_agents.critic_actor import (
    K9CriticActorAgent,
    CriticActorDisposition,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _critic_response(accepted, score, issues=None, summary="ok"):
    return json.dumps({
        "accepted": accepted,
        "score":    score,
        "issues":   issues or [],
        "summary":  summary,
    })


def _make(config=None):
    return K9CriticActorAgent(config=config or {})


def _patch_llm(actor_output="draft output", critic_output=None):
    """Patch llm_invoke — actor and critic share the same mock by default."""
    if critic_output is None:
        critic_output = _critic_response(True, 0.9)

    call_count = [0]
    mock_resp  = MagicMock()

    def side_effect(config, req):
        role = req.metadata.get("role", "actor")
        mock_resp.output = critic_output if role == "critic" else actor_output
        call_count[0] += 1
        return mock_resp

    return patch(
        "k9_aif_abb.k9_agents.critic_actor.k9_critic_actor_agent.llm_invoke",
        side_effect=side_effect,
    )


# ── OOB loop behaviour ─────────────────────────────────────────────────────────


def test_accepts_on_first_round_when_critic_satisfied():
    agent = _make({"acceptance_threshold": 0.8})
    with _patch_llm(critic_output=_critic_response(True, 0.95)):
        result = agent.execute({"input": "write a summary"})
    assert result["disposition"] == CriticActorDisposition.ACCEPTED
    assert result["rounds"] == 1
    assert result["final_score"] == 0.95


def test_refines_and_accepts_on_second_round():
    responses = [
        _critic_response(False, 0.5, issues=["too brief"]),
        _critic_response(True,  0.9),
    ]
    call_count = [0]
    mock_resp  = MagicMock()

    def side_effect(config, req):
        role = req.metadata.get("role", "actor")
        if role == "critic":
            mock_resp.output = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
        else:
            mock_resp.output = "actor draft"
        return mock_resp

    with patch(
        "k9_aif_abb.k9_agents.critic_actor.k9_critic_actor_agent.llm_invoke",
        side_effect=side_effect,
    ):
        result = _make({"acceptance_threshold": 0.8, "max_rounds": 3}).execute({"input": "x"})

    assert result["disposition"] == CriticActorDisposition.ACCEPTED
    assert result["rounds"] == 2
    assert result["final_score"] == 0.9


def test_escalates_when_max_rounds_reached_and_not_finalize():
    agent = _make({
        "acceptance_threshold": 0.9,
        "max_rounds": 2,
        "finalize_on_max_rounds": False,
    })
    with _patch_llm(critic_output=_critic_response(False, 0.5, issues=["still wrong"])):
        result = agent.execute({"input": "data"})
    assert result["disposition"] == CriticActorDisposition.ESCALATE
    assert result["rounds"] == 2


def test_finalizes_when_max_rounds_reached_and_finalize_configured():
    agent = _make({
        "acceptance_threshold": 0.9,
        "max_rounds": 2,
        "finalize_on_max_rounds": True,
    })
    with _patch_llm(critic_output=_critic_response(False, 0.5, issues=["still wrong"])):
        result = agent.execute({"input": "data"})
    assert result["disposition"] == CriticActorDisposition.ACCEPTED
    assert result["rounds"] == 2


def test_fails_when_score_below_floor_and_no_issues():
    agent = _make({"acceptance_threshold": 0.8, "max_rounds": 3})
    with _patch_llm(critic_output=_critic_response(False, 0.1, issues=[])):
        result = agent.execute({"input": "data"})
    assert result["disposition"] == CriticActorDisposition.FAIL
    assert result["rounds"] == 1


def test_step_history_recorded():
    agent = _make({"acceptance_threshold": 0.8})
    with _patch_llm(critic_output=_critic_response(True, 0.9, summary="looks good")):
        result = agent.execute({"input": "x"})
    assert len(result["steps"]) == 1
    step = result["steps"][0]
    assert step["round"] == 1
    assert step["score"] == 0.9
    assert step["disposition"] == CriticActorDisposition.ACCEPTED


def test_output_contains_draft_score_and_summary():
    agent = _make({"acceptance_threshold": 0.8})
    with _patch_llm(
        actor_output="my generated draft",
        critic_output=_critic_response(True, 0.95, summary="excellent"),
    ):
        result = agent.execute({"input": "write something"})
    assert "draft" in result["output"]
    assert result["output"]["score"] == 0.95
    assert result["output"]["summary"] == "excellent"


def test_critique_log_populated():
    responses = [
        _critic_response(False, 0.5, summary="needs work"),
        _critic_response(True,  0.9, summary="much better"),
    ]
    call_count = [0]
    mock_resp  = MagicMock()

    def side_effect(config, req):
        role = req.metadata.get("role", "actor")
        if role == "critic":
            mock_resp.output = responses[min(call_count[0], len(responses) - 1)]
            call_count[0] += 1
        else:
            mock_resp.output = "draft"
        return mock_resp

    with patch(
        "k9_aif_abb.k9_agents.critic_actor.k9_critic_actor_agent.llm_invoke",
        side_effect=side_effect,
    ):
        result = _make({"acceptance_threshold": 0.8, "max_rounds": 3}).execute({})

    assert "needs work" in result["critique_log"][0]
    assert "much better" in result["critique_log"][1]


def test_execute_returns_full_contract():
    agent = _make()
    with _patch_llm(critic_output=_critic_response(True, 0.9)):
        result = agent.execute({})
    for key in ("agent", "disposition", "output", "rounds", "final_score", "critique_log", "steps"):
        assert key in result, f"missing key: {key}"


# ── Critic error handling ──────────────────────────────────────────────────────


def test_critic_exception_causes_fail_by_default():
    agent = _make({"escalate_on_critic_error": False})
    mock_resp = MagicMock()
    mock_resp.output = "actor draft"

    def side_effect(config, req):
        if req.metadata.get("role") == "critic":
            raise RuntimeError("validator crashed")
        return mock_resp

    with patch(
        "k9_aif_abb.k9_agents.critic_actor.k9_critic_actor_agent.llm_invoke",
        side_effect=side_effect,
    ):
        result = agent.execute({"input": "data"})
    assert result["disposition"] == CriticActorDisposition.FAIL


def test_critic_exception_escalates_when_configured():
    agent = _make({"escalate_on_critic_error": True})
    mock_resp = MagicMock()
    mock_resp.output = "actor draft"

    def side_effect(config, req):
        if req.metadata.get("role") == "critic":
            raise RuntimeError("validator crashed")
        return mock_resp

    with patch(
        "k9_aif_abb.k9_agents.critic_actor.k9_critic_actor_agent.llm_invoke",
        side_effect=side_effect,
    ):
        result = agent.execute({"input": "data"})
    assert result["disposition"] == CriticActorDisposition.ESCALATE


# ── _parse_llm_json ────────────────────────────────────────────────────────────


def test_parse_llm_json_clean():
    agent = _make()
    data = agent._parse_llm_json('{"accepted": true, "score": 0.9, "issues": []}')
    assert data["accepted"] is True
    assert data["score"] == 0.9


def test_parse_llm_json_markdown_fenced():
    agent = _make()
    text = "Here is my critique:\n```json\n{\"accepted\": false, \"score\": 0.4, \"issues\": [\"too short\"]}\n```"
    data = agent._parse_llm_json(text)
    assert data["accepted"] is False


def test_parse_llm_json_bad_returns_empty():
    agent = _make()
    assert agent._parse_llm_json("not json") == {}
    assert agent._parse_llm_json("") == {}
    assert agent._parse_llm_json(None) == {}


# ── Subclass extension ─────────────────────────────────────────────────────────


class SchemaValidatorAgent(K9CriticActorAgent):
    """SBB that overrides critique() with a real schema checker."""

    layer = "SchemaValidatorAgent"

    REQUIRED_FIELDS = {"name", "amount", "date"}

    def critique(self, draft, ctx):
        try:
            data   = json.loads(draft)
            missing = self.REQUIRED_FIELDS - set(data.keys())
            score   = 1.0 if not missing else max(0.0, 1.0 - len(missing) * 0.3)
            return {
                "accepted": not missing,
                "score":    score,
                "issues":   [f"missing field: {f}" for f in sorted(missing)],
                "summary":  "schema valid" if not missing else f"{len(missing)} fields missing",
            }
        except (json.JSONDecodeError, TypeError):
            return {"accepted": False, "score": 0.0, "issues": ["not valid JSON"], "summary": "parse error"}


def test_subclass_override_critique_with_schema_validator():
    agent = SchemaValidatorAgent(config={"acceptance_threshold": 0.8, "max_rounds": 3})
    mock_resp = MagicMock()

    responses = [
        '{"name": "Alice"}',                                  # missing amount, date
        '{"name": "Alice", "amount": 100, "date": "2026-01-01"}',  # valid
    ]
    call_count = [0]

    def side_effect(config, req):
        mock_resp.output = responses[min(call_count[0], len(responses) - 1)]
        call_count[0] += 1
        return mock_resp

    with patch(
        "k9_aif_abb.k9_agents.critic_actor.k9_critic_actor_agent.llm_invoke",
        side_effect=side_effect,
    ):
        result = agent.execute({"task": "extract fields"})

    assert result["disposition"] == CriticActorDisposition.ACCEPTED
    assert result["rounds"] == 2
