# SPDX-License-Identifier: Apache-2.0
# k9x_studio API routes

import os as _os
import re
import html as _html
from fastapi import APIRouter, HTTPException, UploadFile, File, Form

# Set K9X_BLOCK_LOCAL=true in .env only for public-hosted instances.
# Default (local / intranet use): localhost endpoints are allowed.
_BLOCK_LOCAL = _os.environ.get("K9X_BLOCK_LOCAL", "false").lower() == "true"
_LOCAL_ADDRS = ("localhost", "127.0.0.1", "::1", "0.0.0.0")

# Splash-screen login. Defaults to demo/demo; set K9X_STUDIO_USER and
# K9X_STUDIO_PASSWORD in .env to restrict access.
_STUDIO_USER = _os.environ.get("K9X_STUDIO_USER", "demo")
_STUDIO_PASSWORD = _os.environ.get("K9X_STUDIO_PASSWORD", "demo")


def _is_local_blocked(endpoint: str) -> bool:
    return _BLOCK_LOCAL and any(loc in endpoint for loc in _LOCAL_ADDRS)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import zipfile
import io as _io
import time as _time
import uuid as _uuid
from pathlib import Path

from backend.services.scaffold_service import generate_scaffold
from backend.services.bpmn_service import parse_bpmn, extract_process_name, build_mapping_document
from backend.services.spec_parsing_service import sanitize_suggestion

router = APIRouter()


# ── Component palette ──────────────────────────────────────────────────────────

PALETTE = [
    {
        "type": "intent_squad",
        "label": "Intent Orchestrator",
        "abbClass": "IntentOrchestrator",
        "color": "#06b6d4",
        "description": "Optional pre-router squad. Contains one IntentAgent that classifies incoming event intent for non-deterministic routing.",
        "singleton": True,
    },
    {
        "type": "router",
        "label": "Router",
        "abbClass": "K9EventRouter",
        "color": "#6366f1",
        "description": "Routes events by event_type to the correct orchestrator.",
        "singleton": True,
    },
    {
        "type": "orchestrator",
        "label": "Orchestrator",
        "abbClass": "BaseOrchestrator",
        "color": "#8b5cf6",
        "description": "Coordinates squad execution for a domain workflow.",
    },
    {
        "type": "squad",
        "label": "Squad",
        "abbClass": "BaseSquad",
        "color": "#0ea5e9",
        "description": "Executes a defined flow of agents in sequence.",
    },
    {
        "type": "agent",
        "label": "Agent",
        "abbClass": "BaseAgent",
        "color": "#10b981",
        "description": "One-shot agent: execute(payload) → dict.",
    },
    {
        "type": "validation_loop",
        "label": "Validation Loop",
        "abbClass": "K9ValidationLoopAgent",
        "color": "#f59e0b",
        "description": "Iterative hypothesis-validate-reason loop agent.",
    },
    {
        "type": "critic_actor",
        "label": "Critic-Actor",
        "abbClass": "K9CriticActorAgent",
        "color": "#ef4444",
        "description": "Generate-critique-refine-accept agent.",
    },
    {
        "type": "guard",
        "label": "Guard",
        "abbClass": "BaseGovernance",
        "color": "#64748b",
        "description": "Governance / zero-trust guard.",
    },
    {
        "type": "hil_orchestrator",
        "label": "HIL Orchestrator",
        "abbClass": "BaseHILOrchestrator",
        "color": "#14b8a6",
        "description": "Human-in-the-loop orchestrator — event-driven, subscribes to Kafka HIL topics. No Router needed.",
        "singleton": True,
    },
]


@router.get("/components")
def get_components():
    return {"components": PALETTE}


# ── Splash-screen login ──────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
def login(req: LoginRequest):
    if req.username == _STUDIO_USER and req.password == _STUDIO_PASSWORD:
        return {"ok": True}
    raise HTTPException(status_code=401, detail="Invalid credentials")


# ── Architecture suggestion ────────────────────────────────────────────────────

class LlmSessionConfig(BaseModel):
    provider: str = "ollama"
    endpoint: str = ""
    model: str = ""
    api_key: str = ""


class SuggestRequest(BaseModel):
    project_name: str
    author: str = ""
    domain: str = ""
    description: str = ""
    llm: Optional[LlmSessionConfig] = None


@router.post("/suggest")
def suggest(req: SuggestRequest):
    """
    Suggest a K9-AIF architecture using the session-provided LLM config.
    LLM config is transient — passed per-request, never stored on disk.
    Falls back to a sensible default if no LLM is configured or call fails.
    """
    import json, re, requests as http
    from backend.services.context_service import get_llm_context
    _fw = get_llm_context()

    prompt = f"""{_fw}

---

## Project to design

Project name: {req.project_name}
Domain: {req.domain}
Description: {req.description}

---

Design a complete K9-AIF multi-agent architecture for this project.
Identify the distinct workflows in the description — each major workflow becomes a Squad.
For each Squad define 2–5 agents in execution order.

Return ONLY a JSON object — no explanation, no markdown, no code fences:
{{
  "orchestrators": [{{"name": "ExampleOrchestrator"}}],
  "squads": [{{"name": "ExampleSquad", "agents": ["AgentOne", "AgentTwo", "AgentThree"]}}],
  "agents": [
    {{"name": "AgentOne", "type": "BaseAgent", "model": "general", "description": "Triage and classify incoming requests"}},
    {{"name": "AgentTwo", "type": "K9ValidationLoopAgent", "model": "reasoning", "description": "Iteratively validates business rules until confidence threshold is met"}},
    {{"name": "AgentThree", "type": "K9CriticActorAgent", "model": "reasoning", "description": "Drafts and refines the output report"}}
  ]
}}

Return ONLY valid JSON. Every agent name in squads[].agents must have a matching entry in agents[].
"""

    default = _default_suggestion(req.project_name, req.domain)

    import os as _os
    from backend.services.config_service import get_llm_config

    # Priority: session config (browser UI) → env vars (.env / docker) → config.yaml → no LLM
    llm = req.llm
    if llm and llm.endpoint.strip():
        provider = llm.provider.strip() or "ollama"
        endpoint = llm.endpoint.strip().rstrip("/")
        model    = llm.model.strip() or "granite3-dense:2b"
        api_key  = llm.api_key or ""
    elif _os.environ.get("LLM_ENDPOINT", "").strip():
        endpoint = _os.environ.get("LLM_ENDPOINT", "").strip().rstrip("/")
        provider = _os.environ.get("LLM_PROVIDER", "ollama").strip()
        model    = _os.environ.get("LLM_MODEL", "granite3-dense:2b").strip()
        api_key  = _os.environ.get("LLM_API_KEY", "").strip()
    else:
        cfg = get_llm_config()
        endpoint = cfg.get("endpoint", "").strip().rstrip("/")
        provider = cfg.get("provider", "ollama")
        model    = cfg.get("model", "granite3-dense:2b")
        api_key  = cfg.get("api_key", "")

    if not endpoint:
        return {"suggestion": default, "source": "default"}

    # Normalise scheme — requests requires http:// or https://
    if not endpoint.startswith(("http://", "https://")):
        endpoint = "http://" + endpoint

    if _is_local_blocked(endpoint):
        return {"suggestion": default, "source": "default"}

    try:
        raw = _call_llm(endpoint, provider, model, api_key, prompt)
        raw = re.sub(r"```(?:json)?", "", raw).strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            suggestion = json.loads(match.group())
            if "agents" in suggestion and "squads" in suggestion:
                return {"suggestion": suggestion, "source": "llm"}
    except Exception:
        pass

    return {"suggestion": default, "source": "default"}


