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
from datetime import datetime, timezone
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
            p = Path(PROJECTS_ROOT).resolve() / p
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
    return datetime.now(timezone.utc).isoformat()


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
    root = Path(PROJECTS_ROOT).resolve()
    reviews: list[dict[str, Any]] = []

    if not root.exists():
        return {"projects_root": str(root), "reviews": [], "note": "PROJECTS_ROOT does not exist yet."}

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

    return {"status": "initialized", "title": title, "review_type": review_type, "path": str(base_dir)}


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
    has_dedup = flow["deduplication"]["recorded_at"] is not None
    has_ta_screening = flow["screening"]["title_abstract"]["recorded_at"] is not None
    has_ft_screening = flow["screening"]["full_text"]["recorded_at"] is not None

    if standard == "prisma-2020":
        checklist = [
            {"section": "Title", "item": 1, "description": "Identify the report as a systematic review", "status": "manual"},
            {"section": "Abstract", "item": 2, "description": "Structured summary", "status": "manual"},
            {"section": "Introduction", "item": 3, "description": "Rationale", "status": "manual"},
            {"section": "Introduction", "item": 4, "description": "Objectives with PICO", "status": "manual"},
            {"section": "Methods", "item": 5, "description": "Protocol and registration", "status": "complete" if flow.get("protocol_id") else "incomplete"},
            {"section": "Methods", "item": 6, "description": "Eligibility criteria", "status": "manual"},
            {"section": "Methods", "item": 7, "description": "Information sources", "status": "complete" if has_searches else "incomplete"},
            {"section": "Methods", "item": 8, "description": "Search strategy", "status": "complete" if has_searches else "incomplete"},
            {"section": "Methods", "item": 9, "description": "Selection process", "status": "complete" if has_ta_screening else "incomplete"},
            {"section": "Methods", "item": 10, "description": "Data collection process", "status": "manual"},
            {"section": "Methods", "item": 11, "description": "Data items", "status": "manual"},
            {"section": "Methods", "item": 12, "description": "Study risk of bias assessment", "status": "manual"},
            {"section": "Methods", "item": 13, "description": "Effect measures", "status": "manual"},
            {"section": "Methods", "item": 14, "description": "Synthesis methods", "status": "manual"},
            {"section": "Methods", "item": 15, "description": "Reporting bias assessment", "status": "manual"},
            {"section": "Methods", "item": 16, "description": "Certainty assessment", "status": "manual"},
            {"section": "Results", "item": 17, "description": "Study selection (PRISMA flow)", "status": "complete" if has_ft_screening else "incomplete"},
            {"section": "Results", "item": 18, "description": "Study characteristics", "status": "manual"},
            {"section": "Results", "item": 19, "description": "Risk of bias in studies", "status": "manual"},
            {"section": "Results", "item": 20, "description": "Results of individual studies", "status": "manual"},
            {"section": "Results", "item": 21, "description": "Results of syntheses", "status": "manual"},
            {"section": "Results", "item": 22, "description": "Reporting biases", "status": "manual"},
            {"section": "Results", "item": 23, "description": "Certainty of evidence", "status": "manual"},
            {"section": "Discussion", "item": 24, "description": "Discussion", "status": "manual"},
            {"section": "Other", "item": 25, "description": "Registration and protocol", "status": "complete" if flow.get("protocol_id") else "incomplete"},
            {"section": "Other", "item": 26, "description": "Support/funding", "status": "manual"},
            {"section": "Other", "item": 27, "description": "Competing interests", "status": "manual"},
        ]
    elif standard == "prisma-scr":
        checklist = [
            {"section": "Title", "item": 1, "description": "Identify as scoping review", "status": "manual"},
            {"section": "Abstract", "item": 2, "description": "Structured summary", "status": "manual"},
            {"section": "Introduction", "item": 3, "description": "Rationale", "status": "manual"},
            {"section": "Introduction", "item": 4, "description": "Objectives", "status": "manual"},
            {"section": "Methods", "item": 5, "description": "Protocol and registration", "status": "complete" if flow.get("protocol_id") else "incomplete"},
            {"section": "Methods", "item": 6, "description": "Eligibility criteria (PCC)", "status": "manual"},
            {"section": "Methods", "item": 7, "description": "Information sources", "status": "complete" if has_searches else "incomplete"},
            {"section": "Methods", "item": 8, "description": "Search", "status": "complete" if has_searches else "incomplete"},
            {"section": "Methods", "item": 9, "description": "Selection of sources", "status": "complete" if has_ta_screening else "incomplete"},
            {"section": "Methods", "item": 10, "description": "Data charting process", "status": "manual"},
            {"section": "Methods", "item": 11, "description": "Data items", "status": "manual"},
            {"section": "Methods", "item": 12, "description": "Critical appraisal", "status": "manual"},
            {"section": "Methods", "item": 13, "description": "Synthesis of results", "status": "manual"},
            {"section": "Results", "item": 14, "description": "Selection of sources", "status": "complete" if has_ft_screening else "incomplete"},
            {"section": "Results", "item": 15, "description": "Characteristics of sources", "status": "manual"},
            {"section": "Results", "item": 16, "description": "Critical appraisal", "status": "manual"},
            {"section": "Results", "item": 17, "description": "Results of individual sources", "status": "manual"},
            {"section": "Results", "item": 18, "description": "Synthesis of results", "status": "manual"},
            {"section": "Discussion", "item": 19, "description": "Summary of evidence", "status": "manual"},
            {"section": "Discussion", "item": 20, "description": "Limitations", "status": "manual"},
            {"section": "Discussion", "item": 21, "description": "Conclusions", "status": "manual"},
            {"section": "Other", "item": 22, "description": "Funding", "status": "manual"},
        ]
    elif standard == "moose":
        checklist = [
            {"section": "Reporting of background", "item": 1, "description": "Problem definition", "status": "manual"},
            {"section": "Reporting of background", "item": 2, "description": "Hypothesis statement", "status": "manual"},
            {"section": "Reporting of background", "item": 3, "description": "Objective description", "status": "manual"},
            {"section": "Reporting of background", "item": 4, "description": "Type of study designs used", "status": "manual"},
            {"section": "Reporting of search strategy", "item": 5, "description": "Qualifications of searchers", "status": "manual"},
            {"section": "Reporting of search strategy", "item": 6, "description": "Search strategy including databases", "status": "complete" if has_searches else "incomplete"},
            {"section": "Reporting of search strategy", "item": 7, "description": "Effort to include all available studies", "status": "manual"},
            {"section": "Reporting of search strategy", "item": 8, "description": "Use of hand searching", "status": "manual"},
            {"section": "Reporting of search strategy", "item": 9, "description": "List of citations located and those excluded with reasons", "status": "complete" if has_ft_screening else "incomplete"},
            {"section": "Reporting of methods", "item": 10, "description": "Description of relevance assessment", "status": "manual"},
            {"section": "Reporting of methods", "item": 11, "description": "Assessment of study quality", "status": "manual"},
            {"section": "Reporting of methods", "item": 12, "description": "Method of data extraction", "status": "manual"},
            {"section": "Reporting of methods", "item": 13, "description": "Statistical methods", "status": "manual"},
            {"section": "Reporting of results", "item": 14, "description": "Flow of studies (PRISMA diagram)", "status": "complete" if has_ft_screening else "incomplete"},
            {"section": "Reporting of results", "item": 15, "description": "Study characteristics", "status": "manual"},
            {"section": "Reporting of results", "item": 16, "description": "Quantitative data synthesis", "status": "manual"},
            {"section": "Reporting of discussion", "item": 17, "description": "Quantitative assessment of bias", "status": "manual"},
            {"section": "Reporting of discussion", "item": 18, "description": "Justification for exclusions", "status": "manual"},
            {"section": "Reporting of discussion", "item": 19, "description": "Assessment of quality of included studies", "status": "manual"},
        ]
    else:
        return {"error": f"Unknown standard: {standard}. Use 'prisma-2020', 'prisma-scr', or 'moose'."}

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
