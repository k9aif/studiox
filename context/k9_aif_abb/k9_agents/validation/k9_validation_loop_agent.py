# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9ValidationLoopAgent — OOB concrete implementation of BaseValidationLoopAgent.

Analogous to K9ModelRouter (OOB implementation of BaseModelRouter): provides a
generic, LLM-driven validation loop that works without modification for most use
cases.  Domain teams that need a custom validation tool (rule engine, database,
sandbox) extend BaseValidationLoopAgent directly.  Domain teams whose validation
tool is the LLM itself use K9ValidationLoopAgent — either as-is, or by
overriding only the method(s) that differ for their domain.

How it works
------------
generate_hypothesis  — builds a structured prompt from the payload, agent YAML
                        role/goal, and prior iteration observations
run_validation       — calls llm_invoke(); the LLM is the validation tool
evaluate_observation — parses JSON from the LLM response; extracts confidence,
                        conclusion, reasoning, and a needs_more signal
should_continue      — compares confidence against confidence_threshold; uses
                        needs_more and a low-confidence floor to decide
finalize             — packages the last observation + full step history

Config keys (from agent YAML or merged global config)
------------------------------------------------------
role                  : str   — LLM system role (default: generic analytical agent)
goal                  : str   — LLM goal statement (default: generic)
model                 : str   — model alias for llm_invoke() task_type (default: reasoning)
max_iterations        : int   — inherited from BaseValidationLoopAgent (default 5)
confidence_threshold  : float — inherited; used in should_continue() (default 0.8)
finalize_on_max_iterations: bool — inherited (default True)
escalate_on_tool_error: bool  — inherited (default False)
"""

import json
import logging
import re
from typing import Any, Dict

from k9_aif_abb.k9_agents.validation.base_validation_loop_agent import BaseValidationLoopAgent
from k9_aif_abb.k9_agents.validation.models.validation_loop import (
    ValidationDisposition,
    ValidationLoopContext,
    ValidationLoopResult,
)
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke

log = logging.getLogger(__name__)

_DEFAULT_ROLE = "You are an analytical AI agent."
_DEFAULT_GOAL = "Validate the given input and provide a confidence-scored assessment."
_LOW_CONFIDENCE_FLOOR = 0.3


class K9ValidationLoopAgent(BaseValidationLoopAgent):
    """
    OOB K9 Validation Loop Agent — LLM-driven iterative reasoning.

    The LLM is the validation tool.  Each iteration asks the LLM to assess
    the payload, return a confidence score, and indicate whether further
    analysis would improve its answer.  The loop continues until the LLM
    reaches confidence_threshold, exhausts max_iterations, or signals it
    cannot improve further.

    Subclasses may override any of the five methods to customise behaviour
    without re-implementing the full loop.  Typical pattern:

        class FraudValidationAgent(K9ValidationLoopAgent):
            layer = "FraudValidationAgent SBB"

            def should_continue(self, observation, loop_ctx):
                # Only domain-specific threshold logic here
                if observation["confidence"] >= 0.9:
                    return ValidationDisposition.FINALIZE
                if observation["confidence"] < 0.2:
                    return ValidationDisposition.FAIL
                return ValidationDisposition.CONTINUE
    """

    layer = "K9ValidationLoopAgent"

    # ------------------------------------------------------------------
    # BaseValidationLoopAgent implementation
    # ------------------------------------------------------------------

    def generate_hypothesis(self, loop_ctx: ValidationLoopContext) -> str:
        role = self.config.get("role", _DEFAULT_ROLE)
        goal = self.config.get("goal", _DEFAULT_GOAL)

        prior_context = ""
        if loop_ctx.steps:
            lines = [
                f"  Iteration {s.iteration}: confidence={s.confidence:.2f} — "
                f"{s.observation.get('reasoning', str(s.observation)[:120])}"
                for s in loop_ctx.steps
            ]
            prior_context = "\n\nPrior iterations:\n" + "\n".join(lines)

        return (
            f"Role: {role}\n"
            f"Goal: {goal}\n\n"
            f"Input:\n{json.dumps(loop_ctx.payload, indent=2)}"
            f"{prior_context}\n\n"
            f"Iteration {loop_ctx.iteration}.\n"
            f"Return a JSON object with exactly these keys:\n"
            f"  conclusion  : string  — your finding\n"
            f"  confidence  : float   — 0.0 (no confidence) to 1.0 (certain)\n"
            f"  reasoning   : string  — brief explanation of your confidence score\n"
            f"  needs_more  : boolean — true if another iteration would improve confidence\n"
        )

    def run_validation(self, hypothesis: str, loop_ctx: ValidationLoopContext) -> str:
        req = InferenceRequest(
            prompt=hypothesis,
            task_type=self.config.get("model", "reasoning"),
            metadata={"agent": self.layer, "iteration": loop_ctx.iteration},
        )
        resp = llm_invoke(self.config, req)
        return resp.output

    def evaluate_observation(self, tool_result: str, loop_ctx: ValidationLoopContext) -> Dict[str, Any]:
        data = self._parse_llm_json(tool_result)
        return {
            "conclusion": data.get("conclusion", str(tool_result)[:200]),
            "confidence": data.get("confidence", 0.5),
            "reasoning":  data.get("reasoning", ""),
            "needs_more": bool(data.get("needs_more", False)),
        }

    def should_continue(self, observation: Dict[str, Any], loop_ctx: ValidationLoopContext) -> ValidationDisposition:
        threshold  = float(self.config.get("confidence_threshold", 0.8))
        max_iter   = int(self.config.get("max_iterations", 5))
        confidence = observation["confidence"]

        if confidence >= threshold:
            return ValidationDisposition.FINALIZE

        has_room = loop_ctx.iteration < max_iter - 1
        if observation.get("needs_more") and has_room:
            return ValidationDisposition.CONTINUE

        if confidence < _LOW_CONFIDENCE_FLOOR:
            return ValidationDisposition.ESCALATE

        return ValidationDisposition.CONTINUE

    def finalize(self, loop_ctx: ValidationLoopContext) -> ValidationLoopResult:
        last = loop_ctx.steps[-1] if loop_ctx.steps else None
        obs  = last.observation if last else {}
        return ValidationLoopResult(
            disposition      = ValidationDisposition.FINALIZE,
            output           = {
                "conclusion": obs.get("conclusion", ""),
                "confidence": last.confidence if last else 0.0,
                "reasoning":  obs.get("reasoning", ""),
            },
            steps            = loop_ctx.steps,
            iterations       = loop_ctx.iteration,
            final_confidence = last.confidence if last else 0.0,
            evidence         = [
                s.observation.get("reasoning", str(s.observation)[:120])
                for s in loop_ctx.steps
            ],
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_llm_json(text: str) -> Dict[str, Any]:
        """Extract a JSON object from LLM output — tolerates markdown fences."""
        if not text:
            return {}
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass
        match = re.search(r"\{[^{}]+\}", str(text), re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}
