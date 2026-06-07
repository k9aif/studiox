# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Retrieval Package

The `k9_retrieval` package provides retrieval-related components within
the K9-AIF framework.

It is responsible for accessing, searching, and retrieving relevant
information from data sources such as vector databases, document stores,
and external knowledge systems.

This package builds on retrieval abstractions defined in `k9_core` and
includes default reusable retrieval implementations (e.g., K9Retriever)
that can be used directly or extended by downstream Solution Building
Blocks (SBBs).


## Key Responsibilities

- Retrieving relevant data from structured and unstructured sources
- Supporting vector search and semantic retrieval
- Enabling document parsing and chunking workflows
- Providing pluggable retrieval backends
- Supporting integration with persistence and inference layers


## Architectural Pattern

In K9-AIF, retrieval is a core part of agent execution:

    Agent → Retriever → Data Source (Vector DB / Documents / APIs)

- Agents request relevant context through retrieval components
- Retrievers interact with persistence or external systems
- Retrieved data is passed back into agent workflows or inference layers


## Default Retrieval Component

- `K9Retriever` — default retrieval implementation provided by the framework

This component typically:
- connects to vector databases
- performs similarity search
- retrieves relevant document chunks
- returns structured context for downstream processing


## Example: Using a Retriever

```python
from k9_aif_abb.k9_factories.retriever_factory import RetrieverFactory

config = {
    "retrieval": {
        "type": "k9"
    }
}

retriever = RetrieverFactory.create(config)

results = retriever.retrieve("What is K9-AIF?")
print(results)

"""