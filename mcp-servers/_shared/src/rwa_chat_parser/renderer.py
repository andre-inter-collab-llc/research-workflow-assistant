"""Render a parsed ChatSession to Quarto Markdown (.qmd) format."""

from __future__ import annotations

import html
import re
from datetime import datetime
from textwrap import dedent

from .models import ChatMessage, ChatSession, ThinkingBlock, ToolCall

# ANSI escape sequence stripper
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\[\?[0-9]*[a-zA-Z]")


def render_qmd(
    session: ChatSession,
    *,
    include_thinking: bool = True,
    detail_level: str = "summary",
) -> str:
    """Render a ChatSession to a QMD string.

    Parameters
    ----------
    session:
        Parsed chat session.
    include_thinking:
        If True (default), include model thinking blocks in collapsible
        ``<details>`` sections. If False, omit them entirely.
    detail_level:
        ``"summary"`` (default) shows only tool invocation labels.
        ``"full"`` includes tool inputs and outputs.
    """
    parts: list[str] = []

    # YAML front matter
    parts.append(_yaml_header(session))
    parts.append("")

    # Session summary
    parts.append(f"**Session ID:** `{session.session_id}`  ")
    parts.append(f"**Model:** `{session.model_id}`  ")
    if session.creation_date:
        parts.append(
            f"**Date:** {session.creation_date.strftime('%Y-%m-%d %H:%M UTC')}  "
        )
    parts.append(f"**Turns:** {len(session.messages)}")
    parts.append("")
    parts.append("---")
    parts.append("")

    # Messages
    for i, msg in enumerate(session.messages, start=1):
        parts.append(f"## Turn {i}")
        parts.append("")
        parts.append(_render_message(msg, include_thinking=include_thinking, detail_level=detail_level))
        parts.append("")

    return "\n".join(parts)


def _yaml_header(session: ChatSession) -> str:
    """Generate the YAML front matter block."""
    title = session.title or "Chat Session Log"
    # Escape quotes in title for YAML
    safe_title = title.replace('"', '\\"')
    date_str = (
        session.creation_date.strftime("%Y-%m-%d")
        if session.creation_date
        else "today"
    )

    # Collect unique agent names
    agents = sorted({m.agent_name for m in session.messages if m.agent_name})
    agents_yaml = ", ".join(f'"{a}"' for a in agents) if agents else ""

    return dedent(f"""\
        ---
        title: "{safe_title}"
        date: "{date_str}"
        format:
          html:
            toc: true
            self-contained: true
            code-fold: true
        params:
          session_id: "{session.session_id}"
          model: "{session.model_id}"
          agents_used: [{agents_yaml}]
        ---""")


def _render_message(
    msg: ChatMessage,
    *,
    include_thinking: bool,
    detail_level: str,
) -> str:
    """Render a single request-response turn."""
    parts: list[str] = []

    # Timestamp
    ts_str = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    parts.append(f"*{ts_str}*")
    if msg.agent_name:
        parts.append(f" | Agent: **{msg.agent_name}**")
    if msg.model_id:
        parts.append(f" | Model: `{msg.model_id}`")
    parts.append("")
    parts.append("")

    # User message
    parts.append("### User")
    parts.append("")
    user_text = msg.user_text.strip()
    if user_text:
        parts.append(user_text)
    else:
        parts.append("*(empty message)*")
    parts.append("")

    # AI response
    parts.append("### Assistant")
    parts.append("")

    # Thinking blocks (before main response)
    if include_thinking and msg.thinking_blocks:
        for tb in msg.thinking_blocks:
            parts.append(_render_thinking(tb))
            parts.append("")

    # Tool calls
    if msg.tool_calls:
        parts.append(_render_tool_calls(msg.tool_calls, detail_level=detail_level))
        parts.append("")

    # Response text
    if msg.response_text.strip():
        parts.append(msg.response_text.strip())
    elif not msg.tool_calls:
        parts.append("*(no text response)*")
    parts.append("")

    parts.append("---")
    return "\n".join(parts)


def _render_thinking(tb: ThinkingBlock) -> str:
    """Render a thinking block in a collapsible <details> section."""
    content = tb.content.strip()
    return dedent(f"""\
        <details>
        <summary>Model thinking</summary>

        {content}

        </details>""")


def _render_tool_calls(
    calls: list[ToolCall], *, detail_level: str
) -> str:
    """Render tool calls as a list."""
    parts: list[str] = []
    parts.append("**Tool calls:**")
    parts.append("")

    for tc in calls:
        label = tc.past_tense_message or tc.invocation_message or tc.tool_id
        # Clean up markdown link artifacts from VS Code's display format
        label = label.strip()
        if not label:
            label = tc.tool_id

        source_tag = f" *({tc.source_label})*" if tc.source_label else ""
        parts.append(f"- {label}{source_tag}")

        if detail_level == "full" and (tc.result_input or tc.result_output):
            parts.append("")
            parts.append("  <details>")
            parts.append(f"  <summary>Details: {tc.tool_id}</summary>")
            parts.append("")
            if tc.result_input:
                clean_input = _strip_ansi(tc.result_input)
                parts.append("  **Input:**")
                parts.append(f"  ```\n  {clean_input}\n  ```")
            if tc.result_output:
                clean_output = _strip_ansi(tc.result_output)
                # Truncate very large outputs
                if len(clean_output) > 2000:
                    clean_output = clean_output[:2000] + "\n  ... (truncated)"
                parts.append("  **Output:**")
                parts.append(f"  ```\n  {clean_output}\n  ```")
            if tc.is_error:
                parts.append("  **Status:** Error")
            parts.append("")
            parts.append("  </details>")

    return "\n".join(parts)


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from terminal output."""
    return _ANSI_RE.sub("", text)
