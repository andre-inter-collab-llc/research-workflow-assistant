"""PRISMA Tracker MCP Server implementation.

Local file-based tracking of PRISMA 2020 systematic review flow.
Stores data in review-tracking/prisma-flow.json within the research project directory.

Supports multiple projects via:
  - ``project_path`` parameter on every tool (explicit per-call targeting)
  - ``set_active_review`` tool (sets a session-wide default)
  - ``PROJECTS_ROOT`` env var (base directory for relative project paths)
  - ``PRISMA_PROJECT_DIR`` env var (legacy single-project fallback)

Storage: {project_root}/review-tracking/prisma-flow.json
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_DIR = os.environ.get("PRISMA_PROJECT_DIR", ".")
PROJECTS_ROOT = os.environ.get("PROJECTS_ROOT", "./my_projects")
TRACKING_DIR = "review-tracking"
FLOW_FILE = "prisma-flow.json"

# Session-level active project (set via set_active_review tool)
_active_project: str | None = None

mcp = FastMCP(
    "prisma-tracker",
    instructions="Track PRISMA 2020 systematic review flow: searches, screening, and reporting",
)


# ---------------------------------------------------------------------------
# Path resolution helpers
# ---------------------------------------------------------------------------

def _resolve_project_dir(project_path: str | None = None, *, must_exist: bool = True) -> Path:
    """Resolve a project directory from the various possible sources.

    Priority order:
      1. Explicit ``project_path`` argument (absolute or relative to PROJECTS_ROOT)
      2. ``_active_project`` module state (set via ``set_active_review``)
      3. ``PRISMA_PROJECT_DIR`` env var (legacy single-project mode)

    Raises ``ValueError`` when *must_exist* is True and the path does not exist.
    """
    raw: str | None = project_path or _active_project or None

    if raw:
        p = Path(raw)
        if not p.is_absolute():
            p = _resolve_projects_root() / p
        p = p.resolve()
    else:
        p = Path(PROJECT_DIR).resolve()

    if must_exist and not p.exists():
        raise ValueError(f"Project directory does not exist: {p}")

    return p


def _flow_path(base_dir: Path | None = None) -> Path:
    """Get the path to the PRISMA flow file."""
    if base_dir is None:
        base_dir = _resolve_project_dir()
    return base_dir / TRACKING_DIR / FLOW_FILE


def _resolve_projects_root(*, must_exist: bool = False) -> Path:
    """Resolve PROJECTS_ROOT consistently against PROJECT_DIR when relative."""
    projects_root = Path(PROJECTS_ROOT)
    if not projects_root.is_absolute():
        projects_root = Path(PROJECT_DIR).resolve() / projects_root
    projects_root = projects_root.resolve()

    if must_exist and not projects_root.is_dir():
        raise ValueError(f"Projects directory does not exist: {projects_root}")

    return projects_root


def _load_flow(base_dir: Path | None = None) -> dict[str, Any]:
    """Load the PRISMA flow data from disk."""
    path = _flow_path(base_dir)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_flow(data: dict[str, Any], base_dir: Path | None = None) -> None:
    """Save the PRISMA flow data to disk."""
    path = _flow_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _now() -> str:
    """Return current UTC timestamp as ISO string."""
    return datetime.now(UTC).isoformat()


def _ci(
    section: str, item: int, description: str, status: str = "manual",
) -> dict[str, Any]:
    """Build a single checklist item dict."""
    return {
        "section": section,
        "item": item,
        "description": description,
        "status": status,
    }


# ---------------------------------------------------------------------------
# Project management tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def set_active_review(project_path: str) -> dict[str, Any]:
    """Set the active review project for this session.

    All subsequent tool calls will target this project unless overridden
    by an explicit ``project_path`` parameter.

    Args:
        project_path: Path to the project directory (absolute, or relative
            to PROJECTS_ROOT).

    Returns:
        Confirmation with the resolved path.
    """
    global _active_project
    p = _resolve_project_dir(project_path)
    _active_project = str(p)
    has_flow = _flow_path(p).exists()
    return {
        "status": "active_review_set",
        "path": str(p),
        "has_prisma_data": has_flow,
    }


@mcp.tool()
async def list_reviews() -> dict[str, Any]:
    """List all projects under PROJECTS_ROOT that contain PRISMA review data.

    Returns:
        List of projects with their review title, type, and path.
    """
    root = _resolve_projects_root()
    reviews: list[dict[str, Any]] = []

    if not root.exists():
        return {
            "projects_root": str(root),
            "reviews": [],
            "note": (
                "PROJECTS_ROOT does not exist yet. "
                "Create it or set PROJECTS_ROOT to a valid path in .env."
            ),
        }

    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        flow_file = child / TRACKING_DIR / FLOW_FILE
        entry: dict[str, Any] = {"name": child.name, "path": str(child)}
        if flow_file.exists():
            try:
                flow = json.loads(flow_file.read_text(encoding="utf-8"))
                entry["title"] = flow.get("title", "")
                entry["review_type"] = flow.get("review_type", "")
                entry["has_prisma_data"] = True
            except (json.JSONDecodeError, OSError):
                entry["has_prisma_data"] = False
        else:
            entry["has_prisma_data"] = False
        reviews.append(entry)

    return {
        "projects_root": str(root),
        "reviews": reviews,
        "active_project": _active_project,
    }


# ---------------------------------------------------------------------------
# Review tracking tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def init_review(
    title: str,
    protocol_id: str = "",
    review_type: str = "systematic-review",
    project_path: str = "",
) -> dict[str, Any]:
    """Initialize PRISMA tracking for a new systematic review.

    Args:
        title: Title of the systematic review.
        protocol_id: Optional protocol registration ID (e.g., PROSPERO CRD number).
        review_type: Type of review: 'systematic-review', 'scoping-review',
            'meta-analysis'. Default 'systematic-review'.
        project_path: Path to the project directory (absolute, or relative
            to PROJECTS_ROOT). Leave empty to use the active project.

    Returns:
        Confirmation with initialized flow structure.
    """
    base_dir = _resolve_project_dir(project_path or None, must_exist=False)
    base_dir.mkdir(parents=True, exist_ok=True)
    flow = {
        "title": title,
        "protocol_id": protocol_id,
        "review_type": review_type,
        "created_at": _now(),
        "updated_at": _now(),
        "identification": {
            "database_searches": [],
            "other_sources": [],
            "total_records_databases": 0,
            "total_records_other": 0,
        },
        "deduplication": {
            "before_count": 0,
            "after_count": 0,
            "duplicates_removed": 0,
            "method": "",
            "recorded_at": None,
        },
        "screening": {
            "title_abstract": {
                "screened": 0,
                "excluded": 0,
                "excluded_reasons": {},
                "included_to_full_text": 0,
                "recorded_at": None,
            },
            "full_text": {
                "assessed": 0,
                "excluded": 0,
                "excluded_reasons": {},
                "included_in_review": 0,
                "recorded_at": None,
            },
        },
        "included": {
            "qualitative_synthesis": 0,
            "quantitative_synthesis": 0,
        },
    }
    _save_flow(flow, base_dir)

    return {
        "status": "initialized",
        "title": title,
        "review_type": review_type,
        "path": str(base_dir),
    }


@mcp.tool()
async def record_search(
    database: str,
    query: str,
    date: str,
    results_count: int,
    notes: str = "",
    project_path: str = "",
) -> dict[str, Any]:
    """Record a database search in the PRISMA identification stage.

    Args:
        database: Name of the database searched (e.g., 'PubMed', 'OpenAlex').
        query: The search query string used.
        date: Date the search was run (YYYY-MM-DD).
        results_count: Number of records retrieved.
        notes: Optional notes about the search.
        project_path: Path to the project directory. Leave empty to use the active project.

    Returns:
        Updated identification totals.
    """
    base_dir = _resolve_project_dir(project_path or None)
    flow = _load_flow(base_dir)
    if not flow:
        return {"error": "No review initialized. Call init_review first."}

    search_entry = {
        "database": database,
        "query": query,
        "date": date,
        "results_count": results_count,
        "notes": notes,
        "recorded_at": _now(),
    }
    flow["identification"]["database_searches"].append(search_entry)
    flow["identification"]["total_records_databases"] = sum(
        s["results_count"] for s in flow["identification"]["database_searches"]
    )
    flow["updated_at"] = _now()
    _save_flow(flow, base_dir)

    return {
        "status": "recorded",
        "database": database,
        "results_count": results_count,
        "total_records_databases": flow["identification"]["total_records_databases"],
    }


@mcp.tool()
async def record_deduplication(
    before_count: int,
    after_count: int,
    method: str = "automated",
    project_path: str = "",
) -> dict[str, Any]:
    """Record the deduplication step.

    Args:
        before_count: Number of records before deduplication.
        after_count: Number of records after deduplication.
        method: Method used ('automated', 'manual', 'semi-automated').
        project_path: Path to the project directory. Leave empty to use the active project.

    Returns:
        Updated deduplication counts.
    """
    base_dir = _resolve_project_dir(project_path or None)
    flow = _load_flow(base_dir)
    if not flow:
        return {"error": "No review initialized. Call init_review first."}

    flow["deduplication"] = {
        "before_count": before_count,
        "after_count": after_count,
        "duplicates_removed": before_count - after_count,
        "method": method,
        "recorded_at": _now(),
    }
    flow["updated_at"] = _now()
    _save_flow(flow, base_dir)

    return {
        "status": "recorded",
        "duplicates_removed": before_count - after_count,
        "records_for_screening": after_count,
    }


@mcp.tool()
async def record_screening(
    stage: str,
    included: int,
    excluded_with_reasons: dict[str, int],
    project_path: str = "",
) -> dict[str, Any]:
    """Record screening results for a PRISMA stage.

    Args:
        stage: Screening stage: 'title_abstract' or 'full_text'.
        included: Number of records included (passing to next stage).
        excluded_with_reasons: Dictionary of exclusion reasons and counts.
            Example: {"wrong population": 15, "wrong outcome": 8, "not primary study": 5}
        project_path: Path to the project directory. Leave empty to use the active project.

    Returns:
        Updated screening counts for the stage.
    """
    base_dir = _resolve_project_dir(project_path or None)
    flow = _load_flow(base_dir)
    if not flow:
        return {"error": "No review initialized. Call init_review first."}

    total_excluded = sum(excluded_with_reasons.values())
    total_screened = included + total_excluded

    if stage == "title_abstract":
        flow["screening"]["title_abstract"] = {
            "screened": total_screened,
            "excluded": total_excluded,
            "excluded_reasons": excluded_with_reasons,
            "included_to_full_text": included,
            "recorded_at": _now(),
        }
    elif stage == "full_text":
        flow["screening"]["full_text"] = {
            "assessed": total_screened,
            "excluded": total_excluded,
            "excluded_reasons": excluded_with_reasons,
            "included_in_review": included,
            "recorded_at": _now(),
        }
        flow["included"]["qualitative_synthesis"] = included
    else:
        return {"error": f"Unknown stage '{stage}'. Use 'title_abstract' or 'full_text'."}

    flow["updated_at"] = _now()
    _save_flow(flow, base_dir)

    return {
        "status": "recorded",
        "stage": stage,
        "screened": total_screened,
        "excluded": total_excluded,
        "included": included,
    }


@mcp.tool()
async def get_prisma_status(project_path: str = "") -> dict[str, Any]:
    """Get the current PRISMA flow status summary.

    Args:
        project_path: Path to the project directory. Leave empty to use the active project.

    Returns:
        Complete PRISMA flow numbers at each stage.
    """
    base_dir = _resolve_project_dir(project_path or None)
    flow = _load_flow(base_dir)
    if not flow:
        return {"error": "No review initialized. Call init_review first."}

    return {
        "title": flow.get("title", ""),
        "review_type": flow.get("review_type", ""),
        "protocol_id": flow.get("protocol_id", ""),
        "identification": {
            "databases_searched": len(flow["identification"]["database_searches"]),
            "total_records_databases": flow["identification"]["total_records_databases"],
            "total_records_other": flow["identification"]["total_records_other"],
            "searches": [
                {"database": s["database"], "count": s["results_count"], "date": s["date"]}
                for s in flow["identification"]["database_searches"]
            ],
        },
        "deduplication": {
            "before": flow["deduplication"]["before_count"],
            "after": flow["deduplication"]["after_count"],
            "removed": flow["deduplication"]["duplicates_removed"],
        },
        "screening_title_abstract": {
            "screened": flow["screening"]["title_abstract"]["screened"],
            "excluded": flow["screening"]["title_abstract"]["excluded"],
            "passed_to_full_text": flow["screening"]["title_abstract"]["included_to_full_text"],
        },
        "screening_full_text": {
            "assessed": flow["screening"]["full_text"]["assessed"],
            "excluded": flow["screening"]["full_text"]["excluded"],
            "excluded_reasons": flow["screening"]["full_text"]["excluded_reasons"],
            "included": flow["screening"]["full_text"]["included_in_review"],
        },
        "included": flow["included"],
        "updated_at": flow.get("updated_at", ""),
    }


@mcp.tool()
async def generate_prisma_diagram(project_path: str = "") -> dict[str, Any]:
    """Generate PRISMA 2020 flow diagram data for rendering.

    Returns structured data that can be rendered as a PRISMA flow diagram
    in Quarto/Mermaid or other visualization tools.

    Args:
        project_path: Path to the project directory. Leave empty to use the active project.

    Returns:
        Dictionary with all PRISMA boxes and their values, plus a Mermaid
        diagram string ready to paste into a Quarto document.
    """
    base_dir = _resolve_project_dir(project_path or None)
    flow = _load_flow(base_dir)
    if not flow:
        return {"error": "No review initialized. Call init_review first."}

    ident = flow["identification"]
    dedup = flow["deduplication"]
    screen_ta = flow["screening"]["title_abstract"]
    screen_ft = flow["screening"]["full_text"]
    included = flow["included"]

    # Build exclusion reason strings
    ta_reasons = "; ".join(f"{k} (n={v})" for k, v in screen_ta["excluded_reasons"].items())
    ft_reasons = "; ".join(f"{k} (n={v})" for k, v in screen_ft["excluded_reasons"].items())

    db_total = ident["total_records_databases"]
    other_total = ident["total_records_other"]
    after_dedup = dedup["after_count"]
    ta_excluded = screen_ta["excluded"]
    ft_assessed = screen_ft["assessed"]
    ft_excluded = screen_ft["excluded"]
    final_qual = included.get("qualitative_synthesis", 0)
    final_quant = included.get("quantitative_synthesis", 0)

    mermaid = f"""```mermaid
flowchart TD
    A["Records identified through<br/>database searching<br/>(n={db_total})"]
    B["Additional records from<br/>other sources<br/>(n={other_total})"]
    C["Records after duplicates removed<br/>(n={after_dedup})"]
    D["Records screened<br/>(n={screen_ta['screened']})"]
    E["Records excluded<br/>(n={ta_excluded})"]
    F["Full-text articles assessed<br/>for eligibility<br/>(n={ft_assessed})"]
    G["Full-text articles excluded<br/>(n={ft_excluded})<br/>{ft_reasons}"]
    H["Studies included in<br/>qualitative synthesis<br/>(n={final_qual})"]
    I["Studies included in<br/>quantitative synthesis<br/>(n={final_quant})"]

    A --> C
    B --> C
    C --> D
    D --> E
    D --> F
    F --> G
    F --> H
    H --> I
```"""

    return {
        "boxes": {
            "identification_databases": db_total,
            "identification_other": other_total,
            "after_deduplication": after_dedup,
            "screened_title_abstract": screen_ta["screened"],
            "excluded_title_abstract": ta_excluded,
            "excluded_ta_reasons": ta_reasons,
            "assessed_full_text": ft_assessed,
            "excluded_full_text": ft_excluded,
            "excluded_ft_reasons": ft_reasons,
            "included_qualitative": final_qual,
            "included_quantitative": final_quant,
        },
        "mermaid_diagram": mermaid,
    }


@mcp.tool()
async def export_prisma_checklist(
    standard: str = "prisma-2020",
    project_path: str = "",
) -> dict[str, Any]:
    """Generate a PRISMA reporting checklist with completion status.

    Args:
        standard: Checklist standard: 'prisma-2020', 'prisma-scr' (scoping reviews),
            or 'moose'. Default 'prisma-2020'.
        project_path: Path to the project directory. Leave empty to use the active project.

    Returns:
        Dictionary with checklist items, each showing section, item, and completion status.
    """
    base_dir = _resolve_project_dir(project_path or None)
    flow = _load_flow(base_dir)
    if not flow:
        return {"error": "No review initialized. Call init_review first."}

    has_searches = len(flow["identification"]["database_searches"]) > 0
    has_ta_screening = flow["screening"]["title_abstract"]["recorded_at"] is not None
    has_ft_screening = flow["screening"]["full_text"]["recorded_at"] is not None

    has_proto = bool(flow.get("protocol_id"))

    if standard == "prisma-2020":
        checklist = [
            _ci("Title", 1, "Identify the report as a systematic review"),
            _ci("Abstract", 2, "Structured summary"),
            _ci("Introduction", 3, "Rationale"),
            _ci("Introduction", 4, "Objectives with PICO"),
            _ci("Methods", 5, "Protocol and registration",
                "complete" if has_proto else "incomplete"),
            _ci("Methods", 6, "Eligibility criteria"),
            _ci("Methods", 7, "Information sources",
                "complete" if has_searches else "incomplete"),
            _ci("Methods", 8, "Search strategy",
                "complete" if has_searches else "incomplete"),
            _ci("Methods", 9, "Selection process",
                "complete" if has_ta_screening else "incomplete"),
            _ci("Methods", 10, "Data collection process"),
            _ci("Methods", 11, "Data items"),
            _ci("Methods", 12, "Study risk of bias assessment"),
            _ci("Methods", 13, "Effect measures"),
            _ci("Methods", 14, "Synthesis methods"),
            _ci("Methods", 15, "Reporting bias assessment"),
            _ci("Methods", 16, "Certainty assessment"),
            _ci("Results", 17, "Study selection (PRISMA flow)",
                "complete" if has_ft_screening else "incomplete"),
            _ci("Results", 18, "Study characteristics"),
            _ci("Results", 19, "Risk of bias in studies"),
            _ci("Results", 20, "Results of individual studies"),
            _ci("Results", 21, "Results of syntheses"),
            _ci("Results", 22, "Reporting biases"),
            _ci("Results", 23, "Certainty of evidence"),
            _ci("Discussion", 24, "Discussion"),
            _ci("Other", 25, "Registration and protocol",
                "complete" if has_proto else "incomplete"),
            _ci("Other", 26, "Support/funding"),
            _ci("Other", 27, "Competing interests"),
        ]
    elif standard == "prisma-scr":
        checklist = [
            _ci("Title", 1, "Identify as scoping review"),
            _ci("Abstract", 2, "Structured summary"),
            _ci("Introduction", 3, "Rationale"),
            _ci("Introduction", 4, "Objectives"),
            _ci("Methods", 5, "Protocol and registration",
                "complete" if has_proto else "incomplete"),
            _ci("Methods", 6, "Eligibility criteria (PCC)"),
            _ci("Methods", 7, "Information sources",
                "complete" if has_searches else "incomplete"),
            _ci("Methods", 8, "Search",
                "complete" if has_searches else "incomplete"),
            _ci("Methods", 9, "Selection of sources",
                "complete" if has_ta_screening else "incomplete"),
            _ci("Methods", 10, "Data charting process"),
            _ci("Methods", 11, "Data items"),
            _ci("Methods", 12, "Critical appraisal"),
            _ci("Methods", 13, "Synthesis of results"),
            _ci("Results", 14, "Selection of sources",
                "complete" if has_ft_screening else "incomplete"),
            _ci("Results", 15, "Characteristics of sources"),
            _ci("Results", 16, "Critical appraisal"),
            _ci("Results", 17, "Results of individual sources"),
            _ci("Results", 18, "Synthesis of results"),
            _ci("Discussion", 19, "Summary of evidence"),
            _ci("Discussion", 20, "Limitations"),
            _ci("Discussion", 21, "Conclusions"),
            _ci("Other", 22, "Funding"),
        ]
    elif standard == "moose":
        checklist = [
            _ci("Reporting of background", 1, "Problem definition"),
            _ci("Reporting of background", 2, "Hypothesis statement"),
            _ci("Reporting of background", 3,
                "Objective description"),
            _ci("Reporting of background", 4,
                "Type of study designs used"),
            _ci("Reporting of search strategy", 5,
                "Qualifications of searchers"),
            _ci("Reporting of search strategy", 6,
                "Search strategy including databases",
                "complete" if has_searches else "incomplete"),
            _ci("Reporting of search strategy", 7,
                "Effort to include all available studies"),
            _ci("Reporting of search strategy", 8,
                "Use of hand searching"),
            _ci("Reporting of search strategy", 9,
                "List of citations located and excluded",
                "complete" if has_ft_screening else "incomplete"),
            _ci("Reporting of methods", 10,
                "Description of relevance assessment"),
            _ci("Reporting of methods", 11,
                "Assessment of study quality"),
            _ci("Reporting of methods", 12,
                "Method of data extraction"),
            _ci("Reporting of methods", 13, "Statistical methods"),
            _ci("Reporting of results", 14,
                "Flow of studies (PRISMA diagram)",
                "complete" if has_ft_screening else "incomplete"),
            _ci("Reporting of results", 15,
                "Study characteristics"),
            _ci("Reporting of results", 16,
                "Quantitative data synthesis"),
            _ci("Reporting of discussion", 17,
                "Quantitative assessment of bias"),
            _ci("Reporting of discussion", 18,
                "Justification for exclusions"),
            _ci("Reporting of discussion", 19,
                "Assessment of quality of included studies"),
        ]
    else:
        return {
            "error": (
                f"Unknown standard: {standard}. "
                "Use 'prisma-2020', 'prisma-scr', or 'moose'."
            ),
        }

    completed = sum(1 for c in checklist if c["status"] == "complete")
    total = len(checklist)
    return {
        "standard": standard,
        "checklist": checklist,
        "progress": f"{completed}/{total} items auto-tracked as complete",
    }


def serve() -> None:
    """Run the PRISMA Tracker MCP server."""
    mcp.run(transport="stdio")
