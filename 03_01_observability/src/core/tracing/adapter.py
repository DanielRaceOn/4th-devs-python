# -*- coding: utf-8 -*-

#   adapter.py

"""
### Description:
Tracing adapter wrapper — mirrors src/core/tracing/adapter.ts.

``with_generation_tracing`` wraps any ``Adapter`` implementation so that
every call to ``complete()`` automatically opens a Langfuse generation
span, records input/output and token usage, and closes (or errors) the
span when the call resolves.

---

@Author:        Claude Sonnet 4.6
@Created on:    08.04.2026
@Based on:      src/core/tracing/adapter.ts

"""

from typing import Any

from ..result import Err, Ok
from ...types import Adapter, CompletionError, CompletionParams, CompletionResult
from .tracer import start_generation


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
                "input": [
                    {"role": m.get("role"), "content": m.get("content")}
                    for m in params.input
                ],
                "metadata": {
                    "has_tools": bool(params.tools),
                    "has_instructions": bool(params.instructions),
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
            gen_handle.end(
                {
                    "output": cr.text or (
                        [tc.to_dict() for tc in cr.tool_calls] if cr.tool_calls else None
                    ),
                    "usage": usage_dict,
                }
            )
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
