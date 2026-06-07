# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

from typing import Dict, Any, Optional
from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from k9_aif_abb.k9_agents.storage.object_storage_agent import ObjectStorageAgent


class StorageAgent(BaseAgent):
    """
    ABB StorageAgent
    ----------------
    Handles persistence of processed artifacts into a storage backend.
    """

    layer = "Storage ABB"  

    def __init__(self, config: Optional[Dict[str, Any]] = None, backend: Optional[Any] = None):
        super().__init__(config or {})
        self.backend = backend or ObjectStorageAgent()
        self.log(f"[{self.layer}] Initialized with backend: {self.backend.__class__.__name__}")

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Store the given payload via the configured backend."""
        self.log(f"[{self.layer}] Executing storage operation for payload keys: {list(payload.keys())}")

        try:
            self.backend.execute(payload)
            result = {"status": "stored", "backend": self.backend.__class__.__name__}
            self.log(f"[{self.layer}] Successfully stored payload", "INFO")
        except Exception as e:
            result = {"status": "error", "error": str(e)}
            self.log(f"[{self.layer}] Storage failed: {e}", "ERROR")

        return result