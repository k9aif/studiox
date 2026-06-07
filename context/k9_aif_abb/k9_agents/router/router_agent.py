# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# K9-AIF - RouterAgent (ABB Core)

import logging
import yaml
from typing import Dict, Any, Optional

from k9_aif_abb.k9_core.router.base_router import BaseRouter


class RouterAgent(BaseRouter):
    layer = "Router ABB"

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        monitor=None,
        message_bus=None,
        governance=None,
    ):
        super().__init__(
            config=config,
            monitor=monitor,
            message_bus=message_bus,
            governance=governance,
        )
        self.logger = logging.getLogger("RouterAgent")

        try:
            raw_registry = (config or {}).get("orchestrators", {}) or self._load_registry()
            self.registry = self._normalize_registry(raw_registry)

            self.logger.info(f"[{self.layer}] Loaded {len(self.registry)} orchestrators")
            for intent, orch in self.registry.items():
                self.logger.info(f"[{self.layer}] intent='{intent}' -> orchestrator='{orch}'")
        except Exception as e:
            self.registry = {}
            self.logger.warning(f"[{self.layer}] Failed to load orchestrator registry: {e}")

    def _load_registry(self) -> Dict[str, Any]:
        """Load orchestrators.yaml if not provided by config."""
        try:
            path = "k9_aif_abb/config/orchestrators.yaml"
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return data.get("orchestrators", [])
        except Exception as e:
            self.logger.error(f"[{self.layer}] Failed to read orchestrators.yaml: {e}")
            return {}

    def _normalize_registry(self, raw: Any) -> Dict[str, str]:
        """Convert orchestrator list/dict -> dict: intent -> name."""
        mapping: Dict[str, str] = {}

        if isinstance(raw, dict):
            for k, v in raw.items():
                if isinstance(v, dict):
                    mapping[k] = v.get("name", "")
                elif isinstance(v, str):
                    mapping[k] = v

        elif isinstance(raw, list):
            for entry in raw:
                if not isinstance(entry, dict):
                    continue
                intent = entry.get("intent")
                name = entry.get("name")
                if intent and name:
                    mapping[intent] = name

        return mapping

    async def route(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.normalize(payload)

        payload = await self.apply_pre_governance(payload)

        if payload.get("blocked"):
            return payload

        intent = payload.get("intent", "unknown")
        orchestrator = self.registry.get(intent)

        if orchestrator:
            self.logger.info(f"[{self.layer}] Routed intent='{intent}' -> '{orchestrator}'")
        else:
            self.logger.warning(f"[{self.layer}] No orchestrator found for intent='{intent}'")

        result = {
            "intent": intent,
            "orchestrator": orchestrator,
        }

        result = await self.apply_post_governance(result)
        return result