# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from k9_aif_abb.k9_factories.retriever_factory import RetrieverFactory
from k9_aif_abb.k9_data.retrieval.k9_retriever import K9Retriever


def test_k9_retriever_basic():
    config = {
        "retrieval": {
            "default_retriever": "k9",
            "sources": {
                "test_docs": {
                    "type": "vectordb",
                    "collection": "test_collection",
                }
            },
            "routing": {
                "test_lookup": {
                    "sources": ["test_docs"]
                }
            },
        }
    }

    RetrieverFactory.reset()
    RetrieverFactory.bootstrap(config)
    RetrieverFactory.register("k9", K9Retriever)

    retriever = RetrieverFactory.get()

    results = retriever.retrieve(
        intent="test_lookup",
        query="What is K9-AIF?"
    )

    assert isinstance(results, list)
    assert len(results) > 0

    item = results[0]

    assert "text" in item
    assert "score" in item
    assert "source" in item
    assert "metadata" in item


def test_routing_sources():
    config = {
        "retrieval": {
            "default_retriever": "k9",
            "sources": {
                "a": {"type": "vectordb"},
                "b": {"type": "vectordb"},
            },
            "routing": {
                "multi": {
                    "sources": ["a", "b"]
                }
            },
        }
    }

    RetrieverFactory.reset()
    RetrieverFactory.bootstrap(config)
    RetrieverFactory.register("k9", K9Retriever)

    retriever = RetrieverFactory.get()

    results = retriever.retrieve(intent="multi", query="test")

    sources = [r["source"] for r in results]

    assert "a" in sources
    assert "b" in sources