# Moved to backend/services/llm_service.py so doc_narration_service.py can
# share the exact same provider dispatch instead of hardcoding its own
# Ollama-only call — kept as a local alias so every existing call site
# below (_call_llm(...)) needs no change.
from backend.services.llm_service import call_llm as _call_llm


def _default_suggestion(project_name: str, domain: str) -> dict:
    from backend.services.scaffold_service import to_pascal
    prefix = to_pascal(project_name)
    d = domain.strip().title() if domain else prefix
    return {
        "orchestrators": [{"name": f"{prefix}Orchestrator"}],
        "squads": [{"name": f"{prefix}Squad", "agents": [
            f"TriageAgent", f"ProcessingAgent", f"AuditAgent"
        ]}],
        "agents": [
            {"name": "TriageAgent", "type": "BaseAgent", "model": "general",
             "description": f"Triage and classify incoming {d} requests"},
            {"name": "ProcessingAgent", "type": "K9ValidationLoopAgent", "model": "reasoning",
             "description": f"Core {d} processing with iterative validation"},
            {"name": "AuditAgent", "type": "BaseAgent", "model": "general",
             "description": f"Audit and compliance check for {d} outcomes"},
        ],
    }


# ── BPMN import ───────────────────────────────────────────────────────────────

@router.post("/bpmn/import")
async def bpmn_import(file: UploadFile = File(...), llm_config: Optional[str] = Form(None), force_llm: Optional[str] = Form(None)):
    """
    Parse a BPMN 2.0 file or IBM BlueWorks Live ZIP export.

    Rule-based (deterministic) by default and only by default — a BPMN
    document already carries everything needed (lanes, zones, HITL intent)
    via explicit parsing, so there's no ambiguity for an LLM to usefully
    resolve. The LLM regrouping path only runs when force_llm is explicitly
    set alongside llm_config — never merely because a session happens to
    have an LLM configured elsewhere in the app. See plan.md
    "mapping-document-first" decision (no LLM for structured input).
    ZIP: skips .xsd and Glossaries.bpmn, parses the main process .bpmn.
    """
    import io as _io

    fname = (file.filename or "").lower()
    if not fname.endswith((".bpmn", ".xml", ".zip")):
        raise HTTPException(status_code=400, detail="Upload a .bpmn, .xml, or .zip file")

    raw = await file.read()

    # ── Unzip if needed ────────────────────────────────────────────────────────
    if fname.endswith(".zip"):
        try:
            with zipfile.ZipFile(_io.BytesIO(raw)) as zf:
                candidates = [
                    n for n in zf.namelist()
                    if n.lower().endswith(".bpmn")
                    and "glossar" not in n.lower()
                ]
                if not candidates:
                    raise HTTPException(status_code=422,
                        detail="No process .bpmn file found inside the ZIP")
                # Prefer files that aren't just resources/participants
                main = next(
                    (c for c in candidates if "resource" not in c.lower()), candidates[0]
                )
                raw = zf.read(main)
        except zipfile.BadZipFile:
            raise HTTPException(status_code=422, detail="Not a valid ZIP file")

    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 2MB)")
    content = raw.decode("utf-8", errors="replace")
    governance_err = _governance_check(content)
    if governance_err:
        raise HTTPException(status_code=422, detail=governance_err)
    try:
        base_suggestion = parse_bpmn(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    process_name = extract_process_name(content)
    if not process_name:
        # Real Process-Studio-exported BPMN files often have no name attribute
        # at all on <process>/<definitions> (e.g. just id="Process_1") — found
        # via the AP-invoice sample: extract_process_name() correctly returns
        # None, but leaving project_name empty silently disables Generate
        # Scaffold client-side ("Set a project name first") with no visible
        # reason on this tab. Fall back to the uploaded filename so a fresh
        # BPMN import always leaves project_name populated; the SA can still
        # rename it (Project Info panel, or the Traceability tab doesn't
        # cover this field — it's project-level, not per-component).
        # Process Studio's own naming convention always appends "-bpmn" to
        # the diagram filename (e.g. "accounts-payable-...-bpmn.bpmn") —
        # strip it so it doesn't leak into project_name (and from there into
        # app_folder/the scaffold zip's name: "..._bpmn_scaffold.zip" reads
        # like a mistake, not a feature).
        stem = Path(file.filename or "process").stem
        stem = re.sub(r"[-_]?bpmn$", "", stem, flags=re.I)
        process_name = re.sub(r"[-_]+", " ", stem).strip().title() or "Imported Process"

    # Built from the deterministic parse (base_suggestion), not whatever the
    # LLM path below might return — this is the authoritative traceability
    # data regardless of which suggestion (LLM-regrouped or rule-based) ends
    # up on canvas. See plan.md mapping-document step 8: once "no LLM for
    # structured input" is locked down, the LLM path won't fire for BPMN
    # import at all and this divergence risk goes away.
    mapping_document = build_mapping_document(base_suggestion)

    # ── LLM regrouping — only when explicitly force_llm'd, never merely because
    # a session LLM config happens to exist (plan.md: no LLM for structured
    # input by default) ─────────────────────────────────────────────────────
    if llm_config and force_llm:
        import json as _json, re as _re
        try:
            cfg = _json.loads(llm_config)
            endpoint = cfg.get("endpoint", "").strip().rstrip("/")
            provider = cfg.get("provider", "ollama").strip()
            model    = cfg.get("model", "granite3-dense:2b").strip()
            api_key  = cfg.get("api_key", "")
            if endpoint and not _is_local_blocked(endpoint):
                if not endpoint.startswith(("http://", "https://")):
                    endpoint = "http://" + endpoint
                from backend.services.context_service import get_llm_context as _get_ctx
                _fw = _get_ctx()
                agent_names = [a["name"].replace("Agent", "") for a in base_suggestion["agents"]]
                task_list   = "\n".join(f"- {n}" for n in agent_names)
                prompt = f"""{_fw}

---

## BPMN tasks to organise into K9-AIF squads

Process: {process_name or 'Process'}
Tasks extracted from the BPMN diagram:
{task_list}

Group these tasks into logical squads. Each squad represents a distinct workflow stage.
Assign the correct agent type to each task based on what it does.
Never put all tasks in one squad — identify 2–5 logical groupings.

Return ONLY a JSON object — no explanation, no markdown, no code fences:
{{
  "orchestrators": [{{"name": "ExampleOrchestrator"}}],
  "squads": [{{"name": "ExampleSquad", "agents": ["AgentOne", "AgentTwo"]}}],
  "agents": [{{"name": "AgentOne", "type": "BaseAgent", "model": "general", "description": "What this agent does"}}]
}}

Every agent name in squads[].agents must have a matching entry in agents[]. Return ONLY valid JSON.
"""
                raw_text = _call_llm(endpoint, provider, model, api_key, prompt)
                raw_text = _re.sub(r"```(?:json)?", "", raw_text).strip()
                match = _re.search(r"\{.*\}", raw_text, _re.DOTALL)
                if match:
                    llm_suggestion = _json.loads(match.group())
                    if "agents" in llm_suggestion and "squads" in llm_suggestion:
                        return {
                            "suggestion": llm_suggestion,
                            "mapping_document": mapping_document,
                            "process_name": process_name,
                            "source": "bpmn+llm",
                        }
        except Exception:
            pass  # fall through to rule-based result

    return {
        "suggestion": base_suggestion,
        "mapping_document": mapping_document,
        "process_name": process_name,
        "source": "bpmn",
    }


@router.post("/blueprint/import")
async def blueprint_import(file: UploadFile = File(...)):
    """
    Parse an EAEF blueprint (.md/.txt/.html) — the governance layer a BPMN
    structurally cannot encode (MCP tool register, agent definitions,
    observability requirements, behavioral evals, HITL touchpoints).

    Rule-based always, same as BPMN import — a blueprint's numbered
    sections and pipe-delimited tables are exactly as structured as a BPMN
    diagram, nothing for an LLM to usefully resolve. See
    blueprint_service.py's module docstring.
    """
    fname = (file.filename or "").lower()
    if not fname.endswith((".md", ".txt", ".html", ".htm")):
        raise HTTPException(status_code=400, detail="Upload a .md, .txt, or .html blueprint file")

    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    content = raw.decode("utf-8", errors="replace")

    if fname.endswith((".html", ".htm")):
        # Simple tag-strip — the real sample .html export is the same EAEF
        # content marked up, not a different document; no new dependency
        # (BeautifulSoup etc.) needed for well-formed generator output.
        content = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", content, flags=re.I | re.S)
        content = re.sub(r"<[^>]+>", "\n", content)
        content = _html.unescape(content)

    governance_err = _governance_check(content)
    if governance_err:
        raise HTTPException(status_code=422, detail=governance_err)

    from backend.services.blueprint_service import looks_like_blueprint, parse_blueprint, build_suggestion_from_blueprint

    if not looks_like_blueprint(content):
        raise HTTPException(
            status_code=422,
            detail="This doesn't look like an EAEF blueprint — none of the expected sections "
                   "(Atomic Thinking Step Register, MCP Tool Register, Agent Definition Register, "
                   "Observability Requirements, Behavioral Evals) were found.",
        )

    stem = Path(file.filename or "blueprint").stem
    process_name = re.sub(r"[-_]+", " ", stem).strip().title() or "Imported Blueprint"

    parsed = parse_blueprint(content)
    suggestion = sanitize_suggestion(build_suggestion_from_blueprint(process_name, parsed))
    mapping_document = build_mapping_document(suggestion)

    return {
        "suggestion": suggestion,
        "parsed": parsed,
        "mapping_document": mapping_document,
        "counts": parsed["counts"],
        "process_name": process_name,
        "source": "blueprint",
    }


@router.post("/evals/import")
async def evals_import(file: UploadFile = File(...)):
    """
    Parse Process Studio's companion Agent Evaluation Plan (filename suffix
    "-evals.md") — Functional/Behavioral/Adversarial/Domain/Failure Mode/
    HITL/Observability/Regression test-case tables. Rule-based, same as
    BPMN/blueprint import — see evals_service.py's module docstring.

    Unlike BPMN/blueprint, this never drives canvas generation — it has no
    suggestion/mapping_document. The parsed rows are only used, later, to
    generate tests/evals/*.py stubs in the scaffold (see
    scaffold_service.py's _gen_eval_test_files()).
    """
    fname = (file.filename or "").lower()
    if not fname.endswith((".md", ".txt")):
        raise HTTPException(status_code=400, detail="Upload a .md or .txt eval plan file")

    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    content = raw.decode("utf-8", errors="replace")

    governance_err = _governance_check(content)
    if governance_err:
        raise HTTPException(status_code=422, detail=governance_err)

    from backend.services.evals_service import looks_like_evals, parse_evals

    if not looks_like_evals(content):
        raise HTTPException(
            status_code=422,
            detail="This doesn't look like an Agent Evaluation Plan — none of the expected "
                   "sections (Functional Evals, Behavioral Evals, Adversarial Evals, Failure Mode "
                   "& Fallback Testing, Human-in-the-Loop Validation, Observability Validation) "
                   "were found.",
        )

    parsed = parse_evals(content)
    return {
        "rows": parsed["rows"],
        "counts": parsed["counts"],
        "total": parsed["total"],
        "source": "evals",
    }


class CombineRequest(BaseModel):
    project_name: str = ""
    bpmn_parsed: dict
    blueprint_parsed: dict


@router.post("/intake/combine")
def intake_combine(req: CombineRequest):
    """
    Join a staged BPMN parse + a staged blueprint parse into one suggestion
    — BPMN gives canvas geometry, blueprint gives the governance layer,
    joined on ATS/task identity (see blueprint_service.combine()). Only
    used when BOTH are staged; a single staged input generates directly
    from its own /api/bpmn/import or /api/blueprint/import result without
    this endpoint.
    """
    from backend.services.blueprint_service import combine

    result = combine(req.project_name, req.bpmn_parsed, req.blueprint_parsed)
    suggestion = sanitize_suggestion(result["suggestion"])
    mapping_document = build_mapping_document(suggestion)

    return {
        "suggestion": suggestion,
        "mapping_document": mapping_document,
        "warnings": result["warnings"],
        "source": "bpmn+blueprint",
    }


# ── Project generation ─────────────────────────────────────────────────────────

class AgentDef(BaseModel):
    name: str
    type: str = "BaseAgent"
    model: str = "general"
    pattern: str = "reasoning"
    description: str = ""
    # GREEN/AMBER/RED, process_id: added along with build_mapping_document()
    # (plan.md mapping-document work) — without these two fields, a real
    # request through /api/generate silently dropped both (Pydantic ignores
    # undeclared fields), even though bpmn_service.py has sent them since
    # that work landed. Confirmed and fixed 2026-09-10 via a live HTTP test
    # (sent adapters, got 0 back) that exposed this alongside the missing
    # AdapterDef below.
    zone: Optional[str] = None
    process_id: Optional[str] = None

class SquadDef(BaseModel):
    name: str
    agents: List[str]
    zone: Optional[str] = None
    process_id: Optional[str] = None

class AdapterDef(BaseModel):
    """Was entirely missing from this schema until 2026-09-10 — confirmed via
    a live HTTP test that every real scaffold-generation request silently
    dropped all adapter data (Pydantic ignores fields a model doesn't
    declare). Every GREEN/deterministic step, and detailed-design.md's
    matrix rows for them, were affected."""
    name: str
    adapter_type: str = "api_adapter"
    description: str = ""
    orchestrator: Optional[str] = None
    zone: Optional[str] = None
    process_id: Optional[str] = None

class OrchestratorDef(BaseModel):
    name: str
    squads: List[str] = Field(default_factory=list)
    parallel: bool = False
    process_id: Optional[str] = None

class ScenarioDef(BaseModel):
    """A single 'best case' use-case scenario embedded in the generated scaffold.
    main.py prints title + narrative, then sends payload to the squad as input."""
    title: str = ""
    narrative: str = ""
    payload: dict = Field(default_factory=dict)

class ProjectDef(BaseModel):
    project_name: str
    author: str = ""
    domain: str = ""
    description: str = ""
    project_folder: str = ""
    framework_path: str = ""
    platforms: List[str] = Field(default_factory=list)
    messaging_list: List[str] = Field(default_factory=list)
    database_list: List[str] = Field(default_factory=list)
    object_storage_list: List[str] = Field(default_factory=list)
    docling_enabled: bool = False
    deployment_list: List[str] = Field(default_factory=list)
    output_path: str = ""
    orchestrators: List[OrchestratorDef] = Field(default_factory=list)
    squads: List[SquadDef] = Field(default_factory=list)
    agents: List[AgentDef] = Field(default_factory=list)
    # Was entirely missing until 2026-09-10 — see AdapterDef above for the
    # bug this fixes (every real /api/generate request silently dropped all
    # adapter data).
    adapters: List[AdapterDef] = Field(default_factory=list)
    llm_provider: str = ""
    llm_model: str = ""
    # Ravi: "remove the wiring to the qwen model. Only when a user or myself
    # sets up a LLM using the setup then it can be used" — the "LLM
    # narration" feature (generate_rich_docs) needs the actual reachable
    # endpoint/credentials, not just a display-only provider/model label,
    # so it can call the SAME LLM the Setup tab configured rather than a
    # separate hardwired default. Both empty (no LLM configured anywhere)
    # means narration is skipped entirely — see scaffold_service.py.
    llm_endpoint: str = ""
    llm_api_key: str = ""
    generation_source: str = ""
    generation_scoring: Optional[dict] = None
    scenario: Optional[ScenarioDef] = None
    # Which Process Studio input files fed this generation — set by
    # IntakePanel.tsx's stage*File functions on the frontend, read by
    # scaffold_service.py's _gen_manifest_md() to build MANIFEST.md's
    # input-artifact -> output-artifact table.
    source_bpmn_filename: str = ""
    source_spec_filename: str = ""
    source_evals_filename: str = ""
    source_evals_case_count: Optional[int] = None
    # Parsed eval-case rows (evals_service.parse_evals()'s "rows" list) —
    # carried through so scaffold_service.py's _gen_eval_test_files() can
    # generate tests/evals/*.py stubs, one per row, without re-parsing the
    # original file server-side a second time.
    source_evals_rows: List[dict] = Field(default_factory=list)
    # Ravi: "so, we do not yet have MCP... that's the missing piece?
    # scaffold for MCP." Parsed §1.7/§3.4 MCP tool rows from the blueprint
    # (blueprint_service.py's _tool_from_row()) — was parsed correctly but
    # dropped in build_suggestion_from_blueprint()/combine() before ever
    # reaching this payload; both fixed to include it. Carried through so
    # scaffold_service.py's _gen_mcp_tool_files() can generate one stub per
    # tool without re-parsing the blueprint server-side a second time.
    mcp_tools: List[dict] = Field(default_factory=list)
    # Blueprint's own title/subtitle/Target Outcome/Process Reference +
    # atomic-step stats (14 steps/64% deterministic/36% AI-powered) — feeds
    # docs/main.html's cover section (see _gen_main_html).
    header_meta: dict = Field(default_factory=dict)
    # Opt-in LLM narration pass (doc_narration_service.py) — replaces
    # README/MANIFEST/ARCHITECTURE/implementation-plan.md with two documents
    # narrated by a local LLM from the same verified project data, matching
    # IBM Process Studio's own house style. Off by default: it's slower
    # (a 27B model call, not instant) and depends on a reachable LLM host —
    # falls back to the plain deterministic docs if that call fails.
    generate_rich_docs: bool = False
    # Ravi: internal IBM hosting has no login of its own (SSO handled
    # upstream by ICA) — everyone lands as the same "demo" identity, so
    # this is what actually tells concurrent reviewers' work apart. A
    # per-browser id (crypto.randomUUID(), persisted client-side — see
    # store.ts's clientId), not a real user identity; purely so two
    # people generating at once leave distinguishable traces (e.g. in the
    # implementation doc's own metadata table below), not because any
    # server-side state today could actually collide (generate_scaffold
    # is a pure function of its argument — no shared mutable state to
    # collide on in the first place).
    client_id: str = ""


_BINARY_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif")


def _zip_file_listing(zip_buf) -> list:
    files = []
    with zipfile.ZipFile(zip_buf, "r") as zf:
        for name in sorted(zf.namelist()):
            if not name.endswith("/"):
                raw = zf.read(name)
                if name.lower().endswith(_BINARY_EXTENSIONS):
                    import base64 as _base64
                    files.append({"path": name, "content": _base64.b64encode(raw).decode("ascii"), "binary": True})
                else:
                    files.append({"path": name, "content": raw.decode("utf-8", errors="replace"), "binary": False})
    return files


@router.post("/scaffold-preview")
def scaffold_preview(project: ProjectDef):
    """Return scaffold file tree as JSON without downloading a zip."""
    zip_buf = generate_scaffold(project.model_dump())
    return {"files": _zip_file_listing(zip_buf)}


@router.get("/generate/preview/{token}")
def generate_preview(token: str):
    # Ravi: "the original studio does not use LLM. This one does. This is
    # the difference" — and correctly so: with Rich Docs now always on
    # (Studio.tsx), the old flow called /api/generate (runs narration once,
    # ~60-70s) and then immediately called /api/scaffold-preview with the
    # SAME payload — a completely independent generate_scaffold() call that
    # reran the entire narration a second time just to list the files
    # already sitting in the zip we just built. This reads the file listing
    # straight out of that already-built, already-narrated zip (same
    # _PENDING_ZIPS token the download uses) — zero extra LLM calls, zero
    # extra generation work.
    entry = _PENDING_ZIPS.get(token)
    if entry is None:
        raise HTTPException(status_code=404, detail="This generation has expired. Generate the scaffold again.")
    return {"files": _zip_file_listing(_io.BytesIO(entry["data"]))}



# Ravi reported the scaffold zip repeatedly landing as a stuck
# "<name>.zip.crdownload" even after confirming the browser's own save
# prompt properly. The fetch()+res.blob()+URL.createObjectURL()+<a>.click()
# blob path was an early suspect and got replaced below with a token+plain-
# GET flow — but that turned out NOT to be the actual cause: a side-by-side
# test against the original k9x_studio (identical machine/browser) showed
# ITS blob-based download always completes fine, while this app's download
# still got stuck even via a real GET. The one concrete code difference
# found was the explicit Content-Length header this endpoint added (see
# generate_download() below) — removed to match k9x_studio's own working
# implementation, which never sets it. The token+GET split itself is kept
# anyway since it's a genuine improvement (server-side archived copy,
# re-downloadable from Generated Docs without a fresh generate call).
_PENDING_ZIPS: dict = {}
_PENDING_ZIP_TTL_S = 15 * 60


def _purge_pending_zips() -> None:
    cutoff = _time.time() - _PENDING_ZIP_TTL_S
    for tok in [t for t, v in _PENDING_ZIPS.items() if v["created"] < cutoff]:
        _PENDING_ZIPS.pop(tok, None)


def _scaffold_filename(project_name: str) -> str:
    safe_name = project_name.encode("ascii", "ignore").decode("ascii")
    # Ravi: "multiple runs the same day a user would like to keep older
    # version" — date+time prefix matching the app_folder inside the zip
    # (scaffold_service.py), so this fallback filename (only used if the
    # frontend's own a.download name — see Studio.tsx — doesn't apply)
    # stays consistent and collision-free too.
    from datetime import datetime as _datetime
    date_stamp = _datetime.now().strftime("%y%m%d_%H%M%S")
    return date_stamp + "_k9x_" + re.sub(r"[^a-z0-9]+", "_", safe_name.lower()).strip("_") + "_scaffold.zip"


def _generated_archive_dir() -> "Path | None":
    # Ravi: "perhaps we store the project artifacts there? and make it
    # available?" — re: the K9X_PROJECTS_ROOT host volume already mounted
    # by ubuntu/build-run.sh (-v .../k9x-studiox-ibm/projects:/k9x/projects)
    # but otherwise unused by the browser-download generate flow. Every
    # /api/generate call now also drops a durable copy under
    # <K9X_PROJECTS_ROOT>/generated/ — a server-side audit trail that
    # survives a browser refresh/crash, independent of the in-memory,
    # time-limited _PENDING_ZIPS token above. No-ops locally where
    # K9X_PROJECTS_ROOT isn't set (dev mode), same "never fail the export
    # over a nice-to-have" precedent as the rich-docs .html export.
    root = _os.environ.get("K9X_PROJECTS_ROOT", "").strip()
    if not root:
        return None
    d = Path(root) / "generated"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Ravi's live PowerAI instance hit this: the -v host volume is
        # created via `sudo mkdir -p` (build-run.sh) so it's root:root, but
        # the container runs as USER 1001 (Containerfile) — mkdir here can
        # legitimately fail on permissions. This whole archive is a
        # best-effort convenience, never load-bearing for the actual
        # download, so degrade to "no archive" rather than 500ing every
        # /api/generate and /api/generated-archive call.
        return None
    return d


@router.post("/generate")
def generate(project: ProjectDef):
    zip_buf = generate_scaffold(project.model_dump())
    data = zip_buf.getvalue()
    filename = _scaffold_filename(project.project_name)
    _purge_pending_zips()
    token = _uuid.uuid4().hex
    _PENDING_ZIPS[token] = {"data": data, "filename": filename, "created": _time.time()}
    try:
        archive_dir = _generated_archive_dir()
        if archive_dir is not None:
            (archive_dir / filename).write_bytes(data)
    except Exception:
        pass  # archive is best-effort; never block the download over it
    return {"token": token, "filename": filename, "size": len(data)}


@router.get("/generated-archive")
def list_generated_archive():
    """Every scaffold zip ever generated on this server, newest first —
    the durable copy under K9X_PROJECTS_ROOT/generated/, independent of any
    one browser's session. Empty list if K9X_PROJECTS_ROOT isn't set."""
    archive_dir = _generated_archive_dir()
    if archive_dir is None:
        return {"files": []}
    files = []
    for f in archive_dir.glob("*.zip"):
        st = f.stat()
        files.append({"name": f.name, "size": st.st_size, "mtime": st.st_mtime})
    files.sort(key=lambda f: f["mtime"], reverse=True)
    return {"files": files}


@router.get("/generated-archive/download/{name}")
def download_generated_archive(name: str):
    archive_dir = _generated_archive_dir()
    if archive_dir is None:
        raise HTTPException(status_code=404, detail="No archive configured on this server.")
    # Reject anything that isn't a bare filename in this one directory —
    # no path traversal into the rest of K9X_PROJECTS_ROOT or beyond.
    if "/" in name or "\\" in name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid filename.")
    path = (archive_dir / name).resolve()
    if archive_dir.resolve() not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    data = path.read_bytes()
    return StreamingResponse(
        _io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={name}"},
    )


@router.get("/generate/download/{token}")
def generate_download(token: str):
    entry = _PENDING_ZIPS.get(token)
    if entry is None:
        raise HTTPException(status_code=404, detail="This download has expired. Generate the scaffold again.")
    data = entry["data"]
    # Ravi: side-by-side test against the original k9x_studio (same machine,
    # same browser) proved its downloads always complete while this app's
    # got stuck as .crdownload — and the one concrete difference found was
    # this explicit Content-Length header (added earlier this session,
    # believing it would help). k9x_studio's own working /generate never
    # sets it, relying on Starlette's default chunked transfer-encoding
    # (self-terminating — the browser knows it's done from the framing
    # itself, not a byte count). Dropped to match.
    return StreamingResponse(
        _io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={entry['filename']}"},
    )


@router.post("/generate-to-disk")
def generate_to_disk(project: ProjectDef):
    """Generate scaffold directly into a folder on the server's filesystem."""
    import os
    output_path = (project.output_path or project.project_folder).strip()
    if not output_path:
        raise HTTPException(status_code=400, detail="output_path is required")

    out_dir = Path(output_path).expanduser().resolve()

    # Guard: if a projects root is configured, the output path must be inside it.
    # This prevents writes landing inside the container instead of the mounted volume.
    projects_root = os.environ.get("K9X_PROJECTS_ROOT", "")
    if projects_root:
        root_dir = Path(projects_root).resolve()
        try:
            out_dir.relative_to(root_dir)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Output path must be inside {projects_root} (your mounted projects folder). "
                    f"Got: {out_dir}. Use a path starting with {projects_root}."
                ),
            )

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot create directory: {e}")

    zip_buf = generate_scaffold(project.model_dump())

    import os
    with zipfile.ZipFile(zip_buf, "r") as zf:
        zf.extractall(out_dir)

    for sh in out_dir.rglob("*.sh"):
        sh.chmod(0o755)

    return {"status": "ok", "path": str(out_dir)}


