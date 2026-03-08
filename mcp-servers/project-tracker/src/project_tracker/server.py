"""Project Tracker MCP Server implementation.

Local file-based research project management: phases, milestones, tasks,
decisions, meetings, and progress briefs.

Storage: project-tracking/ directory with YAML files.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from mcp.server.fastmcp import FastMCP

PROJECT_DIR = os.environ.get("PROJECT_TRACKER_DIR", ".")
TRACKING_DIR = "project-tracking"

mcp = FastMCP(
    "project-tracker",
    description="Track research project phases, milestones, tasks, decisions, and generate progress briefs",
)


def _tracking_path() -> Path:
    return Path(PROJECT_DIR) / TRACKING_DIR


def _load_yaml(filename: str) -> dict[str, Any]:
    path = _tracking_path() / filename
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {}


def _save_yaml(filename: str, data: dict[str, Any] | list[Any]) -> None:
    path = _tracking_path() / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")


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
async def init_project(
    title: str,
    pi: str,
    team: list[str] | None = None,
    start_date: str = "",
    target_end: str = "",
) -> dict[str, Any]:
    """Initialize project tracking for a new research project.

    Args:
        title: Project title.
        pi: Principal investigator name.
        team: List of team member names.
        start_date: Project start date (YYYY-MM-DD). Defaults to today.
        target_end: Target completion date (YYYY-MM-DD).

    Returns:
        Confirmation with project metadata.
    """
    project = {
        "title": title,
        "pi": pi,
        "team": team or [],
        "start_date": start_date or _today(),
        "target_end": target_end,
        "created_at": _now(),
        "updated_at": _now(),
        "current_phase": "",
        "phases": [],
    }
    _save_yaml("project.yaml", project)
    _save_yaml("tasks.yaml", {"tasks": []})
    _save_yaml("decisions.yaml", {"decisions": []})

    meetings_dir = _tracking_path() / "meetings"
    meetings_dir.mkdir(parents=True, exist_ok=True)
    briefs_dir = _tracking_path() / "briefs"
    briefs_dir.mkdir(parents=True, exist_ok=True)

    return {"status": "initialized", "title": title, "pi": pi}


@mcp.tool()
async def define_phases(
    phases: list[dict[str, str]],
) -> dict[str, Any]:
    """Define research phases with target dates.

    Args:
        phases: List of phase dictionaries, each with 'name', 'target_start',
            and 'target_end' keys. Standard phases include: Protocol, Ethics/IRB,
            Registration, Data Collection, Analysis, Writing, Review, Submission, Revision.

    Returns:
        Confirmation with defined phases.
    """
    project = _load_yaml("project.yaml")
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
    _save_yaml("project.yaml", project)

    return {"status": "defined", "phases": [p["name"] for p in phase_list]}


@mcp.tool()
async def define_milestones(
    phase: str,
    milestones: list[dict[str, str]],
) -> dict[str, Any]:
    """Add milestones within a phase.

    Args:
        phase: Name of the phase to add milestones to.
        milestones: List of milestone dictionaries with 'name' and optional 'target_date'.

    Returns:
        Confirmation with defined milestones.
    """
    project = _load_yaml("project.yaml")
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
    _save_yaml("project.yaml", project)
    return {"status": "defined", "phase": phase, "milestones": [m["name"] for m in milestones]}


@mcp.tool()
async def update_milestone(
    milestone_id: str,
    status: str,
    notes: str = "",
) -> dict[str, Any]:
    """Update milestone status.

    Args:
        milestone_id: The milestone ID (e.g., 'M001').
        status: New status: 'not-started', 'in-progress', 'completed', 'blocked'.
        notes: Optional notes about the update.

    Returns:
        Updated milestone information.
    """
    project = _load_yaml("project.yaml")
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
                _save_yaml("project.yaml", project)
                return {"status": "updated", "milestone": m["name"], "new_status": status}

    return {"error": f"Milestone '{milestone_id}' not found."}


@mcp.tool()
async def add_task(
    description: str,
    assignee: str = "",
    due_date: str = "",
    phase: str = "",
    priority: str = "medium",
) -> dict[str, Any]:
    """Create a new task.

    Args:
        description: Task description.
        assignee: Person responsible.
        due_date: Due date (YYYY-MM-DD).
        phase: Associated research phase.
        priority: 'high', 'medium', or 'low'.

    Returns:
        Created task with its ID.
    """
    tasks_data = _load_yaml("tasks.yaml")
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
    _save_yaml("tasks.yaml", {"tasks": tasks})

    return {"status": "created", "task_id": task["id"], "description": description}


@mcp.tool()
async def update_task(
    task_id: str,
    status: str,
    notes: str = "",
) -> dict[str, Any]:
    """Update a task's status.

    Args:
        task_id: The task ID (e.g., 'T001').
        status: New status: 'not-started', 'in-progress', 'completed', 'blocked'.
        notes: Optional notes.

    Returns:
        Updated task information.
    """
    tasks_data = _load_yaml("tasks.yaml")
    tasks = tasks_data.get("tasks", [])

    for task in tasks:
        if task["id"] == task_id:
            task["status"] = status
            if notes:
                task["notes"] = notes
            task["updated_at"] = _now()
            if status == "completed":
                task["completed_at"] = _now()
            _save_yaml("tasks.yaml", {"tasks": tasks})
            return {"status": "updated", "task_id": task_id, "new_status": status}

    return {"error": f"Task '{task_id}' not found."}


@mcp.tool()
async def log_decision(
    decision: str,
    rationale: str,
    made_by: str,
    date: str = "",
    context: str = "",
) -> dict[str, Any]:
    """Record a research decision with rationale.

    Args:
        decision: What was decided.
        rationale: Why this decision was made (must be provided by the human).
        made_by: Who made the decision.
        date: Date of decision (YYYY-MM-DD). Defaults to today.
        context: Additional context or alternatives considered.

    Returns:
        Confirmation with decision ID.
    """
    decisions_data = _load_yaml("decisions.yaml")
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
    _save_yaml("decisions.yaml", {"decisions": decisions})

    return {"status": "recorded", "decision_id": entry["id"]}


@mcp.tool()
async def log_meeting(
    date: str,
    attendees: list[str],
    notes: str,
    action_items: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Record meeting notes with action items.

    Args:
        date: Meeting date (YYYY-MM-DD).
        attendees: List of attendee names.
        notes: Meeting discussion notes.
        action_items: Optional list of action item dictionaries with
            'description', 'assignee', and 'due_date' keys.

    Returns:
        Confirmation with meeting file path.
    """
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
    _save_yaml(filename, meeting)

    # Also create tasks for action items
    if action_items:
        tasks_data = _load_yaml("tasks.yaml")
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
        _save_yaml("tasks.yaml", {"tasks": tasks})

    return {"status": "recorded", "file": filename, "action_items_count": len(meeting["action_items"])}


