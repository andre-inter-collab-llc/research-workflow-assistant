#!/usr/bin/env python3
"""Validate the research-workflow-assistant environment setup.

Run from the repository root:
    python scripts/validate_setup.py

Outputs a JSON report of the environment status.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Load .env so that env key checks reflect what servers will actually see
_workspace_root = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv

    _env_file = _workspace_root / ".env"
    if _env_file.is_file():
        load_dotenv(_env_file)
except ImportError:
    pass  # python-dotenv not installed yet; env key checks will use system env only


def _check_python_version() -> dict:
    """Check Python version >= 3.11."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    ok = version >= (3, 11)
    return {"status": "ok" if ok else "fail", "version": version_str}


def _check_server_importable(module_name: str) -> dict:
    """Check if an MCP server package is importable."""
    try:
        importlib.import_module(module_name)
        return {"status": "ok"}
    except ImportError as e:
        return {"status": "fail", "error": str(e)}


def _check_servers() -> dict:
    """Check all 9 MCP server packages."""
    servers = {
        "pubmed": "pubmed_server",
        "openalex": "openalex_server",
        "semantic-scholar": "semantic_scholar_server",
        "europe-pmc": "europe_pmc_server",
        "crossref": "crossref_server",
        "zotero": "zotero_server",
        "zotero-local": "zotero_local_server",
        "prisma-tracker": "prisma_tracker",
        "project-tracker": "project_tracker",
    }
    return {name: _check_server_importable(mod) for name, mod in servers.items()}


def _check_env_keys(workspace_root: Path) -> dict:
    """Check which .env keys are configured (without revealing values)."""
    env_path = workspace_root / ".env"
    keys_to_check = [
        "NCBI_API_KEY",
        "OPENALEX_API_KEY",
        "OPENALEX_EMAIL",
        "S2_API_KEY",
        "S2_API_KEY_STATUS",
        "CROSSREF_EMAIL",
        "ZOTERO_API_KEY",
        "ZOTERO_USER_ID",
        "ZOTERO_DATA_DIR",
        "PROJECTS_ROOT",
    ]
    result: dict[str, str] = {}

    if not env_path.exists():
        return {k: "missing" for k in keys_to_check}

    # Parse .env file (simple key=value, no shell expansion)
    env_vars: dict[str, str] = {}
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env_vars[key.strip()] = value.strip()

    for key in keys_to_check:
        value = env_vars.get(key, "")
        if value:
            result[key] = "set"
        else:
            result[key] = "empty"

    # OPENALEX_EMAIL is optional when OPENALEX_API_KEY is configured.
    if result.get("OPENALEX_EMAIL") == "empty" and result.get("OPENALEX_API_KEY") == "set":
        result["OPENALEX_EMAIL"] = "optional"

    # Treat Semantic Scholar key as intentionally pending when explicitly marked.
    if result.get("S2_API_KEY") == "empty" and result.get("S2_API_KEY_STATUS") == "set":
        result["S2_API_KEY"] = "pending"

    return result


def _check_projects_dir(workspace_root: Path) -> dict:
    """Check if the projects directory exists and list projects."""
    # Determine projects root from .env or default
    env_keys = _check_env_keys(workspace_root)
    projects_root_str = os.environ.get("PROJECTS_ROOT", "")

    if not projects_root_str:
        # Try reading from .env
        env_path = workspace_root / ".env"
        if env_path.exists():
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("PROJECTS_ROOT="):
                        projects_root_str = line.split("=", 1)[1].strip()
                        break

    if not projects_root_str:
        projects_root_str = "./my_projects"

    projects_root = Path(projects_root_str)
    if not projects_root.is_absolute():
        projects_root = workspace_root / projects_root

    if not projects_root.exists():
        return {"status": "missing", "path": str(projects_root), "projects": []}

    # List project directories and detect whether each appears initialized.
    # Support both tracker-based initialization and lightweight project config files.
    projects = []
    if projects_root.is_dir():
        for child in sorted(projects_root.iterdir()):
            if child.is_dir() and child.name != ".gitkeep":
                has_project_tracking = (child / "project-tracking" / "project.yaml").exists()
                has_review_tracking = (child / "review-tracking" / "prisma-flow.json").exists()
                has_project_config = (child / "project-config.yaml").exists()
                has_ai_log = (child / "ai-contributions-log.md").exists()

                # Mark as initialized if any supported project marker is present.
                is_initialized = (
                    has_project_tracking
                    or has_review_tracking
                    or has_project_config
                    or has_ai_log
                )
                projects.append({
                    "name": child.name,
                    "initialized": is_initialized,
                })

    return {"status": "ok", "path": str(projects_root), "projects": projects}


