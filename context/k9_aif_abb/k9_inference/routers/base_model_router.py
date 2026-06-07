# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from abc import ABC, abstractmethod

from ..models.inference_request import InferenceRequest
from ..models.inference_response import InferenceResponse
from ..models.route_decision import RouteDecision


class BaseModelRouter(ABC):
    """
    Architecture Building Block (ABB) for model routing.

    Implementations decide which model should handle
    a given inference request.
    """

    @abstractmethod
    def route(self, request: InferenceRequest) -> RouteDecision:
        """
        Select the best model for the request.
        """
        pass

    @abstractmethod
    def invoke(self, request: InferenceRequest) -> InferenceResponse:
        """
        Route the request and execute the inference (sync).
        """
        pass

    @abstractmethod
    async def ainvoke(self, request: InferenceRequest) -> InferenceResponse:
        """
        Route the request and execute the inference (async).
        """
        pass