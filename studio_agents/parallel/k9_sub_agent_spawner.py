# SPDX-License-Identifier: Apache-2.0
# k9x_studio — K9SubAgentSpawner (new ABB, Phase 2)
#
# Parent-agent contract for spawning child BaseAgent instances concurrently
# (ThreadPoolExecutor, sync in Phase 2 — async in Phase 3) or sequentially,
# then merging their results back into the shared squad context.
#
# Mirrors the OOB-extension pattern used elsewhere in K9-AIF (K9ModelRouter,
# K9ValidationLoopAgent): the spawner provides spawning *mechanics* only and
# never contains domain logic — subclasses (e.g. SpecParserAgent,
# TemplateRendererAgent) decide which child agents to spawn and how to merge.

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Type

from k9_aif_abb.k9_core.agent.base_agent import BaseAgent


class K9SubAgentSpawner(BaseAgent):
    """
    ABB: spawns child agents in parallel or in sequence.

    Stays abstract — does not implement ``execute()`` — so subclasses remain
    responsible for their own domain behavior; this class only supplies
    ``spawn_parallel`` / ``spawn_sequential``.
    """

    layer = "K9SubAgentSpawner ABB"

    def spawn_parallel(
        self,
        agent_classes: List[Type[BaseAgent]],
        payload: Dict[str, Any],
        max_workers: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Construct one instance per ``agent_classes[i]`` (sharing this agent's
        merged config) and run ``execute(payload)`` concurrently.

        Returns results in ``agent_classes`` order — not completion order —
        so callers can zip results back to their originating agent class.
        The first child exception encountered is re-raised (fail-fast); the
        squad flow already logs and propagates agent failures the same way.
        """
        agents = [cls(config=self.config) for cls in agent_classes]
        results: List[Optional[Dict[str, Any]]] = [None] * len(agents)

        with ThreadPoolExecutor(max_workers=max_workers or len(agents)) as pool:
            future_to_idx = {
                pool.submit(agent.execute, payload): idx
                for idx, agent in enumerate(agents)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()

        return results  # type: ignore[return-value]

    def spawn_sequential(
        self,
        agent_classes: List[Type[BaseAgent]],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run each child agent in order, threading the accumulated context
        forward — each agent's result dict is merged on top of the running
        context before the next agent runs. Returns the final context.
        """
        context = dict(payload)
        for cls in agent_classes:
            agent = cls(config=self.config)
            context = {**context, **agent.execute(context)}
        return context
