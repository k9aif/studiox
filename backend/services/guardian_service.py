# SPDX-License-Identifier: Apache-2.0
# Mandatory content-safety screen for every file staged into Intake. Ravi:
# "I would love to incorporate granite-guardian to govern and check input
# file. what if a user uploads some nasty file? so, studio, has to use
# guardian mandatory." Reuses the same provider-agnostic call_llm() dispatch
# as narration/canvas-suggestion (backend/services/llm_service.py) so any
# configured endpoint works, not just Ollama+granite-guardian specifically —
# but the model field is expected to be a Granite Guardian model (e.g.
# "granite4.1-guardian:8b") for the verdict framing below to be meaningful.

import re

from backend.services.llm_service import call_llm

_MAX_CHARS = 8000

# Granite Guardian is a fine-tuned classifier, not an instruction-following
# chat model — empirically verified against both a local granite3-guardian
# and the deployed granite4.1-guardian:8b (a LAN Ollama host): it ignores
# custom formatting instructions entirely and always answers yes (risk
# detected) or no (no risk), for whatever text it's given as the user turn.
# So the prompt is just the document itself, not a wrapped instruction —
# asking it to also explain itself or follow a VERDICT: format doesn't
# change that. The exact wrapper differs by model version though: the older
# granite3-guardian answers a bare "Yes"/"No", while granite4.1-guardian:8b
# wraps it as "<score> no </score>" — hence the word-boundary regex below
# instead of a strict prefix match.
_YES_RE = re.compile(r"\byes\b", re.I)
_NO_RE = re.compile(r"\bno\b", re.I)


def check_content_safety(
    endpoint: str, provider: str, model: str, api_key: str, content: str,
    timeout: int = 30,
) -> dict:
    """Returns {checked, safe, reason, raw}. Never raises — a Guardian outage
    is reported in the result, not an exception, so the caller decides how to
    treat "couldn't check" (this app fails closed: unreachable ⇒ blocked,
    matching Ravi's "mandatory")."""
    excerpt = content[:_MAX_CHARS]
    try:
        raw = call_llm(endpoint, provider, model, api_key, excerpt, timeout=timeout, max_tokens=10)
    except Exception as e:
        return {"checked": False, "safe": False, "reason": f"Guardian unreachable: {e}", "raw": ""}

    verdict = (raw or "").strip()
    has_yes, has_no = bool(_YES_RE.search(verdict)), bool(_NO_RE.search(verdict))
    if has_no and not has_yes:
        return {"checked": True, "safe": True, "reason": None, "raw": verdict[:400]}
    if has_yes and not has_no:
        return {"checked": True, "safe": False,
                "reason": "Granite Guardian flagged this content as a risk.",
                "raw": verdict[:400]}
    # Model didn't answer a clear yes/no — fail closed rather than silently
    # waving the file through unreviewed.
    return {"checked": True, "safe": False,
            "reason": "Guardian returned an unexpected response — blocked to be safe.",
            "raw": verdict[:400]}
