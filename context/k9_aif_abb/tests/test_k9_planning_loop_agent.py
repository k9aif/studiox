# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
Tests for K9PlanningLoopAgent (OOB dynamic-planning sibling of
K9ValidationLoopAgent).

llm_invoke is patched at the module level so no LLM or network is required.
All tests are fully offline.
"""

import json
from unittest.mock import MagicMock, patch

from k9_aif_abb.k9_agents.planning import K9PlanningLoopAgent
from k9_aif_abb.k9_agents.validation import ValidationDisposition


# ── Helpers ────────────────────────────────────────────────────────────────────

def _llm_response(conclusion, confidence, reasoning="ok", remaining_steps=None, notes=None):
    """Build a fake LLM text output that K9PlanningLoopAgent can parse."""
    data = {
        "conclusion": conclusion,
        "confidence": confidence,
        "reasoning":  reasoning,
    }
    if remaining_steps is not None:
        data["remaining_steps"] = remaining_steps
    if notes is not None:
        data["notes"] = notes
    return json.dumps(data)


def _make(config=None):
    return K9PlanningLoopAgent(config=config or {})


def _patch_llm(output: str):
    mock_resp = MagicMock()
    mock_resp.output = output
    return patch(
        "k9_aif_abb.k9_agents.planning.k9_planning_loop_agent.llm_invoke",
        return_value=mock_resp,
    )


def _patch_llm_sequence(outputs, capture_prompts=None):
    """Patch llm_invoke to return successive outputs, recording prompts if given."""
    mock_resp = MagicMock()
    call_count = 0

    def side_effect(config, req):
        nonlocal call_count
        if capture_prompts is not None:
            capture_prompts.append(req.prompt)
        mock_resp.output = outputs[min(call_count, len(outputs) - 1)]
        call_count += 1
        return mock_resp

    return patch(
        "k9_aif_abb.k9_agents.planning.k9_planning_loop_agent.llm_invoke",
        side_effect=side_effect,
    )


# ── Plan-driven finalization ────────────────────────────────────────────────────


def test_finalizes_when_plan_complete_even_below_confidence_threshold():
    agent = _make({"confidence_threshold": 0.8})
    with _patch_llm(_llm_response("done", confidence=0.5, remaining_steps=[])):
        result = agent.execute({"input": "task"})
    assert result["disposition"] == ValidationDisposition.FINALIZE
    assert result["iterations"] == 1
    assert result["remaining_steps"] == []


def test_finalizes_on_confidence_threshold_even_with_remaining_plan():
    agent = _make({"confidence_threshold": 0.8})
    with _patch_llm(_llm_response("good enough", confidence=0.95, remaining_steps=["step2"])):
        result = agent.execute({"input": "task"})
    assert result["disposition"] == ValidationDisposition.FINALIZE
    assert result["iterations"] == 1


def test_continues_with_multi_step_plan_and_carries_notes_forward():
    responses = [
        _llm_response("started", confidence=0.4, remaining_steps=["step2", "step3"], notes={"found": "a"}),
        _llm_response("progressing", confidence=0.6, remaining_steps=["step3"], notes={"found": "a", "more": "b"}),
        _llm_response("done", confidence=0.7, remaining_steps=[], notes={"found": "a", "more": "b", "done": True}),
    ]
    prompts = []
    agent = _make({"confidence_threshold": 0.9, "max_iterations": 5})

    with _patch_llm_sequence(responses, capture_prompts=prompts):
        result = agent.execute({"input": "investigate"})

    assert result["disposition"] == ValidationDisposition.FINALIZE
    assert result["iterations"] == 3
    assert result["remaining_steps"] == []
    assert result["notes"] == {"found": "a", "more": "b", "done": True}

    # iteration 1: no plan yet
    assert "No plan yet" in prompts[0]
    # iteration 2: plan from iteration 1 is shown, including step2 and step3
    assert "step2" in prompts[1]
    assert "step3" in prompts[1]
    assert '"found": "a"' in prompts[1]
    # iteration 3: only step3 remains
    assert "step3" in prompts[2]
    assert "step2" not in prompts[2]


# ── Confidence-floor / max-iterations behaviour (mirrors K9ValidationLoopAgent) ─


def test_finalizes_on_max_iterations_when_configured():
    agent = _make({
        "confidence_threshold": 0.9,
        "max_iterations": 2,
        "finalize_on_max_iterations": True,
    })
    with _patch_llm(_llm_response("still working", confidence=0.5, remaining_steps=["keep going"])):
        result = agent.execute({"input": "data"})
    assert result["disposition"] == ValidationDisposition.FINALIZE
    assert result["iterations"] == 2


def test_escalates_on_max_iterations_when_configured():
    agent = _make({
        "confidence_threshold": 0.9,
        "max_iterations": 2,
        "finalize_on_max_iterations": False,
    })
    with _patch_llm(_llm_response("still working", confidence=0.5, remaining_steps=["keep going"])):
        result = agent.execute({"input": "data"})
    assert result["disposition"] == ValidationDisposition.ESCALATE
    assert result["iterations"] == 2


def test_unparseable_llm_output_falls_back_to_confidence_continuation():
    agent = _make({"confidence_threshold": 0.9, "max_iterations": 1, "finalize_on_max_iterations": True})
    with _patch_llm("Sorry, I cannot provide a structured answer."):
        result = agent.execute({"input": "data"})
    # no remaining_steps in output → plan_complete False; default confidence 0.5
    # below threshold, hits max_iterations → FINALIZE
    assert result["disposition"] == ValidationDisposition.FINALIZE
    assert result["remaining_steps"] == []


# ── Output contract ──────────────────────────────────────────────────────────


def test_execute_returns_full_contract_including_plan_fields():
    agent = _make()
    with _patch_llm(_llm_response("ok", confidence=0.9, remaining_steps=[])):
        result = agent.execute({})
    for key in ("agent", "disposition", "output", "iterations", "final_confidence",
                "evidence", "steps", "remaining_steps", "notes"):
        assert key in result, f"missing key: {key}"


# ── _parse_llm_json — nested objects (notes) ──────────────────────────────────


def test_parse_llm_json_handles_nested_notes_object():
    agent = _make()
    text = (
        '```json\n'
        '{"conclusion": "ok", "confidence": 0.7, "reasoning": "r", '
        '"remaining_steps": ["a"], "notes": {"k": "v", "n": 1}}\n'
        '```'
    )
    data = agent._parse_llm_json(text)
    assert data["confidence"] == 0.7
    assert data["notes"] == {"k": "v", "n": 1}
    assert data["remaining_steps"] == ["a"]


def test_parse_llm_json_bad_input_returns_empty():
    agent = _make()
    assert agent._parse_llm_json("not json at all") == {}
    assert agent._parse_llm_json("") == {}
    assert agent._parse_llm_json(None) == {}


# ── Subclass extension ─────────────────────────────────────────────────────────


class StrictPlanningAgent(K9PlanningLoopAgent):
    """SBB that fails fast on very low confidence regardless of plan state."""

    layer = "StrictPlanningAgent"

    def should_continue(self, observation, loop_ctx):
        if observation["confidence"] < 0.2:
            return ValidationDisposition.FAIL
        return super().should_continue(observation, loop_ctx)


def test_subclass_overrides_should_continue_to_fail():
    agent = StrictPlanningAgent(config={"max_iterations": 3})
    with _patch_llm(_llm_response("ruled out", confidence=0.1, remaining_steps=["x"])):
        result = agent.execute({"input": "data"})
    assert result["disposition"] == ValidationDisposition.FAIL
    assert result["iterations"] == 1
