# SPDX-License-Identifier: Apache-2.0
# k9x_studio — K9-AIF framework context loader
#
# context/ layout:
#   k9_aif_llm_context.md  — curated prompt-injection doc (edit this to update LLM knowledge)
#   CLAUDE.md              — full architecture reference
#   SKILLS.md              — full skills reference
#   k9_aif_abb/            — full ABB source copy (used for RAG / direct lookup)

from pathlib import Path

_CONTEXT_DIR = Path(__file__).resolve().parent.parent.parent / "context"


def get_llm_context() -> str:
    """Return the curated K9-AIF context for LLM prompt injection. Read fresh each call."""
    path = _CONTEXT_DIR / "k9_aif_llm_context.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def get_abb_source(relative_path: str) -> str:
    """Read a specific ABB source file by path relative to k9_aif_abb/.
    Example: get_abb_source('k9_core/agent/base_agent.py')
    Returns empty string if not found.
    """
    path = _CONTEXT_DIR / "k9_aif_abb" / relative_path
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def list_abb_files(pattern: str = "**/*.py") -> list[str]:
    """List all ABB source files matching a glob pattern."""
    base = _CONTEXT_DIR / "k9_aif_abb"
    if not base.exists():
        return []
    return [str(p.relative_to(base)) for p in base.glob(pattern)]


