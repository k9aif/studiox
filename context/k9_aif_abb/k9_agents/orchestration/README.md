# Orchestration Layer
Implements orchestration strategies by extending `BaseOrchestrator`.

## Extend
```python
# my_orchestrator.py
from typing import Dict, Any
from k9_core.base_orchestrator import BaseOrchestrator

class MyOrchestrator(BaseOrchestrator):
    def executeFlow(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._emit_metric("orch.start")
        try:
            # ... your flow ...
            return {"status": "OK", "answer": "done", "meta": {"orchestrator": self.name()}}
        except Exception as e:
            self._observe("orch.error", {"err": str(e)})
            return {"status": "ERROR", "error": str(e)}

            

Register with router:

from k9_agents.orchestration.router_agent import RouterAgent
from .my_orchestrator import MyOrchestrator

router = RouterAgent()
router.register("myflow", MyOrchestrator())

Add Confi-drive (optional)

flows:
  - intent: "myflow"
    orchestrator: "k9_agents.orchestration.my_orchestrator:MyOrchestrator"