#!/usr/bin/env python3
"""Run a lightweight MCP JSON-RPC smoke check against one local server.

This script validates that the local `project_tracker` MCP server can start and
respond to an `initialize` request. It is intentionally fast and low-impact.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _print_human_report(report: dict[str, str]) -> None:
    status = report.get("status", "fail")
    print("MCP Smoke Check")
    print("=" * 48)
    if status == "ok":
        print("[OK] project-tracker server responded to initialize")
    elif status == "timeout":
        print("[FAIL] project-tracker server timed out")
    else:
        print("[FAIL] project-tracker server did not respond correctly")

    if "error" in report:
        print(f"Error: {report['error']}")
    if "stdout" in report:
        print(f"stdout (truncated): {report['stdout']}")
    if "stderr" in report:
        print(f"stderr (truncated): {report['stderr']}")
    print("=" * 48)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a project-tracker MCP smoke check")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    args = parser.parse_args()

    workspace_root = Path(__file__).resolve().parent.parent
    server_cwd = workspace_root / "mcp-servers" / "project-tracker" / "src"

    if not server_cwd.is_dir():
        report = {"status": "fail", "error": f"missing server path: {server_cwd}"}
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            _print_human_report(report)
        return 1

    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "smoke-check", "version": "0.1"},
        },
    }
    init_payload = json.dumps(init_msg)
    wire_payload = f"Content-Length: {len(init_payload)}\r\n\r\n{init_payload}"

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "project_tracker"],
            input=wire_payload,
            capture_output=True,
            text=True,
            timeout=8,
            cwd=str(server_cwd),
        )
    except subprocess.TimeoutExpired:
        report = {"status": "timeout", "server": "project-tracker"}
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            _print_human_report(report)
        return 1
    except Exception as exc:  # pragma: no cover
        report = {"status": "fail", "error": str(exc)}
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            _print_human_report(report)
        return 1

    ok = '"result"' in proc.stdout
    report = {
        "status": "ok" if ok else "fail",
        "server": "project-tracker",
    }
    if not ok:
        report["stdout"] = proc.stdout[:500]
        report["stderr"] = proc.stderr[:500]

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human_report(report)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
