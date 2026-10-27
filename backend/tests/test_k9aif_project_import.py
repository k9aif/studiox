# SPDX-License-Identifier: Apache-2.0
"""Import K9-AIF project: an existing application drawn from its own code.

Property: the canvas suggestion matches the project's files exactly (every squad
an orchestrator names, every agent a squad names, every gate in the process
model), and nothing is invented. Fixture: a small project in the DAS shape,
including a squad shared through a project base orchestrator.
"""

import io
import zipfile

import pytest

from backend.services.k9aif_project_service import (
    ProjectImportError, files_from_github, files_from_zip, parse_github_url, parse_k9aif_project, wanted,
)

FILES = {
    "src/app/squads/yaml/draft_squad.yaml": """
squads:
  DraftSquad:
    description: Drafts the document.
    agents: [WriterAgent, CheckerAgent]
""",
    "src/app/squads/yaml/gate_squad.yaml": """
squads:
  GateSquad:
    agents: [ScorerAgent]
""",
    "src/app/squads/yaml/review_squad.yaml": """
squads:
  ReviewSquad:
    agents: [ReviewerAgent]
""",
    "src/app/agents/yaml/writer_agent.yaml": "name: WriterAgent\nclass: WriterAgent\nmodel: package_synthesis\ndescription: Writes.\n",
    "src/app/agents/yaml/checker_agent.yaml": "name: CheckerAgent\nclass: CheckerAgent\nmodel: reasoning\n",
    "src/app/agents/yaml/scorer_agent.yaml": "name: ScorerAgent\nclass: ScorerAgent\nmodel: reasoning\n",
    "src/app/agents/src/checker_agent.py": "class CheckerAgent(K9ValidationLoopAgent):\n    pass\n",
    "src/app/orchestrators/stage_base.py": """
class StageOrchestrator(BaseOrchestrator):
    def prepare_gate(self):
        return self._load_squad("gate_squad.yaml", "GateSquad")
""",
    "src/app/orchestrators/draft_orchestrator.py": """
class DraftOrchestrator(StageOrchestrator):
    def execute_flow(self, payload):
        self._load_squad("draft_squad.yaml", "DraftSquad")
""",
    "src/app/orchestrators/review_orchestrator.py": """
class ReviewOrchestrator(StageOrchestrator):
    def execute_flow(self, payload):
        self._load_squad("review_squad.yaml", "ReviewSquad")
""",
    "src/app/routers/app_router.py": "class AppRouter(BaseRouter):\n    pass\n",
    "src/app/config/process_model.yaml": """
process_model:
  id: pm-1
  as_of: "2026-10-01"
  stages:
    - {id: DRAFT, kind: agents, owner: draft}
    - {id: DRAFT-GATE, title: Draft approval, kind: gate, owner: draft}
    - {id: REVIEW, kind: agents, owner: review}
    - {id: SIDE-GATE, title: Side review, kind: gate, owner: draft, parallel: true}
    - {id: FINAL, title: Final review, kind: gate, owner: review}
  gates:
    DRAFT-GATE: {approval_starts: review, authority: Board, blocking: true, entry_criteria: [a, b]}
    SIDE-GATE: {approval_starts: null, blocking: false}
    FINAL: {approval_starts: null, blocking: true}
""",
    "tests/test_x.py": "class Junk(BaseOrchestrator):\n    pass\n",
}


def _parse():
    return parse_k9aif_project({p: t for p, t in FILES.items() if wanted(p)}, {"name": "demo"})


def test_structure_matches_the_files():
    r = _parse()
    s = r["suggestion"]
    assert s["router"] == "AppRouter"
    # The project base orchestrator is not drawn; its squad is shared by both stages
    assert [(o["name"], o["squads"]) for o in s["orchestrators"]] == [
        ("DraftOrchestrator", ["DraftSquad", "GateSquad"]),
        ("ReviewOrchestrator", ["ReviewSquad", "GateSquad"]),
    ]
    assert {a["name"] for a in s["agents"]} == {"WriterAgent", "CheckerAgent", "ScorerAgent", "ReviewerAgent"}
    assert r["counts"] == {"orchestrators": 2, "squads": 3, "agents": 4, "gates": 3, "files_read": 12}


def test_agent_type_and_model_come_from_the_code():
    agents = {a["name"]: a for a in _parse()["suggestion"]["agents"]}
    assert agents["CheckerAgent"]["type"] == "K9ValidationLoopAgent"
    assert agents["WriterAgent"]["type"] == "BaseAgent"
    assert agents["WriterAgent"]["model"] == "package_synthesis"