class ScaffoldDownloadRequest(BaseModel):
    path: str


@router.post("/scaffold/download")
def download_scaffold(req: ScaffoldDownloadRequest):
    """Stream a ZIP of an already-written scaffold directory."""
    import io as _io
    path = Path(req.path).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise HTTPException(status_code=404, detail=f"Scaffold folder not found: {path}")

    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in path.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(path))
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={path.name}.zip"},
    )


class FeedbackRequest(BaseModel):
    text: str
    project: str = ""


@router.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    """Append feedback entry to feedback.jsonl in the projects root."""
    import json, os
    from datetime import datetime, timezone

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Feedback text is required")

    projects_root = os.environ.get("K9X_PROJECTS_ROOT", ".")
    feedback_dir = Path(projects_root) / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "project": req.project or "",
        "text": text,
    }
    with open(feedback_dir / "feedback.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")

    return {"status": "ok"}


@router.get("/stats")
def get_stats():
    """Increment and return studio visit counter. Stored in projects root."""
    import json, os, threading
    _lock = getattr(get_stats, "_lock", None)
    if _lock is None:
        get_stats._lock = threading.Lock()  # type: ignore[attr-defined]
        _lock = get_stats._lock

    projects_root = os.environ.get("K9X_PROJECTS_ROOT", ".")
    stats_path = Path(projects_root) / "stats.json"

    with _lock:
        stats: dict = {"visits": 0}
        if stats_path.exists():
            try:
                stats = json.loads(stats_path.read_text())
            except Exception:
                stats = {"visits": 0}
        stats["visits"] = stats.get("visits", 0) + 1
        try:
            stats_path.parent.mkdir(parents=True, exist_ok=True)
            stats_path.write_text(json.dumps(stats))
        except Exception:
            pass

    return {"visits": stats["visits"]}


