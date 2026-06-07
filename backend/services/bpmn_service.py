# SPDX-License-Identifier: Apache-2.0
# BPMN 2.0 → K9-AIF architecture mapper
# Supports IBM BlueWorks Live and any standard BPMN 2.0 export (.bpmn / .xml)

import re
import xml.etree.ElementTree as ET
from typing import Optional

# Standard BPMN 2.0 namespace (IBM BWL, Camunda, Bizagi all use this)
_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"

# BPMN task types that map to agents
_TASK_TAGS = {
    "task", "usertask", "servicetask", "scripttask",
    "businessruletask", "sendtask", "receivetask", "manualtask",
}

# Heuristics for richer agent type selection
_VALIDATION_HINTS = re.compile(
    r"validat|verif|check|review|audit|inspect|assess|evaluat", re.I
)
_CRITIC_HINTS = re.compile(
    r"generat|draft|writ|creat|refine|critique|recommend|propos|analys|analyz", re.I
)


def _tag(el: ET.Element) -> str:
    """Return local tag name (strips namespace URI)."""
    tag = el.tag
    if "}" in tag:
        tag = tag.split("}", 1)[1]
    return tag.lower()


def _attr(el: ET.Element, name: str, default: str = "") -> str:
    return el.get(name, el.get(f"{{{_NS}}}{name}", default)).strip()


def _to_pascal(s: str) -> str:
    """Convert any string to PascalCase."""
    s = re.sub(r"[^a-zA-Z0-9\s_-]", " ", s)
    return "".join(w.capitalize() for w in re.split(r"[\s_-]+", s) if w)


def _agent_type(name: str, tag: str) -> str:
    if tag == "businessruletask" or _VALIDATION_HINTS.search(name):
        return "K9ValidationLoopAgent"
    if _CRITIC_HINTS.search(name):
        return "K9CriticActorAgent"
    return "BaseAgent"


def _model_for(agent_type: str) -> str:
    return "reasoning" if agent_type != "BaseAgent" else "general"


def _make_agent(name: str, tag: str, description: str = "") -> dict:
    pascal = _to_pascal(name)
    if not pascal.endswith("Agent"):
        pascal += "Agent"
    atype = _agent_type(name, tag)
    return {
        "name": pascal,
        "type": atype,
        "model": _model_for(atype),
        "description": description or name,
    }


def _is_task(el: ET.Element) -> bool:
    return _tag(el) in _TASK_TAGS


def _tasks_in(el: ET.Element) -> list[ET.Element]:
    return [c for c in el.iter() if _is_task(c)]


def parse_bpmn(xml_content: str) -> dict:
    """
    Parse BPMN 2.0 XML and return a K9-AIF suggestion dict compatible with
    /api/suggest response: { orchestrators, squads, agents }.

    Mapping strategy
    ────────────────
    Lanes present  → each lane  = one Orchestrator + one Squad
    SubProcesses   → each subprocess = one Squad  (grouped under one Orchestrator)
    Flat tasks     → all tasks grouped into one default Squad + one Orchestrator
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML: {exc}")

    # Collect all <process> elements regardless of namespace
    processes = [el for el in root.iter() if _tag(el) == "process"]
    if not processes:
        raise ValueError("No <process> element found in BPMN file.")

    orchestrators: list[dict] = []
    squads: list[dict] = []
    agents: list[dict] = []

    seen_agents: set[str] = set()

    def add_agent(a: dict):
        if a["name"] not in seen_agents:
            seen_agents.add(a["name"])
            agents.append(a)

    for process in processes:
        proc_name = _attr(process, "name") or "Main"
        proc_pascal = _to_pascal(proc_name)

        # ── Case 1: Lanes ─────────────────────────────────────────────────────
        lanes = [el for el in process.iter() if _tag(el) == "lane"]

        if lanes:
            # Build id→element map for all tasks in process
            task_by_id: dict[str, ET.Element] = {
                _attr(el, "id"): el
                for el in process.iter()
                if _is_task(el)
            }

            for lane in lanes:
                lane_name = _attr(lane, "name") or "DefaultLane"
                orch_name = _to_pascal(lane_name)
                if not orch_name.endswith("Orchestrator"):
                    orch_name += "Orchestrator"
                squad_name = _to_pascal(lane_name)
                if not squad_name.endswith("Squad"):
                    squad_name += "Squad"

                # flowNodeRef elements list the IDs of tasks in this lane
                ref_ids = {
                    el.text.strip()
                    for el in lane.iter()
                    if _tag(el) == "flownoderef" and el.text
                }
                lane_tasks = [task_by_id[rid] for rid in ref_ids if rid in task_by_id]

                agent_names: list[str] = []
                for t in lane_tasks:
                    a = _make_agent(_attr(t, "name") or _tag(t), _tag(t))
                    add_agent(a)
                    agent_names.append(a["name"])

                if not agent_names:
                    a = _make_agent(f"Process{lane_name}", "task")
                    add_agent(a)
                    agent_names.append(a["name"])

                orchestrators.append({"name": orch_name})
                squads.append({"name": squad_name, "agents": agent_names})

        # ── Case 2: SubProcesses ──────────────────────────────────────────────
        else:
            subprocs = [el for el in process.iter()
                        if _tag(el) == "subprocess" and el is not process]

            if subprocs:
                orch_name = proc_pascal
                if not orch_name.endswith("Orchestrator"):
                    orch_name += "Orchestrator"
                orchestrators.append({"name": orch_name})

                for sp in subprocs:
                    sp_name = _attr(sp, "name") or "Step"
                    squad_name = _to_pascal(sp_name)
                    if not squad_name.endswith("Squad"):
                        squad_name += "Squad"

                    sp_tasks = _tasks_in(sp)
                    agent_names = []
                    for t in sp_tasks:
                        a = _make_agent(_attr(t, "name") or sp_name, _tag(t))
                        add_agent(a)
                        agent_names.append(a["name"])

                    if not agent_names:
                        a = _make_agent(sp_name, "task")
                        add_agent(a)
                        agent_names.append(a["name"])

                    squads.append({"name": squad_name, "agents": agent_names})

            # ── Case 3: Flat tasks ────────────────────────────────────────────
            else:
                direct_tasks = [el for el in process.iter() if _is_task(el)]

                orch_name = proc_pascal
                if not orch_name.endswith("Orchestrator"):
                    orch_name += "Orchestrator"
                squad_name = proc_pascal
                if not squad_name.endswith("Squad"):
                    squad_name += "Squad"

                agent_names = []
                for t in direct_tasks:
                    a = _make_agent(_attr(t, "name") or "Task", _tag(t))
                    add_agent(a)
                    agent_names.append(a["name"])

                if not agent_names:
                    a = _make_agent(f"{proc_pascal}Processing", "task",
                                    "Core processing agent")
                    add_agent(a)
                    agent_names.append(a["name"])

                orchestrators.append({"name": orch_name})
                squads.append({"name": squad_name, "agents": agent_names})

    return {
        "orchestrators": orchestrators,
        "squads": squads,
        "agents": agents,
    }


def extract_process_name(xml_content: str) -> Optional[str]:
    """Return the name of the first <process> or <definitions> element, if set."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return None
    for el in root.iter():
        if _tag(el) in ("process", "definitions"):
            name = _attr(el, "name")
            if name:
                return name
    return None
