# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from pydantic import BaseModel
from typing import Optional, Dict, Any


class InferenceRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    task_type: Optional[str] = None

    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

    sensitivity: Optional[str] = None

    # Routing hints — used by K9ModelRouter scoring.
    # When omitted (None) the router falls back to capability-only matching,
    # preserving backwards compatibility with all existing callers.
    latency_budget: Optional[str] = None   # "realtime" | "interactive" | "batch"
    cost_profile:   Optional[str] = None   # "minimal" | "standard" | "premium"

    metadata: Optional[Dict[str, Any]] = None