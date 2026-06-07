# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class TrustDecisionType(str, Enum):
    ALLOW = "ALLOW"
    ALLOW_WITH_OBLIGATIONS = "ALLOW_WITH_OBLIGATIONS"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    BYPASS = "BYPASS"


@dataclass
class TrustDecision:
    decision: TrustDecisionType
    allowed: bool
    risk_score: float
    reason: str
    obligations: List[str] = field(default_factory=list)

    @staticmethod
    def allow(reason: str = "Allowed", risk_score: float = 0.0) -> "TrustDecision":
        return TrustDecision(
            decision=TrustDecisionType.ALLOW,
            allowed=True,
            risk_score=risk_score,
            reason=reason,
        )

    @staticmethod
    def deny(reason: str, risk_score: float = 1.0) -> "TrustDecision":
        return TrustDecision(
            decision=TrustDecisionType.DENY,
            allowed=False,
            risk_score=risk_score,
            reason=reason,
        )

    @staticmethod
    def allow_with_obligations(
        reason: str,
        obligations: List[str],
        risk_score: float,
    ) -> "TrustDecision":
        return TrustDecision(
            decision=TrustDecisionType.ALLOW_WITH_OBLIGATIONS,
            allowed=True,
            risk_score=risk_score,
            reason=reason,
            obligations=obligations,
        )

    @staticmethod
    def require_approval(
        reason: str,
        risk_score: float,
        obligations: List[str] | None = None,
    ) -> "TrustDecision":
        return TrustDecision(
            decision=TrustDecisionType.REQUIRE_APPROVAL,
            allowed=False,
            risk_score=risk_score,
            reason=reason,
            obligations=obligations or ["human_approval"],
        )