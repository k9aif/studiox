# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Orchestrator Registry Package

The `k9_orchestrators.registry` package provides registry-related components
for managing orchestrator implementations within the K9-AIF framework.

It enables dynamic registration, lookup, and retrieval of orchestrators,
supporting flexible and configuration-driven orchestration selection.


## Key Responsibilities

- Registering orchestrator implementations
- Providing lookup and retrieval of orchestrators by name or type
- Supporting dynamic and pluggable orchestration strategies
- Enabling configuration-driven orchestrator selection
- Decoupling orchestrator definition from instantiation


## Architectural Role

The registry acts as a coordination layer between:

- Orchestrator definitions (`k9_orchestrators`)
- Factory components (`k9_factories`)
- Runtime configuration

It allows the framework to resolve which orchestrator should be used
without hardcoding dependencies.


## Example: Registering an Orchestrator

```python
from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator

class MyOrchestrator(BaseOrchestrator):
    def run(self, input_data):
        return input_data

# Example registration pattern
registry.register("default", MyOrchestrator)

```

Relationship to Other K9-AIF Packages
	•	k9_orchestrators defines orchestrator abstractions and implementations
	•	k9_factories may use the registry to instantiate orchestrators
	•	k9_core provides the base orchestrator contract
	•	k9_squad provides execution units coordinated by orchestrators

Architectural Positioning

The k9_orchestrators.registry package is a supporting infrastructure layer
that enables dynamic orchestration resolution.

It enhances flexibility and extensibility by allowing orchestrators to be
registered and selected at runtime based on configuration or system needs.

"""