@router.post("/llm/verify")
def verify_llm(req: LlmSessionConfig):
    """Lightweight connectivity check for a user-supplied LLM endpoint."""
    import requests as http

    endpoint = req.endpoint.strip().rstrip("/")
    if not endpoint:
        raise HTTPException(status_code=400, detail="Endpoint is required")
    if not endpoint.startswith(("http://", "https://")):
        endpoint = "http://" + endpoint

    if _is_local_blocked(endpoint):
        raise HTTPException(status_code=400, detail="Local addresses are not allowed on this instance")

    provider = req.provider.strip() or "ollama"
    headers: dict = {}
    if req.api_key:
        headers["Authorization"] = f"Bearer {req.api_key}"

    try:
        if provider == "ollama":
            # POST /api/generate with stream:false — same call OllamaLLM.generate() uses
            model = req.model.strip() or "llama3.1:latest"
            r = http.post(
                f"{endpoint}/api/generate",
                json={"model": model, "prompt": "hi", "stream": False},
                timeout=30,
            )
            if r.status_code == 404:
                raise HTTPException(status_code=502, detail=f"Model '{model}' not found on this Ollama server")
            r.raise_for_status()
            return {"ok": True, "detail": f"Connected · model {model} responded"}

        elif provider in ("openai", "custom"):
            r = http.get(f"{endpoint}/models", headers=headers, timeout=8)
            r.raise_for_status()
            return {"ok": True, "detail": "Connected"}

        elif provider == "anthropic":
            # Anthropic has no free health endpoint — send a minimal 1-token message
            r = http.post(
                f"{endpoint}/v1/messages",
                headers={**headers, "x-api-key": req.api_key or "", "anthropic-version": "2023-06-01"},
                json={"model": req.model or "claude-haiku-4-5-20251001",
                      "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                timeout=12,
            )
            if r.status_code in (200, 400, 529):
                return {"ok": True, "detail": "Connected"}
            r.raise_for_status()
            return {"ok": True, "detail": "Connected"}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    except http.exceptions.ConnectionError:
        return {"ok": False, "detail": f"Cannot reach {endpoint}"}
    except http.exceptions.Timeout:
        return {"ok": False, "detail": "Endpoint timed out"}
    except http.exceptions.HTTPError as e:
        return {"ok": False, "detail": f"Endpoint returned {e.response.status_code}"}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


@router.post("/llm/models")
def list_models(req: LlmSessionConfig):
    import requests as http
    endpoint = req.endpoint.strip().rstrip("/")
    if not endpoint:
        if req.provider == "anthropic": endpoint = "https://api.anthropic.com"
        elif req.provider == "ollama":  endpoint = "http://localhost:11434"
    if not endpoint.startswith(("http://", "https://")):
        endpoint = "http://" + endpoint

    if req.provider == "anthropic":
        return {"models": ["claude-sonnet-4-6", "claude-opus-4-8", "claude-haiku-4-5-20251001"]}

    if req.provider == "watsonx":
        return {"models": [
            "ibm/granite-3-3-8b-instruct",
            "ibm/granite-3-3-2b-instruct",
            "ibm/granite-3-2-8b-instruct",
            "meta-llama/llama-3-3-70b-instruct",
            "meta-llama/llama-3-1-8b-instruct",
            "mistralai/mistral-large",
        ]}

    try:
        if req.provider == "ollama":
            r = http.get(f"{endpoint}/api/tags", timeout=8)
            r.raise_for_status()
            return {"models": [m["name"] for m in r.json().get("models", [])]}
        elif req.provider in ("openai", "custom"):
            headers = {}
            if req.api_key: headers["Authorization"] = f"Bearer {req.api_key}"
            r = http.get(f"{endpoint}/models", headers=headers, timeout=8)
            r.raise_for_status()
            return {"models": sorted(m["id"] for m in r.json().get("data", []))}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Cannot fetch models: {e}")
    return {"models": []}


class GuardianCheckRequest(BaseModel):
    filename: str = ""
    content: str
    llm_endpoint: str = ""
    llm_provider: str = "ollama"
    llm_model: str = ""
    llm_api_key: str = ""


def _guardian_config(req_endpoint: str = "", req_provider: str = "", req_model: str = "", req_api_key: str = ""):
    """Server-side GOVERNANCE_LLM_ENDPOINT/GOVERNANCE_LLM_MODEL env vars win when
    set — Ravi: "wire to this under the hood" — so Guardian works for every
    upload without each reviewer configuring Setup themselves. Falls back to
    whatever the Setup screen has configured (useful for local dev), and
    finally to plain Ollama defaults."""
    endpoint = (_GOVERNANCE_ENDPOINT or req_endpoint or "").strip().rstrip("/")
    provider = "ollama" if _GOVERNANCE_ENDPOINT else (req_provider.strip() or "ollama")
    model = (_GOVERNANCE_MODEL if _GOVERNANCE_ENDPOINT else req_model).strip() or _GOVERNANCE_MODEL
    api_key = "" if _GOVERNANCE_ENDPOINT else req_api_key
    if endpoint and not endpoint.startswith(("http://", "https://")):
        endpoint = "http://" + endpoint
    return endpoint, provider, model, api_key


@router.post("/guardian/check")
def guardian_check(req: GuardianCheckRequest):
    """Mandatory content-safety screen — every staged Intake file (BPMN,
    spec/blueprint, eval plan, Process Studio .html) is sent here before
    it's accepted. Ravi: "studio has to use guardian mandatory." Fails
    closed: no endpoint/model configured, or the model unreachable, both
    block the upload rather than silently skipping the check."""
    from backend.services.guardian_service import check_content_safety

    if not _GUARDIAN_ENABLED:
        return {"checked": False, "safe": True, "skipped": True,
                "reason": "Guardian disabled (GUARDIAN_ENABLED=false)", "raw": ""}

    endpoint, provider, model, api_key = _guardian_config(req.llm_endpoint, req.llm_provider, req.llm_model, req.llm_api_key)
    if not endpoint or not model:
        raise HTTPException(
            status_code=400,
            detail="Guardian safety check requires an LLM endpoint and model — configure one in Setup "
                   f"(a Granite Guardian model, e.g. {_GOVERNANCE_MODEL}) before uploading files.",
        )
    if _is_local_blocked(endpoint):
        raise HTTPException(status_code=400, detail="Local addresses are not allowed on this instance")

    result = check_content_safety(endpoint, provider, model, api_key, req.content)
    return result


@router.get("/guardian/status")
def guardian_status(endpoint: str = "", provider: str = "", model: str = "", api_key: str = ""):
    """Backs the "Guardian Live" indicator in the Studio header — a quick
    reachability probe, not a content check.

    granite4.1-guardian:8b is a "thinking" model -- it emits a full
    chain-of-thought before its <score> verdict even for a two-character
    prompt (confirmed live 2026-09-21: ~11s total, of which load_duration
    was ~0ms -- the model was already resident, all ~11s was genuine
    generation time for 312 "thinking" tokens). The original 8s timeout
    here predates that model (env_template.py's still-documented default
    is the older, non-thinking granite3-guardian:latest) and was never
    revisited when .env moved to granite4.1-guardian:8b -- every status
    check timed out and reported Offline even though the model was
    reachable and correct. Fixed two ways: options.num_predict caps the
    response so the check doesn't need to wait for a full reasoning pass
    (this is a reachability probe, not a real safety verdict -- it never
    reads the response content), and the timeout has headroom above the
    observed ~11s in case num_predict doesn't cut generation short enough
    on some provider/model combos.
    """
    import requests as http

    if not _GUARDIAN_ENABLED:
        return {"enabled": False, "live": False, "model": "", "detail": "disabled (GUARDIAN_ENABLED=false)"}

    gw_endpoint, gw_provider, gw_model, gw_api_key = _guardian_config(endpoint, provider, model, api_key)
    if not gw_endpoint or not gw_model:
        return {"live": False, "model": gw_model, "detail": "not configured"}
    try:
        if gw_provider == "ollama":
            r = http.post(
                f"{gw_endpoint}/api/generate",
                json={"model": gw_model, "prompt": "hi", "stream": False, "options": {"num_predict": 8}},
                timeout=20,
            )
            r.raise_for_status()
        else:
            r = http.get(f"{gw_endpoint}/models", headers={"Authorization": f"Bearer {gw_api_key}"} if gw_api_key else {}, timeout=20)
            r.raise_for_status()
        return {"live": True, "model": gw_model, "detail": "reachable"}
    except Exception as e:
        return {"live": False, "model": gw_model, "detail": str(e)}


@router.get("/docs")
def list_docs(folder: str = ""):
    import os
    if not folder:
        return {"files": []}
    projects_root = os.environ.get("K9X_PROJECTS_ROOT", "")
    out_dir = Path(folder).expanduser().resolve()
    if projects_root:
        root_dir = Path(projects_root).resolve()
        try:
            out_dir.relative_to(root_dir)
        except ValueError:
            return {"files": []}
    if not out_dir.exists():
        return {"files": []}
    files = []
    for f in sorted(out_dir.glob("*")):
        if f.is_file() and f.suffix in (".md", ".zip"):
            files.append({"name": f.name, "path": str(f), "size": f.stat().st_size})
    return {"files": files}


@router.get("/download")
def download_file(path: str = ""):
    import os
    from fastapi.responses import FileResponse
    if not path:
        raise HTTPException(status_code=400, detail="path required")
    projects_root = os.environ.get("K9X_PROJECTS_ROOT", "")
    file_path = Path(path).expanduser().resolve()
    if projects_root:
        root_dir = Path(projects_root).resolve()
        try:
            file_path.relative_to(root_dir)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(file_path), filename=file_path.name)


