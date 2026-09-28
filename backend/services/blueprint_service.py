# SPDX-License-Identifier: Apache-2.0
# EAEF blueprint (.md/.html) -> K9-AIF governance-layer mapper
#
# Companion to bpmn_service.py — where BPMN carries process structure + zone
# colors, an EAEF blueprint carries the governance layer BPMN structurally
# cannot encode: MCP tool register, agent definitions, observability
# requirements, behavioral evals, HITL touchpoints. Deterministic table
# parsing, no LLM — same rule as the BPMN path (see plan.md
# "mapping-document-first" decision).
#
# Matches headings by TEXT, not section number: the real sample blueprint
# uses "### 1.8 Agent Definition Register" where an earlier generation of
# this codebase's spec_parsing_service.py expected "### 3.1.8" — EAEF
# section numbering has already drifted once, so don't rely on it again.

from __future__ import annotations

import re
from typing import Optional

from backend.services.scaffold_service import to_pascal
from backend.services.spec_parsing_service import zone_to_agent_type

# ── Heading detection ────────────────────────────────────────────────────────

_HEADING_PATTERNS: dict[str, re.Pattern] = {
    "ats":            re.compile(r"^#{1,4}\s*(?:[\d.]+\s+)?Atomic Thinking Step Register", re.I | re.M),
    "tools":          re.compile(r"^#{1,4}\s*(?:[\d.]+\s+)?MCP Tool Register", re.I | re.M),
    "agents":         re.compile(r"^#{1,4}\s*(?:[\d.]+\s+)?Agent (?:Definition Register|Roster)", re.I | re.M),
    "observability":  re.compile(r"^#{1,4}\s*(?:[\d.]+\s+)?Observability Requirements", re.I | re.M),
    "behavioral":     re.compile(r"^#{1,4}\s*(?:[\d.]+\s+)?Behavioral Evals", re.I | re.M),
    "mcp_eng_plan":   re.compile(r"^#{1,4}\s*(?:[\d.]+\s+)?MCP Tool Engineering Plan", re.I | re.M),
}

# At least this many of the headings above must be present for a document to
# be recognized as an EAEF blueprint at all (vs. a generic spec doc) — see
# looks_like_blueprint().
_MIN_HEADINGS_FOR_BLUEPRINT = 2

_NEXT_HEADING = re.compile(r"^#{1,4}\s+\S", re.M)


def looks_like_blueprint(content: str) -> bool:
    """Content-based role detection (not extension-based) — a real spec doc
    or random markdown file won't carry >=2 of these specific EAEF section
    headings."""
    hits = sum(1 for pat in _HEADING_PATTERNS.values() if pat.search(content))
    return hits >= _MIN_HEADINGS_FOR_BLUEPRINT


def _table_under_heading(content: str, heading_pat: re.Pattern) -> list[dict[str, str]]:
    """Find a heading anywhere in the document (any #-level, any/no section
    number — matched by text), capture the markdown table immediately under
    it up to the next heading, and return rows as dicts keyed by the table's
    own header row (not hardcoded column positions — section layouts vary)."""
    m = heading_pat.search(content)
    if not m:
        return []
    rest = content[m.end():]
    end = _NEXT_HEADING.search(rest)
    section = rest[: end.start()] if end else rest

    lines = [l.strip() for l in section.split("\n") if l.strip().startswith("|")]
    if len(lines) < 2:
        return []

    headers = [c.strip() for c in lines[0].split("|") if c.strip()]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:  # skip header + '---' separator row
        cols = [c.strip() for c in line.split("|")]
        cols = cols[1:-1] if len(cols) >= 2 and cols[0] == "" and cols[-1] == "" else cols
        if not cols or not cols[0] or set(cols[0]) <= {"-", ":"}:
            continue
        row = {headers[i]: (cols[i] if i < len(cols) else "") for i in range(len(headers))}
        rows.append(row)
    return rows