@mcp.tool()
async def get_project_status() -> dict[str, Any]:
    """Get a full project status snapshot.

    Returns:
        Complete status including phases, milestones, task counts, and blockers.
    """
    project = _load_yaml("project.yaml")
    if not project:
        return {"error": "No project initialized."}

    tasks_data = _load_yaml("tasks.yaml")
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
async def get_overdue_items() -> dict[str, Any]:
    """List overdue milestones and tasks.

    Returns:
        Lists of overdue milestones and tasks with their details.
    """
    today = _today()
    project = _load_yaml("project.yaml")
    tasks_data = _load_yaml("tasks.yaml")
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
) -> dict[str, Any]:
    """Generate structured data for a progress brief.

    Args:
        audience: Target audience: 'team', 'supervisor', or 'funder'.
            Controls detail level.
        period: Reporting period: 'weekly', 'monthly', or 'custom'.
        format: Output format: 'markdown' (quick) or 'quarto' (for rendering).

    Returns:
        Dictionary with brief content ready for rendering or copy-pasting.
    """
    project = _load_yaml("project.yaml")
    if not project:
        return {"error": "No project initialized."}

    tasks_data = _load_yaml("tasks.yaml")
    tasks = tasks_data.get("tasks", [])
    decisions_data = _load_yaml("decisions.yaml")
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
    brief_path = _tracking_path() / brief_filename
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
        qmd_path = _tracking_path() / qmd_filename
        qmd_path.write_text(qmd_content, encoding="utf-8")
        result["quarto_file"] = qmd_filename

    return result


@mcp.tool()
async def get_decision_log(date_range: str | None = None) -> dict[str, Any]:
    """Retrieve the decision log, optionally filtered by date.

    Args:
        date_range: Optional date range as 'YYYY-MM-DD:YYYY-MM-DD'. Returns all if omitted.

    Returns:
        List of decisions.
    """
    decisions_data = _load_yaml("decisions.yaml")
    decisions = decisions_data.get("decisions", [])

    if date_range and ":" in date_range:
        start, end = date_range.split(":")
        decisions = [d for d in decisions if start <= d.get("date", "") <= end]

    return {"decisions": decisions, "total": len(decisions)}


@mcp.tool()
async def get_action_items(
    assignee: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """List action items (tasks), optionally filtered.

    Args:
        assignee: Filter by assignee name.
        status: Filter by status: 'not-started', 'in-progress', 'completed', 'blocked'.

    Returns:
        Filtered list of tasks/action items.
    """
    tasks_data = _load_yaml("tasks.yaml")
    tasks = tasks_data.get("tasks", [])

    if assignee:
        tasks = [t for t in tasks if t.get("assignee", "").lower() == assignee.lower()]
    if status:
        tasks = [t for t in tasks if t.get("status") == status]

    return {"action_items": tasks, "total": len(tasks)}


def serve() -> None:
    """Run the Project Tracker MCP server."""
    mcp.run(transport="stdio")
