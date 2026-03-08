"""Entry point for running the PubMed MCP server as a module."""

from .server import serve

if __name__ == "__main__":
    serve()
