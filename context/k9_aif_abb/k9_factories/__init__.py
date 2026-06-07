# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Factories Package

The `k9_factories` package provides factory components responsible for
constructing and provisioning runtime implementations of K9-AIF framework
services.

Factories enable configuration-driven instantiation of components such as
persistence backends, routers, orchestrators, governance modules,
connectors, and monitoring adapters.

They serve as the bridge between architectural abstractions (ABB layer) and
concrete runtime implementations, ensuring modularity, extensibility, and
decoupled design across the framework.


## Key Responsibilities

- Centralized creation of framework components
- Configuration-driven backend and provider selection
- Decoupling of implementation from usage
- Support for pluggable and extensible integrations
- Consistent construction patterns across framework layers


## Available Factory Modules

- connector_factory
- data_transformation_factory
- governance_factory
- llm_factory
- mcp_client_connection_factory
- message_factory
- model_router_factory
- monitor_factory
- orchestration_factory
- persistence_factory
- retriever_factory
- router_factory
- security_factory
- streaming_factory


## Architectural Positioning

The `k9_factories` package is part of the framework’s construction layer.

It operationalizes architectural building blocks by instantiating concrete
components while preserving abstraction boundaries and enabling flexible,
configuration-driven system behavior.


## Usage Example

    from k9_aif_abb.k9_factories.persistence_factory import PersistenceFactory
    from k9_aif_abb.k9_factories.router_factory import RouterFactory

    # Example configuration
    config = {
        "persistence": {
            "backend": "sqlite"
        },
        "router": {
            "type": "default"
        }
    }

    # Create persistence backend
    store = PersistenceFactory.create(config)

    # Create router
    router = RouterFactory.create(config)

    # Use components
    route = router.route({"input": "sample payload"})


## Architectural Note

Factories are primarily consumed by SBB components (agents, orchestrators,
retrievers) rather than directly by end users. They enable runtime flexibility
while preserving strict separation between ABB contracts and SBB implementations.
"""