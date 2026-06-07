# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Governance Package

The `k9_governance` package provides governance-oriented framework components
within K9-AIF.

It builds on the governance abstractions defined in `k9_core` and supplies
default, reusable governance implementations that can be used directly,
extended, or replaced by downstream Solution Building Blocks (SBBs).

This package exists to make governance a built-in architectural capability
rather than an afterthought. It enables agentic systems to enforce rules,
validate behavior, and apply operational guardrails in a structured and
reusable way.


## Architectural Role

The `k9_governance` package supports the framework by providing:

- Default governance components built on ABB contracts
- Reusable policy enforcement patterns
- Validation and guardrail mechanisms
- Extension points for application-specific governance implementations
- Integration hooks for orchestrators, agents, monitoring, and persistence


## Design Intent

The intent of this package is to ensure that governance in K9-AIF is:

- Reusable — common governance logic can be shared across solutions
- Extensible — default implementations can be subclassed or replaced
- Policy-aware — governance behavior is aligned with framework rules and controls
- Operational — enforcement occurs during execution, not only at design time
- Observable — governance outcomes can be monitored and audited


## Default Governance Components

This package may include framework-provided governance implementations such as:

- `ProfanityGovernance` — a default governance component that validates or filters inappropriate content according to configured rules

Such components are reference implementations built on `BaseGovernance` and are
intended to demonstrate how governance ABB contracts can be realized in practice.


## Example: Governance Implementation Pattern

    from k9_aif_abb.k9_core.governance.base_governance import BaseGovernance

    class ProfanityGovernance(BaseGovernance):
        def validate(self, text):
            return {
                "allowed": True,
                "text": text
            }


## Architectural Note

k9_governance provides reusable governance implementations built on ABB
contracts, while `policies` defines the declarative rules those components enforce.
"""