# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from pydantic import BaseModel
from typing import Optional, Dict


class InferenceResponse(BaseModel):
    output: str

    model_alias: Optional[str] = None
    provider: Optional[str] = None

    token_usage: Optional[Dict[str, int]] = None
    latency_ms: Optional[int] = None