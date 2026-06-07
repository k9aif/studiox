# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
k9_agents.intent — Intent classification ABB layer.

Provides a two-level hierarchy matching the rest of the K9-AIF ABB stack:

- ``BaseIntentAgent`` — abstract skeleton; SBBs override ``classify()``.
- ``K9IntentAgent``   — OOB LLM-driven implementation; configurable via YAML.

Typical imports::

    from k9_aif_abb.k9_agents.intent import BaseIntentAgent, K9IntentAgent
"""

from k9_aif_abb.k9_agents.intent.base_intent_agent import BaseIntentAgent
from k9_aif_abb.k9_agents.intent.k9_intent_agent import K9IntentAgent

__all__ = ["BaseIntentAgent", "K9IntentAgent"]
