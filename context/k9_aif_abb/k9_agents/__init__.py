# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Agents Package (ABB Layer)

The `k9_agents` package defines the agent-oriented Architecture Building Blocks
(ABBs) of the K9-AIF framework.

It contains the foundational abstractions, patterns, and supporting components
required to model agents as governed, extensible, and orchestration-aware
architectural elements within enterprise agentic systems.

In K9-AIF, agents are treated as architectural building blocks rather than
standalone scripts or isolated runtime units. They are designed to participate
in structured orchestration flows, operate under governance policies, and
integrate cleanly with persistence, monitoring, routing, and external systems.


## Architectural Role

The `k9_agents` package provides the agent-level ABB foundation for:

- Defining agent responsibilities and execution patterns
- Establishing reusable agent contracts and extension points
- Supporting governed and policy-aware agent behavior
- Enabling integration with orchestrators, routers, persistence, and monitoring
- Promoting consistent design across domain-specific agent implementations


## Core Design Intent

The purpose of this package is to ensure that agents in K9-AIF are:

- Contract-driven — built on well-defined interfaces and execution methods
- Extensible — designed for specialization into domain-specific behaviors
- Governed — capable of participating in policy-aware and auditable flows
- Composable — able to function as part of larger orchestrated systems
- Observable — ready for monitoring, tracing, and operational oversight


## Typical Responsibilities of Agent ABBs

Agent-related ABBs in this package may support patterns such as:

- Receiving and processing structured payloads
- Performing domain-specific reasoning or transformation
- Interacting with persistence or retrieval layers
- Calling external services, tools, or APIs
- Returning structured outputs for downstream orchestration
- Participating in monitored and policy-governed execution flows


## Relationship to Other K9-AIF Packages

The `k9_agents` package works in conjunction with other ABB packages:

- `k9_core` provides the foundational base classes and interfaces
- `k9_orchestrators` coordinates multi-step and multi-agent execution flows
- `k9_factories` constructs dependent components and integrations
- `k9_persistence` supplies storage and state management abstractions
- `k9_monitoring` supports observability and runtime telemetry
- `policies` provides governance and compliance rules


## Example: Extending an Agent ABB

    from k9_aif_abb.k9_core.agent.base_agent import BaseAgent

    class MyAgent(BaseAgent):
        def execute(self, payload):
            return {
                "status": "success",
                "result": payload
            }

"""