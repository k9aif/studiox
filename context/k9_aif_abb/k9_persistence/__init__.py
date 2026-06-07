# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Persistence Package

The `k9_persistence` package provides persistence-related components within
the K9-AIF framework.

It is responsible for the durable storage and backend persistence of structured,
unstructured, and vector-oriented data used by agents, retrievers, orchestrators,
and other framework services.

This package builds on the `BasePersistence` contract defined in `k9_core`
and provides concrete persistence implementations that can be provisioned
through `PersistenceFactory`, reused by framework agents, or extended by
downstream Solution Building Blocks (SBBs).


## Key Responsibilities

- Providing concrete persistence implementations
- Managing durable storage of framework data
- Supporting structured and vector-oriented persistence backends
- Enabling pluggable persistence providers
- Separating storage mechanics from higher-level data and retrieval logic
- Supporting framework-level persistence usage through factory provisioning


## Typical Components

This package may include:

- `sqlite_persistence` — SQLite-based persistence implementation
- `chromadb_persistence` — ChromaDB-based vector persistence implementation
- Additional persistence backends for future framework extensions


## Example: Extending BasePersistence

    from k9_aif_abb.k9_core.persistence.base_persistence import BasePersistence

    class CustomPersistence(BasePersistence):
        def save(self, key, value):
            pass

        def load(self, key):
            pass


This example shows how persistence implementations are derived from the
core BasePersistence abstraction.


## Relationship to Other K9-AIF Packages

- `k9_core` defines the BasePersistence contract
- `k9_factories` provisions persistence implementations through PersistenceFactory
- `k9_agents` may use persistence components for shared or durable storage
- `k9_retrieval` may access vector-enabled persistence backends for search
- `k9_orchestrators` may persist workflow state
- `k9_monitoring` and `k9_governance` may rely on persistent records


## Architectural Positioning

The `k9_persistence` package represents the framework persistence layer of K9-AIF.

It focuses on how data is physically stored and retrieved through managed backend
implementations, while higher-level packages such as `k9_data` define how data
is modeled, interpreted, and used within retrieval and agentic workflows.

This separation preserves clean architectural boundaries between data semantics
and durable storage mechanics.


## Architectural Note

`k9_persistence` defines how data is physically stored and retrieved,
while `k9_data` defines the structure and semantics of that data.

"""