# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from k9_aif_abb.k9_core.retrieval.base_retriever import BaseRetriever

log = logging.getLogger("K9Retriever")


class K9Retriever(BaseRetriever):
    """
    OOB retriever — VectorDB-backed semantic search.

    Uses EmbeddingServiceFactory for embeddings and VectorDBFactory for
    the vector store.  Both are config-driven: the SBB picks the provider
    in config.yaml (``vectordb.provider``, ``vectordb.embedding_provider``).

    Falls back to source-mapping stub behaviour when no VectorDB is configured.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config=config)
        self.sources = self.config.get("sources", {})
        self.routing = self.config.get("routing", {})
        self._vectordb = None
        self._embedding_svc = None
        self._vectordb_available: Optional[bool] = None

    def _ensure_services(self) -> bool:
        """Lazy-init VectorDB + EmbeddingService. Returns True when operational."""
        if self._vectordb_available is not None:
            return self._vectordb_available
        try:
            from k9_aif_abb.k9_data.vectordb_factory import VectorDBFactory
            from k9_aif_abb.k9_factories.embedding_factory import EmbeddingServiceFactory

            self._vectordb = VectorDBFactory.create(self.config)
            svc = EmbeddingServiceFactory.create(self.config)
            svc.embed("probe")
            self._embedding_svc = svc
            self._vectordb_available = True
            log.info("[K9Retriever] VectorDB + EmbeddingService initialised")
        except Exception as exc:
            log.warning("[K9Retriever] VectorDB not available, falling back to source mapping: %s", exc)
            self._vectordb = None
            self._embedding_svc = None
            self._vectordb_available = False
        return self._vectordb_available

    def retrieve(
        self,
        intent: str,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        filters = filters or {}

        if self._ensure_services():
            return self._retrieve_from_vectordb(query, top_k, intent, filters)
        return self._retrieve_from_sources(intent, query, top_k, filters)

    def _retrieve_from_vectordb(
        self,
        query: str,
        top_k: int,
        intent: str,
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        query_embedding = self._embedding_svc.embed(query)
        if not query_embedding:
            log.warning("[K9Retriever] Empty embedding for query — falling back to source mapping")
            return self._retrieve_from_sources(intent, query, top_k, filters)

        hits = self._vectordb.search(query_embedding, top_k=top_k)
        results: List[Dict[str, Any]] = []
        for hit in hits:
            results.append({
                "text": hit.get("text", ""),
                "score": hit.get("score", 0.0),
                "source": hit.get("metadata", {}).get("source", "vectordb"),
                "metadata": {
                    "intent": intent,
                    "filters": filters,
                    **hit.get("metadata", {}),
                },
            })
        return results

    def _retrieve_from_sources(
        self,
        intent: str,
        query: str,
        top_k: int,
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        source_names = self.routing.get(intent, {}).get("sources", [])
        results: List[Dict[str, Any]] = []
        for source_name in source_names[:top_k]:
            results.append({
                "text": f"Stub result for query='{query}' from source='{source_name}'",
                "score": 1.0,
                "source": source_name,
                "metadata": {
                    "intent": intent,
                    "filters": filters,
                    "source_config": self.sources.get(source_name, {}),
                },
            })
        return results

    def store(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Embed and store a document in the VectorDB. Returns False if VectorDB unavailable."""
        if not self._ensure_services():
            return False
        embedding = self._embedding_svc.embed(text)
        if not embedding:
            return False
        self._vectordb.insert(doc_id, embedding, metadata or {})
        return True

    def store_context(self, result_key: str, agent_result: Dict[str, Any]) -> bool:
        """Store an agent's result in the VectorDB for downstream retrieval."""
        text = json.dumps(agent_result, default=str)
        return self.store(
            doc_id=f"ctx:{result_key}",
            text=text,
            metadata={"result_key": result_key, "type": "agent_context"},
        )
