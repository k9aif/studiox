# SPDX-License-Identifier: Apache-2.0
# Existing K9-AIF application -> canvas suggestion ("Import K9-AIF project")
#
# The other intake paths design a NEW system from a BPMN, blueprint or spec.
# This one draws a system that already exists, from its own files: squad YAML,
# agent YAML, the orchestrator/router Python sources and, when the project has
# one, a process model with HIL gates (dow-k9-aif's config/process_model.yaml).
# Rule-based only, no LLM: the canvas must show exactly what the code says, so
# re-importing after a change shows the change.
#
# Reading rules (each one is what the K9-AIF conventions guarantee):
#   - a squad is a YAML file with a top-level `squads:` map of {agents: [...]}
#   - an agent config is a YAML file with `class:` (and role/goal/module)
#   - an orchestrator is a project class whose ancestry reaches BaseOrchestrator;
#     the squads it runs are the squad YAML files it names (an orchestrator knows
#     only squads, K9-DEC-002), plus those named by its project base classes. A
#     project base class that other orchestrators extend is not drawn itself.
#   - the router is a project class whose ancestry reaches BaseRouter
#   - gates come from process_model.yaml: `stages` (kind: gate, owner) and
#     `gates` (authority, blocking, hil_queue, approval_starts)

from __future__ import annotations

import io
import json
import re
import urllib.error
import urllib.request
import zipfile
from pathlib import PurePosixPath
from typing import Optional

import yaml

MAX_FILES = 600
MAX_FILE_BYTES = 512 * 1024

_CLASS_RE = re.compile(r"^class\s+(\w+)\s*(?:\(([^)]*)\))?\s*:", re.M)
_YAML_LITERAL_RE = re.compile(r"""["']([\w\-./]+\.ya?ml)["']""")

_LOOP_BASES = {"K9ValidationLoopAgent", "BaseValidationLoopAgent", "K9PlanningLoopAgent"}
_CRITIC_BASES = {"K9CriticActorAgent", "BaseCriticActorAgent"}


class ProjectImportError(ValueError):
    """The input is not a K9-AIF project this importer can read."""


# ── Which files matter ───────────────────────────────────────────────────────

def wanted(path: str) -> bool:
    """Files the parser reads: squad/agent YAML, the process model, and Python
    sources of orchestrators, routers and agents. Tests and examples are not
    part of the running application."""
    p = path.lower()
    parts = PurePosixPath(p).parts
    if any(seg in ("tests", "test", "examples", "node_modules", ".venv", "venv", "__pycache__") for seg in parts):
        return False
    if p.endswith(("process_model.yaml", "process_model.yml")):
        return True
    if p.endswith((".yaml", ".yml")):
        return any(seg in ("squads", "agents") for seg in parts)
    if p.endswith(".py"):
        return any(seg in ("orchestrators", "routers", "agents", "squads") for seg in parts)
    return False


# ── Sources: zip upload, GitHub repository ───────────────────────────────────

def files_from_zip(raw: bytes) -> dict[str, str]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise ProjectImportError("Not a valid .zip file") from exc
    files: dict[str, str] = {}
    for info in zf.infolist():
        if info.is_dir() or not wanted(info.filename) or info.file_size > MAX_FILE_BYTES:
            continue
        files[info.filename] = zf.read(info).decode("utf-8", errors="replace")
        if len(files) > MAX_FILES:
            raise ProjectImportError(f"More than {MAX_FILES} matching files; zip the application folder only")
    return files


_GITHUB_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?"
    r"(?:/tree/(?P<ref>[\w.\-]+)(?:/(?P<subdir>[\w.\-/]+?))?)?/?$"
)


def parse_github_url(url: str) -> dict:
    m = _GITHUB_URL_RE.match(url.strip())
    if not m:
        raise ProjectImportError("Use a public GitHub repository URL: https://github.com/<owner>/<repo>")
    return {k: v for k, v in m.groupdict().items()}


def _http_json(url: str, timeout: float = 20.0):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "k9x-studio"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ProjectImportError("Repository or branch not found (is it public?)") from exc
        if exc.code == 403:
            raise ProjectImportError("GitHub API rate limit reached; try again later or upload a .zip") from exc
        raise


