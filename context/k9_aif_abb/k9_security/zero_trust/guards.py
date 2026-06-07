# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from abc import ABC, abstractmethod

from .context import ExecutionContext
from .decisions import TrustDecision, TrustDecisionType
from .evaluators import BaseRiskEvaluator, ContextualRiskEvaluator


class BaseCompromiseGuard(ABC):
    @abstractmethod
    def inspect(self, context: ExecutionContext) -> TrustDecision:
        raise NotImplementedError


class BaseDataLossGuard(ABC):
    @abstractmethod
    def inspect(self, context: ExecutionContext) -> TrustDecision:
        raise NotImplementedError


class BaseZeroTrustGuard(ABC):
    @abstractmethod
    def evaluate(self, context: ExecutionContext) -> TrustDecision:
        raise NotImplementedError


class PromptInjectionGuard(BaseCompromiseGuard):
    def inspect(self, context: ExecutionContext) -> TrustDecision:
        text = str(context.payload).lower()

        suspicious_terms = [
            "ignore previous instructions",
            "bypass policy",
            "disable guardrails",
            "exfiltrate",
            "leak secrets",
            "dump credentials",
        ]

        if any(term in text for term in suspicious_terms):
            return TrustDecision.deny(
                reason="Potential prompt injection or compromise attempt detected",
                risk_score=1.0,
            )

        return TrustDecision.allow(reason="No compromise indicator detected")


class SensitiveDataLossGuard(BaseDataLossGuard):
    def inspect(self, context: ExecutionContext) -> TrustDecision:
        sensitivity = context.attributes.data_sensitivity.lower()

        if sensitivity in {"restricted", "confidential"} and context.destination.is_external:
            return TrustDecision.allow_with_obligations(
                reason="Sensitive data leaving trusted boundary requires masking and audit",
                obligations=["mask_sensitive_data", "audit_log"],
                risk_score=0.75,
            )

        return TrustDecision.allow(reason="No data loss concern detected")


class DefaultZeroTrustGuard(BaseZeroTrustGuard):
    """
    Default K9-AIF Zero Trust execution guard.

    Flow:
    Verify  -> identity/context present
    Control -> inspect compromise, data loss, risk
    Enforce -> return execution decision + obligations
    """

    def __init__(
        self,
        risk_evaluator: BaseRiskEvaluator | None = None,
        compromise_guard: BaseCompromiseGuard | None = None,
        data_loss_guard: BaseDataLossGuard | None = None,
        deny_threshold: float = 0.85,
        approval_threshold: float = 0.75,
        obligation_threshold: float = 0.60,
    ):
        self.risk_evaluator = risk_evaluator or ContextualRiskEvaluator()
        self.compromise_guard = compromise_guard or PromptInjectionGuard()
        self.data_loss_guard = data_loss_guard or SensitiveDataLossGuard()
        self.deny_threshold = deny_threshold
        self.approval_threshold = approval_threshold
        self.obligation_threshold = obligation_threshold

    def evaluate(self, context: ExecutionContext) -> TrustDecision:
        compromise_decision = self.compromise_guard.inspect(context)
        if not compromise_decision.allowed:
            return compromise_decision

        data_loss_decision = self.data_loss_guard.inspect(context)
        if data_loss_decision.decision == TrustDecisionType.ALLOW_WITH_OBLIGATIONS:
            return data_loss_decision

        risk_score = self.risk_evaluator.score(context)

        if risk_score >= self.deny_threshold:
            return TrustDecision.deny(
                reason="Risk score exceeds deny threshold",
                risk_score=risk_score,
            )

        if risk_score >= self.approval_threshold:
            return TrustDecision.require_approval(
                reason="Risk score requires human approval",
                risk_score=risk_score,
            )

        if risk_score >= self.obligation_threshold:
            return TrustDecision.allow_with_obligations(
                reason="Risk allowed with runtime obligations",
                obligations=["audit_log", "step_up_review"],
                risk_score=risk_score,
            )

        return TrustDecision.allow(
            reason="Zero Trust evaluation passed",
            risk_score=risk_score,
        )