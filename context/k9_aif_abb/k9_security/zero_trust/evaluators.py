# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from abc import ABC, abstractmethod

from .context import ExecutionContext


class BaseRiskEvaluator(ABC):
    @abstractmethod
    def score(self, context: ExecutionContext) -> float:
        raise NotImplementedError


class ContextualRiskEvaluator(BaseRiskEvaluator):
    def score(self, context: ExecutionContext) -> float:
        score = 0.0

        sensitivity = context.attributes.data_sensitivity.lower()
        destination_type = context.destination.destination_type.lower()
        principal_type = context.identity.principal_type.lower()

        if context.destination.is_external:
            score += 0.35

        if sensitivity in {"high", "restricted", "confidential"}:
            score += 0.35

        if destination_type in {"unknown", "external_api", "public_api"}:
            score += 0.20

        if principal_type in {"anonymous", "unknown"}:
            score += 0.30

        return min(score, 1.0)