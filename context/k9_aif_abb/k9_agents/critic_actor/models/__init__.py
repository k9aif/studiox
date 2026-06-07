# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""Data contracts for the BaseCriticActorAgent refinement pattern."""

from .critic_actor import (
    CriticActorContext,
    CriticActorDisposition,
    CriticActorResult,
    CriticActorStep,
)

__all__ = [
    "CriticActorContext",
    "CriticActorDisposition",
    "CriticActorResult",
    "CriticActorStep",
]
