# SPDX-License-Identifier: Apache-2.0
# Optional LLM narration pass over K9X Studio's own deterministic docs.
#
# Deliberately NOT "ask an LLM to write an implementation guide from the
# spec" — that's an open invitation to hallucinate facts about a generated
# project that aren't true. Instead: feed the LLM ONLY the docs
# scaffold_service.py already generated deterministically (traceability
# matrix, architecture rationale, manifest, governance notes — all already
# verified against real project data), plus the real framework CLAUDE.md for
# correct terminology, and instruct it to reorganize/narrate that material
# into two polished documents matching IBM Process Studio's own house style
# (title block, italic subtitle, bold key/value metadata line, Phase/section
# structure, tables) — never to add a fact that isn't already in the source.
#
# Opt-in and additive-safe: generate_scaffold() falls back to the plain
# deterministic docs whenever this fails (LLM unreachable, timeout, bad
# response) — an optional formatting pass must never break scaffold
# generation itself.
#
# No hardwired model. Ravi: "my concern is that the LLM would not be
# consistent here at all. we need not have LLM at all. let us generate
# without LLM... remove the wiring to the qwen model. Only when a user or
# myself sets up a LLM using the setup then it can be used." This module
# used to default to a specific host/model (a fixed LAN Ollama host and
# qwen3.8:27b) regardless of what the user configured anywhere else in the
# app — narration now only ever runs against whatever LLM the caller
# explicitly configured via the Setup tab (same LlmSessionConfig used for
# canvas generation), through the shared llm_service.call_llm() dispatch.
# No endpoint/model configured there → no narration, full stop; the plain
# deterministic docs are the only output, which is the actual default.

from __future__ import annotations

import logging

from backend.services.llm_service import call_llm

log = logging.getLogger(__name__)

# A capable model producing a long, detailed document on local hardware can
# take minutes, not seconds — routes.py's own _call_llm() uses 60s for the
# (short, structured-extraction) spec-import path; that would fail here
# every time.
NARRATION_TIMEOUT_S = 600

_STYLE_GUIDE = """House style to match exactly (this is IBM Process Studio's own document
convention — match it precisely, don't invent a different style):

# <Title>

*<italic one-line subtitle describing the project>*

**Target Outcome:** <one line, or omit this field entirely if no such fact
exists in the source material — never invent a metric>

---

## Phase N: <Phase Name>

### N.M <Section Name>

| Column | Column | ... |
|---|---|---|
| ... table rows for structured facts (agents, zones, checks, etc.) ... |

Use tables for anything structured (agent lists, zone breakdowns, check
mappings, checklists-with-status). Use numbered lists for sequential
instructions. Use narrative paragraphs to connect and explain — that
narration is the entire point of this pass, the source material is already
correct but reads as disconnected bullet points today.
"""

_GROUNDING_RULES = """Rules — follow these exactly:
1. Use ONLY facts present in the SOURCE MATERIAL below. Never invent a
   metric, percentage, tool name, config key, file path, or capability that
   isn't explicitly stated in it.
2. If the source material doesn't state something (e.g. no target outcome
   percentage was given), omit that line entirely rather than inventing a
   plausible-sounding placeholder.
3. Reorganize, connect, and narrate — turn disconnected bullet lists into
   flowing prose with real transitions — but do not change what is claimed
   to be true.
4. Preserve every concrete class name, check name, file path, and config key
   from the source material verbatim (e.g. `K9ValidationLoopAgent`,
   `PromptInjectionCheck`, `security.shield.enabled`) — these are exact
   identifiers a reader will search their codebase for for; do not paraphrase them.
5. Output valid Markdown only. No commentary about what you're doing, no
   "Here is the document:" preamble — begin directly with the `#` title.
6. Do not add your own closing divider, sign-off, or "end of document"
   remark — the application appends a standard closing footer after your
   output automatically. End on your document's last substantive content.
"""


def _call(endpoint: str, provider: str, model: str, api_key: str, prompt: str) -> str:
    text = call_llm(endpoint, provider, model, api_key, prompt,
                     timeout=NARRATION_TIMEOUT_S, max_tokens=4096)
    if not text.strip():
        raise ValueError("LLM returned an empty response")
    return text.strip()


def _setup_guide_prompt(app_name: str, readme_source: str, framework_claude_md: str) -> str:
    return f"""You are producing a Solutions Architect-facing setup guide for a generated
software project. {_STYLE_GUIDE}

{_GROUNDING_RULES}

Title this document "{app_name} — Implementation Setup Guide".

=== SOURCE MATERIAL: generated README (setup/run/troubleshooting facts) ===
{readme_source}

=== SOURCE MATERIAL: framework conventions (for correct terminology only —
do not describe framework capabilities not actually used by this project) ===
{framework_claude_md[:6000]}

Produce the complete setup guide now."""


def _implementation_prompt(app_name: str, implementation_plan_source: str, architecture_source: str,
                            manifest_source: str) -> str:
    return f"""You are producing a Solutions Architect-facing implementation guide for a generated
multi-agent software project. {_STYLE_GUIDE}

{_GROUNDING_RULES}

Title this document "{app_name} — Implementation Guide".

Cover, in this order: an executive summary of scope (counts of orchestrators/
squads/agents/adapters, zone breakdown), the input-to-output artifact
mapping, the process traceability (what each process element became and
why), the governance/security patterns actually wired in, and the Solutions
Architect's remaining checklist. Narrate the traceability matrix's rows as
prose grouped by orchestrator, not as one giant table dump — but DO include
the real component names and process IDs.

=== SOURCE MATERIAL: traceability matrix + governance + patterns + checklist ===
{implementation_plan_source}

=== SOURCE MATERIAL: architecture classification rationale ===
{architecture_source}

=== SOURCE MATERIAL: input artifact -> output artifact manifest ===
{manifest_source}

Produce the complete implementation guide now."""


def generate_narrated_docs(
    app_name: str,
    readme_source: str,
    implementation_plan_source: str,
    architecture_source: str,
    manifest_source: str,
    framework_claude_md: str,
    llm_endpoint: str,
    llm_provider: str = "ollama",
    llm_model: str = "",
    llm_api_key: str = "",
) -> dict[str, str] | None:
    """Returns {"setup_guide": md_text, "implementation": md_text}, or None
    if the LLM call failed for any reason — caller must fall back to the
    plain deterministic docs, never hard-fail scaffold generation over an
    optional formatting pass. llm_endpoint/llm_model are required (the
    caller — scaffold_service.py — only calls this at all when the user has
    actually configured an LLM; there is no built-in default model here)."""
    try:
        setup_guide = _call(llm_endpoint, llm_provider, llm_model, llm_api_key,
                             _setup_guide_prompt(app_name, readme_source, framework_claude_md))
        implementation = _call(
            llm_endpoint, llm_provider, llm_model, llm_api_key,
            _implementation_prompt(app_name, implementation_plan_source, architecture_source, manifest_source)
        )
        return {"setup_guide": setup_guide, "implementation": implementation}
    except Exception as exc:  # noqa: BLE001 - any failure here must degrade gracefully
        log.warning("LLM doc narration failed, falling back to deterministic docs: %s", exc)
        return None
