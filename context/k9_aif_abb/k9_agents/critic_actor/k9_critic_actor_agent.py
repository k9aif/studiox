# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9CriticActorAgent — OOB concrete implementation of BaseCriticActorAgent.

Analogous to K9ModelRouter (OOB implementation of BaseModelRouter) and
K9ValidationLoopAgent (OOB implementation of BaseValidationLoopAgent).

Both Actor and Critic roles are played by the LLM using role-switched
system prompts from the agent YAML config.  Domain teams that need a
real external Critic (test runner, schema validator, compliance checker)
extend BaseCriticActorAgent directly and override ``critique()``.
Domain teams whose Critic is the LLM use K9CriticActorAgent — either
as-is, or by overriding only the method(s) that differ.

How it works
------------
generate   — Actor LLM call: role/goal + payload → initial draft
critique   — Critic LLM call: critic_role/critic_goal + draft → JSON feedback
refine     — Actor LLM call: role/goal + draft + issues → improved draft
should_accept — checks feedback["accepted"] and score >= acceptance_threshold
finalize   — packages the accepted draft + full round history

Config keys (from agent YAML or merged global config)
------------------------------------------------------
role                   : str   — Actor system role (default: generic generator)
goal                   : str   — Actor goal statement
critic_role            : str   — Critic system role (default: strict quality critic)
critic_goal            : str   — Critic goal statement
model                  : str   — model alias for llm_invoke() (default: reasoning)
max_rounds             : int   — inherited from BaseCriticActorAgent (default 3)
acceptance_threshold   : float — inherited; used in should_accept() (default 0.8)
finalize_on_max_rounds : bool  — inherited (default True)
"""

import json
import logging
import re
from typing import Any, Dict

from k9_aif_abb.k9_agents.critic_actor.base_critic_actor_agent import BaseCriticActorAgent
from k9_aif_abb.k9_agents.critic_actor.models.critic_actor import (
    CriticActorContext,
    CriticActorDisposition,
    CriticActorResult,
)
from k9_aif_abb.k9_inference.models.inference_request import InferenceRequest
from k9_aif_abb.k9_utils.llm_invoke import llm_invoke

log = logging.getLogger(__name__)

_DEFAULT_ACTOR_ROLE  = "You are an expert content generator."
_DEFAULT_ACTOR_GOAL  = "Produce a high-quality output for the given input."
_DEFAULT_CRITIC_ROLE = "You are a strict quality critic."
_DEFAULT_CRITIC_GOAL = (
    "Evaluate the draft against the original requirements. "
    "Return JSON with: accepted (bool), score (float 0–1), issues (list of strings), "
    "and summary (string)."
)


class K9CriticActorAgent(BaseCriticActorAgent):
    """
    OOB K9 Critic-Actor Agent — LLM plays both Actor and Critic roles.

    Override ``critique()`` to replace the LLM Critic with a real external
    tool (test runner, Pydantic validator, compliance checker, etc.).
    Override ``should_accept()`` for domain-specific acceptance logic.
    Everything else — loop skeleton, step history, telemetry, escalation —
    is inherited.

    Typical domain SBB pattern (swap in a real Critic):

        class ContractDraftingAgent(K9CriticActorAgent):
            layer = "ContractDraftingAgent SBB"

            def critique(self, draft, ctx):
                issues = compliance_checker.scan(draft)
                score  = 1.0 if not issues else max(0.0, 1.0 - len(issues) * 0.2)
                return {
                    "accepted": not issues,
                    "score":    score,
                    "issues":   issues,
                    "summary":  f"{len(issues)} compliance issues found",
                }
    """

    layer = "K9CriticActorAgent"

    # ------------------------------------------------------------------
    # BaseCriticActorAgent implementation
    # ------------------------------------------------------------------

    def generate(self, ctx: CriticActorContext) -> str:
        role = self.config.get("role", _DEFAULT_ACTOR_ROLE)
        goal = self.config.get("goal", _DEFAULT_ACTOR_GOAL)

        prompt = (
            f"Role: {role}\n"
            f"Goal: {goal}\n\n"
            f"Input:\n{json.dumps(ctx.payload, indent=2)}\n\n"
            f"Produce your best output for this input."
        )
        return self._actor_invoke(prompt, ctx)

    def critique(self, draft: str, ctx: CriticActorContext) -> Dict[str, Any]:
        critic_role = self.config.get("critic_role", _DEFAULT_CRITIC_ROLE)
        critic_goal = self.config.get("critic_goal", _DEFAULT_CRITIC_GOAL)

        prompt = (
            f"Role: {critic_role}\n"
            f"Goal: {critic_goal}\n\n"
            f"Original input:\n{json.dumps(ctx.payload, indent=2)}\n\n"
            f"Draft to evaluate (round {ctx.round}):\n{draft}\n\n"
            f"Return a JSON object with exactly these keys:\n"
            f"  accepted : boolean — true if the draft meets requirements\n"
            f"  score    : float   — 0.0 (unacceptable) to 1.0 (perfect)\n"
            f"  issues   : array   — list of specific problems to fix (empty if accepted)\n"
            f"  summary  : string  — one-sentence assessment\n"
        )
        raw = self._critic_invoke(prompt, ctx)
        return self._parse_llm_json(raw)

    def refine(self, draft: str, feedback: Dict[str, Any], ctx: CriticActorContext) -> str:
        role   = self.config.get("role", _DEFAULT_ACTOR_ROLE)
        goal   = self.config.get("goal", _DEFAULT_ACTOR_GOAL)
        issues = feedback.get("issues", [])

        issue_text = "\n".join(f"  - {i}" for i in issues) if issues else "  (none specified)"

        prompt = (
            f"Role: {role}\n"
            f"Goal: {goal}\n\n"
            f"Original input:\n{json.dumps(ctx.payload, indent=2)}\n\n"
            f"Previous draft (round {ctx.round - 1}):\n{draft}\n\n"
            f"Critic feedback — issues to fix:\n{issue_text}\n\n"
            f"Produce a revised draft that addresses all issues."
        )
        return self._actor_invoke(prompt, ctx)

    def should_accept(
        self, feedback: Dict[str, Any], ctx: CriticActorContext
    ) -> CriticActorDisposition:
        threshold = float(self.config.get("acceptance_threshold", 0.8))
        score     = float(feedback.get("score", 0.0))
        accepted  = bool(feedback.get("accepted", False))

        if accepted or score >= threshold:
            return CriticActorDisposition.ACCEPTED

        # Score below 0.2 with no hope of fixing → FAIL
        issues = feedback.get("issues", [])
        if score < 0.2 and not issues:
            return CriticActorDisposition.FAIL

        return CriticActorDisposition.REJECTED

    def finalize(self, ctx: CriticActorContext) -> CriticActorResult:
        last = ctx.steps[-1] if ctx.steps else None
        return CriticActorResult(
            disposition  = CriticActorDisposition.ACCEPTED,
            output       = {
                "draft":   last.draft if last else "",
                "score":   last.score if last else 0.0,
                "summary": last.feedback.get("summary", "") if last else "",
            },
            steps        = ctx.steps,
            rounds       = ctx.round,
            final_score  = last.score if last else 0.0,
            critique_log = [
                s.feedback.get("summary", str(s.feedback)[:100])
                for s in ctx.steps
            ],
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _actor_invoke(self, prompt: str, ctx: CriticActorContext) -> str:
        req = InferenceRequest(
            prompt=prompt,
            task_type=self.config.get("model", "reasoning"),
            metadata={"agent": self.layer, "role": "actor", "round": ctx.round},
        )
        resp = llm_invoke(self.config, req)
        return resp.output

    def _critic_invoke(self, prompt: str, ctx: CriticActorContext) -> str:
        req = InferenceRequest(
            prompt=prompt,
            task_type=self.config.get("model", "reasoning"),
            metadata={"agent": self.layer, "role": "critic", "round": ctx.round},
        )
        resp = llm_invoke(self.config, req)
        return resp.output

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
