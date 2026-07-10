# SPDX-License-Identifier: Apache-2.0
# k9x_studio — spec document parsing & governance helpers
#
# Pure functions extracted from the original backend/api/routes.py
# /spec/import handler so the SpecImport agent squad can call them as
# private helpers (mirrors how scaffold_service/bpmn_service back their
# respective squads). No FastAPI, no agent classes — just the parsing
# and scoring logic, unchanged in behavior from the monolithic version.

import os
import re
from typing import Optional

from backend.services.scaffold_service import to_pascal

# ── Governance screening ──────────────────────────────────────────────────────

_PROFANITY = re.compile(
    r'\b(fuck|shit|ass|bitch|bastard|cunt|dick|pussy|cock|whore|nigger|faggot|retard)\b',
    re.IGNORECASE
)
_INJECTION = re.compile(
    r'(ignore\s+(previous|all)\s+instructions?|<\s*script|prompt\s*injection|jailbreak)',
    re.IGNORECASE
)

_GOVERNANCE_MAX_CHARS = int(os.environ.get("GOVERNANCE_MAX_CHARS", "50000"))
_GOVERNANCE_ENDPOINT  = os.environ.get("GOVERNANCE_LLM_ENDPOINT", "").strip().rstrip("/")
_GOVERNANCE_MODEL     = os.environ.get("GOVERNANCE_LLM_MODEL", "granite3-guardian:latest").strip()