def _table_rows_under_heading_raw(content: str, heading_pat: re.Pattern) -> tuple[list[str], list[list[str]]]:
    """Same heading/section-slice logic as _table_under_heading(), but
    returns (headers, raw_cell_lists) instead of zipping into dicts — lets
    a caller handle a row whose cell count doesn't match the header count
    itself, rather than silently misaligning via positional zip. Needed for
    §1.7 MCP Tool Register specifically — see _parse_mcp_tools_table()."""
    m = heading_pat.search(content)
    if not m:
        return [], []
    rest = content[m.end():]
    end = _NEXT_HEADING.search(rest)
    section = rest[: end.start()] if end else rest

    lines = [l.strip() for l in section.split("\n") if l.strip().startswith("|")]
    if len(lines) < 2:
        return [], []

    headers = [c.strip() for c in lines[0].split("|") if c.strip()]
    raw_rows: list[list[str]] = []
    for line in lines[2:]:
        cols = [c.strip() for c in line.split("|")]
        cols = cols[1:-1] if len(cols) >= 2 and cols[0] == "" and cols[-1] == "" else cols
        if not cols or not cols[0] or set(cols[0]) <= {"-", ":"}:
            continue
        raw_rows.append(cols)
    return headers, raw_rows


def _parse_mcp_tools_table(content: str) -> list[dict[str, str]]:
    """§1.7 MCP Tool Register — Process Studio's own generator emits this
    table's "Input/Output Schema" column as TWO markdown cells ("In: ..."
    and "Out: ...") without widening the header row to match, so every data
    row has one more cell than there are headers. The generic
    _table_under_heading() zips positionally and silently misaligns from
    that column onward — "Input/Output Schema" only gets the "In:" half,
    "Authentication" gets the "Out:" text, and the real auth value
    (OAuth 2.0 / Service Account / API Key / Certificate) is dropped
    entirely. Confirmed against a real Process Studio export before fixing.
    Merges the two overflow cells back into one Input/Output Schema value
    when detected; falls back to a plain positional zip if a future export
    already has the header widened to match (no double-fix)."""
    headers, raw_rows = _table_rows_under_heading_raw(content, _HEADING_PATTERNS["tools"])
    if not headers:
        return []

    schema_idx = next((i for i, h in enumerate(headers) if "schema" in h.lower()), None)
    rows: list[dict[str, str]] = []
    for cols in raw_rows:
        if schema_idx is not None and len(cols) == len(headers) + 1:
            # Merge the two overflow cells (schema_idx and schema_idx+1)
            # into one value, restoring correct positional alignment for
            # every column after it (notably Authentication).
            merged = f"{cols[schema_idx]}; {cols[schema_idx + 1]}"
            cols = cols[:schema_idx] + [merged] + cols[schema_idx + 2:]
        rows.append({headers[i]: (cols[i] if i < len(cols) else "") for i in range(len(headers))})
    return rows


_ID_PREFIX = re.compile(r"^([A-Z]+\d+)\s*[-‐-―−]\s*(.*)$")


def _first_token(text: str) -> str:
    """'AGN1 – Deterministic Rule Engine' -> 'AGN1'. Falls back to the whole
    text if there's no leading id token (some tables don't have one)."""
    m = _ID_PREFIX.match(text.strip())
    return m.group(1) if m else text.strip()


def _display_name(text: str) -> str:
    """'AGN1 – Deterministic Rule Engine' -> 'Deterministic Rule Engine' —
    strips the id-and-dash prefix so the remainder is safe to pascal-case
    into a Python class name. The register tables use a typographic en/em
    dash (not ASCII '-'), which to_snake()/to_pascal() don't treat as a
    separator — left in, it would leak into the generated agent's class
    name as a literal character and break the generated Python file."""
    m = _ID_PREFIX.match(text.strip())
    return m.group(2).strip() if m else text.strip()


def _split_list(text: str) -> list[str]:
    return [t.strip() for t in re.split(r",\s*", text) if t.strip()]


# Ravi: "the .md file input has the information, we can make that as the
# header... the main.html can be beautiful with all this information."
# The blueprint's own opening block (H1 title, italic one-line subtitle,
# **Target Outcome:**/**Process Reference:** lines) was never parsed at
# all — sitting right there in every real blueprint, unused. Matches
# Process Studio's own rendered .html cover (verified against the real
# accounts-payable file: title/subtitle/Target Outcome/Process Reference
# APQC PCF 9.5 all present exactly this shape).
_TITLE_H1_RE = re.compile(r"^#\s+(.+)$", re.M)
_SUBTITLE_ITALIC_RE = re.compile(r"^\*([^*].*[^*])\*\s*$", re.M)
_TARGET_OUTCOME_RE = re.compile(r"^\*\*Target Outcome:\*\*\s*(.+)$", re.M)
_PROCESS_REF_RE = re.compile(r"^\*\*Process Reference:\*\*\s*(.+)$", re.M)


