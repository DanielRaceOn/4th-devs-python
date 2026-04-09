# -*- coding: utf-8 -*-

#   types.py

"""
### Description:
Shared data types for the 03_01_evals module.

Uses the OpenAI **Responses API** (not Chat Completions), so:
  - ``Message``  = Responses API input item (user/assistant/function_call_output)
  - ``ToolCall`` has ``call_id`` (not ``id``)
  - ``CompletionResult`` carries the raw ``output`` list for history replay

Mirrors src/types.ts from the JavaScript source.

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/types.ts

"""

from typing import Any, Callable, Literal, Optional

# ---------------------------------------------------------------------------
# Message / completion types
# ---------------------------------------------------------------------------

# Responses API input item — dict representation.
# Covers: {"role": "user", "content": "..."} and
#         {"type": "function_call_output", "call_id": "...", "output": "..."}
Message = dict[str, Any]

# Responses API output item — raw dict returned by the API and replayed
# as future input items.
OutputItem = dict[str, Any]


class ToolCall:
    """A single tool call issued by the model via the Responses API."""

    def __init__(self, call_id: str, name: str, arguments: str) -> None:
        # ``call_id`` mirrors the JS ``callId`` field (from item.call_id)
        self.call_id = call_id
        self.name = name
        self.arguments = arguments

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation."""
        return {
            "call_id": self.call_id,
            "name": self.name,
            "arguments": self.arguments,
        }


class Usage:
    """Token usage counters from a completion response."""

    def __init__(
        self,
        input: Optional[int] = None,
        output: Optional[int] = None,
        total: Optional[int] = None,
    ) -> None:
        self.input = input
        self.output = output
        self.total = total

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation."""
        return {"input": self.input, "output": self.output, "total": self.total}


class CompletionParams:
    """Parameters for a single LLM completion call (Responses API)."""

    def __init__(
        self,
        input: list[Message],
        instructions: Optional[str] = None,
        model: Optional[str] = None,
        tools: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        self.input = input
        self.instructions = instructions
        self.model = model
        self.tools = tools


class CompletionResult:
    """Successful result of an LLM completion call (Responses API).

    ``output`` holds the raw output items returned by the API; the agent
    loop appends these directly to the session history so the next call
    sees the full conversation context in Responses API format.
    """

    def __init__(
        self,
        text: str,
        tool_calls: list[ToolCall],
        output: list[OutputItem],
        usage: Optional[Usage] = None,
    ) -> None:
        self.text = text
        self.tool_calls = tool_calls
        self.output = output
        self.usage = usage


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------

CompletionErrorCode = Literal[
    "PROVIDER_NOT_CONFIGURED",
    "AUTHENTICATION_ERROR",
    "RATE_LIMITED",
    "BAD_REQUEST",
    "CONNECTION_ERROR",
    "TIMEOUT",
    "INTERNAL_SERVER_ERROR",
    "UNKNOWN_ERROR",
]

Provider = Literal["openai"]


class CompletionError:
    """Structured error returned by an adapter."""

    def __init__(
        self,
        code: CompletionErrorCode,
        message: str,
        provider: Optional[Provider] = None,
        status: Optional[int] = None,
    ) -> None:
        self.code = code
        self.message = message
        self.provider = provider
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation."""
        return {
            "code": self.code,
            "message": self.message,
            "provider": self.provider,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# Adapter / resolver
# ---------------------------------------------------------------------------


class Adapter:
    """Protocol for LLM completion adapters."""

    async def complete(
        self, params: "CompletionParams"
    ) -> "Any":  # Result[CompletionResult, CompletionError]
        """Issue a completion request and return a Result.

        Args:
            params: Completion parameters including messages and model.

        Returns:
            ``ok(CompletionResult)`` on success, ``err(CompletionError)`` on failure.
        """
        raise NotImplementedError


# Type alias for the resolver callable
AdapterResolver = Callable[[Provider], Any]  # Provider -> Result[Adapter, CompletionError]


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class Session:
    """In-memory conversation session."""

    def __init__(self, id: str) -> None:
        self.id = id
        self.messages: list[Message] = []


# ---------------------------------------------------------------------------
# Agent run types
# ---------------------------------------------------------------------------


class AgentRunResult:
    """Result of a completed agent run."""

    def __init__(self, response: str, turns: int, usage: Usage) -> None:
        self.response = response
        self.turns = turns
        self.usage = usage

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation."""
        return {
            "response": self.response,
            "turns": self.turns,
            "usage": self.usage.to_dict(),
        }
