# -*- coding: utf-8 -*-

#   types.py

"""
### Description:
Shared data types and factory helpers for the 02_05_agent module.

All types are represented as TypedDicts for lightweight, dict-compatible
structures that match the Responses API JSON format directly.

---

@Author:        Claude Sonnet 4.6
@Created on:    25.03.2026
@Based on:      src/types.ts


"""

from typing import Any, Optional
from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Message types (Responses API input format)
# ---------------------------------------------------------------------------


class TextMessage(TypedDict):
    """A plain text conversation turn (user, assistant, system, developer)."""

    role: str  # 'user' | 'assistant' | 'system' | 'developer'
    content: Optional[str]


class FunctionCallItem(TypedDict):
    """A tool/function call emitted by the model."""

    type: str  # always 'function_call'
    call_id: str
    name: str
    arguments: str  # JSON-encoded argument object


class FunctionCallOutputItem(TypedDict):
    """The result of a tool/function call returned to the model."""

    type: str  # always 'function_call_output'
    call_id: str
    output: str


# Union alias — any single item in the conversation input list
Message = dict  # TextMessage | FunctionCallItem | FunctionCallOutputItem


# ---------------------------------------------------------------------------
# Message type guards
# ---------------------------------------------------------------------------


def is_text_message(m: dict) -> bool:
    """Return True if ``m`` is a TextMessage (has ``role``, no ``type``)."""
    return "role" in m and "type" not in m


def is_function_call(m: dict) -> bool:
    """Return True if ``m`` is a FunctionCallItem."""
    return m.get("type") == "function_call"


def is_function_call_output(m: dict) -> bool:
    """Return True if ``m`` is a FunctionCallOutputItem."""
    return m.get("type") == "function_call_output"


# ---------------------------------------------------------------------------
# Agent template
# ---------------------------------------------------------------------------


class AgentTemplate(TypedDict):
    """Parsed agent definition loaded from a ``.agent.md`` file."""

    name: str
    model: str
    tools: list[str]
    system_prompt: str


# ---------------------------------------------------------------------------
# Calibration & memory state
# ---------------------------------------------------------------------------


class CalibrationState(TypedDict):
    """Running actual/estimated token counters for calibration."""

    cumulative_estimated: int
    cumulative_actual: int


class MemoryState(TypedDict, total=False):
    """Per-session memory state managed by the memory subsystem."""

    active_observations: str
    last_observed_index: int
    observation_token_count: int
    generation_count: int
    observer_log_seq: int
    reflector_log_seq: int
    calibration: CalibrationState
    # Transient per-request flags (not persisted):
    _observer_ran_this_request: bool
    _last_reflection_output_tokens: int


def fresh_memory() -> dict:
    """Create a zeroed MemoryState dict.

    Returns:
        A new MemoryState with all counters at zero.
    """
    return {
        "active_observations": "",
        "last_observed_index": 0,
        "observation_token_count": 0,
        "generation_count": 0,
        "observer_log_seq": 0,
        "reflector_log_seq": 0,
        "calibration": {"cumulative_estimated": 0, "cumulative_actual": 0},
    }


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class Session(TypedDict):
    """In-memory session record."""

    id: str
    messages: list[dict]
    memory: dict  # MemoryState


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


class ToolDefinition(TypedDict):
    """OpenAI function-tool definition schema."""

    type: str  # always 'function'
    name: str
    description: str
    parameters: dict[str, Any]


class Tool(TypedDict):
    """Registered tool with its JSON schema definition and async handler."""

    definition: ToolDefinition
    # handler is stored as a callable in the runtime dict, not in TypedDict


class ResolvedTool(TypedDict):
    """Tool definition in the format expected by the Responses API."""

    type: str  # 'function'
    name: str
    description: str
    parameters: dict[str, Any]
    strict: bool


# ---------------------------------------------------------------------------
# Agent result
# ---------------------------------------------------------------------------


class AgentResult(TypedDict):
    """Return value of a completed agent run."""

    response: str
    usage: dict  # totalEstimatedTokens, totalActualTokens, calibration, turns


# ---------------------------------------------------------------------------
# Memory config
# ---------------------------------------------------------------------------


class MemoryConfig(TypedDict):
    """Tunable thresholds for the observer/reflector memory system."""

    observation_threshold_tokens: int
    reflection_threshold_tokens: int
    reflection_target_tokens: int
    observer_model: str
    reflector_model: str


# ---------------------------------------------------------------------------
# Usage totals
# ---------------------------------------------------------------------------


class UsageTotals(TypedDict):
    """Accumulated token usage across all LLM calls in an agent run."""

    estimated: int
    actual: int


# ---------------------------------------------------------------------------
# Observer / reflector results
# ---------------------------------------------------------------------------


class ObserverResult(TypedDict, total=False):
    """Output of a single observer LLM call."""

    observations: str
    current_task: Optional[str]
    suggested_response: Optional[str]
    raw: str


class ReflectorResult(TypedDict):
    """Output of a single reflector compression attempt."""

    observations: str
    token_count: int
    raw: str
    compression_level: int


# ---------------------------------------------------------------------------
# Processed context
# ---------------------------------------------------------------------------


class ProcessedContext(TypedDict):
    """Context ready to pass to the agent LLM call."""

    system_prompt: str
    messages: list[dict]
