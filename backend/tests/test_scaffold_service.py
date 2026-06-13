# SPDX-License-Identifier: Apache-2.0
"""Regression tests for the exported scaffold's setup/run self-containment.

The exported scaffold must not reference the canonical generator's
k9_projects/<app>/ layout, and the project-local imports used by
run.sh / setup.sh must actually resolve.
"""

import os
import py_compile
import re
import subprocess
import sys
import zipfile

import pytest

from backend.services.scaffold_service import generate_scaffold, to_snake

FRAMEWORK_DIR = __import__("pathlib").Path(__file__).resolve().parents[4] / "k9-aif-framework"

SAMPLE_PROJECT = {
    "project_name": "Customer Service AI",
    "author": "Test Author",
    "domain": "Customer Service",
    "description": "Regression test scaffold",
    "agents": [
        {"name": "IntakeAgent", "type": "BaseAgent", "model": "general", "pattern": "", "description": "Intake"},
        {"name": "TriageAgent", "type": "K9ValidationLoopAgent", "model": "reasoning", "pattern": "", "description": "Triage"},
    ],
    "squads": [{"name": "TriageSquad", "agents": ["IntakeAgent", "TriageAgent"]}],
    "orchestrators": [{"name": "TriageOrchestrator", "squad": "TriageSquad"}],
}

NO_ORCHESTRATOR_PROJECT = {**SAMPLE_PROJECT, "orchestrators": []}

MULTI_SQUAD_PROJECT = {
    "project_name": "Customer Service AI",
    "author": "Test Author",
    "domain": "Customer Service",
    "description": "Regression test scaffold — multiple squads/orchestrators",
    "agents": [
        {"name": "IntentClassifierAgent", "type": "BaseAgent", "model": "general", "pattern": "", "description": "Classify intent"},
        {"name": "SentimentAgent", "type": "BaseAgent", "model": "general", "pattern": "", "description": "Sentiment"},
        {"name": "KnowledgeBaseAgent", "type": "BaseAgent", "model": "general", "pattern": "", "description": "KB lookup"},
        {"name": "ResponseQualityAgent", "type": "BaseAgent", "model": "general", "pattern": "", "description": "QA"},
    ],
    "squads": [
        {"name": "TriageSquad", "agents": ["IntentClassifierAgent", "SentimentAgent"]},
        {"name": "ResolutionSquad", "agents": ["KnowledgeBaseAgent", "ResponseQualityAgent"]},
    ],
    "orchestrators": [
        {"name": "TriageOrchestrator", "squad": "TriageSquad"},
        {"name": "ResolutionOrchestrator", "squad": "ResolutionSquad"},
    ],
}


CRITIC_ACTOR_PROJECT = {
    "project_name": "Customer Service AI",
    "author": "Test Author",
    "domain": "Customer Service",
    "description": "Regression test scaffold — critic-actor agent",
    "agents": [
        {"name": "WorthinessCriticAgent", "type": "K9CriticActorAgent", "model": "reasoning", "pattern": "", "description": "Critic-actor"},
    ],
    "squads": [{"name": "WorthinessSquad", "agents": ["WorthinessCriticAgent"]}],
    "orchestrators": [{"name": "WorthinessOrchestrator", "squad": "WorthinessSquad"}],
}


@pytest.fixture(autouse=True)
def _no_plantuml_network(monkeypatch):
    """Diagram rendering hits an external PlantUML server — stub it out."""
    monkeypatch.setattr(
        "backend.services.scaffold_service.render_puml_to_png",
        lambda *a, **k: None,
    )


def _generate_and_extract(tmp_path, project):
    buf = generate_scaffold(project)
    with zipfile.ZipFile(buf) as zf:
        zf.extractall(tmp_path)
    app_folder = to_snake(project["project_name"])
    return tmp_path / app_folder


def test_scaffold_has_no_k9_projects_references(tmp_path):
    project_root = _generate_and_extract(tmp_path, SAMPLE_PROJECT)

    offenders = []
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue
        if "k9_projects" in text:
            offenders.append(str(path.relative_to(project_root)))

    assert not offenders, f"k9_projects referenced in: {offenders}"


def test_scaffold_includes_setup_run_requirements(tmp_path):
    project_root = _generate_and_extract(tmp_path, SAMPLE_PROJECT)

    for fname in ("setup.sh", "run.sh", "requirements.txt", ".env", "main.py"):
        assert (project_root / fname).is_file(), f"missing {fname}"

    setup_sh = (project_root / "setup.sh").read_text()
    assert "setup was success" in setup_sh
    assert "Ready to rumble!" in setup_sh
    assert "--verify" in setup_sh

    requirements = (project_root / "requirements.txt").read_text()
    assert "pyyaml" in requirements.lower()


def test_shell_scripts_are_executable_in_zip():
    buf = generate_scaffold(SAMPLE_PROJECT)
    with zipfile.ZipFile(buf) as zf:
        sh_entries = [i for i in zf.infolist() if i.filename.endswith(".sh")]
        assert sh_entries, "no .sh files found in scaffold"
        for info in sh_entries:
            perm = (info.external_attr >> 16) & 0o777
            assert perm == 0o755, f"{info.filename} not marked executable (perm={oct(perm)})"


@pytest.mark.parametrize("project", [SAMPLE_PROJECT, NO_ORCHESTRATOR_PROJECT])
def test_generated_python_files_compile(tmp_path, project):
    project_root = _generate_and_extract(tmp_path, project)

    py_files = list(project_root.rglob("*.py"))
    assert py_files, "no .py files found in scaffold"
    for path in py_files:
        py_compile.compile(str(path), doraise=True)


