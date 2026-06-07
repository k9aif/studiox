# SPDX-License-Identifier: Apache-2.0
# Converts a k9x_studio ProjectDef into a Langflow-importable JSON flow.

import uuid
from typing import Any


_AGENT_COLORS = {
    "BaseAgent": "#10b981",
    "K9ValidationLoopAgent": "#f59e0b",
    "K9CriticActorAgent": "#ef4444",
    "BaseGovernance": "#64748b",
}

_AGENT_DESCRIPTIONS = {
    "BaseAgent": "One-shot K9-AIF agent — execute(payload) → dict",
    "K9ValidationLoopAgent": "Iterative K9-AIF agent — hypothesis → validate → reason → continue/finalize",
    "K9CriticActorAgent": "K9-AIF actor-critic agent — generate → critique → refine → accept",
    "BaseGovernance": "K9-AIF governance guard — pre/post process pipeline",
}

_X_START = 100
_X_GAP = 280
_Y_CENTER = 300


def _node_id() -> str:
    return str(uuid.uuid4())[:8]


def _make_node(node_id: str, display_name: str, component_type: str,
               description: str, x: float, y: float,
               color: str = "#6366f1", extra_template: dict | None = None) -> dict:
    template: dict[str, Any] = {
        "code": {
            "type": "code",
            "required": True,
            "value": "",
            "show": False,
        },
        "input": {
            "type": "str",
            "required": False,
            "display_name": "Input",
            "value": "",
            "show": True,
        },
        "output": {
            "type": "str",
            "required": False,
            "display_name": "Output",
            "value": "",
            "show": True,
        },
    }
    if extra_template:
        template.update(extra_template)

    return {
        "id": node_id,
        "type": "genericNode",
        "position": {"x": x, "y": y},
        "data": {
            "id": node_id,
            "type": component_type,
            "node": {
                "template": template,
                "description": description,
                "display_name": display_name,
                "documentation": "https://k9x.ai",
                "base_classes": ["Data", "Message"],
                "name": component_type,
                "color": color,
                "icon": "bot",
                "category": "K9-AIF",
            },
            "showNode": True,
        },
        "width": 240,
        "height": 160,
    }


def _make_edge(source_id: str, target_id: str) -> dict:
    eid = f"{source_id}-{target_id}"
    return {
        "id": eid,
        "source": source_id,
        "target": target_id,
        "sourceHandle": f"{source_id}|output|output",
        "targetHandle": f"{target_id}|input|input",
        "type": "default",
        "animated": True,
        "style": {"stroke": "#6366f1", "strokeWidth": 2},
    }


def export_to_langflow(project: dict) -> dict:
    """
    Convert a k9x_studio project dict to a Langflow-importable JSON flow.

    The flow visualises the K9-AIF execution hierarchy:
      ChatInput → Router → Orchestrator → Agent1 → Agent2 → ... → ChatOutput

    One flow is generated per squad. If the project has multiple squads,
    each squad's flow is laid out on a separate vertical lane (Y offset).
    """
    project_name = project.get("project_name", "K9AIF Project")
    squads = project.get("squads", [])
    agents_def = {a["name"]: a for a in project.get("agents", [])}
    orchestrators = project.get("orchestrators", [])
    orch_map = {o.get("squad", ""): o.get("name", "Orchestrator") for o in orchestrators}

    nodes: list[dict] = []
    edges: list[dict] = []

    y_offset = 0
    y_lane_height = 400

    for squad in squads:
        squad_name = squad.get("name", "Squad")
        agent_names = squad.get("agents", [])
        orch_name = orch_map.get(squad_name, f"{squad_name}Orchestrator")

        x = _X_START
        y = _Y_CENTER + y_offset
        prev_id = None

        # ChatInput
        input_id = _node_id()
        nodes.append(_make_node(
            input_id, "Chat Input", "ChatInput",
            "Entry point — send a payload into the K9-AIF squad pipeline.",
            x, y, "#0ea5e9",
        ))
        prev_id = input_id
        x += _X_GAP

        # Router
        router_id = _node_id()
        nodes.append(_make_node(
            router_id, "K9-AIF Router", "K9EventRouter",
            "Routes the event by event_type to the correct Orchestrator. "
            "Deterministic routing — no LLM needed for known event types.",
            x, y, "#6366f1",
            extra_template={
                "event_type": {
                    "type": "str",
                    "display_name": "Event Type",
                    "value": "default",
                    "show": True,
                }
            },
        ))
        edges.append(_make_edge(prev_id, router_id))
        prev_id = router_id
        x += _X_GAP

        # Orchestrator
        orch_id = _node_id()
        nodes.append(_make_node(
            orch_id, orch_name, "K9Orchestrator",
            f"Coordinates {squad_name} execution. Loads the squad and runs the agent flow.",
            x, y, "#8b5cf6",
            extra_template={
                "squad": {
                    "type": "str",
                    "display_name": "Squad",
                    "value": squad_name,
                    "show": True,
                }
            },
        ))
        edges.append(_make_edge(prev_id, orch_id))
        prev_id = orch_id
        x += _X_GAP

        # Agents
        for agent_name in agent_names:
            adef = agents_def.get(agent_name, {})
            atype = adef.get("type", "BaseAgent")
            adesc = adef.get("description", "") or _AGENT_DESCRIPTIONS.get(atype, "K9-AIF Agent")
            acolor = _AGENT_COLORS.get(atype, "#10b981")

            agent_id = _node_id()
            nodes.append(_make_node(
                agent_id, agent_name, atype,
                adesc, x, y, acolor,
                extra_template={
                    "model": {
                        "type": "str",
                        "display_name": "Model",
                        "value": adef.get("model", "general"),
                        "show": True,
                    },
                    "pattern": {
                        "type": "str",
                        "display_name": "Pattern",
                        "value": adef.get("pattern", "reasoning"),
                        "show": True,
                    },
                },
            ))
            edges.append(_make_edge(prev_id, agent_id))
            prev_id = agent_id
            x += _X_GAP

        # ChatOutput
        output_id = _node_id()
        nodes.append(_make_node(
            output_id, "Chat Output", "ChatOutput",
            "Final enriched context returned from the K9-AIF squad pipeline.",
            x, y, "#0ea5e9",
        ))
        edges.append(_make_edge(prev_id, output_id))

        y_offset += y_lane_height

    flow_id = str(uuid.uuid4())
    return {
        "id": flow_id,
        "name": project_name,
        "description": f"K9-AIF squad flow — exported from k9x_studio",
        "data": {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 0.75},
        },
        "is_component": False,
        "updated_at": None,
        "folder": "K9-AIF",
    }