def _parse_header_meta(content: str) -> dict:
    title_m = _TITLE_H1_RE.search(content)
    subtitle_m = _SUBTITLE_ITALIC_RE.search(content)
    target_m = _TARGET_OUTCOME_RE.search(content)
    ref_m = _PROCESS_REF_RE.search(content)
    return {
        "title": title_m.group(1).strip() if title_m else "",
        "subtitle": subtitle_m.group(1).strip() if subtitle_m else "",
        "target_outcome": target_m.group(1).strip() if target_m else "",
        "process_reference": ref_m.group(1).strip() if ref_m else "",
    }


# ── Top-level parse ──────────────────────────────────────────────────────────

def parse_blueprint(content: str) -> dict:
    ats_rows = _table_under_heading(content, _HEADING_PATTERNS["ats"])
    tool_rows = _parse_mcp_tools_table(content)
    agent_rows = _table_under_heading(content, _HEADING_PATTERNS["agents"])
    obs_rows = _table_under_heading(content, _HEADING_PATTERNS["observability"])
    behavioral_rows = _table_under_heading(content, _HEADING_PATTERNS["behavioral"])
    # §3.4 MCP Tool Engineering Plan — Source (API Wrap / New Build / MCP
    # Gateway) / Build Approach / Status, keyed by bare tool name (this
    # table has no TOLn id prefix, unlike §1.7 — matched below by stripping
    # §1.7's prefix instead of assuming the two tables share a key format).
    eng_plan_rows = _table_under_heading(content, _HEADING_PATTERNS["mcp_eng_plan"])
    eng_plan_by_name = {r.get("Tool", "").strip(): r for r in eng_plan_rows}

    ats_steps = [
        {
            "step_id": r.get("Step", "").strip(),
            "name": r.get("Name", "").strip(),
            "type": r.get("Type", "").strip(),
            "zone": r.get("Zone", "").strip().upper(),
        }
        for r in ats_rows
    ]

    def _tool_from_row(r: dict) -> dict:
        display_name = _display_name(r.get("Tool Name", ""))
        eng = eng_plan_by_name.get(display_name, {})
        return {
            "tool_id": _first_token(r.get("Tool Name", "")),
            "name": r.get("Tool Name", "").strip(),
            "description": r.get("Description", "").strip(),
            # New: previously parsed-but-dropped (io_schema) or never parsed
            # at all (authentication, source, build_approach, status).
            # Ravi: "our HTML could enhance it perfectly with our mapping."
            "io_schema": r.get("Input/Output Schema", "").strip(),
            "authentication": r.get("Authentication", "").strip(),
            "source": eng.get("Source", "").strip(),
            "build_approach": eng.get("Build Approach", "").strip(),
            "status": eng.get("Status", "").strip(),
        }

    tools = [_tool_from_row(r) for r in tool_rows]

    agents = [
        {
            "agent_id": _first_token(r.get("Agent", "")),
            "name": r.get("Agent", "").strip(),
            "goal": r.get("Goal", "").strip(),
            "owned_steps": _split_list(r.get("Owned Steps", "")),
            "zone": r.get("Autonomy Zone", "").strip().upper(),
            "tools_required": _split_list(r.get("Tools Required", "")),
            "hitl": r.get("HITL Touchpoints", "").strip(),
        }
        for r in agent_rows
    ]

    observability = [
        {
            "agent_ref": _first_token(r.get("Agent", "")),
            "metrics": r.get("Key Metrics", "").strip(),
            "alert_thresholds": r.get("Alert Thresholds", "").strip(),
            "dashboard": r.get("Dashboard", "").strip(),
        }
        for r in obs_rows
    ]

    behavioral_rules = [
        {
            "rule": r.get("Behavioral Rule", "").strip(),
            "kpi": r.get("KPI", "").strip(),
            "target": r.get("Target", "").strip(),
            "measurement": r.get("Measurement", "").strip(),
            "pass_criteria": r.get("Pass Criteria", "").strip(),
        }
        for r in behavioral_rows
    ]

    det_count = sum(1 for s in ats_steps if s["type"].strip().upper() == "DETERMINISTIC")
    ai_count = len(ats_steps) - det_count
    header_meta = {
        **_parse_header_meta(content),
        "atomic_steps": len(ats_steps),
        "deterministic_pct": round(det_count / len(ats_steps) * 100) if ats_steps else 0,
        "ai_powered_pct": round(ai_count / len(ats_steps) * 100) if ats_steps else 0,
    }

    return {
        "ats_steps": ats_steps,
        "tools": tools,
        "agents": agents,
        "observability": observability,
        "behavioral_rules": behavioral_rules,
        "header_meta": header_meta,
        "counts": {
            "ats": len(ats_steps),
            "tools": len(tools),
            "agents": len(agents),
            "observability": len(observability),
            "behavioral": len(behavioral_rules),
        },
    }


