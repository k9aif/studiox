# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from pydantic import BaseModel
from typing import Optional


class RouteDecision(BaseModel):
    model_alias: str
    provider: Optional[str] = None

    score: Optional[float] = None
    predicted_cost: Optional[float] = None
    predicted_latency_ms: Optional[int] = None

    rationale: Optional[str] = None