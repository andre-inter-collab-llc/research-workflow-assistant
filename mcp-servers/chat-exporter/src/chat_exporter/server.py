"""Chat Exporter MCP Server implementation.

Exports VS Code Copilot Chat session files (.jsonl) to Quarto Markdown (.qmd)
documents for research reproducibility.

Tools:
  - ``list_sessions`` — discover available chat sessions for this workspace
  - ``export_session`` — export a specific session to QMD
  - ``export_latest`` — export the most recent session to QMD
"""

from __future__ import annotations

import json
import os
import platform
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from mcp.server.fastmcp import FastMCP
from rwa_chat_parser import parse_session, render_qmd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_DIR = os.environ.get("PROJECT_DIR", ".")
PROJECTS_ROOT = os.environ.get("PROJECTS_ROOT", "./my_projects")

mcp = FastMCP(
    "chat-exporter",
    instructions=(
        "Export VS Code Copilot Chat sessions to Quarto Markdown (.qmd) files "
        "for research reproducibility. Supports listing sessions, exporting "
        "specific sessions, and exporting the latest session."
    ),
)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _vscode_storage_root() -> Path:
    """Return the VS Code workspaceStorage root for the current OS."""
    system = platform.system()
    if system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata) / "Code" / "User" / "workspaceStorage"
    elif system == "Darwin":
        home = Path.home()
        return home / "Library" / "Application Support" / "Code" / "User" / "workspaceStorage"
    else:
        config = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        return Path(config) / "Code" / "User" / "workspaceStorage"
    raise RuntimeError("Cannot determine VS Code storage path")


def _normalize_uri(uri: str) -> str:
    """Normalize a file URI for reliable comparison."""
    return unquote(uri).lower().rstrip("/")


def _find_workspace_hash(storage_root: Path, workspace_path: Path) -> str | None:
    """Find the workspace storage hash for a given workspace path."""
    if not storage_root.is_dir():
        return None
    workspace_uri = _normalize_uri(workspace_path.resolve().as_uri())
    for entry in storage_root.iterdir():
        if not entry.is_dir():
            continue
        ws_file = entry / "workspace.json"
        if not ws_file.is_file():
            continue
        try:
            data = json.loads(ws_file.read_text(encoding="utf-8"))
            folder = data.get("folder", "")
            if _normalize_uri(folder) == workspace_uri:
                return entry.name
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _discover_sessions(workspace_path: Path) -> list[dict[str, Any]]:
    """Discover chat sessions for the given workspace."""
    storage_root = _vscode_storage_root()
    ws_hash = _find_workspace_hash(storage_root, workspace_path)
    if not ws_hash:
        return []

    sessions_dir = storage_root / ws_hash / "chatSessions"
    if not sessions_dir.is_dir():
        return []

    results: list[dict[str, Any]] = []
    for jsonl_file in sorted(sessions_dir.glob("*.jsonl")):
        info: dict[str, Any] = {
            "session_id": jsonl_file.stem,
            "path": str(jsonl_file),
            "title": "",
            "creation_date": "",
            "model_id": "",
            "line_count": 0,
        }
        try:
            with open(jsonl_file, encoding="utf-8") as fh:
                line_count = 0
                for raw_line in fh:
                    line_count += 1
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    try:
                        entry = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue
                    kind = entry.get("kind")
                    keys = entry.get("k", [])
                    value = entry.get("v")
                    if kind == 0:
                        v = entry.get("v", {})
                        info["model_id"] = v.get("modelId", "")
                        ts = v.get("creationDate")
                        if ts and isinstance(ts, (int, float)):
                            dt = datetime.fromtimestamp(ts / 1000, tz=UTC)
                            info["creation_date"] = dt.strftime("%Y-%m-%d %H:%M UTC")
                    elif kind == 1 and keys == ["customTitle"]:
                        if isinstance(value, str):
                            info["title"] = value
                info["line_count"] = line_count
        except OSError:
            continue
        results.append(info)

    results.sort(key=lambda x: x["creation_date"], reverse=True)
    return results


def _resolve_workspace() -> Path:
    """Resolve the workspace root directory."""
    return Path(PROJECT_DIR).resolve()


def _resolve_project(project_path: str | None) -> Path | None:
    """Resolve a project directory from the given path."""
    if not project_path:
        return None
    p = Path(project_path)
    if not p.is_absolute():
        p = _resolve_workspace() / p
    return p.resolve()


def _slugify(text: str, max_len: int = 50) -> str:
    """Create a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len] if text else "untitled"


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def list_sessions() -> str:
    """List available VS Code Copilot Chat sessions for this workspace.

    Returns a JSON array of sessions with id, title, date, model, and line count.
    """
    workspace = _resolve_workspace()
    sessions = _discover_sessions(workspace)
    return json.dumps(sessions, indent=2)


@mcp.tool()
def export_session(
    session_id: str,
    project_path: str | None = None,
    output_path: str | None = None,
    detail_level: str = "summary",
    include_thinking: bool = True,
) -> str:
    """Export a VS Code Copilot Chat session to a QMD file.

    Parameters
    ----------
    session_id:
        The session UUID to export.
    project_path:
        Target project directory. Output goes to ``<project>/chat-logs/``.
        Relative paths are resolved against the workspace root.
    output_path:
        Explicit output file path. Overrides project_path if both given.
    detail_level:
        ``"summary"`` (default) or ``"full"`` for tool call details.
    include_thinking:
        Include model thinking blocks in collapsible sections. Default True.
    """
    workspace = _resolve_workspace()
    sessions = _discover_sessions(workspace)

    matches = [s for s in sessions if s["session_id"] == session_id]
    if not matches:
        return json.dumps({"error": f"Session '{session_id}' not found"})

    target = matches[0]
    session_path = Path(target["path"])

    # Determine output
    if output_path:
        out = Path(output_path)
        if not out.is_absolute():
            out = workspace / out
    elif project_path:
        proj = _resolve_project(project_path)
        if proj is None:
            return json.dumps({"error": "Could not resolve project path"})
        title_slug = _slugify(target["title"]) if target["title"] else session_id[:8]
        date_prefix = target["creation_date"][:10] if target["creation_date"] else "undated"
        filename = f"session-{date_prefix}-{title_slug}.qmd"
        out = proj / "chat-logs" / filename
    else:
        return json.dumps({"error": "Specify project_path or output_path"})

    session = parse_session(session_path)
    qmd = render_qmd(session, include_thinking=include_thinking, detail_level=detail_level)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(qmd, encoding="utf-8")

    return json.dumps(
        {
            "exported": str(out),
            "session_id": session_id,
            "title": target["title"],
            "turns": len(session.messages),
            "size_bytes": out.stat().st_size,
        }
    )


@mcp.tool()
def export_latest(
    project_path: str,
    detail_level: str = "summary",
    include_thinking: bool = True,
) -> str:
    """Export the most recent chat session to a QMD file.

    Parameters
    ----------
    project_path:
        Target project directory. Output goes to ``<project>/chat-logs/``.
    detail_level:
        ``"summary"`` (default) or ``"full"`` for tool call details.
    include_thinking:
        Include model thinking blocks in collapsible sections. Default True.
    """
    workspace = _resolve_workspace()
    sessions = _discover_sessions(workspace)
    if not sessions:
        return json.dumps({"error": "No chat sessions found"})

    latest = sessions[0]
    return export_session(
        session_id=latest["session_id"],
        project_path=project_path,
        detail_level=detail_level,
        include_thinking=include_thinking,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def serve() -> None:
    """Run the Chat Exporter MCP server."""
    mcp.run(transport="stdio")
