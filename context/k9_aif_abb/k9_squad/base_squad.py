# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

import logging
import time

log = logging.getLogger(__name__)


def _resolve_path(key: str, ctx: dict):
    """Dot-notation traversal into ctx. Returns None if any segment is missing."""
    val = ctx
    for part in key.split("."):
        if not isinstance(val, dict):
            return None
        val = val.get(part)
    return val


def _eval_when(when_cfg, ctx: dict) -> bool:
    """
    Evaluate a ``when:`` condition block against the accumulated step context.

    Returns True (step should run) if:
    - ``when_cfg`` is None (unconditional)
    - ``when.any`` list: at least one sub-condition is true (OR)
    - ``when.all`` list: every sub-condition is true (AND)
    - single condition with ``key`` + operator (eq/ne/lt/lte/gt/gte)
    """
    if when_cfg is None:
        return True
    if isinstance(when_cfg, list):
        return any(_eval_when(c, ctx) for c in when_cfg)
    if not isinstance(when_cfg, dict):
        return bool(when_cfg)
    if "any" in when_cfg:
        return any(_eval_when(c, ctx) for c in when_cfg["any"])
    if "all" in when_cfg:
        return all(_eval_when(c, ctx) for c in when_cfg["all"])
    key = when_cfg.get("key")
    val = _resolve_path(key, ctx) if key else None
    if "eq"  in when_cfg: return val == when_cfg["eq"]
    if "ne"  in when_cfg: return val != when_cfg["ne"]
    if "lt"  in when_cfg: return val is not None and val <  when_cfg["lt"]
    if "lte" in when_cfg: return val is not None and val <= when_cfg["lte"]
    if "gt"  in when_cfg: return val is not None and val >  when_cfg["gt"]
    if "gte" in when_cfg: return val is not None and val >= when_cfg["gte"]
    return True


class BaseSquad:
    """
    ABB: Represents a coordinated team of agents
    working together for a capability or use case.

    Agent coordination is driven by the ``flow`` config loaded from squads.yaml.
    Each step specifies which agent to call, what key to store its result under,
    and any static context overrides to merge before the call.
    """

    def __init__(self, squad_id, agents, orchestrator=None, monitor=None):
        self.squad_id = squad_id
        self.agents = agents or []
        self.monitor = monitor
        self.description = ""
        self.flow = []
        self.metadata = {}

    def execute(self, payload: dict) -> dict:
        """
        Drive the agent pipeline from flow config in squads.yaml.

        Context scoping:
        - ``context_keys`` on a flow step limits which keys the agent sees.
          The original payload keys are always included; ``context_keys``
          controls which *upstream result keys* are passed through.
        - When ``context_keys`` is absent the agent receives the full
          accumulated context (backwards compatible).

        Steps with a ``when:`` field are skipped if the condition evaluates
        to False against the current context.
        """
        if not self.flow:
            raise RuntimeError(
                f"[{self.squad_id}] No flow defined — add a 'flow:' section to squads.yaml"
            )

        # Validate flow step structure before executing anything
        for i, step in enumerate(self.flow):
            if not isinstance(step, dict) or "agent" not in step:
                raise ValueError(
                    f"[{self.squad_id}] flow step {i} is missing required field 'agent': {step!r}"
                )

        agent_map = {a.__class__.__name__: a for a in self.agents}
        # Only check agents for unconditional steps (conditional ones may legitimately be absent)
        unconditional = [s["agent"] for s in self.flow if s.get("when") is None]
        missing = [name for name in unconditional if name not in agent_map]
        if missing:
            raise RuntimeError(
                f"[{self.squad_id}] Required agents not loaded: {missing}"
            )

        if self.monitor:
            self.monitor.on_squad_start(self.squad_id)

        context = {**payload, "squad_id": self.squad_id}
        results = {}

        for step_idx, step in enumerate(self.flow):
            agent_name = step["agent"]
            result_key = step.get("result_key", agent_name)
            when_cfg   = step.get("when")

            if not _eval_when(when_cfg, context):
                log.debug("[%s] step %d agent=%s skipped (when: condition false)",
                          self.squad_id, step_idx + 1, agent_name)
                continue

            if agent_name not in agent_map:
                raise RuntimeError(
                    f"[{self.squad_id}] Agent '{agent_name}' required by step {step_idx + 1} "
                    f"is not loaded"
                )

            context_keys = step.get("context_keys")
            if context_keys is not None:
                step_context = {
                    k: v for k, v in context.items()
                    if k in context_keys or k in payload or k == "squad_id"
                }
            else:
                step_context = {**context}
            step_context.update(step.get("context", {}))
            log.info("[%s] step %d executing agent=%s", self.squad_id, step_idx + 1, agent_name)
            t0 = time.monotonic()
            try:
                result = agent_map[agent_name].execute(step_context)
            except Exception:
                elapsed_ms = int((time.monotonic() - t0) * 1000)
                log.exception("[%s] step %d agent=%s FAILED elapsed_ms=%d",
                              self.squad_id, step_idx + 1, agent_name, elapsed_ms)
                raise
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            log.info("[%s] step %d agent=%s done elapsed_ms=%d",
                     self.squad_id, step_idx + 1, agent_name, elapsed_ms)
            context[result_key] = result
            results[result_key] = result

        if self.monitor:
            self.monitor.on_squad_end(self.squad_id)

        return {"status": "completed", "squad_id": self.squad_id, **results}

    def run(self, payload):
        """Delegates to execute() — kept for backwards compatibility."""
        return self.execute(payload)