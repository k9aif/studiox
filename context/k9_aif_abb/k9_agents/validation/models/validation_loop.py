# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""Data models for the BaseValidationLoopAgent iterative reasoning pattern."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationDisposition(str, Enum):
    """Decision returned by should_continue() after each validation step."""

    CONTINUE  = "continue"   # confidence insufficient — run another iteration
    FINALIZE  = "finalize"   # confidence sufficient — produce final output
    ESCALATE  = "escalate"   # uncertainty unresolvable — route to HIL
    FAIL      = "fail"       # definitive negative — validation cannot pass


@dataclass
class ValidationLoopStep:
    """Immutable record of one iteration inside the validation loop."""

    iteration:   int
    hypothesis:  Any
    tool_result: Any
    observation: Any
    disposition: ValidationDisposition
    confidence:  float = 0.0
    metadata:    Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationLoopContext:
    """Mutable state carried across iterations — the agent's working memory."""

    payload:         Dict[str, Any]
    steps:           List[ValidationLoopStep] = field(default_factory=list)
    iteration:       int = 0
    metadata:        Dict[str, Any] = field(default_factory=dict)
    remaining_steps: List[str] = field(default_factory=list)
    notes:           Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationLoopResult:
    """Final output produced by finalize(), escalate(), or fail()."""

    disposition:      ValidationDisposition
    output:           Dict[str, Any]
    steps:            List[ValidationLoopStep]
    iterations:       int
    final_confidence: float
    evidence:         List[str] = field(default_factory=list)
    remaining_steps:  List[str] = field(default_factory=list)
    notes:            Dict[str, Any] = field(default_factory=dict)
