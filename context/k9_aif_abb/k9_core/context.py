# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# (c) 2025 Ravi Natarajan. All rights reserved.

# (c) 2025 Ravi Natarajan. All rights reserved.

"""
===============================================================================
K9-AIF Core Context Module
===============================================================================

File:        context.py
Layer:       Core ABB (cross-layer)
Purpose:     Provides the unified execution context object (ExecutionContext)
             carrying both Intent and Situational metadata across all layers
             of the K9-AIF framework (Orchestration, Integration, Inference,
             Data, Monitoring, Security, etc.).

Description:
    This module defines the ExecutionContext - a lightweight, governed data
    structure designed to propagate intent, situation, and trace metadata
    through all K9-AIF components.

    It complements base_component.py by providing shared runtime context
    awareness without introducing dependencies between layers.

    Example:
        from k9_core.context import ExecutionContext
        ctx = ExecutionContext(
            intent="transform.xml_to_json",
            situation={"format": "xml", "source": "upload.api"},
            trace_id="TXN-987654"
        )
        agent.execute({"context": ctx, "data": xml_payload})

Notes:
    - This module sits at the same folder level as base_component.py.
    - It may later include other context abstractions such as:
        - UserContext       (identity, roles, tenant)
        - EnvironmentContext (deployment info, runtime vars)
        - SituationContext  (dynamic payload inspection results)
    - Core ABBs import this module directly for governance traceability.
===============================================================================
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime


@dataclass
class ExecutionContext:
    """Carries both the *intent* and the *situation* across K9-AIF components."""
    intent: str
    situation: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def describe(self) -> str:
        """Human-readable summary for logs."""
        s_fmt = self.situation.get("format", "n/a")
        s_src = self.situation.get("source", "n/a")
        return f"[Intent={self.intent}] [Format={s_fmt}] [Source={s_src}] [Trace={self.trace_id}]"