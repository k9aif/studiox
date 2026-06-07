# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
Tests for BaseValidationLoopAgent.

All concrete subclasses here are test fixtures only — they live in this
file, not in k9_aif_abb, because the ABB is abstract.
"""

import pytest

from k9_aif_abb.k9_agents.validation import (
    BaseValidationLoopAgent,
    ValidationDisposition,
    ValidationLoopContext,
    ValidationLoopResult,
)


# ── Test fixtures — concrete agents for specific test scenarios ────────────


class ConvergingAgent(BaseValidationLoopAgent):
    """
    Converges toward a target value over iterations.
    Guess = current iteration number. Finalizes when guess == target.
    """

    layer = "ConvergingAgent"

    def generate_hypothesis(self, loop_ctx: ValidationLoopContext):
        return loop_ctx.iteration

    def run_validation(self, hypothesis, loop_ctx: ValidationLoopContext):
        target = loop_ctx.payload.get("target", 3)
        return {"correct": hypothesis == target}

    def evaluate_observation(self, tool_result, loop_ctx: ValidationLoopContext):
        return {
            "correct":    tool_result["correct"],
            "confidence": 1.0 if tool_result["correct"] else 0.3,
        }

    def should_continue(self, observation, loop_ctx: ValidationLoopContext):
        if observation["correct"]:
            return ValidationDisposition.FINALIZE
        return ValidationDisposition.CONTINUE

    def finalize(self, loop_ctx: ValidationLoopContext) -> ValidationLoopResult:
        last = loop_ctx.steps[-1] if loop_ctx.steps else None
        return ValidationLoopResult(
            disposition      = ValidationDisposition.FINALIZE,
            output           = {"validated": True, "guess": last.hypothesis if last else None},
            steps            = loop_ctx.steps,
            iterations       = loop_ctx.iteration,
            final_confidence = 1.0,
            evidence         = ["hypothesis matched target"],
        )


class AlwaysEscalateAgent(BaseValidationLoopAgent):
    """Returns ESCALATE on the first iteration."""

    layer = "AlwaysEscalateAgent"

    def generate_hypothesis(self, loop_ctx): return "h"
    def run_validation(self, h, loop_ctx):   return {"result": "uncertain"}

    def evaluate_observation(self, tool_result, loop_ctx):
        return {"confidence": 0.1}

    def should_continue(self, observation, loop_ctx):
        return ValidationDisposition.ESCALATE

    def finalize(self, loop_ctx) -> ValidationLoopResult:
        return ValidationLoopResult(
            disposition=ValidationDisposition.FINALIZE,
            output={}, steps=loop_ctx.steps,
            iterations=loop_ctx.iteration, final_confidence=0.0,
        )


class AlwaysFailAgent(BaseValidationLoopAgent):
    """Returns FAIL on the first iteration."""

    layer = "AlwaysFailAgent"

    def generate_hypothesis(self, loop_ctx): return "h"
    def run_validation(self, h, loop_ctx):   return {"result": "fail"}

    def evaluate_observation(self, tool_result, loop_ctx):
        return {"confidence": 0.0}

    def should_continue(self, observation, loop_ctx):
        return ValidationDisposition.FAIL

    def finalize(self, loop_ctx) -> ValidationLoopResult:
        return ValidationLoopResult(
            disposition=ValidationDisposition.FINALIZE,
            output={}, steps=loop_ctx.steps,
            iterations=loop_ctx.iteration, final_confidence=0.0,
        )


class NeverConvergesAgent(BaseValidationLoopAgent):
    """Always returns CONTINUE — hits max_iterations every time."""

    layer = "NeverConvergesAgent"

    def generate_hypothesis(self, loop_ctx): return "h"
    def run_validation(self, h, loop_ctx):   return {}

    def evaluate_observation(self, tool_result, loop_ctx):
        return {"confidence": 0.2}

    def should_continue(self, observation, loop_ctx):
        return ValidationDisposition.CONTINUE

    def finalize(self, loop_ctx) -> ValidationLoopResult:
        return ValidationLoopResult(
            disposition      = ValidationDisposition.FINALIZE,
            output           = {"reason": "best_effort"},
            steps            = loop_ctx.steps,
            iterations       = loop_ctx.iteration,
            final_confidence = self._last_confidence(loop_ctx),
        )


def _make(cls, config=None):
    return cls(config=config or {})


# ── Tests ──────────────────────────────────────────────────────────────────


def test_loop_finalizes_after_successful_validation():
    agent  = _make(ConvergingAgent)
    result = agent.execute({"target": 2})
    # iteration 1 → guess=1, no match; iteration 2 → guess=2, match → FINALIZE
    assert result["disposition"] == ValidationDisposition.FINALIZE
    assert result["iterations"]  == 2
    assert result["final_confidence"] == 1.0
    assert result["output"]["validated"] is True


def test_loop_continues_when_confidence_is_low():
    # target=99 never reached within 3 iterations → hits max and finalizes
    agent  = _make(ConvergingAgent, config={"max_iterations": 3, "finalize_on_max_iterations": True})
    result = agent.execute({"target": 99})
    assert result["disposition"] == ValidationDisposition.FINALIZE
    assert result["iterations"]  == 3
    assert len(result["steps"])  == 3


def test_loop_escalates_on_uncertainty():
    agent  = _make(AlwaysEscalateAgent)
    result = agent.execute({})
    assert result["disposition"] == ValidationDisposition.ESCALATE
    assert result["iterations"]  == 1


def test_loop_fails_on_fail_disposition():
    agent  = _make(AlwaysFailAgent)
    result = agent.execute({})
    assert result["disposition"] == ValidationDisposition.FAIL
    assert result["iterations"]  == 1


def test_loop_stops_at_max_iterations_and_finalizes():
    agent  = _make(NeverConvergesAgent, config={"max_iterations": 4, "finalize_on_max_iterations": True})
    result = agent.execute({})
    assert result["disposition"] == ValidationDisposition.FINALIZE
    assert result["iterations"]  == 4
    assert len(result["steps"])  == 4


def test_loop_stops_at_max_iterations_and_escalates():
    agent  = _make(NeverConvergesAgent, config={"max_iterations": 3, "finalize_on_max_iterations": False})
    result = agent.execute({})
    assert result["disposition"] == ValidationDisposition.ESCALATE
    assert result["iterations"]  == 3


def test_step_history_is_captured_per_iteration():
    agent  = _make(ConvergingAgent)
    result = agent.execute({"target": 3})
    # target=3 → iterations 1,2 don't match; iteration 3 matches
    assert result["iterations"] == 3
    assert len(result["steps"]) == 3

    steps = result["steps"]
    assert steps[0]["iteration"]  == 1
    assert steps[1]["iteration"]  == 2
    assert steps[2]["iteration"]  == 3
    assert steps[2]["disposition"] == ValidationDisposition.FINALIZE


def test_step_records_hypothesis_and_confidence():
    agent  = _make(ConvergingAgent)
    result = agent.execute({"target": 1})
    # target=1 → iteration 1 matches immediately
    assert len(result["steps"]) == 1
    step = result["steps"][0]
    assert step["hypothesis"]  == "1"
    assert step["confidence"]  == 1.0
    assert step["disposition"] == ValidationDisposition.FINALIZE


def test_execute_returns_dict_conforming_to_base_agent_contract():
    agent  = _make(ConvergingAgent)
    result = agent.execute({"target": 1})
    assert isinstance(result, dict)
    for key in ("agent", "disposition", "output", "iterations", "final_confidence", "evidence", "steps"):
        assert key in result, f"missing key: {key}"


def test_tool_result_not_exposed_in_step_output():
    agent  = _make(ConvergingAgent)
    result = agent.execute({"target": 1})
    for step in result["steps"]:
        assert "tool_result" not in step


# ── _parse_bool ────────────────────────────────────────────────────────────

def test_parse_bool_string_false_is_false():
    agent = _make(ConvergingAgent)
    assert agent._parse_bool("false", True)  is False
    assert agent._parse_bool("False", True)  is False
    assert agent._parse_bool("0",     True)  is False
    assert agent._parse_bool("no",    True)  is False


def test_parse_bool_string_true_is_true():
    agent = _make(ConvergingAgent)
    assert agent._parse_bool("true",  False) is True
    assert agent._parse_bool("True",  False) is True
    assert agent._parse_bool("1",     False) is True
    assert agent._parse_bool("yes",   False) is True


def test_parse_bool_none_returns_default():
    agent = _make(ConvergingAgent)
    assert agent._parse_bool(None, True)  is True
    assert agent._parse_bool(None, False) is False


def test_parse_bool_native_bool_passthrough():
    agent = _make(ConvergingAgent)
    assert agent._parse_bool(True,  False) is True
    assert agent._parse_bool(False, True)  is False


# ── _extract_confidence clamping ───────────────────────────────────────────

def test_extract_confidence_clamps_above_one():
    agent = _make(ConvergingAgent)
    assert agent._extract_confidence({"confidence": 99.0}) == 1.0


def test_extract_confidence_clamps_below_zero():
    agent = _make(ConvergingAgent)
    assert agent._extract_confidence({"confidence": -5.0}) == 0.0


def test_extract_confidence_bad_type_returns_zero():
    agent = _make(ConvergingAgent)
    assert agent._extract_confidence({"confidence": "bad"}) == 0.0
    assert agent._extract_confidence("not a dict")          == 0.0


# ── run_validation error handling ─────────────────────────────────────────

class ErroringAgent(BaseValidationLoopAgent):
    """run_validation always raises."""

    layer = "ErroringAgent"

    def generate_hypothesis(self, loop_ctx): return "h"

    def run_validation(self, h, loop_ctx):
        raise RuntimeError("tool unavailable")

    def evaluate_observation(self, tool_result, loop_ctx):
        return {"confidence": 0.0}

    def should_continue(self, observation, loop_ctx):
        return ValidationDisposition.CONTINUE

    def finalize(self, loop_ctx) -> ValidationLoopResult:
        return ValidationLoopResult(
            disposition=ValidationDisposition.FINALIZE,
            output={}, steps=loop_ctx.steps,
            iterations=loop_ctx.iteration, final_confidence=0.0,
        )


def test_run_validation_error_defaults_to_fail():
    agent  = _make(ErroringAgent)
    result = agent.execute({})
    assert result["disposition"] == ValidationDisposition.FAIL
    assert result["iterations"]  == 1


def test_run_validation_error_escalates_when_configured():
    agent  = _make(ErroringAgent, config={"escalate_on_tool_error": True})
    result = agent.execute({})
    assert result["disposition"] == ValidationDisposition.ESCALATE
    assert result["iterations"]  == 1


def test_run_validation_error_step_recorded():
    agent  = _make(ErroringAgent)
    result = agent.execute({})
    assert len(result["steps"]) == 1
    assert result["steps"][0]["confidence"] == 0.0
