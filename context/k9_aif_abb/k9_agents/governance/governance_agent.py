# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_agents/governance/governance_agent.py

from pathlib import Path
import yaml
import re
from typing import Dict, Any, Optional

from k9_aif_abb.k9_core.governance.base_governance import BaseGovernance
from k9_aif_abb.k9_factories.llm_factory import LLMFactory


class GovernanceAgent(BaseGovernance):
    """
    K9-AIF GovernanceAgent
    ----------------------
    Enforces enterprise safety and compliance policies
    before and after model execution.

    Combines:
    - Keyword / regex-based blocking
    - Intent-domain validation
    - LLM-based reasoning guard
    """

    layer = "Governance ABB"

    def __init__(self, config: Optional[Dict[str, Any]] = None, monitor=None):
        super().__init__(config=config or {}, monitor=monitor)

        default_policy = "k9_aif_abb/policies/governance.yaml"
        policy_path = Path(
            self.config.get("governance", {}).get("policy_path", default_policy)
        )

        try:
            with open(policy_path, "r", encoding="utf-8") as f:
                self.policies = yaml.safe_load(f) or {}
        except FileNotFoundError:
            self.policies = {}

        llm_cfg = self.policies.get(
            "llm_policy_model",
            {"provider": "ollama", "model": "llama-guard-3"},
        )

        try:
            llm = LLMFactory.from_config(llm_cfg)
            if callable(llm) and not hasattr(llm, "generate"):
                class Wrapper:
                    def __init__(self, fn):
                        self.fn = fn

                    def generate(self, prompt: str):
                        return self.fn(prompt)

                self.guard_llm = Wrapper(llm)
            else:
                self.guard_llm = llm
        except Exception:
            class StubLLM:
                def generate(self, prompt: str):
                    return "safe"

            self.guard_llm = StubLLM()

    async def pre_process(
        self,
        payload: Dict[str, Any],
        ctx: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            await self.log(f"Non-dict payload ({type(payload)}), coercing", "WARN")
            payload = {"input": str(payload)}

        text = str(payload)

        for kw in self.policies.get("blocked_keywords", []):
            if kw.lower() in text.lower():
                await self.log(f"Blocked keyword '{kw}' found", "WARN")
                return {"blocked": True, "answer": "Request blocked by governance policy"}

        if "intent" in payload and self.policies.get("allowed_domains"):
            allowed = self.policies["allowed_domains"]
            if payload["intent"] not in allowed:
                await self.log(f"Intent '{payload['intent']}' not allowed", "WARN")
                return {"blocked": True, "answer": "Request blocked by governance policy"}

        prompt = f"Is this request safe under enterprise policy? Answer 'safe' or 'unsafe': {text}"
        result = str(self.guard_llm.generate(prompt))
        if result.strip().lower().startswith("unsafe"):
            await self.log(f"LLM pre-check flagged as unsafe -> {result}", "ERROR")
            return {"blocked": True, "answer": "Request blocked by governance policy"}

        return payload

    async def post_process(
        self,
        payload: Dict[str, Any],
        ctx: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        text = str(payload)

        for rule in self.policies.get("response_redaction", []):
            try:
                text = re.sub(rule["pattern"], rule["replace"], text)
            except re.error as e:
                await self.log(f"Invalid redaction pattern: {e}", "ERROR")

        prompt = f"Check if this system response is safe: {text}"
        result = str(self.guard_llm.generate(prompt))
        if "unsafe" in result.lower():
            await self.log("LLM post-check flagged unsafe output", "ERROR")
            return {"answer": "Response withheld by governance policy"}

        return {"answer": text}