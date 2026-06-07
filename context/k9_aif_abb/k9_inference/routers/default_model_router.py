# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from ..models.inference_request import InferenceRequest
from ..models.inference_response import InferenceResponse
from ..models.route_decision import RouteDecision
from .base_model_router import BaseModelRouter


class DefaultModelRouter(BaseModelRouter):

    def __init__(self, default_model_alias: str):
        self.default_model_alias = default_model_alias

    def route(self, request: InferenceRequest) -> RouteDecision:
        return RouteDecision(
            model_alias=self.default_model_alias,
            rationale="Default router selected configured model"
        )

    def invoke(self, request: InferenceRequest) -> InferenceResponse:
        decision = self.route(request)
        return InferenceResponse(
            output="Model invocation placeholder",
            model_alias=decision.model_alias
        )

    async def ainvoke(self, request: InferenceRequest) -> InferenceResponse:
        return self.invoke(request)