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

# Deterministic BPMN tag → K9-AIF adapter type (unambiguous mappings)
_ADAPTER_TAG_MAP: dict[str, str] = {
    "servicetask":      "api_adapter",        # calls an external service / REST / SOAP
    "businessruletask": "rules_adapter",      # invokes a rules engine (Drools, ODM, Corticon)
    "scripttask":       "workflow_adapter",   # runs a deterministic script
    "sendtask":         "messaging_adapter",  # publishes a message / event to a bus
    "receivetask":      "messaging_adapter",  # waits for a message / event from a bus
}

# Name-based heuristics for generic <task> tags
_ADAPTER_NAME_HINTS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bapi\b|rest\b|graphql|endpoint|http|fetch|invoke|call\b", re.I), "api_adapter"),
    (re.compile(r"\brule|policy|decision\b|drools|odm\b|corticon", re.I),           "rules_adapter"),
    (re.compile(r"kafka|rabbitmq|activemq|sqs\b|sns\b|servicebus|eventhub|pubsub|event\s*bus|message\s*queue|topic\b", re.I), "messaging_adapter"),
    (re.compile(r"workflow|bpm\b|camunda|appian|pega|flowable|step\s*function|airflow", re.I), "workflow_adapter"),
    (re.compile(r"integrat|mulesoft|tibco|esb\b|app\s*connect|mq\b", re.I), "process_adapter"),
    (re.compile(r"\bdata(base)?\b|db\b|\bsql\b|persist|store\b|repo\b|warehouse", re.I), "data_adapter"),
]

# Heuristics for richer agent type selection — used only as a fallback when
# no zone color is present on the task (see _zone_from_hex / _agent_type).
_VALIDATION_HINTS = re.compile(
    r"validat|verif|check|review|audit|inspect|assess|evaluat", re.I
)
_CRITIC_HINTS = re.compile(
    r"generat|draft|writ|creat|refine|critique|recommend|propos|analys|analyz", re.I
)

# GREEN/AMBER/RED zone → K9-AIF agent type, same mapping as
# spec_parsing_service.zone_to_agent_type() for the .md import path.
_ZONE_TO_AGENT_TYPE = {
    "GREEN": "BaseAgent",
    "AMBER": "K9ValidationLoopAgent",
    "RED": "K9CriticActorAgent",
}

# adapter_type -> the actual k9_aif_abb base class scaffold_service.py now
# generates real code against (see its own _ADAPTER_BASE_CLASS — duplicated
# here as just the class name, not the full method-signature mapping, to
# avoid a circular import: scaffold_service.py already imports FROM this
# module). Kept in sync by hand; these 7 names are framework-stable.
_ADAPTER_BASE_CLASS_NAME = {
    "api_adapter":       "BaseApiAdapter",
    "bpm_adapter":        "BaseBpmAdapter",
    "messaging_adapter":  "BaseMessagingAdapter",
    "workflow_adapter":   "BaseWorkflowAdapter",
    "process_adapter":    "BaseProcessFlowAdapter",
    "rules_adapter":      "BaseRulesAdapter",
    "data_adapter":       "BaseDataAdapter",
}

# Known zone fill colors, as seen in Process Studio's BPMN export (Tailwind-
# style light tints). Other tools/palettes won't match here and fall back to
# the name-keyword heuristic below — this is deliberately not exhaustive.
_ZONE_HEX_MAP = {
    "#dcfce7": "GREEN",
    "#fef3c7": "AMBER",
    "#fee2e2": "RED",
}


def _zone_from_hex(hex_color: str | None) -> str | None:
    if not hex_color:
        return None
    return _ZONE_HEX_MAP.get(hex_color.strip().lower())


def _shape_zone_map(root: ET.Element) -> dict[str, str]:
    """Map BPMN element id -> zone (GREEN/AMBER/RED), read from each
    <bpmndi:BPMNShape>'s background-color fill (any color-extension
    namespace — matched by attribute suffix, not a hardcoded URI, so this
    isn't tied to one specific tool's exact namespace declaration)."""
    zone_by_id: dict[str, str] = {}
    for el in root.iter():
        if _tag(el) != "bpmnshape":
            continue
        element_id = el.get("bpmnElement")
        if not element_id:
            continue
        hex_color = next(
            (v for k, v in el.attrib.items() if k.lower().endswith("background-color")),
            None,
        )
        zone = _zone_from_hex(hex_color)
        if zone:
            zone_by_id[element_id] = zone
    return zone_by_id


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