def test_gates_from_the_process_model():
    gates = {g["id"]: g for g in _parse()["suggestion"]["gates"]}
    assert gates["DRAFT-GATE"]["orchestrator"] == "DraftOrchestrator"
    assert gates["DRAFT-GATE"]["starts_orchestrator"] == "ReviewOrchestrator"
    assert gates["DRAFT-GATE"]["criteria_count"] == 2
    assert gates["SIDE-GATE"]["parallel"] is True and gates["SIDE-GATE"]["starts_orchestrator"] is None
    assert gates["FINAL"]["starts_run"] is None


def test_nothing_invented_is_reported():
    # ReviewerAgent has no agent YAML: drawn, and said so
    assert "Agent ReviewerAgent has no agent YAML" in _parse()["warnings"]


def test_not_a_k9aif_project():
    with pytest.raises(ProjectImportError):
        parse_k9aif_project({"src/app/agents/yaml/a.yaml": "name: A\nclass: A\n"}, {})


def test_zip_source_reads_only_project_files():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for p, t in FILES.items():
            zf.writestr(p, t)
        zf.writestr("README.md", "x")
    files = files_from_zip(buf.getvalue())
    assert "README.md" not in files and "tests/test_x.py" not in files
    assert parse_k9aif_project(files, {})["counts"]["orchestrators"] == 2


def test_github_url_only_github():
    assert parse_github_url("https://github.com/k9aif/dow-k9x")["repo"] == "dow-k9x"
    assert parse_github_url("https://github.com/o/r/tree/main/src/app")["subdir"] == "src/app"
    for bad in ("https://evil.example/o/r", "http://github.com/o/r", "https://github.com/o"):
        with pytest.raises(ProjectImportError):
            parse_github_url(bad)


def test_github_source_records_the_commit():
    calls = []

    def http_json(url):
        calls.append(url)
        if url.endswith("/repos/o/r"):
            return {"default_branch": "main"}
        if "/commits/" in url:
            return {"sha": "abc1234def", "commit": {"committer": {"date": "2026-10-27T10:00:00Z"}}}
        return {"tree": [{"path": p, "type": "blob", "size": len(t)} for p, t in FILES.items()]}

    def http_text(url):
        path = url.split("/abc1234def/", 1)[1]
        return FILES[path]

    files, source = files_from_github("https://github.com/o/r", http_json, http_text)
    assert source["commit_short"] == "abc1234" and source["repo"] == "github.com/o/r"
    assert all(u.startswith("https://api.github.com/") for u in calls)
    assert parse_k9aif_project(files, source)["counts"]["gates"] == 3


def test_shared_list_and_document(tmp_path, monkeypatch):
    """A GitHub import is shared (listed, reopened by id); a re-import refreshes
    the same entry; the live link is kept only on an allowed host; the
    architecture document carries the gates and the shared squad."""
    from fastapi.testclient import TestClient
    import backend.services.k9aif_project_service as svc
    from backend.main import app

    monkeypatch.setenv("K9X_PROJECTS_ROOT", str(tmp_path))

    def fake_github(url):
        files = {p: t for p, t in FILES.items() if wanted(p)}
        return files, {"kind": "github", "repo": "github.com/o/demo", "url": "https://github.com/o/demo",
                       "commit_short": "abc1234", "name": "demo"}

    monkeypatch.setattr(svc, "files_from_github", fake_github)
    client = TestClient(app)

    r = client.post("/api/k9aif-project/import", data={"repo_url": "https://github.com/o/demo",
                                                         "live_url": "https://demo.k9x.ai"})
    assert r.status_code == 200, r.text
    assert r.json()["live_url"] == "https://demo.k9x.ai"
    r = client.post("/api/k9aif-project/import", data={"repo_url": "https://github.com/o/demo",
                                                         "live_url": "https://evil.example"})
    assert r.json()["live_url"] == ""

    listed = client.get("/api/k9aif-project/shared").json()["projects"]
    assert [p["id"] for p in listed] == ["o__demo"]
    record = client.get("/api/k9aif-project/shared/o__demo").json()
    assert record["counts"]["gates"] == 3
    assert client.get("/api/k9aif-project/shared/nope").status_code == 404
    for bad in ("../etc", "a/b", ""):
        with pytest.raises(ProjectImportError):
            svc.load_shared(str(tmp_path), bad)

    doc = client.post("/api/k9aif-project/document", json=record)
    assert doc.status_code == 200
    text = doc.text
    assert "| Draft approval | DraftOrchestrator | Board | Yes | 2 | ReviewOrchestrator |" in text
    assert "Run by: DraftOrchestrator, ReviewOrchestrator" in text   # GateSquad, shared
