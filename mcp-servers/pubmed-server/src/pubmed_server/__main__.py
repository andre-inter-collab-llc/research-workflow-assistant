"""Entry point for running the PubMed MCP server as a module."""

from pathlib import Path

from dotenv import load_dotenv

# Walk up from this package to find .env at the workspace root
_dir = Path(__file__).resolve().parent
for _candidate in (_dir, *_dir.parents):
    if (_candidate / ".env").is_file():
        load_dotenv(_candidate / ".env")
        break

from .server import serve  # noqa: E402

if __name__ == "__main__":
    serve()
