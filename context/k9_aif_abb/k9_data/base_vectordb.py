# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_data/base_vectordb.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

from k9_aif_abb.k9_core.base_component import BaseComponent


class BaseVectorDB(BaseComponent, ABC):
    """
    K9-AIF Data ABB - BaseVectorDB
    ------------------------------
    Abstract base class for all vector database backends.
    Concrete SBBs (e.g., FAISSVectorDB, MilvusVectorDB, ChromaVectorDB)
    must implement the methods below.

    Responsibilities:
    - Define a consistent CRUD/search interface for embedding stores.
    - Integrate with BaseComponent for layer-aware telemetry.
    - Emit log events to the live K9-AIF console and Python logger.
    """

    layer = "Data ABB"

    def __init__(self, name: str = "BaseVectorDB", monitor=None):
        super().__init__(monitor=monitor)
        self.name = name
        self.logger = logging.getLogger(self.name)

    async def log(self, message: str, level: str = "INFO"):
        """Layer-aware async log; streams to monitor and Python logger."""
        await super().log(message, level)
        formatted = f"[{self.layer}:{self.name}] {message}"
        getattr(self.logger, level.lower(), self.logger.info)(formatted)

    # ------------------------------------------------------------------
    # Abstract Interface
    # ------------------------------------------------------------------

    @abstractmethod
    def insert(self, doc_id: str, embedding: List[float], metadata: Dict[str, Any]) -> None:
        """
        Insert a vector embedding with associated metadata.
        Example: insert(doc_id="claim_123", embedding=[0.13, ...], metadata={"type":"claim"})
        """
        raise NotImplementedError

    @abstractmethod
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for the top_k most similar embeddings.
        Should return: [{ "doc_id": str, "score": float, "metadata": dict }, ...]
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """Delete a vector entry by its document ID."""
        raise NotImplementedError