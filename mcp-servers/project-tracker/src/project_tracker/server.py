"""Project Tracker MCP Server implementation.

Local file-based research project management: phases, milestones, tasks,
decisions, meetings, and progress briefs.

Supports multiple projects via:
  - ``project_path`` parameter on every tool (explicit per-call targeting)
  - ``set_active_project`` tool (sets a session-wide default)
  - ``PROJECTS_ROOT`` env var (base directory for relative project paths)
  - ``PROJECT_TRACKER_DIR`` / ``PROJECT_DIR`` env vars (legacy single-project fallback)

Storage: {project_root}/project-tracking/ directory with YAML files.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_DIR = os.environ.get("PROJECT_TRACKER_DIR", os.environ.get("PROJECT_DIR", "."))
PROJECTS_ROOT = os.environ.get("PROJECTS_ROOT", "./my_projects")
TRACKING_DIR = "project-tracking"

# Session-level active project (set via set_active_project tool)
_active_project: str | None = None

mcp = FastMCP(
    "project-tracker",
    instructions="Track research project phases, milestones, tasks, decisions, and generate progress briefs",
)


# ---------------------------------------------------------------------------
# Path resolution helpers
# ---------------------------------------------------------------------------

def _resolve_project_dir(project_path: str | None = None, *, must_exist: bool = True) -> Path:
    """Resolve a project directory from the various possible sources.

    Priority order:
      1. Explicit ``project_path`` argument (absolute or relative to PROJECTS_ROOT)
      2. ``_active_project`` module state (set via ``set_active_project``)
      3. ``PROJECT_DIR`` env var (legacy single-project mode)

    Raises ``ValueError`` when *must_exist* is True and the path does not exist.
    """
    raw: str | None = project_path or _active_project or None

    if raw:
        p = Path(raw)
        if not p.is_absolute():
            # Resolve relative paths against PROJECTS_ROOT under PROJECT_DIR.
            p = _resolve_projects_root() / p
        p = p.resolve()
    else:
        # Legacy fallback
        p = Path(PROJECT_DIR).resolve()

    if must_exist and not p.exists():
        raise ValueError(f"Project directory does not exist: {p}")

    return p


def _tracking_path(base_dir: Path | None = None) -> Path:
    """Return the tracking subdirectory for a given project root."""
    if base_dir is None:
        base_dir = _resolve_project_dir()
    return base_dir / TRACKING_DIR


def _resolve_projects_root(*, must_exist: bool = False) -> Path:
    """Resolve PROJECTS_ROOT consistently against PROJECT_DIR when relative."""
    projects_root = Path(PROJECTS_ROOT)
    if not projects_root.is_absolute():
        projects_root = Path(PROJECT_DIR).resolve() / projects_root
    projects_root = projects_root.resolve()

    if must_exist and not projects_root.is_dir():
        raise ValueError(f"Projects directory does not exist: {projects_root}")

    return projects_root


def _load_yaml(filename: str, base_dir: Path | None = None) -> dict[str, Any]:
    path = _tracking_path(base_dir) / filename
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}


def _save_yaml(filename: str, data: dict[str, Any] | list[Any], base_dir: Path | None = None) -> None:
    path = _tracking_path(base_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")


def _strip_empty(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            cleaned = _strip_empty(item)
            if cleaned is None:
                continue
            if cleaned == "" or cleaned == [] or cleaned == {}:
                continue
            result[key] = cleaned
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            cleaned = _strip_empty(item)
            if cleaned is None:
                continue
            if cleaned == "" or cleaned == [] or cleaned == {}:
                continue
            result.append(cleaned)
        return result
    if isinstance(value, str):
        return value.strip()
    return value


def _normalize_affiliation(value: Any) -> dict[str, Any]:
    if isinstance(value, list) and value:
        value = value[0]
    if not isinstance(value, dict):
        return {}
    return _strip_empty(
        {
            "name": value.get("name", ""),
            "city": value.get("city", ""),
            "state": value.get("state", value.get("region", "")),
            "country": value.get("country", ""),
            "url": value.get("url", ""),
        }
    )


def _normalize_authors(
    authors: list[dict[str, Any]] | None,
    pi: str,
    team: list[str] | None,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for author in authors or []:
        if not isinstance(author, dict):
            continue

        cleaned = _strip_empty(
            {
                "name": author.get("name", ""),
                "credentials": author.get("credentials", ""),
                "author_id": author.get("author_id", ""),
                "corresponding": bool(author.get("corresponding", False)),
                "email": author.get("email", ""),
                "orcid": author.get("orcid", ""),
                "profile_url": author.get("profile_url", author.get("url", "")),
                "affiliation": _normalize_affiliation(author.get("affiliation", {})),
            }
        )
        if cleaned.get("name"):
            normalized.append(cleaned)

    if not normalized:
        fallback: list[dict[str, Any]] = []
        if pi:
            fallback.append({"name": pi, "corresponding": True})
        for member in team or []:
            member_name = member.strip()
            if member_name and member_name != pi:
                fallback.append({"name": member_name})
        return fallback

    if not any(author.get("corresponding") for author in normalized):
        normalized[0]["corresponding"] = True

    return normalized


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _next_id(items: list[dict[str, Any]], prefix: str) -> str:
    max_num = 0
    for item in items:
        item_id = item.get("id", "")
        if item_id.startswith(prefix):
            try:
                num = int(item_id[len(prefix):])
                max_num = max(max_num, num)
            except ValueError:
                pass
    return f"{prefix}{max_num + 1:03d}"


@mcp.tool()
async def setup_status() -> dict[str, Any]:
    """Check the current environment setup status.

    Returns information about which API keys are configured (without revealing
    values), whether the projects directory exists, and which projects are
    available.  Used by the setup agent to detect existing configuration.
    """
    workspace = Path(PROJECT_DIR).resolve()
    env_path = workspace / ".env"

    # Check which keys are present in .env (value set vs empty)
    key_names = [
        "NCBI_API_KEY", "OPENALEX_API_KEY", "OPENALEX_EMAIL", "S2_API_KEY",
        "S2_API_KEY_STATUS", "CROSSREF_EMAIL", "ZOTERO_API_KEY", "ZOTERO_USER_ID",
        "PROJECTS_ROOT",
    ]
    env_keys: dict[str, str] = {}
    if env_path.exists():
        with open(env_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip()
                    if k in key_names:
                        env_keys[k] = "set" if v else "empty"
    for k in key_names:
        env_keys.setdefault(k, "missing")

    # OPENALEX_EMAIL is optional when OPENALEX_API_KEY is configured.
    if env_keys.get("OPENALEX_EMAIL") == "missing" and env_keys.get("OPENALEX_API_KEY") == "set":
        env_keys["OPENALEX_EMAIL"] = "optional"

    # Treat Semantic Scholar key as intentionally pending when explicitly marked.
    if env_keys.get("S2_API_KEY") == "empty" and env_keys.get("S2_API_KEY_STATUS") == "set":
        env_keys["S2_API_KEY"] = "pending"

    # Projects directory
    projects_root = _resolve_projects_root()

    projects: list[dict[str, str]] = []
    if projects_root.is_dir():
        for child in sorted(projects_root.iterdir()):
            if child.is_dir() and child.name != ".gitkeep":
                proj_yaml = child / TRACKING_DIR / "project.yaml"
                if proj_yaml.exists():
                    meta = yaml.safe_load(proj_yaml.read_text(encoding="utf-8")) or {}
                    projects.append({
                        "name": child.name,
                        "title": meta.get("title", ""),
                        "status": "initialized",
                    })
                else:
                    projects.append({"name": child.name, "title": "", "status": "empty"})

    result = {
        "env_file": "exists" if env_path.exists() else "missing",
        "env_keys": env_keys,
        "projects_root": str(projects_root),
        "projects_root_exists": projects_root.is_dir(),
        "projects": projects,
        "active_project": _active_project,
    }

    if not projects_root.is_dir():
        result["projects_root_warning"] = (
            "PROJECTS_ROOT does not exist. Create it or set PROJECTS_ROOT to a valid path in .env."
        )

    return result


@mcp.tool()
async def list_projects() -> dict[str, Any]:
    """List all research projects in the projects directory.

    Scans PROJECTS_ROOT for subdirectories.  Returns each project's name,
    title (from project.yaml), and initialization status.
    """
    try:
        projects_root = _resolve_projects_root(must_exist=True)
    except ValueError as exc:
        return {"error": str(exc), "projects": []}

    projects: list[dict[str, Any]] = []
    for child in sorted(projects_root.iterdir()):
        if child.is_dir() and child.name != ".gitkeep":
            proj_yaml = child / TRACKING_DIR / "project.yaml"
            if proj_yaml.exists():
                meta = yaml.safe_load(proj_yaml.read_text(encoding="utf-8")) or {}
                projects.append({
                    "name": child.name,
                    "title": meta.get("title", ""),
                    "current_phase": meta.get("current_phase", ""),
                    "start_date": meta.get("start_date", ""),
                    "target_end": meta.get("target_end", ""),
                    "initialized": True,
                    "path": str(child),
                })
            else:
                projects.append({
                    "name": child.name,
                    "title": "",
                    "initialized": False,
                    "path": str(child),
                })

    return {
        "projects_root": str(projects_root),
        "projects": projects,
        "total": len(projects),
        "active_project": _active_project,
    }


@mcp.tool()
async def set_active_project(project_path: str) -> dict[str, Any]:
    """Set the active project for subsequent tool calls.

    Args:
        project_path: Absolute path to a project directory, or a name/relative
            path to resolve under PROJECTS_ROOT.

    Returns:
        Confirmation with the resolved absolute path.
    """
    global _active_project  # noqa: PLW0603

    p = Path(project_path)
    if not p.is_absolute():
        root = _resolve_projects_root()
        p = root.resolve() / p

    p = p.resolve()

    if not p.is_dir():
        return {"error": f"Directory does not exist: {p}. Create it first or use init_project."}

    _active_project = str(p)
    return {"status": "active_project_set", "path": str(p)}


@mcp.tool()
async def generate_mcp_config(
    target_project_path: str,
    assistant_path: str = "",
) -> dict[str, Any]:
    """Generate a .vscode/mcp.json for an external project.

    This lets a user open any project in VS Code and have the research-workflow-
    assistant MCP servers available without a multi-root workspace.

    Args:
        target_project_path: Absolute path to the external project.
        assistant_path: Absolute path to the research-workflow-assistant repo.
            Defaults to the current workspace (PROJECT_DIR).

    Returns:
        The generated config content and file path.
    """
    assistant = Path(assistant_path or PROJECT_DIR).resolve()
    target = Path(target_project_path).resolve()

    if not target.is_dir():
        return {"error": f"Target project directory does not exist: {target}"}

    # Determine the Python executable path inside the assistant's venv
    venv_python_win = assistant / ".venv" / "Scripts" / "python.exe"
    venv_python_unix = assistant / ".venv" / "bin" / "python"
    if venv_python_win.exists():
        python_cmd = str(venv_python_win)
    elif venv_python_unix.exists():
        python_cmd = str(venv_python_unix)
    else:
        python_cmd = "python"

    servers = {
        "pubmed": {
            "command": python_cmd,
            "args": ["-m", "pubmed_server"],
            "cwd": str(assistant / "mcp-servers" / "pubmed-server" / "src"),
            "env": {"NCBI_API_KEY": "${env:NCBI_API_KEY}"},
        },
        "openalex": {
            "command": python_cmd,
            "args": ["-m", "openalex_server"],
            "cwd": str(assistant / "mcp-servers" / "openalex-server" / "src"),
            "env": {"OPENALEX_EMAIL": "${env:OPENALEX_EMAIL}"},
        },
        "semantic-scholar": {
            "command": python_cmd,
            "args": ["-m", "semantic_scholar_server"],
            "cwd": str(assistant / "mcp-servers" / "semantic-scholar-server" / "src"),
            "env": {"S2_API_KEY": "${env:S2_API_KEY}"},
        },
        "europe-pmc": {
            "command": python_cmd,
            "args": ["-m", "europe_pmc_server"],
            "cwd": str(assistant / "mcp-servers" / "europe-pmc-server" / "src"),
        },
        "crossref": {
            "command": python_cmd,
            "args": ["-m", "crossref_server"],
            "cwd": str(assistant / "mcp-servers" / "crossref-server" / "src"),
            "env": {"CROSSREF_EMAIL": "${env:CROSSREF_EMAIL}"},
        },
        "zotero": {
            "command": python_cmd,
            "args": ["-m", "zotero_server"],
            "cwd": str(assistant / "mcp-servers" / "zotero-server" / "src"),
            "env": {
                "ZOTERO_API_KEY": "${env:ZOTERO_API_KEY}",
                "ZOTERO_USER_ID": "${env:ZOTERO_USER_ID}",
            },
        },
        "prisma-tracker": {
            "command": python_cmd,
            "args": ["-m", "prisma_tracker"],
            "cwd": str(assistant / "mcp-servers" / "prisma-tracker" / "src"),
            "env": {
                "PROJECT_DIR": "${workspaceFolder}",
                "PROJECTS_ROOT": "${workspaceFolder}",
            },
        },
        "project-tracker": {
            "command": python_cmd,
            "args": ["-m", "project_tracker"],
            "cwd": str(assistant / "mcp-servers" / "project-tracker" / "src"),
            "env": {
                "PROJECT_DIR": "${workspaceFolder}",
                "PROJECTS_ROOT": "${workspaceFolder}",
            },
        },
    }

    config = {"servers": servers}
    config_json = json.dumps(config, indent=4)

    # Write to target project
    vscode_dir = target / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    config_path = vscode_dir / "mcp.json"

    if config_path.exists():
        return {
            "error": f"{config_path} already exists. Delete it first or merge manually.",
            "generated_config": config_json,
        }

    config_path.write_text(config_json, encoding="utf-8")
    return {
        "status": "created",
        "path": str(config_path),
        "content": config_json,
    }


@mcp.tool()
async def init_project(
    title: str,
    pi: str,
    team: list[str] | None = None,
    start_date: str = "",
    target_end: str = "",
    authors: list[dict[str, Any]] | None = None,
    project_path: str = "",
) -> dict[str, Any]:
    """Initialize project tracking for a new research project.

    Args:
        title: Project title.
        pi: Principal investigator name.
        team: List of team member names.
        start_date: Project start date (YYYY-MM-DD). Defaults to today.
        target_end: Target completion date (YYYY-MM-DD).
        authors: Optional structured author metadata for report and manuscript outputs.
        project_path: Path to the project directory (absolute, or relative to
            PROJECTS_ROOT). Defaults to the active project or PROJECT_DIR.

    Returns:
        Confirmation with project metadata.
    """
    base = _resolve_project_dir(project_path or None, must_exist=False)
    base.mkdir(parents=True, exist_ok=True)

    project_authors = _normalize_authors(authors, pi, team)
    project_lead = pi or (project_authors[0].get("name", "") if project_authors else "")
    project_team = team or [author.get("name", "") for author in project_authors[1:] if author.get("name")]

    project = {
        "title": title,
        "pi": project_lead,
        "team": project_team,
        "authors": project_authors,
        "start_date": start_date or _today(),
        "target_end": target_end,
        "created_at": _now(),
        "updated_at": _now(),
        "current_phase": "",
        "phases": [],
    }
    _save_yaml("project.yaml", project, base)
    _save_yaml("tasks.yaml", {"tasks": []}, base)
    _save_yaml("decisions.yaml", {"decisions": []}, base)

    meetings_dir = _tracking_path(base) / "meetings"
    meetings_dir.mkdir(parents=True, exist_ok=True)
    briefs_dir = _tracking_path(base) / "briefs"
    briefs_dir.mkdir(parents=True, exist_ok=True)

    # Create ai-contributions-log.md if it doesn't exist
    log_path = base / "ai-contributions-log.md"
    if not log_path.exists():
        log_path.write_text(
            "# AI Contributions Log\n\n"
            "This log tracks all substantive AI contributions to this research project,\n"
            "in compliance with ICMJE recommendations on AI-assisted technology disclosure.\n\n"
            "## Log Entries\n\n",
            encoding="utf-8",
        )

    return {
        "status": "initialized",
        "title": title,
        "pi": project_lead,
        "authors": project_authors,
        "path": str(base),
    }


@mcp.tool()
async def define_phases(
    phases: list[dict[str, str]],
    project_path: str = "",
) -> dict[str, Any]:
    """Define research phases with target dates.

    Args:
        phases: List of phase dictionaries, each with 'name', 'target_start',
            and 'target_end' keys. Standard phases include: Protocol, Ethics/IRB,
            Registration, Data Collection, Analysis, Writing, Review, Submission, Revision.
        project_path: Path to the project directory (absolute, or relative to
            PROJECTS_ROOT). Defaults to the active project or PROJECT_DIR.

    Returns:
        Confirmation with defined phases.
    """
    base = _resolve_project_dir(project_path or None)
    project = _load_yaml("project.yaml", base)
    if not project:
        return {"error": "No project initialized. Call init_project first."}

    phase_list = []
    for p in phases:
        phase_list.append({
            "name": p["name"],
            "target_start": p.get("target_start", ""),
            "target_end": p.get("target_end", ""),
            "status": "not-started",
            "milestones": [],
            "started_at": None,
            "completed_at": None,
        })

    project["phases"] = phase_list
    if phase_list:
        project["current_phase"] = phase_list[0]["name"]
    project["updated_at"] = _now()
    _save_yaml("project.yaml", project, base)

    return {"status": "defined", "phases": [p["name"] for p in phase_list]}


@mcp.tool()
async def define_milestones(
    phase: str,
    milestones: list[dict[str, str]],
    project_path: str = "",
) -> dict[str, Any]:
    """Add milestones within a phase.

    Args:
        phase: Name of the phase to add milestones to.
        milestones: List of milestone dictionaries with 'name' and optional 'target_date'.
        project_path: Path to the project directory (absolute, or relative to
            PROJECTS_ROOT). Defaults to the active project or PROJECT_DIR.

    Returns:
        Confirmation with defined milestones.
    """
    base = _resolve_project_dir(project_path or None)
    project = _load_yaml("project.yaml", base)
    if not project:
        return {"error": "No project initialized."}

    phase_found = False
    for p in project.get("phases", []):
        if p["name"] == phase:
            for m in milestones:
                p["milestones"].append({
                    "id": _next_id(p["milestones"], "M"),
                    "name": m["name"],
                    "target_date": m.get("target_date", ""),
                    "status": "not-started",
                    "notes": "",
                    "completed_at": None,
                })
            phase_found = True
            break

    if not phase_found:
        return {"error": f"Phase '{phase}' not found."}

    project["updated_at"] = _now()
    _save_yaml("project.yaml", project, base)
    return {"status": "defined", "phase": phase, "milestones": [m["name"] for m in milestones]}


@mcp.tool()
async def update_milestone(
    milestone_id: str,
    status: str,
    notes: str = "",
    project_path: str = "",
) -> dict[str, Any]:
    """Update milestone status.

    Args:
        milestone_id: The milestone ID (e.g., 'M001').
        status: New status: 'not-started', 'in-progress', 'completed', 'blocked'.
        notes: Optional notes about the update.
        project_path: Path to the project directory (absolute, or relative to
            PROJECTS_ROOT). Defaults to the active project or PROJECT_DIR.

    Returns:
        Updated milestone information.
    """
    base = _resolve_project_dir(project_path or None)
    project = _load_yaml("project.yaml", base)
    if not project:
        return {"error": "No project initialized."}

    for p in project.get("phases", []):
        for m in p["milestones"]:
            if m["id"] == milestone_id:
                m["status"] = status
                if notes:
                    m["notes"] = notes
                if status == "completed":
                    m["completed_at"] = _now()
                project["updated_at"] = _now()
                _save_yaml("project.yaml", project, base)
                return {"status": "updated", "milestone": m["name"], "new_status": status}

    return {"error": f"Milestone '{milestone_id}' not found."}


@mcp.tool()
async def add_task(
    description: str,
    assignee: str = "",
    due_date: str = "",
    phase: str = "",
    priority: str = "medium",
    project_path: str = "",
) -> dict[str, Any]:
    """Create a new task.

    Args:
        description: Task description.
        assignee: Person responsible.
        due_date: Due date (YYYY-MM-DD).
        phase: Associated research phase.
        priority: 'high', 'medium', or 'low'.
        project_path: Path to the project directory (absolute, or relative to
            PROJECTS_ROOT). Defaults to the active project or PROJECT_DIR.

    Returns:
        Created task with its ID.
    """
    base = _resolve_project_dir(project_path or None)
    tasks_data = _load_yaml("tasks.yaml", base)
    tasks = tasks_data.get("tasks", [])

    task = {
        "id": _next_id(tasks, "T"),
        "description": description,
        "assignee": assignee,
        "due_date": due_date,
        "phase": phase,
        "priority": priority,
        "status": "not-started",
        "notes": "",
        "created_at": _now(),
        "updated_at": _now(),
        "completed_at": None,
    }
    tasks.append(task)
    _save_yaml("tasks.yaml", {"tasks": tasks}, base)

    return {"status": "created", "task_id": task["id"], "description": description}


@mcp.tool()
async def update_task(
    task_id: str,
    status: str,
    notes: str = "",
    project_path: str = "",
) -> dict[str, Any]:
    """Update a task's status.

    Args:
        task_id: The task ID (e.g., 'T001').
        status: New status: 'not-started', 'in-progress', 'completed', 'blocked'.
        notes: Optional notes.
        project_path: Path to the project directory (absolute, or relative to
            PROJECTS_ROOT). Defaults to the active project or PROJECT_DIR.

    Returns:
        Updated task information.
    """
    base = _resolve_project_dir(project_path or None)
    tasks_data = _load_yaml("tasks.yaml", base)
    tasks = tasks_data.get("tasks", [])

    for task in tasks:
        if task["id"] == task_id:
            task["status"] = status
            if notes:
                task["notes"] = notes
            task["updated_at"] = _now()
            if status == "completed":
                task["completed_at"] = _now()
            _save_yaml("tasks.yaml", {"tasks": tasks}, base)
            return {"status": "updated", "task_id": task_id, "new_status": status}

    return {"error": f"Task '{task_id}' not found."}


@mcp.tool()
async def log_decision(
    decision: str,
    rationale: str,
    made_by: str,
    date: str = "",
    context: str = "",
    project_path: str = "",
) -> dict[str, Any]:
    """Record a research decision with rationale.

    Args:
        decision: What was decided.
        rationale: Why this decision was made (must be provided by the human).
        made_by: Who made the decision.
        date: Date of decision (YYYY-MM-DD). Defaults to today.
        context: Additional context or alternatives considered.
        project_path: Path to the project directory (absolute, or relative to
            PROJECTS_ROOT). Defaults to the active project or PROJECT_DIR.

    Returns:
        Confirmation with decision ID.
    """
    base = _resolve_project_dir(project_path or None)
    decisions_data = _load_yaml("decisions.yaml", base)
    decisions = decisions_data.get("decisions", [])

    entry = {
        "id": _next_id(decisions, "D"),
        "decision": decision,
        "rationale": rationale,
        "made_by": made_by,
        "date": date or _today(),
        "context": context,
        "recorded_at": _now(),
    }
    decisions.append(entry)
    _save_yaml("decisions.yaml", {"decisions": decisions}, base)

    return {"status": "recorded", "decision_id": entry["id"]}


@mcp.tool()
async def log_meeting(
    date: str,
    attendees: list[str],
    notes: str,
    action_items: list[dict[str, str]] | None = None,
    project_path: str = "",
) -> dict[str, Any]:
    """Record meeting notes with action items.

    Args:
        date: Meeting date (YYYY-MM-DD).
        attendees: List of attendee names.
        notes: Meeting discussion notes.
        action_items: Optional list of action item dictionaries with
            'description', 'assignee', and 'due_date' keys.
        project_path: Path to the project directory (absolute, or relative to
            PROJECTS_ROOT). Defaults to the active project or PROJECT_DIR.

    Returns:
        Confirmation with meeting file path.
    """
    base = _resolve_project_dir(project_path or None)
    meeting = {
        "date": date,
        "attendees": attendees,
        "notes": notes,
        "action_items": [],
        "recorded_at": _now(),
    }

    for item in (action_items or []):
        meeting["action_items"].append({
            "description": item.get("description", ""),
            "assignee": item.get("assignee", ""),
            "due_date": item.get("due_date", ""),
            "status": "open",
        })

    filename = f"meetings/{date}_meeting.yaml"
    _save_yaml(filename, meeting, base)

    # Also create tasks for action items
    if action_items:
        tasks_data = _load_yaml("tasks.yaml", base)
        tasks = tasks_data.get("tasks", [])
        for item in action_items:
            task = {
                "id": _next_id(tasks, "T"),
                "description": f"[Meeting {date}] {item.get('description', '')}",
                "assignee": item.get("assignee", ""),
                "due_date": item.get("due_date", ""),
                "phase": "",
                "priority": "medium",
                "status": "not-started",
                "notes": f"From meeting on {date}",
                "created_at": _now(),
                "updated_at": _now(),
                "completed_at": None,
            }
            tasks.append(task)
        _save_yaml("tasks.yaml", {"tasks": tasks}, base)

    return {"status": "recorded", "file": filename, "action_items_count": len(meeting["action_items"])}


@mcp.tool()
async def get_project_status(
    project_path: str = "",
) -> dict[str, Any]:
    """Get a full project status snapshot.

    Args:
        project_path: Path to the project directory (absolute, or relative to
            PROJECTS_ROOT). Defaults to the active project or PROJECT_DIR.

    Returns:
        Complete status including phases, milestones, task counts, and blockers.
    """
    base = _resolve_project_dir(project_path or None)
    project = _load_yaml("project.yaml", base)
    if not project:
        return {"error": "No project initialized."}

    tasks_data = _load_yaml("tasks.yaml", base)
    tasks = tasks_data.get("tasks", [])

    phase_status = []
    for p in project.get("phases", []):
        milestones_complete = sum(1 for m in p["milestones"] if m["status"] == "completed")
        milestones_total = len(p["milestones"])
        phase_status.append({
            "name": p["name"],
            "status": p["status"],
            "milestones": f"{milestones_complete}/{milestones_total} completed",
            "target_end": p.get("target_end", ""),
        })

    task_counts = {
        "total": len(tasks),
        "not_started": sum(1 for t in tasks if t["status"] == "not-started"),
        "in_progress": sum(1 for t in tasks if t["status"] == "in-progress"),
        "completed": sum(1 for t in tasks if t["status"] == "completed"),
        "blocked": sum(1 for t in tasks if t["status"] == "blocked"),
    }

    blockers = [
        {"type": "task", "id": t["id"], "description": t["description"]}
        for t in tasks if t["status"] == "blocked"
    ]
    for p in project.get("phases", []):
        for m in p["milestones"]:
            if m["status"] == "blocked":
                blockers.append({"type": "milestone", "id": m["id"], "description": m["name"]})

    return {
        "title": project.get("title", ""),
        "pi": project.get("pi", ""),
        "current_phase": project.get("current_phase", ""),
        "start_date": project.get("start_date", ""),
        "target_end": project.get("target_end", ""),
        "phases": phase_status,
        "tasks": task_counts,
        "blockers": blockers,
        "updated_at": project.get("updated_at", ""),
    }


@mcp.tool()
async def get_overdue_items(
    project_path: str = "",
) -> dict[str, Any]:
    """List overdue milestones and tasks.

    Args:
        project_path: Path to the project directory (absolute, or relative to
            PROJECTS_ROOT). Defaults to the active project or PROJECT_DIR.

    Returns:
        Lists of overdue milestones and tasks with their details.
    """
    base = _resolve_project_dir(project_path or None)
    today = _today()
    project = _load_yaml("project.yaml", base)
    tasks_data = _load_yaml("tasks.yaml", base)
    tasks = tasks_data.get("tasks", [])

    overdue_milestones = []
    for p in project.get("phases", []):
        for m in p["milestones"]:
            if m["target_date"] and m["target_date"] < today and m["status"] not in ("completed",):
                overdue_milestones.append({
                    "id": m["id"],
                    "name": m["name"],
                    "phase": p["name"],
                    "target_date": m["target_date"],
                    "status": m["status"],
                    "days_overdue": (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(m["target_date"], "%Y-%m-%d")).days,
                })

    overdue_tasks = []
    for t in tasks:
        if t["due_date"] and t["due_date"] < today and t["status"] not in ("completed",):
            overdue_tasks.append({
                "id": t["id"],
                "description": t["description"],
                "assignee": t["assignee"],
                "due_date": t["due_date"],
                "status": t["status"],
                "days_overdue": (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(t["due_date"], "%Y-%m-%d")).days,
            })

    return {
        "overdue_milestones": overdue_milestones,
        "overdue_tasks": overdue_tasks,
        "total_overdue": len(overdue_milestones) + len(overdue_tasks),
    }


@mcp.tool()
async def generate_brief(
    audience: str = "team",
    period: str = "weekly",
    format: str = "markdown",
    project_path: str = "",
) -> dict[str, Any]:
    """Generate structured data for a progress brief.

    Args:
        audience: Target audience: 'team', 'supervisor', or 'funder'.
            Controls detail level.
        period: Reporting period: 'weekly', 'monthly', or 'custom'.
        format: Output format: 'markdown' (quick) or 'quarto' (for rendering).
        project_path: Path to the project directory (absolute, or relative to
            PROJECTS_ROOT). Defaults to the active project or PROJECT_DIR.

    Returns:
        Dictionary with brief content ready for rendering or copy-pasting.
    """
    base = _resolve_project_dir(project_path or None)
    project = _load_yaml("project.yaml", base)
    if not project:
        return {"error": "No project initialized."}

    tasks_data = _load_yaml("tasks.yaml", base)
    tasks = tasks_data.get("tasks", [])
    decisions_data = _load_yaml("decisions.yaml", base)
    decisions = decisions_data.get("decisions", [])

    # Gather status
    current_phase = project.get("current_phase", "N/A")
    phases = project.get("phases", [])

    completed_milestones = []
    upcoming_milestones = []
    for p in phases:
        for m in p["milestones"]:
            if m["status"] == "completed":
                completed_milestones.append(f"- {m['name']} ({p['name']})")
            elif m["status"] in ("not-started", "in-progress"):
                upcoming_milestones.append(f"- {m['name']} ({p['name']}) - target: {m.get('target_date', 'TBD')}")

    open_tasks = [t for t in tasks if t["status"] in ("not-started", "in-progress")]
    blocked_tasks = [t for t in tasks if t["status"] == "blocked"]
    recent_decisions = decisions[-5:] if decisions else []

    # Build markdown brief
    lines = [
        f"# Progress Brief: {project.get('title', 'Untitled')}",
        f"**Date:** {_today()}",
        f"**PI:** {project.get('pi', 'N/A')}",
        f"**Current Phase:** {current_phase}",
        "",
        "## Status Summary",
        "",
    ]

    if audience in ("supervisor", "funder"):
        # High-level summary for supervisors/funders
        completed_count = sum(
            sum(1 for m in p["milestones"] if m["status"] == "completed")
            for p in phases
        )
        total_count = sum(len(p["milestones"]) for p in phases)
        lines.append(f"Overall progress: {completed_count}/{total_count} milestones completed.")
        lines.append(f"Tasks: {sum(1 for t in tasks if t['status'] == 'completed')} completed, "
                      f"{len(open_tasks)} in progress/pending, {len(blocked_tasks)} blocked.")
    else:
        lines.append(f"Tasks: {len(open_tasks)} open, {len(blocked_tasks)} blocked")

    if completed_milestones:
        lines.extend(["", "## Completed Milestones", ""])
        lines.extend(completed_milestones[-5:])

    if upcoming_milestones:
        lines.extend(["", "## Upcoming Milestones", ""])
        lines.extend(upcoming_milestones[:5])

    if blocked_tasks:
        lines.extend(["", "## Blockers", ""])
        for t in blocked_tasks:
            lines.append(f"- [{t['id']}] {t['description']}: {t.get('notes', 'No details')}")

    if recent_decisions and audience != "funder":
        lines.extend(["", "## Recent Decisions", ""])
        for d in recent_decisions:
            lines.append(f"- **{d['decision']}** ({d['date']}): {d['rationale']}")

    if open_tasks and audience == "team":
        lines.extend(["", "## Open Tasks", ""])
        for t in open_tasks[:10]:
            assignee = f" [{t['assignee']}]" if t["assignee"] else ""
            due = f" (due {t['due_date']})" if t["due_date"] else ""
            lines.append(f"- [{t['id']}] {t['description']}{assignee}{due}")

    lines.extend(["", "## Next Steps", ""])
    if upcoming_milestones:
        lines.append(f"Focus: {upcoming_milestones[0].strip('- ')}")
    lines.append("")
    lines.append("---")
    lines.append("*This brief was generated with AI assistance. All project data was entered and verified by the research team.*")

    brief_content = "\n".join(lines)

    # Save brief
    brief_filename = f"briefs/{_today()}_brief_{audience}.md"
    brief_path = _tracking_path(base) / brief_filename
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(brief_content, encoding="utf-8")

    result: dict[str, Any] = {
        "audience": audience,
        "period": period,
        "format": format,
        "content": brief_content,
        "saved_to": brief_filename,
    }

    if format == "quarto":
        # Add YAML frontmatter for Quarto rendering
        qmd_lines = [
            "---",
            f'title: "Progress Brief: {project.get("title", "Untitled")}"',
            f'date: "{_today()}"',
            f'author: "{project.get("pi", "")}"',
            "format:",
            "  docx:",
            "    toc: false",
            "  pdf:",
            "    toc: false",
            "---",
            "",
        ]
        qmd_content = "\n".join(qmd_lines) + brief_content
        qmd_filename = f"briefs/{_today()}_brief_{audience}.qmd"
        qmd_path = _tracking_path(base) / qmd_filename
        qmd_path.write_text(qmd_content, encoding="utf-8")
        result["quarto_file"] = qmd_filename

    return result


@mcp.tool()
async def get_decision_log(
    date_range: str | None = None,
    project_path: str = "",
) -> dict[str, Any]:
    """Retrieve the decision log, optionally filtered by date.

    Args:
        date_range: Optional date range as 'YYYY-MM-DD:YYYY-MM-DD'. Returns all if omitted.
        project_path: Path to the project directory (absolute, or relative to
            PROJECTS_ROOT). Defaults to the active project or PROJECT_DIR.

    Returns:
        List of decisions.
    """
    base = _resolve_project_dir(project_path or None)
    decisions_data = _load_yaml("decisions.yaml", base)
    decisions = decisions_data.get("decisions", [])

    if date_range and ":" in date_range:
        start, end = date_range.split(":")
        decisions = [d for d in decisions if start <= d.get("date", "") <= end]

    return {"decisions": decisions, "total": len(decisions)}


@mcp.tool()
async def get_action_items(
    assignee: str | None = None,
    status: str | None = None,
    project_path: str = "",
) -> dict[str, Any]:
    """List action items (tasks), optionally filtered.

    Args:
        assignee: Filter by assignee name.
        status: Filter by status: 'not-started', 'in-progress', 'completed', 'blocked'.
        project_path: Path to the project directory (absolute, or relative to
            PROJECTS_ROOT). Defaults to the active project or PROJECT_DIR.

    Returns:
        Filtered list of tasks/action items.
    """
    base = _resolve_project_dir(project_path or None)
    tasks_data = _load_yaml("tasks.yaml", base)
    tasks = tasks_data.get("tasks", [])

    if assignee:
        tasks = [t for t in tasks if t.get("assignee", "").lower() == assignee.lower()]
    if status:
        tasks = [t for t in tasks if t.get("status") == status]

    return {"action_items": tasks, "total": len(tasks)}


def serve() -> None:
    """Run the Project Tracker MCP server."""
    mcp.run(transport="stdio")
