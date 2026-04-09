# -*- coding: utf-8 -*-

#   adapter.py

"""
### Description:
Tracing adapter wrapper for the Responses API — mirrors
src/core/tracing/adapter.ts.

``with_generation_tracing`` wraps any ``Adapter`` so that every call to
``complete()`` automatically opens a Langfuse generation span, records
input/output (in Responses API format) and token usage, then closes the
span when the call resolves.

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/core/tracing/adapter.ts

"""

from typing import Any

from ..result import Err, Ok
from ...types import Adapter, CompletionError, CompletionParams, CompletionResult
from .tracer import start_generation


def _format_input(params: CompletionParams) -> list[dict[str, Any]]:
    """Format Responses API input for Langfuse generation logging.

    Prepends a system instruction item when ``instructions`` is present,
    then formats each input item into a loggable dict.

    Args:
        params: Completion parameters.

    Returns:
        List of dicts suitable for Langfuse generation ``input``.
    """
    items: list[dict[str, Any]] = []

    if params.instructions:
        items.append({"role": "system", "content": params.instructions})

    for msg in params.input:
        msg_type = msg.get("type")
        if msg_type == "function_call_output":
            items.append({
                "type": "function_call_output",
                "call_id": msg.get("call_id"),
                "output": msg.get("output"),
            })
        else:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, list):
                # Content is an array of parts — join text parts
                content = " ".join(
                    p.get("text", "") for p in content if isinstance(p, dict)
                )
            items.append({"role": role, "content": content})

    return items


class _TracingAdapter(Adapter):
    """Adapter wrapper that instruments every ``complete()`` call."""

    def __init__(self, inner: Adapter) -> None:
        self._inner = inner

    async def complete(
        self, params: CompletionParams
    ) -> "Ok[CompletionResult] | Err[CompletionError]":
        """Execute a completion and record it as a Langfuse generation.

        Args:
            params: Completion parameters forwarded to the inner adapter.

        Returns:
            The Result from the inner adapter, unchanged.
        """
        gen_handle = start_generation(
            {
                "model": params.model,
                "input": _format_input(params),
                "metadata": {
                    "mode": "responses",
                    "has_tools": bool(params.tools),
                    "tool_count": len(params.tools) if params.tools else 0,
                },
            }
        )

        result = await self._inner.complete(params)

        if isinstance(result, Ok):
            cr: CompletionResult = result.value
            usage_dict: Any = None
            if cr.usage is not None:
                usage_dict = {
                    "input": cr.usage.input,
                    "output": cr.usage.output,
                    "total": cr.usage.total,
                }
            # Log either the text response or the tool calls
            output_val: Any = cr.text or (
                [tc.to_dict() for tc in cr.tool_calls] if cr.tool_calls else None
            )
            gen_handle.end({"output": output_val, "usage": usage_dict})
        else:
            ce: CompletionError = result.error
            gen_handle.error({"message": f"[{ce.code}] {ce.message}"})

        return result


def with_generation_tracing(adapter: Adapter) -> Adapter:
    """Wrap an adapter so each ``complete()`` call is traced as a generation.

    Args:
        adapter: The base adapter to wrap.

    Returns:
        A new adapter that behaves identically but emits generation spans.
    """
    return _TracingAdapter(adapter)
