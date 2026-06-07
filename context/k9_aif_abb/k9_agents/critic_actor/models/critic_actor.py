# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""Data models for the BaseCriticActorAgent iterative refinement pattern."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class CriticActorDisposition(str, Enum):
    """Decision returned by should_accept() after each critique."""

    ACCEPTED  = "accepted"   # Critic is satisfied — produce final output
    REJECTED  = "rejected"   # Critic found issues — Actor must refine
    ESCALATE  = "escalate"   # Cannot converge — route to HIL
    FAIL      = "fail"       # Definitive rejection — cannot be fixed


@dataclass
class CriticActorStep:
    """Immutable record of one Actor-Critic round."""

    round:       int
    draft:       Any
    feedback:    Dict[str, Any]   # structured critique from Critic
    disposition: CriticActorDisposition
    score:       float = 0.0      # acceptance score from Critic (0.0–1.0)
    metadata:    Dict[str, Any] = field(default_factory=dict)


@dataclass
class CriticActorContext:
    """Mutable state carried across rounds — the agent's working memory."""

    payload:  Dict[str, Any]
    steps:    List[CriticActorStep] = field(default_factory=list)
    round:    int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CriticActorResult:
    """Final output produced by finalize(), escalate(), or fail()."""

    disposition:   CriticActorDisposition
    output:        Dict[str, Any]
    steps:         List[CriticActorStep]
    rounds:        int
    final_score:   float
    critique_log:  List[str] = field(default_factory=list)
