"""Data models for parsed VS Code Copilot Chat sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ToolCall:
    """A single tool invocation within an AI response."""

    tool_id: str
    invocation_message: str = ""
    past_tense_message: str = ""
    is_complete: bool = True
    source_label: str = ""
    # Verbose-only fields
    result_input: str = ""
    result_output: str = ""
    is_error: bool = False


@dataclass
class ThinkingBlock:
    """An internal reasoning / thinking trace from the model."""

    content: str = ""


@dataclass
class ChatMessage:
    """A single request-response turn in a chat session."""

    request_id: str
    timestamp: datetime
    model_id: str = ""
    agent_name: str = ""
    user_text: str = ""
    # Response parts (in order)
    response_text: str = ""
    thinking_blocks: list[ThinkingBlock] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class ChatSession:
    """A complete parsed chat session."""

    session_id: str = ""
    title: str = ""
    creation_date: datetime | None = None
    model_id: str = ""
    version: int = 0
    messages: list[ChatMessage] = field(default_factory=list)