@router.delete("/delete-file")
def delete_file(path: str = ""):
    import os
    if not path:
        raise HTTPException(status_code=400, detail="path required")
    projects_root = os.environ.get("K9X_PROJECTS_ROOT", "")
    file_path = Path(path).expanduser().resolve()
    if projects_root:
        root_dir = Path(projects_root).resolve()
        try:
            file_path.relative_to(root_dir)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    file_path.unlink()
    return {"status": "ok"}


@router.get("/health")
def health():
    return {"status": "ok", "service": "k9x_studio"}


# ── Work Intake Form ──────────────────────────────────────────────────────────

class WIFRequest(BaseModel):
    project_folder: str
    project_name: str = ""
    author: str = ""
    domain: str = ""
    description: str = ""
    vision: str = ""
    current_state: str = ""
    target_goals: str = ""
    notes: str = ""


@router.post("/save-wif")
def save_wif(req: WIFRequest):
    import os
    from datetime import date

    projects_root = os.environ.get("K9X_PROJECTS_ROOT", "")
    folder = req.project_folder.strip()
    if not folder:
        raise HTTPException(status_code=400, detail="project_folder is required")

    out_dir = Path(folder).expanduser().resolve()

    if projects_root:
        root_dir = Path(projects_root).resolve()
        try:
            out_dir.relative_to(root_dir)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"project_folder must be inside {projects_root}",
            )

    out_dir.mkdir(parents=True, exist_ok=True)

    def section(title: str, content: str) -> str:
        return f"\n## {title}\n\n{content.strip() or '_Not provided_'}\n" if True else ""

    md = f"""# Work Intake Form — {req.project_name or 'Untitled'}

**Date:** {date.today().isoformat()}
**Author:** {req.author or '—'}
**Domain:** {req.domain or '—'}
**Description:** {req.description or '—'}
{section("Business Vision", req.vision)}{section("Current State", req.current_state)}{section("Target Goals", req.target_goals)}{section("Notes", req.notes)}
---
*Generated by K9X Studio*
"""

    slug_proj = re.sub(r"[^a-z0-9]+", "_", req.project_name.lower()).strip("_")
    slug_app  = re.sub(r"[^a-z0-9]+", "_", (req.project_name or "").lower()).strip("_")
    filename  = f"{slug_proj}_intake.md" if not slug_app or slug_app == slug_proj else f"{slug_proj}_{slug_app}_intake.md"
    wif_path = out_dir / filename
    wif_path.write_text(md.strip())
    return {"status": "ok", "path": str(wif_path)}