def _agent_type(name: str, tag: str, zone: str | None = None) -> str:
    # Zone is authoritative when present — it's Process Studio's own explicit
    # risk classification, not a guess. Name-keyword heuristics only apply
    # when no zone color was found on the task (e.g. a hand-drawn BPMN with
    # no color extension at all).
    if zone in _ZONE_TO_AGENT_TYPE:
        return _ZONE_TO_AGENT_TYPE[zone]
    if tag == "businessruletask" or _VALIDATION_HINTS.search(name):
        return "K9ValidationLoopAgent"
    if _CRITIC_HINTS.search(name):
        return "K9CriticActorAgent"
    return "BaseAgent"


def _model_for(agent_type: str) -> str:
    return "reasoning" if agent_type != "BaseAgent" else "general"


def _adapter_type_for(name: str, tag: str) -> str | None:
    """Return an adapter type string if this task should be deterministic, else None → agent."""
    if tag in _ADAPTER_TAG_MAP:
        return _ADAPTER_TAG_MAP[tag]
    if tag == "task":
        for pattern, atype in _ADAPTER_NAME_HINTS:
            if pattern.search(name):
                return atype
    return None


def _make_node(name: str, tag: str, description: str = "", zone: str | None = None, process_id: str | None = None) -> tuple[dict | None, dict | None]:
    """Return (agent_dict, None) or (None, adapter_dict) — exactly one is non-None."""
    pascal = _to_pascal(name)
    adapter_type = _adapter_type_for(name, tag)
    if adapter_type:
        suffix = "Adapter"
        if not pascal.endswith(suffix):
            pascal += suffix
        return None, {
            "name": pascal,
            "adapter_type": adapter_type,
            "description": description or name,
            "zone": zone,
            "process_id": process_id,
        }
    if not pascal.endswith("Agent"):
        pascal += "Agent"
    atype = _agent_type(name, tag, zone)
    return {"name": pascal, "type": atype, "model": _model_for(atype), "description": description or name, "zone": zone, "process_id": process_id}, None


