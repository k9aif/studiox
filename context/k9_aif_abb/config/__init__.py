# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Configuration Layer

The `config` package provides declarative configuration used to define how
K9-AIF systems are instantiated, wired, and executed at runtime.

It contains YAML-based configuration files that drive:

- Agent composition and behavior
- Squad definitions
- Orchestration flows
- Governance policies
- Factory provisioning
- Model and backend selection

This layer acts as the control plane of the system, enabling dynamic and
configuration-driven assembly of ABB and SBB components without modifying code.


## Architectural Positioning

Config → Factories → ABB → SBB → Runtime

The configuration layer does not implement logic. Instead, it defines how
components are selected, connected, and executed.


## Key Files

- `config.yaml` — global system configuration
- `flows.yaml` — workflow definitions
- `example_squads.yaml` — squad composition
- `governance.yaml` — policy definitions
- `orchestrators.yaml` — orchestration wiring


## Architectural Note

> Config defines how the system is wired and executed, while ABB/SBB packages define what the system does.

"""