# -*- coding: utf-8 -*-

#   tracer.py

"""
### Description:
High-level tracing helpers wrapping the Langfuse Python SDK — mirrors
src/core/tracing/tracer.ts.

Provides:
  - ``with_trace``       — root trace span for a full request
  - ``with_agent``       — agent span + contextvars-based context
  - ``start_generation`` — generation span handle (record tokens, end/error)
  - ``with_tool``        — tool execution span
  - ``set_trace_output`` — update the active trace's output field
  - ``record_trace_error`` — log an error on the active trace

All functions are safe no-ops when tracing is inactive.

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/core/tracing/tracer.ts

"""

from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional, TypeVar

from .context import format_generation_name, format_tool_name, with_agent_context
from .init import get_langfuse_client, is_tracing_active

T = TypeVar("T")

# ContextVars for the active Langfuse observation objects
_active_trace: ContextVar[Optional[Any]] = ContextVar("active_trace", default=None)
_active_observation: ContextVar[Optional[Any]] = ContextVar(
    "active_observation", default=None
)


# ---------------------------------------------------------------------------
# with_trace
# ---------------------------------------------------------------------------


async def with_trace(
    params: dict[str, Any],
    fn: Callable[[], Awaitable[T]],
) -> T:
    """Wrap ``fn`` inside a root Langfuse trace.

    Args:
        params: Trace configuration dict (``name``, ``session_id``,
                ``user_id``, ``input``, ``tags``, ``metadata``).
        fn: Async callable to execute inside the trace context.

    Returns:
        Whatever ``fn`` returns.
    """
    if not is_tracing_active():
        return await fn()

    client = get_langfuse_client()
    assert client is not None

    trace = client.trace(  # type: ignore[union-attr]
        name=params.get("name", "trace"),
        session_id=params.get("session_id"),
        user_id=params.get("user_id"),
        input=params.get("input"),
        tags=params.get("tags"),
        metadata=params.get("metadata"),
    )

    token_trace = _active_trace.set(trace)
    token_obs = _active_observation.set(trace)
    try:
        return await fn()
    except Exception as exc:
        try:
            trace.update(level="ERROR", status_message=str(exc))
        except Exception:
            pass
        raise
    finally:
        _active_trace.reset(token_trace)
        _active_observation.reset(token_obs)


# ---------------------------------------------------------------------------
# with_agent
# ---------------------------------------------------------------------------


async def with_agent(
    params: dict[str, Any],
    fn: Callable[[], Awaitable[T]],
) -> T:
    """Wrap ``fn`` inside an agent observation span.

    Args:
        params: Agent span configuration dict (``name``, ``agent_id``,
                ``task``, ``metadata``).
        fn: Async callable to execute inside the agent context.

    Returns:
        Whatever ``fn`` returns.
    """
    if not is_tracing_active():
        return await with_agent_context(
            params.get("name", "agent"),
            params.get("agent_id", ""),
            fn,
        )

    obs = _active_observation.get()
    agent_span = None

    try:
        if obs is not None:
            agent_span = obs.span(  # type: ignore[union-attr]
                name=params.get("name", "agent"),
                input={"task": params.get("task")} if params.get("task") else None,
                metadata=params.get("metadata"),
            )
        else:
            client = get_langfuse_client()
            if client is not None:
                agent_span = client.trace(name=params.get("name", "agent")).span(  # type: ignore[union-attr]
                    name=params.get("name", "agent"),
                )
    except Exception:
        agent_span = None

    token = _active_observation.set(agent_span) if agent_span else None

    async def _inner() -> T:
        return await with_agent_context(
            params.get("name", "agent"),
            params.get("agent_id", ""),
            fn,
        )

    try:
        result = await _inner()
        return result
    except Exception as exc:
        if agent_span is not None:
            try:
                agent_span.update(level="ERROR", status_message=str(exc))
            except Exception:
                pass
        raise
    finally:
        if token is not None:
            _active_observation.reset(token)


