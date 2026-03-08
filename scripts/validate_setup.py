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
import sys
from pathlib import Path


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
    """Check all 8 MCP server packages."""
    servers = {
        "pubmed": "pubmed_server",
        "openalex": "openalex_server",
        "semantic-scholar": "semantic_scholar_server",
        "europe-pmc": "europe_pmc_server",
        "crossref": "crossref_server",
        "zotero": "zotero_server",
        "prisma-tracker": "prisma_tracker",
        "project-tracker": "project_tracker",
    }
    return {name: _check_server_importable(mod) for name, mod in servers.items()}


def _check_env_keys(workspace_root: Path) -> dict:
    """Check which .env keys are configured (without revealing values)."""
    env_path = workspace_root / ".env"
    keys_to_check = [
        "NCBI_API_KEY",
        "OPENALEX_EMAIL",
        "S2_API_KEY",
        "CROSSREF_EMAIL",
        "ZOTERO_API_KEY",
        "ZOTERO_USER_ID",
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

    # List project directories (those containing project-tracking/project.yaml)
    projects = []
    if projects_root.is_dir():
        for child in sorted(projects_root.iterdir()):
            if child.is_dir() and child.name != ".gitkeep":
                has_tracking = (child / "project-tracking" / "project.yaml").exists()
                projects.append({
                    "name": child.name,
                    "initialized": has_tracking,
                })

    return {"status": "ok", "path": str(projects_root), "projects": projects}


def _check_optional_tool(command: str) -> dict:
    """Check if an optional CLI tool is available."""
    path = shutil.which(command)
    if path:
        return {"status": "available", "path": path}
    return {"status": "not-found"}


def main() -> None:
    """Run all checks and output a JSON report."""
    # Determine workspace root (parent of scripts/)
    workspace_root = Path(__file__).resolve().parent.parent

    report = {
        "python": _check_python_version(),
        "servers": _check_servers(),
        "env_file": "exists" if (workspace_root / ".env").exists() else "missing",
        "env_keys": _check_env_keys(workspace_root),
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