# ── Suggestion building (blueprint-only generation) ──────────────────────────

def _enrich_description(agent: dict, parsed: dict) -> str:
    """Fold tools/observability/HITL/behavioral-rule text into the agent's
    description — additive text, no new schema field, so scaffold_service.py
    (which already renders `description` as-is) needs zero changes to carry
    this through. Deliberately NOT changing downstream generation logic."""
    parts = [agent["goal"]] if agent["goal"] else []

    if agent["tools_required"]:
        tool_names = [t["name"] for t in parsed["tools"] if t["tool_id"] in agent["tools_required"]]
        parts.append(f"Tools: {', '.join(tool_names or agent['tools_required'])}.")

    if agent["hitl"] and agent["hitl"].lower() != "none":
        parts.append(f"HITL: {agent['hitl']}.")

    obs = next((o for o in parsed["observability"] if o["agent_ref"] == agent["agent_id"]), None)
    if obs and obs["metrics"]:
        parts.append(f"Observability: {obs['metrics']}.")
        if obs["alert_thresholds"]:
            parts.append(f"Alerts: {obs['alert_thresholds']}.")

    matching_rules = [
        b["rule"] for b in parsed["behavioral_rules"]
        if agent["agent_id"] and agent["agent_id"] in b["rule"]
    ]
    if matching_rules:
        parts.append(f"Behavioral guardrail: {'; '.join(matching_rules)}.")

    return " ".join(parts).strip()


def build_suggestion_from_blueprint(project_name: str, parsed: dict) -> dict:
    """Every Agent Definition Register row becomes a K9-AIF agent — unlike
    the BPMN path (GREEN -> adapter, no agent), a blueprint's Agent register
    is inherently agent-scoped regardless of zone (e.g. AGN1/AGN5 are GREEN
    but still real orchestrated agents in this file, not deterministic
    adapters) — that's the blueprint's own convention, preserved as-is."""
    prefix = to_pascal(project_name or "Blueprint")
    orch_name = f"{prefix}Orchestrator"
    squad_name = f"{prefix}Squad"

    agents = [
        {
            # Display name, not the raw register text ("AGN1 – Deterministic
            # Rule Engine") — that text's typographic dash would otherwise
            # leak into the generated Python class name. The full text
            # (including the AGNn id) still appears in the description.
            "name": _display_name(a["name"]),
            "type": zone_to_agent_type(a["zone"] or "GREEN"),
            "model": "reasoning" if a["zone"] in ("AMBER", "RED") else "general",
            "description": f"({a['agent_id']}) {_enrich_description(a, parsed)}".strip(),
            "zone": a["zone"] or None,
            "process_id": a["agent_id"] or None,
        }
        for a in parsed["agents"]
    ]

    return {
        "orchestrators": [{"name": orch_name, "squads": [squad_name]}],
        "squads": [{"name": squad_name, "agents": [a["name"] for a in agents]}],
        "agents": agents,
        "adapters": [],
        # Ravi: "so, we do not yet have MCP... that's the missing piece?
        # scaffold for MCP." §1.7/§3.4's tool rows were parsed correctly
        # (parse_blueprint's own "tools" key) but dropped here before ever
        # reaching the project payload generate_scaffold() sees — nothing
        # downstream could act on them. Threaded straight through now,
        # unmodified (see _tool_from_row in this file for the shape: each
        # has tool_id/name/description/io_schema/authentication/source/
        # build_approach/status).
        "mcp_tools": parsed.get("tools", []),
        # Same drop-then-fix pattern as mcp_tools above. Ravi: "the .md
        # file input has the information, we can make that as the header
        # and so on.. the main.html can be beautiful with all this
        # information." Title/subtitle/Target Outcome/Process Reference +
        # the atomic-step stats (14 steps/64% deterministic/36% AI-powered
        # in the real accounts-payable blueprint) feed docs/main.html's
        # cover section (see _gen_main_html).
        "header_meta": parsed.get("header_meta", {}),
    }


