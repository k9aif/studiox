# SPDX-License-Identifier: Apache-2.0
"""Regression tests for agent evaluation plan (-evals.md) parsing and the
tests/evals/*.py stub files scaffold_service.py generates from it.

Uses a small synthetic eval plan (fixtures/claim-intake-evals.md) with the
same ID|Agent|Step|Scenario|Expected|Pass Criteria|Severity table shape as
real evaluation plans, e.g. IBM Process Studio's.
"""

import subprocess
import sys
import py_compile
from pathlib import Path

import pytest

from backend.services.evals_service import looks_like_evals, parse_evals
from backend.services.scaffold_service import _gen_eval_test_files

SAMPLE_EVALS_PATH = Path(__file__).resolve().parent / "fixtures" / "claim-intake-evals.md"


def test_parse_evals_matches_doc_inventory():
    """Every table row is parsed and tagged with its category."""
    text = SAMPLE_EVALS_PATH.read_text()
    assert looks_like_evals(text)

    parsed = parse_evals(text)
    assert parsed["total"] == 6
    assert parsed["counts"] == {
        "functional": 2,
        "behavioral": 1,
        "adversarial": 2,
        "hitl": 1,
    }
    # Every row has the fields _gen_eval_test_files depends on.
    for row in parsed["rows"]:
        assert row["id"], f"row missing id: {row}"
        assert row["category"]


def test_generic_spec_doc_is_not_misread_as_evals():
    """A document that merely mentions one eval-sounding phrase in passing
    must not trip the >=2-heading threshold and get misrouted."""
    text = "# Some Spec\n\n## Behavioral Notes\n\nJust a regular spec doc, not an eval plan.\n"
    assert not looks_like_evals(text)


def test_eval_test_files_compile_and_pass(tmp_path):
    """The whole point: every generated stub must be valid Python and must
    PASS when actually run — not skipped, not erroring on collection. Also
    checks the ATSn -> Task_n resolution against a mapping-document-shaped
    project so a known agent shows up correctly in its docstring."""
    parsed = parse_evals(SAMPLE_EVALS_PATH.read_text())
    project = {
        "agents": [
            {"name": "AssessFraudRiskAgent", "type": "K9ValidationLoopAgent",
             "process_id": "Task_4", "zone": "AMBER", "description": "Score fraud risk"},
        ],
        "squads": [{"name": "ClaimsReviewSquad", "agents": ["AssessFraudRiskAgent"]}],
        "orchestrators": [{"name": "ClaimsReviewOrchestrator", "squads": ["ClaimsReviewSquad"]}],
        "adapters": [],
        "source_evals_rows": parsed["rows"],
    }

    files = _gen_eval_test_files(project, "TestApp", "test_app", "2026-01-01 00:00:00")
    assert files, "expected at least one generated file"
    assert "test_app/tests/evals/__init__.py" in files

    for path, content in files.items():
        rel = Path(path).relative_to("test_app")
        full = tmp_path / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        if full.suffix == ".py":
            py_compile.compile(str(full), doraise=True)

    # FUN-02's Step (ATS4) should resolve to the agent registered against
    # process_id "Task_4" above — proves the ATSn -> Task_n lookup,
    # not just that the file happens to compile.
    functional = (tmp_path / "tests" / "evals" / "test_functional.py").read_text()
    assert "AssessFraudRiskAgent (agent)" in functional

    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(tmp_path / "tests" / "evals"), "-q"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "6 passed" in result.stdout


def test_no_evals_staged_generates_nothing():
    files = _gen_eval_test_files({"source_evals_rows": []}, "App", "app", "2026-01-01 00:00:00")
    assert files == {}