# ---------------------------------------------------------------------------
# start_generation
# ---------------------------------------------------------------------------


class _NoOpGenerationHandle:
    """No-op generation handle used when tracing is inactive."""

    def record_first_token(self) -> None:
        """Record the timestamp of the first streamed token (no-op)."""

    def end(self, result: Optional[dict[str, Any]] = None) -> None:
        """Close the generation span (no-op)."""

    def error(self, err: dict[str, Any]) -> None:
        """Mark the generation as failed (no-op)."""


class _GenerationHandle:
    """Live generation handle backed by a Langfuse generation object."""

    def __init__(self, gen: Any) -> None:
        self._gen = gen

    def record_first_token(self) -> None:
        """Record the timestamp of the first streamed token."""
        try:
            self._gen.update(completion_start_time=datetime.now(tz=timezone.utc))
        except Exception:
            pass

    def end(self, result: Optional[dict[str, Any]] = None) -> None:
        """Close the generation span, recording output and usage."""
        try:
            if result:
                self._gen.end(output=result.get("output"), usage=result.get("usage"))
            else:
                self._gen.end()
        except Exception:
            pass

    def error(self, err: dict[str, Any]) -> None:
        """Mark the generation as failed."""
        try:
            self._gen.update(level="ERROR", status_message=err.get("message", ""))
            self._gen.end()
        except Exception:
            pass


def start_generation(
    params: dict[str, Any],
) -> "_GenerationHandle | _NoOpGenerationHandle":
    """Start a generation span as a child of the current observation.

    Args:
        params: Generation configuration dict (``model``, ``input``, ``metadata``).

    Returns:
        A handle with ``record_first_token()``, ``end(result)``, and
        ``error(err)`` methods.
    """
    if not is_tracing_active():
        return _NoOpGenerationHandle()

    obs = _active_observation.get()
    name = format_generation_name()

    gen = None
    try:
        if obs is not None:
            gen = obs.generation(  # type: ignore[union-attr]
                name=name,
                model=params.get("model"),
                input=params.get("input"),
                metadata=params.get("metadata"),
            )
    except Exception:
        gen = None

    if gen is None:
        return _NoOpGenerationHandle()

    return _GenerationHandle(gen)


# ---------------------------------------------------------------------------
# with_tool
# ---------------------------------------------------------------------------


async def with_tool(
    params: dict[str, Any],
    fn: Callable[[], Awaitable[T]],
) -> T:
    """Wrap ``fn`` inside a tool execution span.

    Args:
        params: Tool span configuration dict (``name``, ``input``, ``metadata``).
        fn: Async callable to execute inside the span.

    Returns:
        Whatever ``fn`` returns.
    """
    if not is_tracing_active():
        return await fn()

    obs = _active_observation.get()
    span_name = format_tool_name(params.get("name", "tool"))
    tool_span = None

    try:
        if obs is not None:
            tool_span = obs.span(  # type: ignore[union-attr]
                name=span_name,
                input=params.get("input"),
                metadata=params.get("metadata"),
            )
    except Exception:
        tool_span = None

    try:
        result = await fn()
        if tool_span is not None:
            try:
                tool_span.update(output=str(result) if result is not None else None)
            except Exception:
                pass
        return result
    except Exception as exc:
        if tool_span is not None:
            try:
                tool_span.update(level="ERROR", status_message=str(exc))
            except Exception:
                pass
        raise


# ---------------------------------------------------------------------------
# Trace-level helpers
# ---------------------------------------------------------------------------


def set_trace_output(output: Any) -> None:
    """Update the active trace's output field."""
    trace = _active_trace.get()
    if trace is None:
        return
    try:
        trace.update(output=output)  # type: ignore[union-attr]
    except Exception:
        pass


def record_trace_error(err: Any) -> None:
    """Log an error on the active trace."""
    trace = _active_trace.get()
    if trace is None:
        return
    try:
        trace.update(level="ERROR", status_message=str(err))  # type: ignore[union-attr]
    except Exception:
        pass
