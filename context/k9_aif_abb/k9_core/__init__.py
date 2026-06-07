# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Core Package (ABB Foundation)

The `k9_core` package defines the foundational Architecture Building Blocks
(ABBs) of the K9-AIF framework.

It serves as the core architectural layer from which the rest of the framework
is derived, providing the primary base classes, interfaces, and contracts used
to model governed agentic systems in a structured and extensible way.

This package establishes the common abstractions for core framework concerns,
including agents, orchestrators, routing, persistence, governance, security,
monitoring, logging, retrieval, inference, integration, storage, streaming,
formatting, and presentation.

Rather than implementing domain-specific behavior, `k9_core` defines the
reusable architectural primitives that enable downstream packages and solutions
to remain consistent, composable, and enterprise-ready.


## Architectural Role

The `k9_core` package provides the base contracts for:

- Agent execution
- Orchestration and workflow coordination
- Routing and dispatch
- Persistence and storage
- Governance and security enforcement
- Monitoring and logging
- Retrieval and inference
- Integration and connectivity
- Streaming, formatting, and presentation

These abstractions form the heart of the ABB layer and ensure that all higher
framework components are built on a common architectural foundation.


## Design Intent

The goal of `k9_core` is to provide:

- **Consistency** — shared contracts across all framework layers
- **Extensibility** — reusable base classes designed for specialization
- **Governance-readiness** — integration points for policy, security, and audit
- **Composability** — clean interaction between architectural components
- **Implementation independence** — separation of abstractions from concrete SBBs


## Core Exports

The package exposes foundational framework classes including:

- `BaseComponent` — root base type for reusable framework elements
- `BaseAgent` — base abstraction for agents
- `BaseOrchestrator` — base abstraction for orchestrators
- `BasePersistence` — persistence contract for storage layers
- `IntentRouter` — routing abstraction for intent-driven dispatch
- `BaseMessageAgent` — base abstraction for messaging agents
- `BaseGovernance` — governance abstraction for policy-aware control
- `BaseSecurityAgent` — security abstraction for protected execution
- `BaseMonitor` — monitoring abstraction for telemetry and observability
- `BaseLoggingAgent` — logging abstraction for structured runtime logging
- `BaseDocParser` — retrieval abstraction for document parsing
- `BaseLLM` — inference abstraction for language model providers
- `BaseConnector` — integration abstraction for external systems
- `BaseStorage` — storage abstraction for backend implementations
- `BaseStreamProvider` — abstraction for streaming interfaces
- `BaseFormatterAgent` — formatting abstraction for output transformation
- `BaseUI` — presentation abstraction for user interaction layers


## Example: Extending a Core ABB


    from k9_aif_abb.k9_core.agent.base_agent import BaseAgent

    class MyAgent(BaseAgent):
        def execute(self, payload):
            return {
                "status": "success",
                "payload": payload
            }

"""