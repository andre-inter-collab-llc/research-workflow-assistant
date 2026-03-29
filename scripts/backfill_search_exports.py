#!/usr/bin/env python3
"""Backfill search result exports from existing project search_results.db files.

This utility regenerates export files from the canonical SQLite store:
- data/search_results.xlsx

Usage examples:
  python scripts/backfill_search_exports.py --project-path my_projects/my-project
  python scripts/backfill_search_exports.py --all-projects
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

from rwa_result_store import export_results_excel


def _candidate_projects_from_workspace(workspace_root: Path) -> list[Path]:
    projects: list[Path] = []

    my_projects = workspace_root / "my_projects"
    if my_projects.is_dir():
        projects.extend([p for p in my_projects.iterdir() if p.is_dir()])

    admin_comms = workspace_root / "admin" / "communications"
    if admin_comms.is_dir():
        for child in admin_comms.iterdir():
            if child.is_dir() and (child / "data" / "search_results.db").exists():
                projects.append(child)

    return sorted(set(projects))


def _resolve_projects(
    workspace_root: Path,
    explicit_paths: Iterable[str],
    all_projects: bool,
) -> list[Path]:
    resolved: list[Path] = []

    for raw in explicit_paths:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = (workspace_root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        resolved.append(candidate)

    if all_projects:
        resolved.extend(_candidate_projects_from_workspace(workspace_root))

    unique = sorted(set(resolved))
    return [p for p in unique if p.is_dir()]


def _backfill_project(project_path: Path) -> dict[str, str | bool]:
    db_path = project_path / "data" / "search_results.db"
    if not db_path.exists():
        return {
            "project_path": str(project_path),
            "processed": False,
            "reason": "missing data/search_results.db",
        }

    excel_path = export_results_excel(str(project_path))

    return {
        "project_path": str(project_path),
        "processed": True,
        "excel_path": excel_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill search exports from existing project DB files",
    )
    parser.add_argument(
        "--project-path",
        action="append",
        default=[],
        help="Project directory path (repeatable). "
        "Relative paths are resolved from workspace root.",
    )
    parser.add_argument(
        "--all-projects",
        action="store_true",
        help="Process all projects under my_projects/ and "
        "admin/communications/* containing a search DB.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    args = parser.parse_args()

    workspace_root = Path(__file__).resolve().parent.parent
    targets = _resolve_projects(workspace_root, args.project_path, args.all_projects)

    if not targets:
        message = {
            "status": "no_targets",
            "message": "No valid project directories were provided or discovered.",
        }
        if args.json:
            print(json.dumps(message, indent=2))
        else:
            print(message["message"])
        return 1

    results = [_backfill_project(path) for path in targets]
    processed = sum(1 for r in results if r.get("processed"))

    report = {
        "status": "ok",
        "processed_projects": processed,
        "total_targets": len(targets),
        "results": results,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Processed {processed} of {len(targets)} target project(s).")
        for item in results:
            prefix = "[OK]" if item.get("processed") else "[SKIP]"
            if item.get("processed"):
                print(f"{prefix} {item['project_path']}")
                print(f"      xlsx: {item.get('excel_path', '')}")
            else:
                print(f"{prefix} {item['project_path']} ({item.get('reason', 'not processed')})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
