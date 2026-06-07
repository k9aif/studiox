# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
BaseValidationLoopAgent — iterative hypothesis-validate-reason ABB.

Generalises the iterative convergence pattern:

    Hypothesis → Tool/Test → Observation → Re-reason → Continue or Finalize

This ABB is domain-agnostic.  The loop skeleton is fixed; all domain logic
lives in the five abstract methods that subclasses implement.

Applicable domains
------------------
- Security: commit scan → exploit attempt → confirm/deny
- Fraud: signal correlation → rule check → risk confirmation
- Claims: evidence review → policy match → adjudication confidence
- Compliance: regulation lookup → clause match → gap assessment
- Document extraction: parse attempt → schema validation → confidence check

Config keys (all optional)
--------------------------
max_iterations            : int   — default 5
confidence_threshold      : float — default 0.8; available to should_continue()
finalize_on_max_iterations: bool  — default True; if False, escalates on timeout
escalate_on_tool_error    : bool  — default False; if True, ESCALATE on run_validation()
                                    exception instead of FAIL
"""

import logging
from abc import abstractmethod
from typing import Any, Dict

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from k9_aif_abb.k9_agents.validation.models.validation_loop import (
    ValidationDisposition,
    ValidationLoopContext,
    ValidationLoopResult,
    ValidationLoopStep,
)

log = logging.getLogger(__name__)

_DEFAULT_MAX_ITERATIONS            = 5
_DEFAULT_CONFIDENCE_THRESHOLD      = 0.8
_DEFAULT_FINALIZE_ON_MAX           = True


class BaseValidationLoopAgent(BaseAgent):
    """
    ABB: agent that iterates a hypothesis-validate-reason cycle until it can
    FINALIZE, ESCALATE, or FAIL with evidence-backed output.

    Public interface is unchanged from BaseAgent — callers call
    ``execute(payload)`` and receive a ``dict``.  The loop is internal.

    Subclasses must implement:
        generate_hypothesis()
        run_validation()
        evaluate_observation()
        should_continue()
        finalize()

    Subclasses may override:
        escalate()   — default returns disposition=ESCALATE with generic output
        fail()       — default returns disposition=FAIL with generic output
    """

    layer: str = "BaseValidationLoopAgent"

    # ------------------------------------------------------------------
    # Public entry point — satisfies BaseAgent.execute() contract
    # ------------------------------------------------------------------

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        max_iterations      = int(self.config.get("max_iterations", _DEFAULT_MAX_ITERATIONS))
        finalize_on_max     = self._parse_bool(
            self.config.get("finalize_on_max_iterations"), _DEFAULT_FINALIZE_ON_MAX
        )
        escalate_on_error   = self._parse_bool(
            self.config.get("escalate_on_tool_error"), False
        )

        loop_ctx = ValidationLoopContext(payload=payload)
        self._emit("loop_started", {"max_iterations": max_iterations})

        while loop_ctx.iteration < max_iterations:
            loop_ctx.iteration += 1

            hypothesis = self.generate_hypothesis(loop_ctx)
            self._emit("hypothesis_generated", {
                "iteration": loop_ctx.iteration,
                "hypothesis": str(hypothesis),
            })

            # Item 5: catch run_validation() errors — never let a tool failure
            # crash the loop; convert to FAIL or ESCALATE per config.
            try:
                tool_result = self.run_validation(hypothesis, loop_ctx)
                self._emit("validation_tool_invoked", {"iteration": loop_ctx.iteration})
            except Exception as exc:
                self.logger.error(
                    "[%s] run_validation raised at iteration %d: %s",
                    self.layer, loop_ctx.iteration, exc,
                )
                error_disposition = (
                    ValidationDisposition.ESCALATE if escalate_on_error
                    else ValidationDisposition.FAIL
                )
                loop_ctx.steps.append(ValidationLoopStep(
                    iteration   = loop_ctx.iteration,
                    hypothesis  = hypothesis,
                    tool_result = None,
                    observation = {"error": str(exc), "confidence": 0.0},
                    disposition = error_disposition,
                    confidence  = 0.0,
                ))
                event = "loop_escalated" if escalate_on_error else "loop_failed"
                self._emit(event, {"iterations": loop_ctx.iteration, "error": str(exc)})
                handler = self.escalate if escalate_on_error else self.fail
                return self._to_dict(handler(loop_ctx))

            observation = self.evaluate_observation(tool_result, loop_ctx)
            self._emit("observation_evaluated", {
                "iteration": loop_ctx.iteration,
                "observation": str(observation),
            })

            disposition = self.should_continue(observation, loop_ctx)
            confidence  = self._extract_confidence(observation)

            loop_ctx.steps.append(ValidationLoopStep(
                iteration   = loop_ctx.iteration,
                hypothesis  = hypothesis,
                tool_result = tool_result,
                observation = observation,
                disposition = disposition,
                confidence  = confidence,
            ))

            if disposition is ValidationDisposition.FINALIZE:
                self._emit("loop_finalized", {"iterations": loop_ctx.iteration})
                return self._to_dict(self.finalize(loop_ctx))

            if disposition is ValidationDisposition.ESCALATE:
                self._emit("loop_escalated", {"iterations": loop_ctx.iteration})
                return self._to_dict(self.escalate(loop_ctx))

            if disposition is ValidationDisposition.FAIL:
                self._emit("loop_failed", {"iterations": loop_ctx.iteration})
                return self._to_dict(self.fail(loop_ctx))

            self._emit("loop_continued", {"iteration": loop_ctx.iteration})

        # max iterations reached without a terminal disposition
        if finalize_on_max:
            self._emit("loop_finalized", {
                "reason": "max_iterations_reached",
                "iterations": loop_ctx.iteration,
            })
            return self._to_dict(self.finalize(loop_ctx))

        self._emit("loop_escalated", {
            "reason": "max_iterations_reached",
            "iterations": loop_ctx.iteration,
        })
        return self._to_dict(self.escalate(loop_ctx))

    # ------------------------------------------------------------------
    # Abstract — must be implemented by every subclass
    # ------------------------------------------------------------------

    @abstractmethod
    def generate_hypothesis(self, loop_ctx: ValidationLoopContext) -> Any:
        """
        Form the next hypothesis to test.

        Has full access to ``loop_ctx.steps`` (prior iterations) and
        ``loop_ctx.payload`` (original input).  Return any value — it is
        passed unchanged to ``run_validation()``.
        """

    @abstractmethod
    def run_validation(self, hypothesis: Any, loop_ctx: ValidationLoopContext) -> Any:
        """
        Invoke the tool, function, or external call that tests the hypothesis.

        This is the domain hook: call a sandbox, a rule engine, a calculator,
        a database query, or an LLM.  Return the raw result — interpretation
        happens in ``evaluate_observation()``.
        """

    @abstractmethod
    def evaluate_observation(self, tool_result: Any, loop_ctx: ValidationLoopContext) -> Any:
        """
        Interpret the raw tool result into a structured observation.

        Convention: return a dict that includes a ``confidence`` key (float
        0.0–1.0) so ``should_continue()`` and step records have a numeric
        signal.  Other keys are domain-specific.
        """

    @abstractmethod
    def should_continue(
        self, observation: Any, loop_ctx: ValidationLoopContext
    ) -> ValidationDisposition:
        """
        Decide what happens next based on the latest observation.

        Return one of:
            CONTINUE  — run another iteration
            FINALIZE  — confidence sufficient; produce output
            ESCALATE  — unresolvable uncertainty; route to HIL
            FAIL      — definitive negative result
        """

    @abstractmethod
    def finalize(self, loop_ctx: ValidationLoopContext) -> ValidationLoopResult:
        """
        Produce the validated output.  Called when disposition is FINALIZE
        or when max_iterations is reached with finalize_on_max_iterations=True.
        """

    # ------------------------------------------------------------------
    # Optional overrides — defaults provided
    # ------------------------------------------------------------------

    def escalate(self, loop_ctx: ValidationLoopContext) -> ValidationLoopResult:
        """Route to human-in-the-loop.  Override for domain-specific HIL logic."""
        return ValidationLoopResult(
            disposition      = ValidationDisposition.ESCALATE,
            output           = {"reason": "escalated_for_human_review"},
            steps            = loop_ctx.steps,
            iterations       = loop_ctx.iteration,
            final_confidence = self._last_confidence(loop_ctx),
        )

    def fail(self, loop_ctx: ValidationLoopContext) -> ValidationLoopResult:
        """Return a definitive failure.  Override for domain-specific failure output."""
        return ValidationLoopResult(
            disposition      = ValidationDisposition.FAIL,
            output           = {"reason": "validation_failed"},
            steps            = loop_ctx.steps,
            iterations       = loop_ctx.iteration,
            final_confidence = 0.0,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        # publish_event() is confirmed on BaseAgent. The hasattr guard protects
        # against test doubles or future subclasses that omit the mixin.
        event = {"type": event_type, "agent": self.layer, **data}
        if hasattr(self, "publish_event"):
            self.publish_event(event)
        else:
            self.logger.info("[%s] event: %s", self.layer, event)

    def _extract_confidence(self, observation: Any) -> float:
        # Clamp to [0.0, 1.0] — bad subclasses must not break confidence semantics.
        if isinstance(observation, dict):
            try:
                return min(1.0, max(0.0, float(observation.get("confidence", 0.0))))
            except (TypeError, ValueError):
                return 0.0
        return 0.0

    def _last_confidence(self, loop_ctx: ValidationLoopContext) -> float:
        return loop_ctx.steps[-1].confidence if loop_ctx.steps else 0.0

    @staticmethod
    def _parse_bool(value: Any, default: bool) -> bool:
        """Parse a config value to bool without misreading string "false" as True."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1", "yes", "on")
        return default

    def _to_dict(self, result: ValidationLoopResult) -> Dict[str, Any]:
        return {
            "agent":            self.layer,
            "disposition":      result.disposition.value,
            "output":           result.output,
            "iterations":       result.iterations,
            "final_confidence": result.final_confidence,
            "evidence":         result.evidence,
            "steps": [
                {
                    "iteration":   s.iteration,
                    "hypothesis":  str(s.hypothesis),
                    "observation": str(s.observation),
                    "disposition": s.disposition.value,
                    "confidence":  s.confidence,
                    # tool_result intentionally excluded — raw tool output may
                    # contain sensitive data. Add sanitized_tool_result in
                    # subclass finalize() if inspection is needed.
                }
                for s in result.steps
            ],
        }
