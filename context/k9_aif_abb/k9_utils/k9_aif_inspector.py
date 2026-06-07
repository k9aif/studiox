# SPDX-License-Identifier: Apache-2.0
# K9-AIF Framework

"""
K9-AIF Inspector
================
Inspects a K9-AIF Solution (SBB) folder for compliance with ABB conventions.

Usage:
    python -m k9_aif_abb.k9_utils.k9_aif_inspector /path/to/solution
    python k9_aif_inspector.py /path/to/solution

Checks:
    1. Solution structure   — required directories and files exist
    2. config.yaml          — inference.router, llm_factory, model_catalog present
    3. squads.yaml          — squads: wrapper, flow steps are dicts with agent: key
    4. Agent Python files   — extend BaseAgent, define layer, implement execute()
    5. Agent YAML files     — required fields: class, name, model, role, goal
    6. Orchestrator files   — extend BaseOrchestrator, implement _load_squad()
    7. llm_invoke import    — SBB wrapper only acceptable if utils/llm_invoke.py exists
"""

import ast
import sys
from pathlib import Path

import yaml

from k9_aif_abb.k9_utils.k9_ascii import print_success, print_failure


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _parse_python(path: Path):
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
        return src, tree, None
    except SyntaxError as exc:
        return src, None, str(exc)