# ── Spec doc import ───────────────────────────────────────────────────────────

# ── Governance screening ──────────────────────────────────────────────────────

_PROFANITY = re.compile(
    r'\b(fuck|shit|ass|bitch|bastard|cunt|dick|pussy|cock|whore|nigger|faggot|retard)\b',
    re.IGNORECASE
)
_INJECTION = re.compile(
    r'(ignore\s+(previous|all)\s+instructions?|<\s*script|prompt\s*injection|jailbreak)',
    re.IGNORECASE
)

_GOVERNANCE_MAX_CHARS = int(_os.environ.get("GOVERNANCE_MAX_CHARS", "50000"))
_GOVERNANCE_ENDPOINT  = _os.environ.get("GOVERNANCE_LLM_ENDPOINT", "").strip().rstrip("/")
_GOVERNANCE_MODEL     = _os.environ.get("GOVERNANCE_LLM_MODEL", "granite4.1-guardian:8b").strip()
# GUARDIAN_ENABLED=false in .env turns the Intake Guardian screen off (default: on).
_GUARDIAN_ENABLED     = _os.environ.get("GUARDIAN_ENABLED", "true").strip().lower() not in ("0", "false", "no", "off")


def _governance_check(content: str) -> Optional[str]:
    """
    Returns an error string if content fails governance, None if it passes.
    Layer 1: rule-based (always). Layer 2: Granite Guardian (if configured + doc small enough).
    Only scan first 2000 chars for injection — real attacks appear at the start, not buried in content.
    """
    # Layer 1 — rule-based
    if _PROFANITY.search(content):
        return "Document contains inappropriate language and cannot be processed."
    if _INJECTION.search(content[:2000]):
        return "Document contains prompt injection patterns and cannot be processed."

    # Layer 2 — Granite Guardian (only if endpoint configured and doc is small enough)
    if not _GOVERNANCE_ENDPOINT or len(content) > _GOVERNANCE_MAX_CHARS:
        return None

    endpoint = _GOVERNANCE_ENDPOINT
    if not endpoint.startswith(("http://", "https://")):
        endpoint = "http://" + endpoint

    try:
        import requests as _http
        prompt = (
            "You are a content safety classifier. "
            "Is the following document appropriate professional business content? "
            "Reply with SAFE or UNSAFE only, nothing else.\n\n"
            f"{content[:3000]}"
        )
        resp = _http.post(
            f"{endpoint}/api/generate",
            json={"model": _GOVERNANCE_MODEL, "prompt": prompt, "stream": False},
            timeout=15,
        )
        resp.raise_for_status()
        verdict = resp.json().get("response", "").strip().upper()
        if "UNSAFE" in verdict:
            return "Document failed content safety check and cannot be processed."
    except Exception:
        pass  # governance LLM unavailable — fail open, Layer 1 already passed

    return None


