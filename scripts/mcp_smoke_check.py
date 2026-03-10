#!/usr/bin/env python3
"""Run a lightweight MCP JSON-RPC smoke check against one local server.

This script validates that the local `project_tracker` MCP server can start and
respond to an `initialize` request. It is intentionally fast and low-impact.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    workspace_root = Path(__file__).resolve().parent.parent
    server_cwd = workspace_root / "mcp-servers" / "project-tracker" / "src"

    if not server_cwd.is_dir():
        print(json.dumps({"status": "fail", "error": f"missing server path: {server_cwd}"}, indent=2))
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
        print(json.dumps({"status": "timeout", "server": "project-tracker"}, indent=2))
        return 1
    except Exception as exc:  # pragma: no cover
        print(json.dumps({"status": "fail", "error": str(exc)}, indent=2))
        return 1

    ok = '"result"' in proc.stdout
    report = {
        "status": "ok" if ok else "fail",
        "server": "project-tracker",
    }
    if not ok:
        report["stdout"] = proc.stdout[:500]
        report["stderr"] = proc.stderr[:500]

    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