def _check_optional_tool(command: str) -> dict:
    """Check if an optional CLI tool is available."""
    path = shutil.which(command)
    if path:
        return {"status": "available", "path": path}
    return {"status": "not-found"}


def _check_zotero_local() -> dict:
    """Check if the local Zotero data directory is accessible."""
    try:
        from zotero_local_server import zotero_db
    except ImportError:
        return {"status": "skip", "reason": "zotero_local_server not installed"}

    data_dir = zotero_db.detect_zotero_data_dir()
    if data_dir is None:
        return {"status": "not-found", "message": "Zotero data directory not detected. Set ZOTERO_DATA_DIR."}

    version = zotero_db.get_zotero_version(data_dir)
    storage = data_dir / "storage"
    pdf_count = 0
    if storage.is_dir():
        for child in storage.iterdir():
            if child.is_dir():
                for f in child.iterdir():
                    if f.suffix.lower() == ".pdf":
                        pdf_count += 1

    result: dict = {
        "status": "ok",
        "data_dir": str(data_dir),
        "zotero_version": version,
        "pdf_count": pdf_count,
    }

    # Check for Better BibTeX (non-blocking)
    try:
        import httpx

        resp = httpx.post(
            "http://localhost:23119/better-bibtex/json-rpc",
            json={"jsonrpc": "2.0", "method": "user.groups", "params": [], "id": 1},
            timeout=3.0,
        )
        result["better_bibtex"] = "available" if resp.status_code == 200 else "not-running"
    except Exception:
        result["better_bibtex"] = "not-running"

    return result


def _check_server_health(module_name: str, workspace_root: Path) -> dict:
    """Start an MCP server process and verify it responds to a JSON-RPC initialize."""
    python = sys.executable
    server_map = {
        "pubmed_server": "pubmed-server",
        "openalex_server": "openalex-server",
        "semantic_scholar_server": "semantic-scholar-server",
        "europe_pmc_server": "europe-pmc-server",
        "crossref_server": "crossref-server",
        "zotero_server": "zotero-server",
        "zotero_local_server": "zotero-local-server",
        "prisma_tracker": "prisma-tracker",
        "project_tracker": "project-tracker",
    }
    dir_name = server_map.get(module_name, module_name)
    cwd = workspace_root / "mcp-servers" / dir_name / "src"
    if not cwd.is_dir():
        return {"status": "skip", "reason": f"source directory not found: {cwd}"}

    init_msg = (
        '{"jsonrpc":"2.0","id":1,"method":"initialize",'
        '"params":{"protocolVersion":"2024-11-05",'
        '"capabilities":{},"clientInfo":{"name":"validate","version":"0.1"}}}'
    )
    try:
        proc = subprocess.run(
            [python, "-m", module_name],
            input=f"Content-Length: {len(init_msg)}\r\n\r\n{init_msg}",
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(cwd),
        )
        if '"result"' in proc.stdout:
            return {"status": "ok"}
        return {
            "status": "fail",
            "stdout": proc.stdout[:500],
            "stderr": proc.stderr[:500],
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "fail", "error": str(e)}


def _check_all_server_health(workspace_root: Path) -> dict:
    """Run health checks for all MCP servers."""
    modules = [
        "pubmed_server",
        "openalex_server",
        "semantic_scholar_server",
        "europe_pmc_server",
        "crossref_server",
        "zotero_server",
        "zotero_local_server",
        "prisma_tracker",
        "project_tracker",
    ]
    return {mod: _check_server_health(mod, workspace_root) for mod in modules}


def main() -> None:
    """Run all checks and output a JSON report."""
    # Determine workspace root (parent of scripts/)
    workspace_root = Path(__file__).resolve().parent.parent

    report = {
        "python": _check_python_version(),
        "servers": _check_servers(),
        "server_health": _check_all_server_health(workspace_root),
        "env_file": "exists" if (workspace_root / ".env").exists() else "missing",
        "env_keys": _check_env_keys(workspace_root),
        "zotero_local": _check_zotero_local(),
        "projects_dir": _check_projects_dir(workspace_root),
        "optional_tools": {
            "r": _check_optional_tool("Rscript"),
            "quarto": _check_optional_tool("quarto"),
            "git": _check_optional_tool("git"),
        },
    }

    # Determine overall status
    python_ok = report["python"]["status"] == "ok"
    servers_ok = all(s["status"] == "ok" for s in report["servers"].values())
    env_ok = report["env_file"] == "exists"

    if python_ok and servers_ok and env_ok:
        report["overall"] = "ready"
    elif python_ok and servers_ok:
        report["overall"] = "needs-configuration"
    else:
        report["overall"] = "needs-setup"

    json.dump(report, sys.stdout, indent=2)
    print()  # trailing newline


if __name__ == "__main__":
    main()
