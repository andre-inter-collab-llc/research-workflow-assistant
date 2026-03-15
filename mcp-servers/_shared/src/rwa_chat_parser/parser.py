"""JSONL parser for VS Code Copilot Chat session files.

Reads the undocumented JSONL format stored in:
  %APPDATA%/Code/User/workspaceStorage/<hash>/chatSessions/<session-id>.jsonl

JSONL entry kinds:
  kind 0 — Session metadata (version, model, sessionId, creationDate)
  kind 1 — State patches (title, input text, model state, follow-ups, etc.)
  kind 2 — Request/response data (the actual conversation turns)
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import ChatMessage, ChatSession, ThinkingBlock, ToolCall

logger = logging.getLogger(__name__)


def parse_session(path: Path) -> ChatSession:
    """Parse a VS Code Copilot Chat JSONL file into a ChatSession.

    Parameters
    ----------
    path:
        Absolute path to the ``.jsonl`` session file.

    Returns
    -------
    ChatSession with all messages populated.
    """
    session = ChatSession()
    # Accumulate request entries and response patches separately
    request_map: dict[int, dict[str, Any]] = {}  # index -> raw request dict
    response_patches: dict[int, list[Any]] = {}  # index -> accumulated response items

    with open(path, encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSON on line %d", line_no)
                continue

            kind = entry.get("kind")
            keys = entry.get("k", [])
            value = entry.get("v")

            if kind == 0:
                _parse_session_metadata(entry, session)
            elif kind == 1:
                _apply_state_patch(keys, value, session)
            elif kind == 2:
                _apply_data_entry(keys, value, request_map, response_patches)
            else:
                logger.debug("Unknown entry kind %s on line %d", kind, line_no)

    # Build ChatMessage objects from accumulated data
    session.messages = _build_messages(request_map, response_patches)

    # Backfill session model from first message if not set in metadata
    if not session.model_id and session.messages:
        session.model_id = session.messages[0].model_id

    return session


def _parse_session_metadata(entry: dict[str, Any], session: ChatSession) -> None:
    """Extract session-level metadata from a kind-0 entry."""
    v = entry.get("v", {})
    session.version = v.get("version", 0)
    session.session_id = v.get("sessionId", "")
    session.model_id = v.get("modelId", "")

    creation_ts = v.get("creationDate")
    if creation_ts and isinstance(creation_ts, (int, float)):
        session.creation_date = datetime.fromtimestamp(creation_ts / 1000, tz=UTC)


def _apply_state_patch(keys: list[str], value: Any, session: ChatSession) -> None:
    """Process kind-1 state patches (title, input text, etc.)."""
    if keys == ["customTitle"] and isinstance(value, str):
        session.title = value


def _apply_data_entry(
    keys: list[str],
    value: Any,
    request_map: dict[int, dict[str, Any]],
    response_patches: dict[int, list[Any]],
) -> None:
    """Process kind-2 data entries (requests and responses).

    kind-2 entries come in two forms:
      keys=["requests"]               -> new request(s) with inline response
      keys=["requests", N, "response"] -> response continuation for request index N
    """
    if keys == ["requests"] and isinstance(value, list):
        # New request entry — may contain multiple requests (usually 1)
        for raw_req in value:
            req_index = len(request_map)
            request_map[req_index] = raw_req
            # The initial request often contains response data inline
            inline_response = raw_req.get("response", [])
            if inline_response:
                response_patches.setdefault(req_index, []).extend(inline_response)

    elif (
        len(keys) == 3
        and keys[0] == "requests"
        and keys[2] == "response"
        and isinstance(value, list)
    ):
        try:
            idx = int(keys[1])
        except (ValueError, TypeError):
            return
        response_patches.setdefault(idx, []).extend(value)

    elif keys == ["pendingRequests"]:
        # Ignore pending request markers
        pass


def _build_messages(
    request_map: dict[int, dict[str, Any]],
    response_patches: dict[int, list[Any]],
) -> list[ChatMessage]:
    """Assemble ChatMessage objects from raw request/response data."""
    messages: list[ChatMessage] = []

    for idx in sorted(request_map.keys()):
        raw_req = request_map[idx]
        msg = _parse_request(raw_req)

        # Merge all response patches for this index
        all_response_items = response_patches.get(idx, [])
        _parse_response_items(all_response_items, msg)

        messages.append(msg)

    return messages


def _parse_request(raw: dict[str, Any]) -> ChatMessage:
    """Extract user request metadata into a ChatMessage."""
    timestamp_ms = raw.get("timestamp", 0)
    ts = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC) if timestamp_ms else datetime.now(UTC)

    agent = raw.get("agent", {})
    message = raw.get("message", {})

    return ChatMessage(
        request_id=raw.get("requestId", ""),
        timestamp=ts,
        model_id=raw.get("modelId", ""),
        agent_name=agent.get("name", "") if isinstance(agent, dict) else "",
        user_text=message.get("text", "") if isinstance(message, dict) else "",
    )


def _parse_response_items(items: list[Any], msg: ChatMessage) -> None:
    """Parse response content items and populate the ChatMessage."""
    text_parts: list[str] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        item_kind = item.get("kind")

        if item_kind == "thinking":
            content = item.get("value", "")
            # Skip empty thinking blocks (stop markers)
            if content.strip():
                msg.thinking_blocks.append(ThinkingBlock(content=content))

        elif item_kind == "toolInvocationSerialized":
            msg.tool_calls.append(_parse_tool_call(item))

        elif item_kind == "mcpServersStarting":
            # Internal housekeeping — skip
            continue

        elif item_kind == "inlineReference":
            # File references embedded in response — skip (decorative)
            continue

        elif item_kind is None or item_kind == "markdownContent":
            # Plain text content block
            value = item.get("value", "")
            if isinstance(value, str) and value.strip():
                text_parts.append(value)

        else:
            logger.debug("Unknown response item kind: %s", item_kind)

    msg.response_text = "".join(text_parts)


def _parse_tool_call(item: dict[str, Any]) -> ToolCall:
    """Parse a tool invocation entry."""
    tool_id = item.get("toolId", "")

    inv_msg = item.get("invocationMessage", {})
    inv_text = inv_msg.get("value", "") if isinstance(inv_msg, dict) else str(inv_msg)

    past_msg = item.get("pastTenseMessage", {})
    past_text = past_msg.get("value", "") if isinstance(past_msg, dict) else str(past_msg)

    source = item.get("source", {})
    source_label = source.get("label", "") if isinstance(source, dict) else ""

    tc = ToolCall(
        tool_id=tool_id,
        invocation_message=inv_text,
        past_tense_message=past_text,
        is_complete=bool(item.get("isComplete", True)),
        source_label=source_label,
    )

    # Verbose details from resultDetails (MCP tools)
    rd = item.get("resultDetails")
    if isinstance(rd, dict):
        tc.is_error = bool(rd.get("isError", False))
        tc.result_input = _flatten_result(rd.get("input", ""))
        tc.result_output = _flatten_result(rd.get("output", ""))

    # Terminal tool details
    tsd = item.get("toolSpecificData")
    if isinstance(tsd, dict):
        tsd_kind = tsd.get("kind")
        if tsd_kind == "terminal":
            cmd = tsd.get("commandLine", {})
            cmd_text = cmd.get("original", "") if isinstance(cmd, dict) else ""
            state = tsd.get("terminalCommandState", {})
            exit_code = state.get("exitCode") if isinstance(state, dict) else None
            output = tsd.get("terminalCommandOutput", {})
            out_text = output.get("text", "") if isinstance(output, dict) else ""
            tc.result_input = cmd_text
            tc.result_output = out_text
            if exit_code is not None:
                tc.result_output += f"\n[exit code: {exit_code}]"

    return tc


def _flatten_result(value: Any) -> str:
    """Flatten a result value to a string."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(item.get("value", str(item)))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(value) if value else ""
