# SPDX-License-Identifier: Apache-2.0
# Process Studio's companion Agent Evaluation Plan (filename suffix
# "-evals.md") parser — Functional/Behavioral/Adversarial/Domain/Failure
# Mode/HITL/Observability/Regression test-case tables.
#
# Deterministic table parsing, no LLM — same rule as bpmn_service.py and
# blueprint_service.py (see blueprint_service.py's module docstring). Reuses
# blueprint_service.py's generic _table_under_heading() (heading -> markdown
# table, keyed by the table's own header row) rather than duplicating it —
# every category table here has the same ID|Agent|Step|Scenario|Expected|
# Pass Criteria|Severity shape.

from __future__ import annotations

import re

from backend.services.blueprint_service import _table_under_heading
from backend.services.shield_catalog import coverage_for_row

_CATEGORY_HEADINGS: dict[str, re.Pattern] = {
    "functional":    re.compile(r"^#{1,4}\s*Functional Evals", re.I | re.M),
    "behavioral":    re.compile(r"^#{1,4}\s*Behavioral Evals", re.I | re.M),
    "adversarial":   re.compile(r"^#{1,4}\s*Adversarial Evals", re.I | re.M),
    "domain":        re.compile(r"^#{1,4}\s*Domain Evals", re.I | re.M),
    "failure_mode":  re.compile(r"^#{1,4}\s*Failure Mode\s*(?:&|and)\s*Fallback Testing", re.I | re.M),
    "hitl":          re.compile(r"^#{1,4}\s*Human-in-the-Loop Validation", re.I | re.M),
    "observability": re.compile(r"^#{1,4}\s*Observability Validation", re.I | re.M),
    "regression":    re.compile(r"^#{1,4}\s*Regression Baseline Lock", re.I | re.M),
}

_TITLE_PATTERN = re.compile(r"^#\s*Agent Evaluation Plan", re.I | re.M)
_MIN_HEADINGS_FOR_EVALS = 2


def looks_like_evals(content: str) -> bool:
    """Content-based role detection, same approach as
    blueprint_service.looks_like_blueprint() — the title heading is
    sufficient on its own; otherwise require >=2 category headings so a
    document that merely mentions "Behavioral Evals" in passing (e.g. an
    EAEF blueprint's own Phase 4 summary) isn't misread as an eval plan."""
    if _TITLE_PATTERN.search(content):
        return True
    hits = sum(1 for pat in _CATEGORY_HEADINGS.values() if pat.search(content))
    return hits >= _MIN_HEADINGS_FOR_EVALS


def parse_evals(content: str) -> dict:
    """Every eval-case row across all category tables, tagged with its
    category. Rows are read by header name (ID/Agent/Step/Scenario/
    Expected/Pass Criteria/Severity), not column position, so a reordered
    or slightly renamed column doesn't silently misalign data — same
    defensive approach as blueprint_service.py's table parsing.
    """
    rows: list[dict] = []
    for category, heading in _CATEGORY_HEADINGS.items():
        for r in _table_under_heading(content, heading):
            scenario = r.get("Scenario", "").strip()
            rows.append({
                "category": category,
                "id": r.get("ID", "").strip(),
                "agent": r.get("Agent", "").strip(),
                "step": r.get("Step", "").strip(),
                "scenario": scenario,
                "expected": r.get("Expected", "").strip(),
                "pass_criteria": r.get("Pass Criteria", "").strip(),
                "severity": r.get("Severity", "").strip(),
                # k9x_Shield checks (or explicitly "not a Shield check")
                # that already realize this test case, if any — see
                # shield_catalog.py. None for every category except
                # Adversarial, where Process Studio's own scenario labels
                # match a verified framework check 1:1.
                "framework_coverage": coverage_for_row(category, scenario),
            })

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1

    return {"rows": rows, "counts": counts, "total": len(rows)}