def _has_class_attr(tree, attr_name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id == attr_name:
                            return True
    return False


def _has_method(tree, method_name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return True
    return False


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_structure(solution_dir: Path) -> list:
    issues = []
    required = [
        "agents/src",
        "agents/yaml",
        "config/config.yaml",
        "config/squads.yaml",
        "orchestrators",
    ]
    for rel in required:
        path = solution_dir / rel
        if not path.exists():
            issues.append(f"[STRUCTURE] Missing: {rel}")
    return issues


def check_config(solution_dir: Path) -> list:
    issues = []
    config_path = solution_dir / "config/config.yaml"
    if not config_path.exists():
        return issues  # already caught by structure check

    cfg = _parse_yaml(config_path)
    inference = cfg.get("inference", {})

    if not inference:
        issues.append("[CONFIG] inference: block missing from config.yaml")
        return issues

    # router block
    router = inference.get("router", {})
    if not router:
        issues.append("[CONFIG] inference.router block missing")
    else:
        if not router.get("type"):
            issues.append("[CONFIG] inference.router.type not set")
        if not router.get("default_model"):
            issues.append("[CONFIG] inference.router.default_model not set")
        persistence = router.get("persistence", {})
        if not persistence.get("provider"):
            issues.append("[CONFIG] inference.router.persistence.provider not set")

    # llm_factory
    if not inference.get("llm_factory", {}).get("models"):
        issues.append("[CONFIG] inference.llm_factory.models missing")

    # model_catalog
    if not inference.get("model_catalog", {}).get("models"):
        issues.append("[CONFIG] inference.model_catalog.models missing")

    return issues


def check_squads(solution_dir: Path) -> list:
    issues = []
    squads_path = solution_dir / "config/squads.yaml"
    if not squads_path.exists():
        return issues  # already caught by structure check

    data = _parse_yaml(squads_path)

    if "squads" not in data:
        issues.append("[SQUADS] Missing top-level 'squads:' key in squads.yaml")
        return issues

    for squad_id, cfg in data["squads"].items():
        if not isinstance(cfg, dict):
            issues.append(f"[SQUADS] {squad_id}: configuration must be a mapping")
            continue
        if not cfg.get("orchestrator"):
            issues.append(f"[SQUADS] {squad_id}: missing 'orchestrator' field")
        if not cfg.get("agents"):
            issues.append(f"[SQUADS] {squad_id}: missing 'agents' list")
        flow = cfg.get("flow", [])
        if not flow:
            issues.append(f"[SQUADS] {squad_id}: missing 'flow' list")
        else:
            for i, step in enumerate(flow):
                if not isinstance(step, dict) or "agent" not in step:
                    issues.append(
                        f"[SQUADS] {squad_id}: flow step {i} must be a dict with 'agent:' key "
                        f"(got: {step!r})"
                    )

    return issues


def check_agents(solution_dir: Path) -> list:
    issues = []
    agents_src = solution_dir / "agents/src"
    sbb_llm_invoke_exists = (solution_dir / "utils/llm_invoke.py").exists()

    for path in sorted(agents_src.glob("*.py")):
        if path.name.startswith("_"):
            continue

        src, tree, syntax_err = _parse_python(path)
        if syntax_err:
            issues.append(f"[AGENT] {path.name}: syntax error — {syntax_err}")
            continue

        if "BaseAgent" not in src:
            issues.append(f"[AGENT] {path.name}: does not import or extend BaseAgent")

        if not _has_class_attr(tree, "layer"):
            issues.append(f"[AGENT] {path.name}: missing 'layer' class attribute")

        if not _has_method(tree, "execute"):
            issues.append(f"[AGENT] {path.name}: missing execute() method")

        # llm_invoke import check
        if "llm_invoke" in src:
            sbb_import = any(
                "utils.llm_invoke" in line and "examples." in line
                for line in src.splitlines()
                if "import" in line and "llm_invoke" in line
            )
            if sbb_import and not sbb_llm_invoke_exists:
                issues.append(
                    f"[AGENT] {path.name}: imports llm_invoke from SBB path "
                    f"but utils/llm_invoke.py does not exist in this solution — "
                    f"use k9_aif_abb.k9_utils.llm_invoke instead"
                )

    return issues


def check_agent_yamls(solution_dir: Path) -> list:
    issues = []
    agents_yaml = solution_dir / "agents/yaml"
    required_fields = ["class", "name", "model", "role", "goal"]

    for path in sorted(agents_yaml.glob("*.yaml")):
        data = _parse_yaml(path)
        for field in required_fields:
            if not data.get(field):
                issues.append(f"[AGENT YAML] {path.name}: missing required field '{field}'")

    return issues


def check_orchestrators(solution_dir: Path) -> list:
    issues = []
    orch_dir = solution_dir / "orchestrators"

    for path in sorted(orch_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue

        src, tree, syntax_err = _parse_python(path)
        if syntax_err:
            issues.append(f"[ORCHESTRATOR] {path.name}: syntax error — {syntax_err}")
            continue

        if "BaseOrchestrator" not in src:
            issues.append(f"[ORCHESTRATOR] {path.name}: does not import or extend BaseOrchestrator")

        if not _has_method(tree, "_load_squad"):
            issues.append(f"[ORCHESTRATOR] {path.name}: missing _load_squad() method")

    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def inspect_solution(solution_dir: Path) -> list:
    all_issues = []
    all_issues += check_structure(solution_dir)
    all_issues += check_config(solution_dir)
    all_issues += check_squads(solution_dir)
    all_issues += check_agents(solution_dir)
    all_issues += check_agent_yamls(solution_dir)
    all_issues += check_orchestrators(solution_dir)
    return all_issues


def run_inspector(solution_path: str) -> None:
    solution_dir = Path(solution_path).resolve()

    print(f"\n[K9-AIF Inspector] Inspecting solution: {solution_dir}\n")

    if not solution_dir.exists():
        print(f"ERROR: Solution folder not found: {solution_dir}")
        sys.exit(1)

    issues = inspect_solution(solution_dir)

    if not issues:
        print_success(f"Solution '{solution_dir.name}'")
    else:
        for issue in issues:
            print(f"  ✗ {issue}")
        print(f"\n[SUMMARY] {len(issues)} issue(s) found in '{solution_dir.name}'")
        print_failure(f"Solution '{solution_dir.name}'")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python k9_aif_inspector.py /path/to/solution")
        sys.exit(1)
    run_inspector(sys.argv[1])