def _http_text(url: str, timeout: float = 20.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "k9x-studio"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(MAX_FILE_BYTES + 1).decode("utf-8", errors="replace")


def files_from_github(url: str, http_json=_http_json, http_text=_http_text) -> tuple[dict[str, str], dict]:
    """The matching files of a public repository at one commit, plus where they
    came from. Hosts are fixed (api.github.com, raw.githubusercontent.com), so a
    URL can't point the server anywhere else."""
    g = parse_github_url(url)
    owner, repo, subdir = g["owner"], g["repo"], (g.get("subdir") or "").strip("/")
    ref = g.get("ref") or http_json(f"https://api.github.com/repos/{owner}/{repo}")["default_branch"]
    commit = http_json(f"https://api.github.com/repos/{owner}/{repo}/commits/{ref}")
    sha = commit["sha"]
    tree = http_json(f"https://api.github.com/repos/{owner}/{repo}/git/trees/{sha}?recursive=1")
    paths = [t["path"] for t in tree.get("tree", [])
             if t.get("type") == "blob" and t.get("size", 0) <= MAX_FILE_BYTES
             and (not subdir or t["path"].startswith(subdir + "/")) and wanted(t["path"])]
    if len(paths) > MAX_FILES:
        raise ProjectImportError(f"More than {MAX_FILES} matching files; point the URL at the application folder")
    files = {p: http_text(f"https://raw.githubusercontent.com/{owner}/{repo}/{sha}/{p}") for p in paths}
    source = {
        "kind": "github",
        "repo": f"github.com/{owner}/{repo}",
        "url": f"https://github.com/{owner}/{repo}" + (f"/tree/{ref}/{subdir}" if subdir else ""),
        "ref": ref,
        "commit": sha,
        "commit_short": sha[:7],
        "commit_date": ((commit.get("commit") or {}).get("committer") or {}).get("date", ""),
        "name": repo,
    }
    return files, source


# ── Parsing ──────────────────────────────────────────────────────────────────

def _load_yaml(text: str):
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return None


def _python_classes(files: dict[str, str]) -> dict[str, dict]:
    """Every top-level class: its bases and its body text (up to the next
    top-level class), which is where an orchestrator names its squad files."""
    classes: dict[str, dict] = {}
    for path, text in files.items():
        if not path.endswith(".py"):
            continue
        matches = list(_CLASS_RE.finditer(text))
        for i, m in enumerate(matches):
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            bases = [b.strip().split(".")[-1].split("[")[0] for b in (m.group(2) or "").split(",") if b.strip()]
            classes[m.group(1)] = {"bases": bases, "body": text[m.start():body_end], "path": path}
    return classes


def _ancestry(name: str, classes: dict[str, dict], seen: Optional[set] = None) -> set[str]:
    """All base names reachable from a class, following project classes."""
    seen = seen if seen is not None else set()
    for base in classes.get(name, {}).get("bases", []):
        if base not in seen:
            seen.add(base)
            _ancestry(base, classes, seen)
    return seen


def _agent_type(class_name: str, classes: dict[str, dict]) -> str:
    anc = _ancestry(class_name, classes)
    if anc & _LOOP_BASES:
        return "K9ValidationLoopAgent"
    if anc & _CRITIC_BASES:
        return "K9CriticActorAgent"
    return "BaseAgent"


def _text(value) -> str:
    return " ".join(str(value or "").split())


def parse_k9aif_project(files: dict[str, str], source: Optional[dict] = None) -> dict:
    source = dict(source or {})
    if not files:
        raise ProjectImportError("No K9-AIF files found (squads/, agents/, orchestrators/, routers/)")

    # Squads
    squads: dict[str, dict] = {}
    squad_files: dict[str, list[str]] = {}
    agent_cfgs: dict[str, dict] = {}
    process_model: Optional[dict] = None
    for path, text in files.items():
        if not path.endswith((".yaml", ".yml")):
            continue
        data = _load_yaml(text)
        if not isinstance(data, dict):
            continue
        if isinstance(data.get("process_model"), dict):
            process_model = data["process_model"]
            continue
        if isinstance(data.get("squads"), dict):
            base = PurePosixPath(path).name
            for sq_name, sq in data["squads"].items():
                if not isinstance(sq, dict):
                    continue
                squads[sq_name] = {"name": sq_name, "agents": [str(a) for a in sq.get("agents") or []],
                                   "description": _text(sq.get("description")), "file": base}
                squad_files.setdefault(base, []).append(sq_name)
        elif data.get("class"):
            agent_cfgs[str(data.get("name") or data["class"])] = data

    if not squads:
        raise ProjectImportError("No squad YAML found (a YAML file with a top-level `squads:` map)")

    classes = _python_classes(files)

    # Orchestrators: project classes reaching BaseOrchestrator
    orch_classes = [n for n in classes
                    if any("Orchestrator" in b for b in _ancestry(n, classes)) and n != "BaseOrchestrator"]
    project_bases = {b for n in orch_classes for b in classes[n]["bases"] if b in orch_classes}

    def own_squads(name: str) -> list[str]:
        body = classes[name]["body"]
        found: list[str] = []
        for m in _YAML_LITERAL_RE.finditer(body):
            fname = PurePosixPath(m.group(1)).name
            in_file = squad_files.get(fname, [])
            named = [s for s in in_file if re.search(rf"""["']{re.escape(s)}["']""", body)]
            for s in (named or in_file):
                if s not in found:
                    found.append(s)
        return found

    def all_squads(name: str) -> list[str]:
        result = own_squads(name)
        for base in classes[name]["bases"]:
            if base in classes and base in orch_classes:
                result += [s for s in all_squads(base) if s not in result]
        return result

    orchestrators = [{"name": n, "squads": all_squads(n)} for n in orch_classes if n not in project_bases]

    routers = [n for n in classes if "BaseRouter" in _ancestry(n, classes)]

    # Agents: every agent a squad names, with its YAML config where there is one
    agents: list[dict] = []
    seen_agents: set[str] = set()
    for sq in squads.values():
        for a in sq["agents"]:
            if a in seen_agents:
                continue
            seen_agents.add(a)
            cfg = agent_cfgs.get(a, {})
            cls = str(cfg.get("class") or a)
            agents.append({
                "name": a,
                "type": _agent_type(cls, classes),
                "model": str(cfg.get("model") or "general"),
                "description": _text(cfg.get("description") or cfg.get("goal")),
                "has_config": bool(cfg),
            })

    # Gates and orchestrator order from the process model
    gates: list[dict] = []
    pm_meta: Optional[dict] = None
    if process_model:
        stages = [s for s in process_model.get("stages") or [] if isinstance(s, dict)]
        gate_defs = process_model.get("gates") or {}

        def orch_for_owner(owner: str) -> Optional[str]:
            o = (owner or "").lower().replace("-", "").replace("_", "")
            for orch in orchestrators:
                if orch["name"].lower().startswith(o) and o:
                    return orch["name"]
            return None

        def stage_for_run(run: str) -> Optional[dict]:
            r = (run or "").lower().replace("-", "_")
            exact = [s for s in stages if str(s.get("id", "")).lower().replace("-", "_") == r]
            prefix = [s for s in stages if str(s.get("id", "")).lower().replace("-", "_").startswith(r)]
            return (exact or prefix or [None])[0]

        for st in stages:
            if st.get("kind") != "gate":
                continue
            gid = str(st.get("id"))
            g = gate_defs.get(gid) or {}
            starts = g.get("approval_starts")
            starts_stage = stage_for_run(starts) if starts else None
            gates.append({
                "id": gid,
                "title": _text(st.get("title") or gid),
                "orchestrator": orch_for_owner(st.get("owner", "")),
                "authority": _text(g.get("authority")),
                "blocking": bool(g.get("blocking", True)),
                "parallel": bool(st.get("parallel", False)),
                "hil_queue": g.get("hil_queue", ""),
                "hil_location": " / ".join(x for x in (g.get("hil_application"), g.get("hil_queue_name")) if x),
                "criteria_count": len(g.get("entry_criteria") or []),
                "starts_run": starts,
                "starts_orchestrator": orch_for_owner(starts_stage.get("owner", "")) if starts_stage else None,
                "decision_record": _text(g.get("decision_record")),
            })

        order = []
        for st in stages:
            o = orch_for_owner(st.get("owner", ""))
            if o and o not in order:
                order.append(o)
        orchestrators.sort(key=lambda o: order.index(o["name"]) if o["name"] in order else len(order))
        pm_meta = {
            "id": process_model.get("id", ""),
            "as_of": str(process_model.get("as_of", "")),
            "pathway": _text(process_model.get("pathway_title") or process_model.get("pathway")),
            "designed_not_built": len(process_model.get("designed") or []),
        }

    wired = {s for o in orchestrators for s in o["squads"]}
    warnings = [f"Squad {s} is defined but no orchestrator names it" for s in squads if s not in wired]
    warnings += [f"Agent {a['name']} has no agent YAML" for a in agents if not a["has_config"]]

    name = source.get("name") or "K9-AIF Project"
    return {
        "suggestion": {
            "router": routers[0] if routers else "K9EventRouter",
            "orchestrators": orchestrators,
            "squads": [squads[s] for s in squads if s in wired] + [squads[s] for s in squads if s not in wired],
            "agents": agents,
            "gates": gates,
        },
        "process_model": pm_meta,
        "source": source,
        "process_name": name,
        "counts": {
            "orchestrators": len(orchestrators),
            "squads": len(squads),
            "agents": len(agents),
            "gates": len(gates),
            "files_read": len(files),
        },
        "warnings": warnings,
    }


# ── Shared imports: what any visitor imported from GitHub, listed for everyone ─
#
# Stored under <K9X_PROJECTS_ROOT>/imported/, one JSON per repository (a
# re-import refreshes it). Only GitHub imports are shared: a .zip may be
# private. Capped, and a live-site link is only kept on an allowed host, since
# anyone with the demo login can import.

MAX_SHARED = 50


def _shared_dir(root: str):
    from pathlib import Path
    d = Path(root or ".") / "imported"
    d.mkdir(parents=True, exist_ok=True)
    return d


def shared_id(source: dict) -> str:
    return re.sub(r"[^\w.-]+", "__", (source.get("repo") or "").replace("github.com/", ""))


def allowed_live_url(url: str, hosts: str) -> str:
    """The live-site URL if it is https on an allowed host (or a subdomain of
    one), else ""."""
    from urllib.parse import urlparse
    u = urlparse((url or "").strip())
    host = (u.hostname or "").lower()
    allowed = [h.strip().lower() for h in (hosts or "").split(",") if h.strip()]
    if u.scheme == "https" and any(host == h or host.endswith("." + h) for h in allowed):
        return u.geturl()
    return ""


def save_shared(root: str, record: dict) -> str:
    from datetime import datetime, timezone
    pid = shared_id(record.get("source") or {})
    if not pid:
        raise ProjectImportError("Only GitHub imports are shared")
    d = _shared_dir(root)
    path = d / f"{pid}.json"
    if not path.exists() and len(list(d.glob("*.json"))) >= MAX_SHARED:
        raise ProjectImportError(f"The shared list is full ({MAX_SHARED} projects)")
    record = {**record, "id": pid, "imported_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    path.write_text(json.dumps(record, indent=1), encoding="utf-8")
    return pid


def list_shared(root: str) -> list[dict]:
    items = []
    for p in _shared_dir(root).glob("*.json"):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        src = r.get("source") or {}
        items.append({
            "id": r.get("id"), "name": r.get("process_name"), "repo": src.get("repo"), "url": src.get("url"),
            "commit_short": src.get("commit_short"), "commit_date": src.get("commit_date"),
            "live_url": r.get("live_url", ""), "imported_at": r.get("imported_at"),
            "counts": r.get("counts"), "process_model": r.get("process_model"),
        })
    return sorted(items, key=lambda i: (i["name"] or "").lower())


def load_shared(root: str, pid: str) -> dict:
    if not re.fullmatch(r"[\w.-]+", pid or ""):
        raise ProjectImportError("Unknown project")
    path = _shared_dir(root) / f"{pid}.json"
    if not path.is_file():
        raise ProjectImportError("Unknown project")
    return json.loads(path.read_text(encoding="utf-8"))


# ── Architecture document (Markdown) from an import ──────────────────────────

def _cell(text) -> str:
    return str(text or "").replace("|", "\\|").replace("\n", " ") or "-"


def _mid(name: str) -> str:
    return re.sub(r"\W", "_", name)


def architecture_markdown(record: dict) -> str:
    s = record.get("suggestion") or {}
    src = record.get("source") or {}
    pm = record.get("process_model") or {}
    c = record.get("counts") or {}
    name = record.get("process_name") or "K9-AIF application"
    agents = {a["name"]: a for a in s.get("agents", [])}
    squads = {q["name"]: q for q in s.get("squads", [])}
    out = [f"# {name}: architecture", ""]

    where = src.get("url") and f"[{src.get('repo')}]({src['url']})" or src.get("repo") or src.get("filename") or "upload"
    facts = [f"- **Source:** {where}" + (f" @ `{src['commit_short']}`" if src.get("commit_short") else "")
             + (f" ({src['commit_date'][:10]})" if src.get("commit_date") else "")]
    if record.get("live_url"):
        facts.append(f"- **Live:** {record['live_url']}")
    if pm:
        facts.append(f"- **Process model:** {pm.get('id')}" + (f", as of {pm['as_of']}" if pm.get("as_of") else "")
                     + (f" ({pm['pathway']})" if pm.get("pathway") else ""))
    facts.append(f"- **Size:** {c.get('orchestrators', 0)} orchestrators, {c.get('squads', 0)} squads, "
                 f"{c.get('agents', 0)} agents, {c.get('gates', 0)} human gates")
    facts.append("- **How this was made:** read from the application's own code by K9X Studio "
                 "(squad and agent YAML, orchestrator and router sources, process model). Nothing inferred.")
    out += facts + [""]

    # Flow diagram (Mermaid renders on GitHub and most Markdown viewers)
    out += ["## Flow", "", "```mermaid", "flowchart LR"]
    router = s.get("router") or "Router"
    out.append(f"  {_mid(router)}[\"{router}\"]")
    for o in s.get("orchestrators", []):
        out.append(f"  {_mid(router)} --> {_mid(o['name'])}[\"{o['name']}\"]")
        for q in o.get("squads", []):
            out.append(f"  {_mid(o['name'])} --> {_mid(q)}([\"{q}\"])")
    for g in s.get("gates", []):
        gid = "gate_" + _mid(g["id"])
        out.append(f"  {gid}{{\"{g.get('title') or g['id']}\"}}")
        if g.get("orchestrator"):
            out.append(f"  {_mid(g['orchestrator'])} -.-> {gid}")
        if g.get("starts_orchestrator"):
            out.append(f"  {gid} -. approval .-> {_mid(g['starts_orchestrator'])}")
    out += ["```", ""]

    out += ["## Orchestrators", "", "| Orchestrator | Squads it runs | Gates it prepares |", "|---|---|---|"]
    for o in s.get("orchestrators", []):
        gates = [g.get("title") or g["id"] for g in s.get("gates", []) if g.get("orchestrator") == o["name"]]
        out.append(f"| {o['name']} | {_cell(', '.join(o.get('squads', [])))} | {_cell(', '.join(gates))} |")
    out.append("")

    if s.get("gates"):
        out += ["## Human gates", "",
                "| Gate | Prepared by | Decides | Blocking | Entry criteria | Approval starts | Decision record |",
                "|---|---|---|---|---|---|---|"]
        for g in s["gates"]:
            blocking = "No (parallel)" if g.get("parallel") else ("Yes" if g.get("blocking") else "No")
            out.append(f"| {_cell(g.get('title') or g['id'])} | {_cell(g.get('orchestrator'))} | {_cell(g.get('authority'))} "
                       f"| {blocking} | {g.get('criteria_count') or '-'} | {_cell(g.get('starts_orchestrator') or 'nothing (records the decision)')} "
                       f"| {_cell(g.get('decision_record'))} |")
        out.append("")

    out += ["## Squads", ""]
    for q in s.get("squads", []):
        users = [o["name"] for o in s.get("orchestrators", []) if q["name"] in o.get("squads", [])]
        out += [f"### {q['name']}", ""]
        if q.get("description"):
            out += [q["description"], ""]
        out += [f"Run by: {', '.join(users) or 'no orchestrator'}", "",
                "| # | Agent | Type | Model | What it does |", "|---|---|---|---|---|"]
        for i, a_name in enumerate(q.get("agents", []), 1):
            a = agents.get(a_name, {})
            out.append(f"| {i} | {a_name} | {a.get('type', 'BaseAgent')} | {a.get('model', '-')} | {_cell(a.get('description'))} |")
        out.append("")

    if record.get("warnings"):
        out += ["## Notes from the import", ""] + [f"- {w}" for w in record["warnings"]] + [""]
    out.append("Generated by K9X Studio (studio.k9x.ai). Re-import to refresh after the code changes.")
    return "\n".join(out) + "\n"