def _make_agent(name: str, tag: str, description: str = "", zone: str | None = None, process_id: str | None = None) -> dict:
    pascal = _to_pascal(name)
    if not pascal.endswith("Agent"):
        pascal += "Agent"
    atype = _agent_type(name, tag, zone)
    return {
        "name": pascal,
        "type": atype,
        "model": _model_for(atype),
        "description": description or name,
        "zone": zone,
        "process_id": process_id,
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
    adapters: list[dict] = []

    # Task id -> GREEN/AMBER/RED, from each task's BPMNShape fill color (a
    # source like Process Studio's zone coding). Absent for BPMN sources
    # that don't carry this convention — classify_task falls back to
    # name-keyword heuristics in that case, per _agent_type.
    zone_by_id = _shape_zone_map(root)

    seen_names: set[str] = set()

    def add_agent(a: dict):
        if a["name"] not in seen_names:
            seen_names.add(a["name"])
            agents.append(a)

    def add_adapter(a: dict):
        if a["name"] not in seen_names:
            seen_names.add(a["name"])
            adapters.append(a)

    def classify_task(t: ET.Element, fallback_name: str, orch_name: str) -> tuple[str | None, None]:
        """Classify one BPMN task → returns (agent_name, None) or (None, adapter) added to lists."""
        raw_name = _attr(t, "name") or fallback_name
        tag = _tag(t)
        task_id = _attr(t, "id") or None
        zone = zone_by_id.get(task_id)
        # process_id is the BPMN's own element id (e.g. "Task_1") — the stable,
        # always-available identifier for the mapping document's Process ID
        # column. Process Studio's ATS#/AGN# numbering lives only in the .md,
        # not the .bpmn, so this is the generic fallback for any BPMN source.
        agent, adapter = _make_node(raw_name, tag, zone=zone, process_id=task_id)
        if adapter:
            adapter["orchestrator"] = orch_name
            add_adapter(adapter)
            return None, adapter["name"]
        if agent:
            add_agent(agent)
            return agent["name"], None
        return None, None

    for process in processes:
        proc_name = _attr(process, "name") or "Main"
        proc_pascal = _to_pascal(proc_name)
        proc_id = _attr(process, "id") or None

        # ── Case 1: Lanes ─────────────────────────────────────────────────────
        lanes = [el for el in process.iter() if _tag(el) == "lane"]

        if lanes:
            task_by_id: dict[str, ET.Element] = {
                _attr(el, "id"): el
                for el in process.iter()
                if _is_task(el)
            }

            for lane in lanes:
                lane_id = _attr(lane, "id") or None
                lane_name = _attr(lane, "name") or "DefaultLane"
                orch_name = _to_pascal(lane_name)
                if not orch_name.endswith("Orchestrator"):
                    orch_name += "Orchestrator"
                squad_name = _to_pascal(lane_name)
                if not squad_name.endswith("Squad"):
                    squad_name += "Squad"

                ref_ids = {
                    el.text.strip()
                    for el in lane.iter()
                    if _tag(el) == "flownoderef" and el.text
                }
                lane_tasks = [task_by_id[rid] for rid in ref_ids if rid in task_by_id]

                agent_names: list[str] = []
                for t in lane_tasks:
                    name, _ = classify_task(t, _tag(t), orch_name)
                    if name:
                        agent_names.append(name)

                orch_entry = {"name": orch_name, "process_id": lane_id}
                if agent_names:
                    # Squad zone = the lane's zone, if every agent in it agrees
                    # (the normal case — one BPMN lane is one zone). Left None
                    # if the lane genuinely mixes zones or none were found, so
                    # the frontend doesn't paint a false-confidence color.
                    zone_by_name = {a["name"]: a.get("zone") for a in agents}
                    lane_zones = {zone_by_name.get(n) for n in agent_names if zone_by_name.get(n)}
                    squad_zone = next(iter(lane_zones)) if len(lane_zones) == 1 else None
                    squads.append({"name": squad_name, "agents": agent_names, "zone": squad_zone, "process_id": lane_id})
                    orch_entry["squads"] = [squad_name]
                elif not any(a.get("orchestrator") == orch_name for a in adapters):
                    # Lane had no tasks at all — add a placeholder agent
                    a = _make_agent(f"Process{lane_name}", "task", process_id=lane_id)
                    add_agent(a)
                    squads.append({"name": squad_name, "agents": [a["name"]], "zone": None, "process_id": lane_id})
                    orch_entry["squads"] = [squad_name]
                else:
                    # Lane's tasks all classified as adapters (deterministic/GREEN) —
                    # no squad for this orchestrator. Must be explicit: without this,
                    # a consumer pairing orchestrators to squads by array position
                    # misaligns every orchestrator after this one.
                    orch_entry["squads"] = []
                orchestrators.append(orch_entry)

        # ── Case 2: SubProcesses ──────────────────────────────────────────────
        else:
            subprocs = [el for el in process.iter()
                        if _tag(el) == "subprocess" and el is not process]

            if subprocs:
                orch_name = proc_pascal
                if not orch_name.endswith("Orchestrator"):
                    orch_name += "Orchestrator"
                orch_squad_names: list[str] = []

                for sp in subprocs:
                    sp_id = _attr(sp, "id") or None
                    sp_name = _attr(sp, "name") or "Step"
                    squad_name = _to_pascal(sp_name)
                    if not squad_name.endswith("Squad"):
                        squad_name += "Squad"

                    sp_tasks = _tasks_in(sp)
                    agent_names = []
                    for t in sp_tasks:
                        name, _ = classify_task(t, sp_name, orch_name)
                        if name:
                            agent_names.append(name)

                    if agent_names:
                        squads.append({"name": squad_name, "agents": agent_names, "process_id": sp_id})
                        orch_squad_names.append(squad_name)
                    elif not sp_tasks:
                        a = _make_agent(sp_name, "task", process_id=sp_id)
                        add_agent(a)
                        squads.append({"name": squad_name, "agents": [a["name"]], "process_id": sp_id})
                        orch_squad_names.append(squad_name)
                    # else: subprocess's tasks all classified as adapters — no squad,
                    # deliberately not appended to orch_squad_names.

                orchestrators.append({"name": orch_name, "squads": orch_squad_names, "process_id": proc_id})

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
                    name, _ = classify_task(t, "Task", orch_name)
                    if name:
                        agent_names.append(name)

                orch_entry = {"name": orch_name, "process_id": proc_id}
                if agent_names:
                    squads.append({"name": squad_name, "agents": agent_names, "process_id": proc_id})
                    orch_entry["squads"] = [squad_name]
                elif not direct_tasks:
                    a = _make_agent(f"{proc_pascal}Processing", "task", "Core processing agent", process_id=proc_id)
                    add_agent(a)
                    squads.append({"name": squad_name, "agents": [a["name"]], "process_id": proc_id})
                    orch_entry["squads"] = [squad_name]
                else:
                    orch_entry["squads"] = []
                orchestrators.append(orch_entry)

    return {
        "orchestrators": orchestrators,
        "squads": squads,
        "agents": agents,
        "adapters": adapters,
    }


# ── Mapping document / traceability matrix ─────────────────────────────────
# These notes are verified facts about the current generator (2026-09-11),
# not assumptions — see plan.md "Known bugs" #4. Update this text if/when the
# underlying generator behavior changes; don't let it silently go stale.
#
# Full explanatory text is returned ONCE per mapping document (under
# "notes", see build_mapping_document's return value), not repeated per row
# — Ravi: "'Not wired by default...' is repeated ditto for other cells as
# well ... should we not just say --ditto--?" Repeating a full paragraph in
# every row of a table is unreadable regardless of what fills the repeat, so
# each row instead carries a short status label (below) that the table can
# actually scan, and the full text lives once in a callout the frontend
# renders above the table.
#
# Governance text below describes generator behavior as of the k9x_Shield
# default-wiring change (same day) — every generated agent's __init__ now
# constructs ShieldGovernance(config) itself (backend/templates/agent_*.j2),
# so "Not wired by default" (the previous wording) is no longer true. Ravi:
# "as a user, I assume that the framework is well guarded ... that is why I
# chose this framework" — verified that wasn't true yet (satan.k9x.ai's own
# target only wires 2 of 13 checks; the generator wired zero), then made it
# true rather than just writing the assumption into a doc.
_GOVERNANCE_NOTE = (
    "k9x_Shield wired by default — every generated agent constructs ShieldGovernance(config) "
    "in its own __init__ (see the agent's .py file). All 13 vulnerability checks run in both "
    "directions (ingress: before the LLM; egress: after the LLM, before any tool executes) — "
    "deterministic pattern matching, no LLM call, no extra latency of note. This is broader "
    "than satan.k9x.ai's own demo target, which intentionally wires only 2 of the 13 checks to "
    "show what an unwired check misses. Granite Guardian (semantic LLM screening) is available "
    "as an additive layer on top — off by default (governance.guardian.enabled: false in "
    "config.yaml), since it requires a real pulled model. To disable or narrow k9x_Shield for "
    "this deployment: security.shield.enabled: false turns it off entirely; trimming the "
    "ingress.checks/egress.checks lists narrows it; check_config.<CheckName>.block_on_match: "
    "false downgrades one check from BLOCK to FLAG-only. To override an individual agent "
    "instead: pass governance=YourObject (including NoopGovernance()) into its constructor."
)
_GOVERNANCE_SHORT = "k9x_Shield active by default — 13 checks, both directions (see note above the table)"
# Zero Trust (apply_zero_trust()) is a BaseOrchestrator-only mechanism in the
# framework today — verified against k9_core/orchestration/base_orchestrator.py
# and k9_core/agent/base_agent.py (zero matches there) — there is no
# separate per-agent zero-trust hook. Ravi asked whether agent-level
# pre/post checks are "zero trust at all levels" too: they're a related but
# DIFFERENT mechanism (Governance's pre_process()/post_process() overrides,
# see the Governance note), not a second zero-trust layer, so don't
# conflate the two even though both are boundary checks in spirit.
_ZERO_TRUST_NOTE = (
    "Applied at the orchestrator boundary — every generated orchestrator calls "
    "self.apply_zero_trust(payload) unconditionally, once per squad invocation. This is "
    "the only zero-trust mechanism in the framework today: apply_zero_trust() lives on "
    "BaseOrchestrator, not BaseAgent — there is no separate per-agent zero-trust hook. "
    "Per-agent pre/post checks are a related but different mechanism: any generated agent "
    "can override Governance's pre_process()/post_process() to inspect or reject its own "
    "input/output (see the Governance note above) — that's governance enforcement at the "
    "agent level, not a second zero-trust layer."
)
_ZERO_TRUST_SHORT = "Enforced — orchestrator boundary only (see note above the table)"
_HITL_BY_ZONE: dict[str | None, str] = {
    "GREEN": "None — fully automated",
    "AMBER": "Human review before the workflow proceeds (generic; consult the "
             "source blueprint's HITL spec for the specific reviewer role)",
    "RED": "Dual approval required, cannot be overridden (generic; consult the "
           "source blueprint's HITL spec for the specific reviewer roles)",
    None: "Unknown — no zone data available for this step",
}


def build_mapping_document(parsed: dict) -> dict:
    """
    Build the Process -> Implementation Traceability Matrix from an already-
    parsed BPMN result (see parse_bpmn's return shape). One row per agent or
    adapter — the atomic unit of "a process step became a piece of
    implementation."

    Deliberately built FROM parse_bpmn's own output, not by re-parsing the
    BPMN a second time — same data, single source of truth, no chance of the
    matrix disagreeing with what parse_bpmn actually decided (see plan.md
    "mapping-document-first" architecture decision).
    """
    orch_by_squad: dict[str, str] = {}
    for o in parsed.get("orchestrators", []):
        for sq_name in (o.get("squads") or []):
            orch_by_squad[sq_name] = o["name"]

    squad_by_agent: dict[str, str] = {}
    for sq in parsed.get("squads", []):
        for agent_name in sq.get("agents", []):
            squad_by_agent[agent_name] = sq["name"]

    rows: list[dict] = []

    for a in parsed.get("agents", []):
        squad_name = squad_by_agent.get(a["name"])
        orch_name = orch_by_squad.get(squad_name) if squad_name else None
        zone = a.get("zone")
        rows.append({
            "process_id": a.get("process_id"),
            "process_element": a.get("description") or a["name"],
            "zone": zone,
            "orchestrator": orch_name,
            "squad": squad_name,
            "component": a["name"],
            "component_kind": "agent",
            "agent_base_type": a.get("type"),
            "governance": _GOVERNANCE_SHORT,
            "zero_trust": _ZERO_TRUST_SHORT if orch_name else None,
            "hitl_touchpoint": _HITL_BY_ZONE.get(zone, _HITL_BY_ZONE[None]),
        })

    for ad in parsed.get("adapters", []):
        orch_name = ad.get("orchestrator")
        zone = ad.get("zone")
        rows.append({
            "process_id": ad.get("process_id"),
            "process_element": ad.get("description") or ad["name"],
            "zone": zone,
            "orchestrator": orch_name,
            "squad": None,
            "component": ad["name"],
            "component_kind": "adapter",
            # Ravi: "why can't we generate scaffold for adapters..." — now
            # real (see scaffold_service._gen_adapter_files()), so this
            # shows the actual extended base class, same meaning as an
            # agent row's Base Type column showing its real agent class.
            "agent_base_type": _ADAPTER_BASE_CLASS_NAME.get(
                ad.get("adapter_type", ""), f"{ad.get('adapter_type', 'unknown').replace('_', ' ')} type"
            ),
            "governance": "N/A — not an agent instance",
            "zero_trust": _ZERO_TRUST_SHORT if orch_name else None,
            "hitl_touchpoint": _HITL_BY_ZONE.get(zone, _HITL_BY_ZONE[None]),
        })

    counts = {
        "orchestrators": len(parsed.get("orchestrators", [])),
        "squads": len(parsed.get("squads", [])),
        "agents": len(parsed.get("agents", [])),
        "adapters": len(parsed.get("adapters", [])),
    }

    return {
        "rows": rows,
        "counts": counts,
        # Full text once per document, not once per row — see the _GOVERNANCE_SHORT
        # / _ZERO_TRUST_SHORT comment above. The frontend renders these as a
        # callout above the table; scaffold_service's doc generator pulls from
        # here too instead of reading any row's field.
        "notes": {"governance": _GOVERNANCE_NOTE, "zero_trust": _ZERO_TRUST_NOTE},
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
