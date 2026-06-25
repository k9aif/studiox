# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""ABB contract for embedding services."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseEmbeddingService(ABC):
    """
    K9-AIF Inference ABB — BaseEmbeddingService

    Abstract contract for generating vector embeddings from text.
    Concrete SBBs (OllamaEmbeddingService, etc.) implement the provider-specific
    call. Config-driven selection via EmbeddingServiceFactory.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Generate an embedding vector for a single text string."""
        raise NotImplementedError

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts. Override for batch-optimised providers."""
        return [self.embed(t) for t in texts]
