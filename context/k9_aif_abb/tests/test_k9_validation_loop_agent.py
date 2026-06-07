# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
Tests for K9ValidationLoopAgent (OOB concrete implementation).

llm_invoke is patched at the module level so no LLM or network is required.
All tests are fully offline.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from k9_aif_abb.k9_agents.validation import (
    K9ValidationLoopAgent,
    ValidationDisposition,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _llm_response(conclusion, confidence, reasoning="ok", needs_more=False):
    """Build a fake LLM text output that K9ValidationLoopAgent can parse."""
    return json.dumps({
        "conclusion":  conclusion,
        "confidence":  confidence,
        "reasoning":   reasoning,
        "needs_more":  needs_more,
    })


def _make(config=None):
    return K9ValidationLoopAgent(config=config or {})


def _patch_llm(output: str):
    """Return a patch context that makes llm_invoke return the given string."""
    mock_resp = MagicMock()
    mock_resp.output = output
    return patch(
        "k9_aif_abb.k9_agents.validation.k9_validation_loop_agent.llm_invoke",
        return_value=mock_resp,
    )


# ── OOB loop behaviour ─────────────────────────────────────────────────────────


def test_finalizes_when_llm_returns_high_confidence():
    agent = _make({"confidence_threshold": 0.8})
    with _patch_llm(_llm_response("risk is low", confidence=0.9)):
        result = agent.execute({"input": "claim data"})
    assert result["disposition"] == ValidationDisposition.FINALIZE
    assert result["iterations"] == 1
    assert result["final_confidence"] == 0.9


def test_continues_when_confidence_below_threshold_and_needs_more():
    responses = [
        _llm_response("uncertain", confidence=0.5, needs_more=True),
        _llm_response("confident now", confidence=0.9, needs_more=False),
    ]
    agent = _make({"confidence_threshold": 0.8, "max_iterations": 5})
    mock_resp = MagicMock()
    mock_resp.output = responses[0]

    call_count = 0

    def side_effect(config, req):
        nonlocal call_count
        mock_resp.output = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return mock_resp

    with patch(
        "k9_aif_abb.k9_agents.validation.k9_validation_loop_agent.llm_invoke",
        side_effect=side_effect,
    ):
        result = agent.execute({"input": "claim data"})

    assert result["disposition"] == ValidationDisposition.FINALIZE
    assert result["iterations"] == 2
    assert result["final_confidence"] == 0.9


def test_escalates_when_confidence_below_floor():
    agent = _make({"confidence_threshold": 0.8, "max_iterations": 3})
    with _patch_llm(_llm_response("cannot determine", confidence=0.1, needs_more=False)):
        result = agent.execute({"input": "ambiguous data"})
    assert result["disposition"] == ValidationDisposition.ESCALATE
    assert result["iterations"] == 1


def test_finalizes_on_max_iterations_when_configured():
    agent = _make({
        "confidence_threshold": 0.9,
        "max_iterations": 2,
        "finalize_on_max_iterations": True,
    })
    # confidence 0.5 — never reaches threshold, never below floor → CONTINUE
    with _patch_llm(_llm_response("still uncertain", confidence=0.5, needs_more=True)):
        result = agent.execute({"input": "data"})
    assert result["disposition"] == ValidationDisposition.FINALIZE
    assert result["iterations"] == 2


def test_escalates_on_max_iterations_when_configured():
    agent = _make({
        "confidence_threshold": 0.9,
        "max_iterations": 2,
        "finalize_on_max_iterations": False,
    })
    with _patch_llm(_llm_response("still uncertain", confidence=0.5, needs_more=True)):
        result = agent.execute({"input": "data"})
    assert result["disposition"] == ValidationDisposition.ESCALATE
    assert result["iterations"] == 2


def test_step_history_recorded():
    agent = _make({"confidence_threshold": 0.8})
    with _patch_llm(_llm_response("done", confidence=0.9)):
        result = agent.execute({"input": "x"})
    assert len(result["steps"]) == 1
    step = result["steps"][0]
    assert step["iteration"] == 1
    assert step["confidence"] == 0.9
    assert step["disposition"] == ValidationDisposition.FINALIZE


def test_output_contains_conclusion_and_reasoning():
    agent = _make({"confidence_threshold": 0.8})
    with _patch_llm(_llm_response("approved", confidence=0.95, reasoning="all checks passed")):
        result = agent.execute({"claim_id": "C001"})
    assert result["output"]["conclusion"] == "approved"
    assert result["output"]["reasoning"] == "all checks passed"


def test_evidence_contains_reasoning_from_each_step():
    responses = [
        _llm_response("first pass", confidence=0.5, reasoning="initial scan", needs_more=True),
        _llm_response("confirmed", confidence=0.9, reasoning="deeper check"),
    ]
    call_count = 0
    mock_resp = MagicMock()

    def side_effect(config, req):
        nonlocal call_count
        mock_resp.output = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return mock_resp

    with patch(
        "k9_aif_abb.k9_agents.validation.k9_validation_loop_agent.llm_invoke",
        side_effect=side_effect,
    ):
        result = _make({"confidence_threshold": 0.8, "max_iterations": 5}).execute({})

    assert "initial scan" in result["evidence"][0]
    assert "deeper check" in result["evidence"][1]


def test_execute_returns_full_contract():
    agent = _make()
    with _patch_llm(_llm_response("ok", confidence=0.9)):
        result = agent.execute({})
    for key in ("agent", "disposition", "output", "iterations", "final_confidence", "evidence", "steps"):
        assert key in result, f"missing key: {key}"


# ── _parse_llm_json ────────────────────────────────────────────────────────────


def test_parse_llm_json_clean_json():
    agent = _make()
    data = agent._parse_llm_json('{"confidence": 0.8, "conclusion": "yes"}')
    assert data["confidence"] == 0.8
    assert data["conclusion"] == "yes"


def test_parse_llm_json_markdown_fenced():
    agent = _make()
    text = 'Here is my analysis:\n```json\n{"confidence": 0.7, "conclusion": "maybe"}\n```'
    data = agent._parse_llm_json(text)
    assert data["confidence"] == 0.7


def test_parse_llm_json_embedded_object():
    agent = _make()
    text = 'Some preamble. {"confidence": 0.6, "conclusion": "no"} trailing text.'
    data = agent._parse_llm_json(text)
    assert data["confidence"] == 0.6


def test_parse_llm_json_bad_input_returns_empty():
    agent = _make()
    assert agent._parse_llm_json("not json at all") == {}
    assert agent._parse_llm_json("") == {}
    assert agent._parse_llm_json(None) == {}


# ── LLM returns unparseable output ────────────────────────────────────────────


def test_unparseable_llm_output_defaults_to_mid_confidence():
    agent = _make({"confidence_threshold": 0.9, "max_iterations": 1, "finalize_on_max_iterations": True})
    with _patch_llm("Sorry, I cannot provide a structured answer."):
        result = agent.execute({"input": "data"})
    # default confidence is 0.5 — below threshold, not below floor → CONTINUE → hits max → FINALIZE
    assert result["disposition"] == ValidationDisposition.FINALIZE


# ── Subclass extension ─────────────────────────────────────────────────────────


class FraudValidationAgent(K9ValidationLoopAgent):
    """SBB that overrides run_validation with a fake rule engine."""

    layer = "FraudValidationAgent"

    def run_validation(self, hypothesis, loop_ctx):
        return json.dumps({"confidence": 0.95, "conclusion": "fraud confirmed",
                           "reasoning": "rule engine match", "needs_more": False})


def test_subclass_overrides_run_validation():
    agent = FraudValidationAgent(config={"confidence_threshold": 0.8})
    # No llm_invoke patch needed — subclass doesn't call it
    result = agent.execute({"transaction_id": "T001"})
    assert result["disposition"] == ValidationDisposition.FINALIZE
    assert result["output"]["conclusion"] == "fraud confirmed"
    assert result["final_confidence"] == 0.95


class CustomThresholdAgent(K9ValidationLoopAgent):
    """SBB that overrides only should_continue with domain-specific logic."""

    layer = "CustomThresholdAgent"

    def should_continue(self, observation, loop_ctx):
        if observation["confidence"] >= 0.9:
            return ValidationDisposition.FINALIZE
        if observation["confidence"] < 0.2:
            return ValidationDisposition.FAIL
        return ValidationDisposition.CONTINUE


def test_subclass_overrides_should_continue_to_fail():
    agent = CustomThresholdAgent(config={"max_iterations": 3})
    with _patch_llm(_llm_response("ruled out", confidence=0.1)):
        result = agent.execute({"input": "data"})
    assert result["disposition"] == ValidationDisposition.FAIL
    assert result["iterations"] == 1
