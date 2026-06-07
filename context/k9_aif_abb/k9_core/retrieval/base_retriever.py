# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseRetriever(ABC):
    """
    ABB contract for governed retrieval.

    A retriever receives an intent + query and returns normalized results.
    Concrete implementations decide how sources are searched.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    def retrieve(
        self,
        intent: str,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Return normalized retrieval results.

        Expected normalized shape per item:
        {
            "text": "...",
            "score": 0.92,
            "source": "policy_index",
            "metadata": {...}
        }
        """
        raise NotImplementedError("Subclasses must implement retrieve().")