# ── Reconciliation (BPMN + blueprint staged together) ────────────────────────

_REVIEW_PREFIX = re.compile(r"^review:\s*", re.I)


def _normalize_name(name: str) -> str:
    """Lowercase/punctuation-strip for cross-document matching. Also strips
    a leading 'Review: ' — Process Studio's own BPMN convention for the
    review sub-task half of an AMBER-zone pair (verified in the raw XML:
    Task_4 name='Detect Matching Exceptions', Task_4_review
    name='Review: Detect Matching Exceptions') — without stripping it, a
    review task's name never matches its underlying ATS step's name."""
    name = _REVIEW_PREFIX.sub("", name or "")
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def reconcile(bpmn_parsed: dict, blueprint_parsed: dict) -> list[str]:
    """Join BPMN tasks <-> blueprint ATS/Agent entries by NAME text — Task_1
    and ATS1 share no id scheme, only the process step's name text is common
    to both documents (verified against the real sample files). Flags
    mismatches instead of silently generating a half-bound component — same
    drift class as the earlier '7 agents vs 5' bug."""
    bpmn_names = {
        _normalize_name(a.get("description") or a.get("name", ""))
        for a in (bpmn_parsed.get("agents", []) + bpmn_parsed.get("adapters", []))
    }
    ats_names = {_normalize_name(s["name"]) for s in blueprint_parsed.get("ats_steps", [])}

    warnings: list[str] = []
    for step in blueprint_parsed.get("ats_steps", []):
        if _normalize_name(step["name"]) not in bpmn_names:
            warnings.append(
                f"Blueprint step {step['step_id']} — \"{step['name']}\" has no matching BPMN task."
            )
    for a in bpmn_parsed.get("agents", []) + bpmn_parsed.get("adapters", []):
        label = a.get("description") or a.get("name", "")
        if _normalize_name(label) not in ats_names:
            warnings.append(
                f"BPMN task \"{label}\" ({a.get('process_id') or 'no id'}) has no matching blueprint step."
            )
    return warnings


def combine(project_name: str, bpmn_parsed: dict, blueprint_parsed: dict) -> dict:
    """BPMN gives canvas geometry (orchestrators/squads/adapters/review
    structure); blueprint gives the governance layer, joined onto each
    matching BPMN-derived agent's description. BPMN-derived adapters are
    left as-is (a blueprint's Agent register has no adapter concept).

    This is a three-way join, not a direct name match — verified against
    the real sample files that a blueprint agent's own name ("AGN2 -
    Exception Resolution Agent") does NOT textually match either the BPMN
    task name or the ATS step name it owns ("Detect Matching Exceptions").
    The only text common across all three is the BPMN task name <-> the ATS
    step's Name column; the ATS step's id (e.g. "ATS4") then keys into
    whichever Agent register row lists it under "Owned Steps".
    """
    ats_by_name = {_normalize_name(s["name"]): s for s in blueprint_parsed.get("ats_steps", [])}
    agent_by_owned_step = {
        step_id: a
        for a in blueprint_parsed.get("agents", [])
        for step_id in a["owned_steps"]
    }

    suggestion = {
        "orchestrators": bpmn_parsed.get("orchestrators", []),
        "squads": bpmn_parsed.get("squads", []),
        "adapters": bpmn_parsed.get("adapters", []),
        "agents": [],
        # Same drop bug as build_suggestion_from_blueprint() above, in the
        # BPMN+blueprint combined path — this is actually the more common
        # real demo path (BPMN for canvas geometry + blueprint for the MCP
        # tool register), so it needed the same fix.
        "mcp_tools": blueprint_parsed.get("tools", []),
        "header_meta": blueprint_parsed.get("header_meta", {}),
    }
    for a in bpmn_parsed.get("agents", []):
        enriched = dict(a)
        label = _normalize_name(a.get("description") or a.get("name", ""))
        ats_step = ats_by_name.get(label)
        bp_agent = agent_by_owned_step.get(ats_step["step_id"]) if ats_step else None
        if bp_agent:
            enriched["description"] = (
                f"{enriched.get('description', '')} — {_enrich_description(bp_agent, blueprint_parsed)}".strip(" —")
            )
        enriched.setdefault("zone", a.get("zone"))
        suggestion["agents"].append(enriched)

    warnings = reconcile(bpmn_parsed, blueprint_parsed)
    return {"suggestion": suggestion, "warnings": warnings}
