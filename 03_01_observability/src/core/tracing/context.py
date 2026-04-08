# -*- coding: utf-8 -*-

#   context.py

"""
### Description:
Async-local tracing context using Python's contextvars — mirrors the
Node.js AsyncLocalStorage-based src/core/tracing/context.ts.

Stores agent name, agent ID, current turn number, tool index, and an
optional prompt reference.  All state is scoped to the current asyncio
Task so concurrent requests stay isolated.

---

@Author:        Claude Sonnet 4.6
@Created on:    08.04.2026
@Based on:      src/core/tracing/context.ts

"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional, TypeVar

T = TypeVar("T")


@dataclass
class PromptRef:
    """Reference to a Langfuse-managed prompt version."""

    name: str
    version: int
    is_fallback: bool


@dataclass
class TracingContext:
    """Per-request tracing state propagated via ContextVar."""

    agent_name: str = ""
    agent_id: str = ""
    turn_number: int = 0
    tool_index: int = 0
    prompt_ref: Optional[PromptRef] = field(default=None)


# Single ContextVar that holds the mutable TracingContext dataclass.
# We mutate the dataclass in-place rather than replacing the token so
# that advance_turn / next_tool_index work without re-setting the var.
_ctx: ContextVar[Optional[TracingContext]] = ContextVar("tracing_ctx", default=None)


async def with_agent_context(
    agent_name: str,
    agent_id: str,
    fn: Callable[[], Awaitable[T]],
) -> T:
    """Run *fn* inside a fresh TracingContext scoped to this task.

    Args:
        agent_name: Display name for the agent (used in span names).
        agent_id: Unique identifier for this agent run.
        fn: Async callable to execute inside the context.

    Returns:
        Whatever ``fn`` returns.
    """
    ctx = TracingContext(agent_name=agent_name, agent_id=agent_id)
    token = _ctx.set(ctx)
    try:
        return await fn()
    finally:
        _ctx.reset(token)


def advance_turn() -> int:
    """Increment the turn counter and reset the tool index.

    Returns:
        The new (post-increment) turn number, or 0 if no context is active.
    """
    ctx = _ctx.get()
    if ctx is None:
        return 0
    ctx.turn_number += 1
    ctx.tool_index = 0
    return ctx.turn_number


def _next_tool_index() -> int:
    """Increment and return the tool index within the current turn.

    Returns:
        The new (post-increment) tool index, or 1 if no context is active.
    """
    ctx = _ctx.get()
    if ctx is None:
        return 1
    ctx.tool_index += 1
    return ctx.tool_index


def get_current_turn() -> int:
    """Return the current turn number (0 when no context is active).

    Returns:
        Current turn number.
    """
    ctx = _ctx.get()
    return ctx.turn_number if ctx else 0


def get_current_agent_name() -> Optional[str]:
    """Return the active agent name, or None if no context is active.

    Returns:
        Agent name string or ``None``.
    """
    ctx = _ctx.get()
    return ctx.agent_name if ctx else None


def format_generation_name(base_name: str = "generation") -> str:
    """Build a qualified generation name for the current turn.

    E.g. ``"Alice/generation#3"``

    Args:
        base_name: Base label, defaults to ``"generation"``.

    Returns:
        Qualified name string.
    """
    ctx = _ctx.get()
    if ctx is None:
        return base_name
    return f"{ctx.agent_name}/{base_name}#{ctx.turn_number}"


def format_tool_name(tool_name: str) -> str:
    """Build a qualified tool span name including tool index.

    E.g. ``"Alice/get_current_time#1"``

    Args:
        tool_name: The bare tool name.

    Returns:
        Qualified name string.
    """
    ctx = _ctx.get()
    if ctx is None:
        return tool_name
    idx = _next_tool_index()
    return f"{ctx.agent_name}/{tool_name}#{idx}"


def set_prompt_ref(ref: Optional[PromptRef]) -> None:
    """Store the active prompt reference in the current context.

    Args:
        ref: A ``PromptRef`` or ``None`` to clear it.
    """
    ctx = _ctx.get()
    if ctx is None:
        return
    ctx.prompt_ref = ref


def get_prompt_ref() -> Optional[PromptRef]:
    """Return the active prompt reference, or None.

    Returns:
        The stored ``PromptRef`` or ``None``.
    """
    ctx = _ctx.get()
    return ctx.prompt_ref if ctx else None
