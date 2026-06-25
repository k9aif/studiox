# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9PlanningLoopAgent — OOB dynamic-planning sibling of K9ValidationLoopAgent.

Same family as K9ValidationLoopAgent: extends BaseValidationLoopAgent directly
and uses the LLM as the validation tool. The difference is the loop-continuation
signal — instead of (or alongside) a confidence threshold, the LLM maintains an
explicit plan (`remaining_steps`) and a scratchpad (`notes`) that are carried in
ValidationLoopContext across iterations.

How it works
------------
generate_hypothesis  — builds a prompt from the payload, agent YAML role/goal,
                        the current plan, the scratchpad, and prior iteration
                        observations
run_validation       — calls llm_invoke(); the LLM is the validation tool
evaluate_observation — parses JSON from the LLM response; updates
                        loop_ctx.remaining_steps / loop_ctx.notes in place and
                        extracts confidence, conclusion, reasoning,
                        plan_complete
should_continue      — FINALIZE if the LLM explicitly returned an empty
                        remaining_steps (plan_complete) or confidence reaches
                        confidence_threshold; otherwise CONTINUE/ESCALATE per
                        max_iterations and the low-confidence floor
finalize             — packages the last observation, full step history, and
                        the final plan/notes state

Config keys (from agent YAML or merged global config)
------------------------------------------------------
role                  : str   — LLM system role (default: generic planning agent)
goal                  : str   — LLM goal statement (default: generic)
model                 : str   — model alias for llm_invoke() task_type (default: reasoning)
max_iterations        : int   — inherited from BaseValidationLoopAgent (default 5)
confidence_threshold  : float — inherited; used in should_continue() (default 0.8)
finalize_on_max_iterations: bool — inherited (default True)
escalate_on_tool_error: bool  — inherited (default False)

Example agent YAML (Skill 1 pattern)
-------------------------------------
    name: InvestigationAgent
    class: K9PlanningLoopAgent

    pattern: reasoning
    model: reasoning

    role: >
      You are an investigative analyst agent.

    goal: >
      Investigate the input, maintaining and updating your own plan
      (remaining_steps) and notes until the investigation is complete.

    max_iterations: 6
    confidence_threshold: 0.85

    governance:
      pre_process: true
      post_process: false
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

_DEFAULT_ROLE = "You are an analytical AI agent that plans and tracks its own work."
_DEFAULT_GOAL = "Complete the task, maintaining a plan (remaining_steps) and notes until done."
_LOW_CONFIDENCE_FLOOR = 0.3


class K9PlanningLoopAgent(BaseValidationLoopAgent):
    """
    OOB K9 Planning Loop Agent — LLM-driven loop with dynamic planning.

    Like K9ValidationLoopAgent, the LLM is the validation tool. In addition to
    confidence-based convergence, the LLM maintains an explicit plan
    (`remaining_steps`) and scratchpad (`notes`) that persist across iterations
    via ValidationLoopContext. The loop finalizes when the LLM explicitly
    signals the plan is complete (empty remaining_steps) or confidence reaches
    confidence_threshold — whichever comes first.

    Subclasses may override any of the five methods to customise behaviour
    without re-implementing the full loop, exactly as with K9ValidationLoopAgent.
    """

    layer = "K9PlanningLoopAgent"

    # ------------------------------------------------------------------
    # BaseValidationLoopAgent implementation
    # ------------------------------------------------------------------

    def generate_hypothesis(self, loop_ctx: ValidationLoopContext) -> str:
        role = self.config.get("role", _DEFAULT_ROLE)
        goal = self.config.get("goal", _DEFAULT_GOAL)

        if loop_ctx.remaining_steps:
            plan_section = "\n\nCurrent plan (remaining steps):\n" + "\n".join(
                f"  {i}. {step}" for i, step in enumerate(loop_ctx.remaining_steps, 1)
            )
        elif loop_ctx.iteration == 1:
            plan_section = "\n\nNo plan yet — propose one as part of your response."
        else:
            plan_section = (
                "\n\nPlan is empty — confirm the task is complete, "
                "or add new steps if more work remains."
            )

        notes_section = (
            f"\n\nScratchpad (notes carried from prior iterations):\n"
            f"{json.dumps(loop_ctx.notes, indent=2)}"
            if loop_ctx.notes else ""
        )

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
            f"{plan_section}{notes_section}{prior_context}\n\n"
            f"Iteration {loop_ctx.iteration}.\n"
            f"Return a JSON object with exactly these keys:\n"
            f"  conclusion      : string  — your finding for this iteration\n"
            f"  confidence      : float   — 0.0 (no confidence) to 1.0 (certain)\n"
            f"  reasoning       : string  — brief explanation of your confidence score\n"
            f"  remaining_steps : array of strings — the updated plan after this "
            f"step; an empty array signals the task is complete\n"
            f"  notes           : object  — scratchpad to carry forward to the "
            f"next iteration (merge with, don't discard, prior notes)\n"
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

        plan_provided = isinstance(data.get("remaining_steps"), list)
        if plan_provided:
            loop_ctx.remaining_steps = [str(s) for s in data["remaining_steps"]]

        notes = data.get("notes")
        if isinstance(notes, dict):
            loop_ctx.notes = notes

        return {
            "conclusion":     data.get("conclusion", str(tool_result)[:200]),
            "confidence":     data.get("confidence", 0.5),
            "reasoning":      data.get("reasoning", ""),
            "plan_complete":  plan_provided and not loop_ctx.remaining_steps,
        }

    def should_continue(self, observation: Dict[str, Any], loop_ctx: ValidationLoopContext) -> ValidationDisposition:
        threshold  = float(self.config.get("confidence_threshold", 0.8))
        max_iter   = int(self.config.get("max_iterations", 5))
        confidence = observation["confidence"]

        if observation.get("plan_complete") or confidence >= threshold:
            return ValidationDisposition.FINALIZE

        if loop_ctx.iteration < max_iter - 1:
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
            remaining_steps  = loop_ctx.remaining_steps,
            notes            = loop_ctx.notes,
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
        match = re.search(r"\{.*\}", str(text), re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}
