# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from unittest.mock import patch, MagicMock
import pytest

from k9_aif_abb.k9_core.inference.base_embedding_service import BaseEmbeddingService
from k9_aif_abb.k9_factories.embedding_factory import EmbeddingServiceFactory


class StubEmbeddingService(BaseEmbeddingService):
    def embed(self, text):
        return [0.1, 0.2, 0.3]


class TestEmbeddingServiceFactory:

    def setup_method(self):
        EmbeddingServiceFactory._bootstrapped = False
        EmbeddingServiceFactory._registry.clear()

    def test_register_and_create_custom_provider(self):
        EmbeddingServiceFactory.register("stub", StubEmbeddingService)
        svc = EmbeddingServiceFactory.create({"vectordb": {"embedding_provider": "stub"}})
        assert isinstance(svc, StubEmbeddingService)
        assert svc.embed("hello") == [0.1, 0.2, 0.3]

    def test_unknown_provider_raises(self):
        EmbeddingServiceFactory._ensure_defaults()
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            EmbeddingServiceFactory.create({"vectordb": {"embedding_provider": "nonexistent"}})

    def test_default_provider_is_ollama(self):
        EmbeddingServiceFactory._ensure_defaults()
        assert "ollama" in EmbeddingServiceFactory._registry

    def test_batch_embed_delegates_to_embed(self):
        svc = StubEmbeddingService()
        result = svc.embed_batch(["a", "b"])
        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]


class TestK9RetrieverFallback:

    def test_retriever_falls_back_when_vectordb_unavailable(self):
        from k9_aif_abb.k9_data.retrieval.k9_retriever import K9Retriever

        config = {
            "sources": {"docs": {"type": "vectordb"}},
            "routing": {"lookup": {"sources": ["docs"]}},
        }
        r = K9Retriever(config=config)
        results = r.retrieve(intent="lookup", query="test")
        assert len(results) == 1
        assert results[0]["source"] == "docs"
        assert r._vectordb_available is False
