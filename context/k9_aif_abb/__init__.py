# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Framework (ABB Layer)

K9-AIF (Agent-based Integration Framework) is a governed, modular, and extensible
architecture-first framework for designing and building agentic systems.

This package represents the **Architecture Building Block (ABB) layer** of K9-AIF.

It defines the foundational abstractions, base classes, contracts, and extension
points required to construct enterprise-grade agentic AI systems. These ABBs
serve as the blueprint from which concrete Solution Building Blocks (SBBs) are
derived in downstream implementations.

K9-AIF introduces a missing architectural layer for agentic AI — enabling systems
to move from experimental orchestration toward governed, observable, and
architecturally defensible solutions.


## Core Architectural Principles

- Architecture-first design for agentic systems
- Clear separation of ABB (architecture) and SBB (implementation)
- Contract-driven design using base classes and interfaces
- Extensible orchestration, routing, persistence, and monitoring layers
- Policy-driven governance and security integration points
- Interoperability with external agent frameworks and LLM providers


## Scope of the ABB Layer

The ABB layer defines the architectural foundation for:

- Base agent definitions and execution contracts
- Router abstractions for intent-based dispatch
- Orchestrator abstractions for multi-step coordination
- Persistence interfaces and storage contracts
- Monitoring and observability interfaces
- Factory-based component instantiation
- Governance, policy, and security extension points

These abstractions are intentionally implementation-agnostic and are designed
to be specialized into SBBs in application-specific or integration layers.


## Primary Packages (ABB Components)

- `k9_core` — Core base classes and abstract framework contracts
- `k9_agents` — Agent abstractions and agent-related framework components
- `k9_factories` — Factory abstractions for constructing framework components
- `k9_monitoring` — Monitoring and telemetry interfaces and adapters
- `k9_persistence` — Persistence abstractions and storage contracts
- `k9_orchestrators` — Orchestration and control-flow abstractions
- `k9_utils` — Shared utilities supporting framework operation


## K9-AIF ABB Package Structure

| Package | Architectural Role | Description |
|---------|--------------------|-------------|
| `k9_core` | ABB Foundation | Defines core abstract classes and interfaces (Agent, Router, Orchestrator, Persistence, Governance, Security). |
| `k9_agents` | Agent Abstractions | Provides agent-related base classes, patterns, and supporting framework components. |
| `k9_factories` | Factory Layer | Defines factory abstractions for creating orchestrators, persistence layers, monitoring adapters, and connectors. |
| `k9_monitoring` | Observability Interfaces | Provides monitoring, telemetry, and runtime observability abstractions. |
| `k9_persistence` | Persistence Interfaces | Defines storage contracts and abstraction layers for structured and vector data. |
| `k9_orchestrators` | Orchestration Interfaces | Defines coordination and execution flow abstractions for multi-agent systems. |
| `k9_utils` | Utility Layer | Provides configuration loading, logging setup, timing utilities, and transformation helpers. |
| `policies` | Governance Configuration | Contains configuration-driven policies for governance, compliance, and security. |
| `tests` | Verification Layer | Validates ABB contracts, interfaces, and framework behavior. |


## Architectural Positioning

K9-AIF ABB is the architectural foundation of the broader K9-AIF ecosystem.

It does not implement domain-specific solutions. Instead, it defines the reusable
architectural building blocks required to construct governed agentic systems.

Solution Building Blocks (SBBs) — including concrete agents, orchestrators,
connectors, and integrations — are derived from these ABBs in higher-level
implementation layers.

This separation ensures:

- Long-term maintainability
- Architectural clarity
- Implementation flexibility
- Enterprise-grade governance


## Example: Defining a Custom Agent from ABB

    from k9_aif_abb.k9_core.agent.base_agent import BaseAgent

    class MyAgent(BaseAgent):
        def execute(self, payload):
            return {
                "status": "success",
                "input": payload
            }

"""