@pytest.mark.parametrize("project", [SAMPLE_PROJECT, NO_ORCHESTRATOR_PROJECT])
def test_project_local_imports_resolve(tmp_path, project):
    """Mirrors the PROJECT_IMPORT_CHECK that run.sh / setup.sh execute."""
    pytest.importorskip("k9_aif_abb")

    project_root = _generate_and_extract(tmp_path, project)

    run_sh = (project_root / "run.sh").read_text()
    match = re.search(r"^PROJECT_IMPORT_CHECK='(.*)'$", run_sh, re.MULTILINE)
    assert match, "PROJECT_IMPORT_CHECK not found in run.sh"
    check_stmt = match.group(1)

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(project_root), env.get("PYTHONPATH", "")])
    )

    result = subprocess.run(
        [sys.executable, "-c", check_stmt],
        cwd=str(project_root),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "project import ok" in result.stdout


def test_multi_squad_orchestrators_load_independently(tmp_path):
    """Each orchestrator must build only its own squad.

    Regression: SquadLoader.load(path) builds *every* squad defined in the
    YAML file it's given. Pointing every orchestrator at the combined
    config/squads.yaml means an orchestrator whose agent_registry only knows
    its own squad's agents crashes while SquadLoader tries to build the
    *other* squad too. Orchestrators must load from their own per-squad file
    under squads/yaml/.
    """
    pytest.importorskip("k9_aif_abb")

    project_root = _generate_and_extract(tmp_path, MULTI_SQUAD_PROJECT)

    script = (
        "import sys, yaml\n"
        "from pathlib import Path\n"
        "project_root = Path(sys.argv[1])\n"
        "sys.path.insert(0, str(project_root))\n"
        "from orchestrators.triage_orchestrator import TriageOrchestrator\n"
        "from orchestrators.resolution_orchestrator import ResolutionOrchestrator\n"
        "config = yaml.safe_load(open(project_root / 'config' / 'config.yaml'))\n"
        "squads_path = str(project_root / 'config' / 'squads.yaml')\n"
        "for cls in (TriageOrchestrator, ResolutionOrchestrator):\n"
        "    orch = cls(config=config)\n"
        "    orch.start(squads_path)\n"
        "print('squads loaded ok')\n"
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(project_root), env.get("PYTHONPATH", "")])
    )
    env["K9_ENV"] = "development"

    result = subprocess.run(
        [sys.executable, "-c", script, str(project_root)],
        cwd=str(project_root),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "squads loaded ok" in result.stdout


def test_critic_actor_agent_signatures_match_base(tmp_path):
    """Generated K9CriticActorAgent subclasses must accept the same number of
    positional arguments as BaseCriticActorAgent's abstract methods.

    BaseCriticActorAgent.execute() calls these methods positionally (e.g.
    self.should_accept(feedback, ctx)), so parameter *names* may legitimately
    differ (e.g. "draft" vs "output") but arity must match.

    Regression: the generated should_accept(self, output, critique, ctx) had
    an extra leading parameter, so the positional call
    self.should_accept(feedback, ctx) left ctx unbound at runtime —
    TypeError: should_accept() missing 1 required positional argument: 'ctx'.
    """
    pytest.importorskip("k9_aif_abb")

    project_root = _generate_and_extract(tmp_path, CRITIC_ACTOR_PROJECT)

    script = (
        "import inspect, sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from k9_aif_abb.k9_agents.critic_actor import BaseCriticActorAgent\n"
        "from agents.src.worthiness_critic_agent import WorthinessCriticAgent\n"
        "for name in ('generate', 'critique', 'refine', 'should_accept', 'finalize'):\n"
        "    base = list(inspect.signature(getattr(BaseCriticActorAgent, name)).parameters)\n"
        "    sub = list(inspect.signature(getattr(WorthinessCriticAgent, name)).parameters)\n"
        "    assert len(sub) == len(base), f'{name}: expected {len(base)} params {base}, got {len(sub)} params {sub}'\n"
        "print('signatures ok')\n"
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(project_root), env.get("PYTHONPATH", "")])
    )

    result = subprocess.run(
        [sys.executable, "-c", script, str(project_root)],
        cwd=str(project_root),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "signatures ok" in result.stdout


@pytest.mark.skipif(
    not (FRAMEWORK_DIR / "k9_aif_abb").is_dir(),
    reason="k9-aif-framework checkout not found alongside k9x-ecosystem",
)
def test_setup_sh_verify(tmp_path):
    """End-to-end: setup.sh --verify against a real framework checkout."""
    project_root = _generate_and_extract(tmp_path, SAMPLE_PROJECT)

    env_path = project_root / ".env"
    env_text = env_path.read_text()
    env_text = re.sub(
        r"^#?\s*K9_FRAMEWORK_PATH=.*$",
        f'K9_FRAMEWORK_PATH="{FRAMEWORK_DIR}"',
        env_text,
        count=1,
        flags=re.MULTILINE,
    )
    env_path.write_text(env_text)

    env = os.environ.copy()
    env["VIRTUAL_ENV"] = sys.prefix
    bin_dir = str(__import__("pathlib").Path(sys.executable).parent)
    env["PATH"] = os.pathsep.join([bin_dir, env.get("PATH", "")])

    result = subprocess.run(
        ["bash", "setup.sh", "--verify"],
        cwd=str(project_root),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "setup was success" in result.stdout
    assert "Ready to rumble!" in result.stdout