def governance_check(content: str) -> Optional[str]:
    """
    Returns an error string if content fails governance, None if it passes.
    Layer 1: rule-based (always). Layer 2: Granite Guardian (if configured + doc small enough).
    Only scan first 2000 chars for injection — real attacks appear at the start, not buried in content.
    """
    if _PROFANITY.search(content):
        return "Document contains inappropriate language and cannot be processed."
    if _INJECTION.search(content[:2000]):
        return "Document contains prompt injection patterns and cannot be processed."

    if not _GOVERNANCE_ENDPOINT or len(content) > _GOVERNANCE_MAX_CHARS:
        return None

    endpoint = _GOVERNANCE_ENDPOINT
    if not endpoint.startswith(("http://", "https://")):
        endpoint = "http://" + endpoint

    try:
        import requests as http
        prompt = (
            "You are a content safety classifier. "
            "Is the following document appropriate professional business content? "
            "Reply with SAFE or UNSAFE only, nothing else.\n\n"
            f"{content[:3000]}"
        )
        resp = http.post(
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


# ── Spec document parsing ─────────────────────────────────────────────────────

def parse_table(table_text: str, col_name: int, col_desc: int, col_zone: int) -> list:
    agents = []
    rows = [l.strip() for l in table_text.split('\n') if l.strip().startswith('|')]
    for row in rows[2:]:  # skip header + separator
        cols = [c.strip() for c in row.split('|')]
        cols = [c for c in cols if c]  # drop empty edge cells
        if len(cols) <= col_name:
            continue
        name = cols[col_name]
        desc = cols[col_desc] if col_desc < len(cols) else ''
        zone = cols[col_zone].upper() if col_zone >= 0 and col_zone < len(cols) else 'GREEN'
        if name and name != '---':
            agents.append({'name': name, 'description': desc, 'zone': zone})
    return agents


def extract_intake(content: str) -> dict:
    """Extract project intake fields (name, description, vision, goals, domain) via regex."""
    intake: dict = {}

    h1 = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if h1:
        intake['project_name'] = h1.group(1).strip()

    outcome = re.search(r'\*\*Target Outcome:\*\*\s*(.+?)(?:\n|$)', content)
    if outcome:
        intake['description'] = outcome.group(1).strip()
        intake['vision'] = outcome.group(1).strip()

    kpi_matches = re.findall(r'(\d+[-–]\d+%[^;,\n]{0,60})', content)
    if kpi_matches:
        intake['target_goals'] = '; '.join(kpi_matches[:4])

    text_lower = content.lower()
    if any(k in text_lower for k in ('claim', 'insurance', 'policy', 'fnol')):
        intake['domain'] = 'Insurance'
    elif any(k in text_lower for k in ('invoice', 'accounts payable', 'expense reimburs')):
        intake['domain'] = 'Finance / AP'
    elif any(k in text_lower for k in ('patient', 'clinical', 'ehr')):
        intake['domain'] = 'Healthcare'
    elif any(k in text_lower for k in ('loan', 'mortgage', 'credit')):
        intake['domain'] = 'Banking'

    return intake


def extract_agents_raw(content: str) -> list:
    """Extract the agent register table (name/description/zone) from §3.1.8 or §3.3.1."""
    sec318 = re.search(r'###\s+3\.1\.8[^\n]*\n(.*?)(?=\n###|\Z)', content, re.DOTALL)
    if sec318:
        agents_raw = parse_table(sec318.group(1), col_name=0, col_desc=1, col_zone=5)
        if agents_raw:
            return agents_raw

    sec331 = re.search(r'###\s+3\.3\.1[^\n]*\n(.*?)(?=\n###|\Z)', content, re.DOTALL)
    if sec331:
        return parse_table(sec331.group(1), col_name=0, col_desc=2, col_zone=-1)

    return []


def group_by_zone(agents_raw: list) -> dict:
    """Split the agent register into GREEN (deterministic) vs AMBER/RED (AI) buckets."""
    green = [a for a in agents_raw if a['zone'] == 'GREEN']
    ai    = [a for a in agents_raw if a['zone'] in ('AMBER', 'RED')]

    if not green and not ai and agents_raw:
        half = max(1, len(agents_raw) // 2)
        green, ai = agents_raw[:half], agents_raw[half:]

    return {'green': green, 'ai': ai}


def zone_to_agent_type(zone: str) -> str:
    if zone == 'RED':
        return 'K9CriticActorAgent'
    if zone == 'AMBER':
        return 'K9ValidationLoopAgent'
    return 'BaseAgent'


_SPEC_ADAPTER_HINTS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bapi\b|rest\b|graphql|endpoint|http|fetch|invoke|call\b|webhook", re.I), "api_adapter"),
    (re.compile(r"\brule|policy|decision\b|drools|odm\b|corticon|brms", re.I),              "rules_adapter"),
    (re.compile(r"workflow|bpm\b|camunda|appian|pega|flowable|step\s*function|airflow", re.I), "workflow_adapter"),
    (re.compile(r"integrat|mulesoft|tibco|esb\b|app\s*connect|mq\b|event\s*bus|pubsub", re.I), "process_adapter"),
    (re.compile(r"\bdata(base)?\b|db\b|\bsql\b|persist|store\b|repo\b|warehouse|s3\b", re.I), "data_adapter"),
]


def _spec_adapter_type(name: str, description: str) -> str:
    """Pick the best adapter type from name + description; defaults to api_adapter."""
    text = f"{name} {description}"
    for pattern, atype in _SPEC_ADAPTER_HINTS:
        if pattern.search(text):
            return atype
    return "api_adapter"


def build_suggestion_from_zones(project_name: str, zone_groups: dict) -> dict:
    """
    Rule-based canvas suggestion.
    GREEN (deterministic) → Integration Adapters wired to an OperationsOrchestrator.
    AMBER / RED (AI)      → Agents inside squads under an IntelligenceOrchestrator.
    """
    prefix = to_pascal(project_name)
    green = zone_groups.get('green', [])
    ai    = zone_groups.get('ai', [])

    orchestrators, squads, all_agents, adapters = [], [], [], []

    if green:
        orch_name = f'{prefix}OperationsOrchestrator'
        orchestrators.append({'name': orch_name})
        for a in green:
            atype = _spec_adapter_type(a['name'], a.get('description', ''))
            adapters.append({
                'name': a['name'],
                'adapter_type': atype,
                'description': a.get('description', a['name']),
                'orchestrator': orch_name,
            })

    if ai:
        orchestrators.append({'name': f'{prefix}IntelligenceOrchestrator'})
        squads.append({'name': f'{prefix}IntelligenceSquad', 'agents': [a['name'] for a in ai]})
        for a in ai:
            all_agents.append({'name': a['name'], 'type': zone_to_agent_type(a['zone']),
                               'model': 'reasoning', 'description': a.get('description', a['name'])})

    return {'orchestrators': orchestrators, 'squads': squads, 'agents': all_agents, 'adapters': adapters}


def default_suggestion(project_name: str, domain: str) -> dict:
    prefix = to_pascal(project_name)
    d = domain.strip().title() if domain else prefix
    return {
        "orchestrators": [{"name": f"{prefix}Orchestrator"}],
        "squads": [{"name": f"{prefix}Squad", "agents": [
            "TriageAgent", "ProcessingAgent", "AuditAgent"
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


def sanitize_suggestion(suggestion: dict) -> dict:
    """
    PascalCase every agent/squad/orchestrator name via to_pascal().

    Spec documents (agent register tables) and LLM groupings can return
    names with spaces or punctuation, e.g. "FNOL Intake Engine". Those
    break the generated Python class names (agent_base.py.j2 etc.) and
    the PlantUML class diagram, which both use these names as identifiers.
    """
    for a in suggestion.get('agents', []):
        a['name'] = to_pascal(a['name'])

    for sq in suggestion.get('squads', []):
        sq['name'] = to_pascal(sq['name'])
        sq['agents'] = [to_pascal(n) for n in sq.get('agents', [])]

    for o in suggestion.get('orchestrators', []):
        o['name'] = to_pascal(o['name'])
        if o.get('squad'):
            o['squad'] = to_pascal(o['squad'])

    return suggestion


def score_suggestion(suggestion: dict) -> dict:
    """Score a suggestion by agent count, squad count, and agent type diversity."""
    agents = suggestion.get('agents', [])
    squads = suggestion.get('squads', [])
    types  = set(a.get('type', 'BaseAgent') for a in agents)
    score  = len(agents) * 2 + len(squads) * 3 + len(types)
    return {
        'score':       score,
        'agent_count': len(agents),
        'squad_count': len(squads),
        'type_count':  len(types),
    }


# ── Multi-provider LLM call (governance-screened, transient session config) ───

def call_llm(endpoint: str, provider: str, model: str, api_key: str, prompt: str) -> str:
    """Call the configured LLM and return the raw text response. Raises on failure."""
    import requests as http
    if provider == "ollama":
        resp = http.post(
            f"{endpoint}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    elif provider == "watsonx":
        headers: dict = {"Content-Type": "application/json", "Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        resp = http.post(
            f"{endpoint}/chat/completions",
            headers=headers,
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    elif provider in ("openai", "custom"):
        headers: dict = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        resp = http.post(
            f"{endpoint}/chat/completions",
            headers=headers,
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    elif provider == "anthropic":
        resp = http.post(
            f"{endpoint}/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": api_key,
                     "anthropic-version": "2023-06-01"},
            json={"model": model, "max_tokens": 2048,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
    raise ValueError(f"Unknown provider: {provider}")


def is_local_blocked(endpoint: str) -> bool:
    """Mirrors backend.api.routes._is_local_blocked — blocks localhost targets when K9X_BLOCK_LOCAL=true."""
    if os.environ.get("K9X_BLOCK_LOCAL", "false").lower() != "true":
        return False
    e = (endpoint or "").lower()
    return "localhost" in e or "127.0.0.1" in e or "0.0.0.0" in e