@router.post("/mapping-document/from-project")
def mapping_document_from_project(project: ProjectDef):
    """
    Rebuild the traceability matrix from a project payload — used by
    "Import Implementation Plan" (Intake tab) to restore the matrix from
    the state snapshot embedded in a downloaded implementation-plan.md,
    without re-parsing any source document. Reuses build_mapping_document
    directly (same function scaffold generation itself uses for
    detailed-design.md's matrix) rather than a second implementation —
    the matrix a re-imported project sees must be computed exactly the
    same way as the one it was exported with.
    """
    return build_mapping_document(project.model_dump())


@router.post("/spec/import")
async def spec_import(file: UploadFile = File(...), llm_config: Optional[str] = Form(None), force_llm: Optional[str] = Form(None)):
    """
    Parse a project spec .md and return intake fields + canvas suggestion.

    Phase 2 — thin HTTP layer: validate the upload, then hand off to
    K9EventRouter → SpecImportOrchestrator → SpecImportSquad. All parsing,
    governance screening, LLM grouping, and scoring now live in that agent
    chain (see agents/, squads/yaml/spec_import_squad.yaml,
    orchestrators/spec_import_orchestrator.py). No business logic here.
    """
    fname = (file.filename or "").lower()
    if not fname.endswith((".md", ".txt")):
        raise HTTPException(status_code=400, detail="Upload a .md or .txt file")

    content = (await file.read()).decode("utf-8", errors="replace")
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Document too large (max 2MB)")

    from studio_core.router.router_factory import route_event
    result = route_event("spec_import", {
        "content": content,
        "filename": file.filename,
        "llm_config": llm_config,
        "force_llm": force_llm,
    })

    if result.get("status") == "blocked":
        raise HTTPException(status_code=422, detail=result.get("reason"))

    return {k: v for k, v in result.items() if k != "status"}


