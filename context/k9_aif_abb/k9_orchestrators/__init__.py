# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Orchestrators Package (ABB Layer)

The `k9_orchestrators` package defines the orchestration-level Architecture 
Building Blocks (ABBs) within the K9-AIF framework.

Orchestrators coordinate execution across squads and agents, manage workflow
progression, enforce sequencing and dependencies, and ensure that system-level
objectives are achieved in a controlled and observable manner.


## Architectural Role

Within the K9-AIF hierarchy:

    Router → Orchestrator → Squad → Agents

- Routers determine intent and route requests
- Orchestrators control execution flow
- Squads group and coordinate agents
- Agents perform atomic processing tasks

The orchestrator acts as the central control layer that binds these components
into a coherent execution model.


## Key Concepts

- Workflow coordination  
- Squad-level control  
- Execution sequencing  
- State management  
- Governance integration  


## Responsibilities of an Orchestrator

- Invoking squads in the correct sequence
- Managing dependencies between execution steps
- Handling branching and conditional logic
- Aggregating results from multiple squads
- Ensuring observability, logging, and traceability
- Enforcing governance and security policies


## Example: Extending an Orchestrator ABB

from k9_aif_abb.k9_core.orchestration.base_orchestrator import BaseOrchestrator

class ExampleOrchestrator(BaseOrchestrator):
    def __init__(self, squads):
        super().__init__()
        self.squads = squads

    def run(self, input_data):
        result = input_data
        for squad in self.squads:
            result = squad.run(result)
        return result

        
## Relationship to Other K9-AIF Packages
	•	Receives routing decisions from router components
	•	Coordinates squads defined in k9_squad
	•	Uses k9_factories to construct dependencies
	•	Integrates with k9_monitoring for observability
	•	Persists state via k9_persistence
	•	Enforces policies defined in k9_governance

Architectural Positioning

The k9_orchestrators package represents the control layer of the K9-AIF
architecture.

It enables structured, governed, and scalable execution of multi-agent systems
by coordinating squads and enforcing workflow logic at an architectural level.

"""
