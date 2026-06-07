# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Policies Package

The `policies` package contains declarative governance rules used by the
K9-AIF framework.

These policies define security, compliance, validation, and operational
constraints that are enforced at runtime by governance components.


## Key Responsibilities

- Defining governance rules in declarative form (YAML)
- Supporting policy-driven validation and enforcement
- Enabling configurable security and compliance controls
- Separating policy definition from enforcement logic


## Typical Contents

- `governance.yaml` — rules for validation, security, and compliance


## Architectural Positioning

Policies → Governance → Agents / Orchestrators

The `policies` package defines *what rules exist*, while `k9_governance`
components define *how those rules are enforced*.


## Architectural Note

> policies define the rules, while k9_governance enforces those rules.

"""