@router.get("/config")
def get_config():
    """Return runtime configuration visible to the frontend."""
    import os
    return {
        "projects_root": os.environ.get("K9X_PROJECTS_ROOT", ""),
    }


# ── Framework setup ───────────────────────────────────────────────────────────

class CloneRequest(BaseModel):
    target_path: str
    repo_url: str = "https://github.com/k9aif/k9-aif-framework.git"


class VerifyRequest(BaseModel):
    path: str


@router.post("/setup/verify-framework")
def verify_framework(req: VerifyRequest):
    """Check whether a path contains a valid k9-aif-framework clone."""
    raw = req.path.strip()
    if not raw.startswith('/') and not raw.startswith('~'):
        raw = f"~/{raw}"
    target = Path(raw).expanduser().resolve()
    valid = (target / "generator" / "templates").exists()
    return {"valid": valid, "path": str(target)}


@router.post("/setup/clone-framework")
def clone_framework(req: CloneRequest):
    """
    Clone k9-aif-framework into target_path.
    If the directory already contains a valid clone, pull latest instead.
    """
    import subprocess

    raw = req.target_path.strip()
    # Relative paths → resolve from $HOME, not backend CWD
    if not raw.startswith('/') and not raw.startswith('~'):
        raw = f"~/{raw}"
    target = Path(raw).expanduser().resolve()

    try:
        target.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot create directory: {e}")

    git_dir = target / ".git"
    templates_dir = target / "generator" / "templates"
    try:
        if git_dir.exists() and templates_dir.exists():
            # Already a valid framework clone — nothing to do
            (target / "k9_projects").mkdir(exist_ok=True)
            return {"status": "ok", "path": str(target), "note": "already_exists"}
        elif git_dir.exists():
            # Repo present but incomplete — pull to complete it
            subprocess.run(
                ["git", "-C", str(target), "pull", "--depth=1"],
                check=True, capture_output=True, timeout=120,
            )
        else:
            # Fresh clone
            subprocess.run(
                ["git", "clone", "--depth=1", req.repo_url, str(target)],
                check=True, capture_output=True, timeout=180,
            )
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ""
        raise HTTPException(status_code=500, detail=f"git failed: {stderr.strip() or str(e)}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="git clone timed out — check your network")

    # Ensure k9_projects/ exists inside the framework folder
    (target / "k9_projects").mkdir(exist_ok=True)

    return {"status": "ok", "path": str(target)}
