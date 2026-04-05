"""Shared library for parsing and rendering VS Code Copilot Chat sessions.

Usage::

    from rwa_chat_parser import parse_session, render_qmd

    session = parse_session(Path("path/to/session.jsonl"))
    qmd_text = render_qmd(session, include_thinking=True, detail_level="full")
"""

from .models import ChatMessage, ChatSession, ClarificationQA, ThinkingBlock, ToolCall
from .parser import parse_session
from .renderer import render_qmd

__all__ = [
    "ClarificationQA",
    "ChatMessage",
    "ChatSession",
    "ThinkingBlock",
    "ToolCall",
    "parse_session",
    "render_qmd",
]
