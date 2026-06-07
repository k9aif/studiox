# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

# File: k9_aif_abb/k9_agents/supporting/async_agent.py

import time
import uuid
from typing import Dict, Any, Optional

# K9-AIF Agent Imports - aligned to ABB -> SBB layering

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent
from k9_aif_abb.k9_core.persistence.base_persistence import (
    BasePersistence,
    MemoryPersistence,
)
from k9_aif_abb.k9_persistence.sqlite_persistence import SQLitePersistence
from k9_aif_abb.k9_core.messaging.base_queue import BaseQueue, LocalQueue


class AsyncAgent(BaseAgent):
    """
    K9-AIF AsyncAgent
    -----------------
    ABB-level agent for handling long-running tasks asynchronously.

    Responsibilities:
    - Queue incoming tasks into LocalQueue or external queues (future)
    - Persist task state (MemoryPersistence or SQLitePersistence)
    - Provide lifecycle methods for query/delete
    """

    layer = "Async ABB"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config or {})
        self.name = "AsyncAgent"

        # --- Persistence setup ---
        persistence_cfg = self.config.get("persistence", {})
        backend = persistence_cfg.get("backend", "memory").lower()

        if backend == "sqlite":
            db_path = persistence_cfg.get("db_path", "k9_aif_state.db")
            self.persistence: BasePersistence = SQLitePersistence(db_path=db_path)
            self.log(f"[{self.layer}] Using SQLite persistence at {db_path}", "INFO")
        else:
            self.persistence: BasePersistence = MemoryPersistence()
            self.log(f"[{self.layer}] Using in-memory persistence", "INFO")

        # --- Queue setup (stub) ---
        self.queue: BaseQueue = LocalQueue()
        self.log(f"[{self.layer}] Initialized LocalQueue backend", "DEBUG")

    # ----------------------------------------------------------------------
    # Core task execution logic
    # ----------------------------------------------------------------------
    def execute(self, request: Dict[str, Any], task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Store request state and simulate async task execution.
        Allows caller to provide a task_id, or generates one if not provided.
        """
        task_id = task_id or str(uuid.uuid4())
        start_ts = time.time()

        # --- Initial state ---
        state = {
            "task_id": task_id,
            "status": "queued",
            "request": request,
            "created_at": start_ts,
        }
        self.persistence.save_state(task_id, state)
        self.queue.send(task_id, request)
        self.log(f"[{self.layer}] Queued async task {task_id}", "INFO")

        # --- Simulated processing ---
        time.sleep(0.1)
        state.update({
            "status": "completed",
            "completed_at": time.time(),
            "result": f"Processed request: {request}",
        })
        self.persistence.update_state(task_id, state)
        self.log(f"[{self.layer}] Completed async task {task_id}", "INFO")

        return {
            "task_id": task_id,
            "status": state["status"],
            "result": state["result"],
        }

    # ----------------------------------------------------------------------
    # Lifecycle utility methods
    # ----------------------------------------------------------------------
    def load_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task state by ID."""
        state = self.persistence.load_state(task_id)
        if not state:
            self.log(f"[{self.layer}] Task {task_id} not found", "WARNING")
        return state

    def delete_task(self, task_id: str) -> None:
        """Remove task state."""
        self.persistence.delete_state(task_id)
        self.log(f"[{self.layer}] Deleted task {task_id}", "INFO")