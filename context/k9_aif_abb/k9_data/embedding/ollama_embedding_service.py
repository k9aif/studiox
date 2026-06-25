# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""OOB embedding service using Ollama — lazy imports, config-driven."""

import logging
from typing import Any, Dict, List, Optional

from k9_aif_abb.k9_core.inference.base_embedding_service import BaseEmbeddingService

log = logging.getLogger("OllamaEmbeddingService")


class OllamaEmbeddingService(BaseEmbeddingService):

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._client = None
        vdb_cfg = self.config.get("vectordb", {})
        self._model = vdb_cfg.get("embedding_model", "nomic-embed-text")
        self._host = vdb_cfg.get(
            "embedding_endpoint",
            self.config.get("inference", {})
            .get("llm_factory", {})
            .get("base_url", "http://localhost:11434"),
        )

    def _ensure_client(self):
        if self._client is not None:
            return
        try:
            from ollama import Client
        except ImportError as exc:
            raise RuntimeError("pip install ollama required for OllamaEmbeddingService") from exc
        self._client = Client(host=self._host)
        log.info("Connected to Ollama embedding endpoint %s model=%s", self._host, self._model)

    def embed(self, text: str) -> List[float]:
        self._ensure_client()
        result = self._client.embeddings(model=self._model, prompt=text)
        return result.get("embedding", [])
