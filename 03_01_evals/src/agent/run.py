# -*- coding: utf-8 -*-

#   run.py

"""
### Description:
Agent loop and run entry point for the Responses API — mirrors
src/agent/run.ts.

Key difference from ``03_01_observability``: uses the OpenAI Responses
API, so:
  - The agent loop appends raw ``output`` items (from ``CompletionResult``)
    directly to the session message list — no manual assistant message
    construction needed.
  - Tool results are appended as
    ``{"type": "function_call_output", "call_id": ..., "output": ...}``
    (not the Chat Completions ``role: "tool"`` format).
  - Tool calls are identified by ``call_id`` (not ``id``).

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/agent/run.ts

"""

import uuid
from typing import Optional

from ..core.logger import Logger
from ..core.result import Ok
from ..core.tracing.context import set_prompt_ref
from ..core.tracing.prompts import get_prompt_ref_by_name
from ..core.tracing.tracer import record_trace_error, with_agent, with_tool
from ..types import (
    Adapter,
    AgentRunResult,
    CompletionParams,
    Session,
    Usage,
)
from .tools import TOOL_DEFINITIONS, execute_tool

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_TURNS = 8
_ALICE_PROMPT_NAME = "agents/alice"

SYSTEM_PROMPT = (
    "You are Alice, a concise and practical assistant.\n"
    "Use tools when they improve correctness.\n"
    "Never invent tool outputs."
)


def build_alice_system_prompt() -> str:
    """Return Alice's system prompt string.

    Returns:
        The system prompt used by the Alice agent.
    """
    return SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _accumulate_usage(total: Usage, delta: Optional[Usage]) -> Usage:
    """Add delta token counts to a running total.

    Args:
        total: Running total ``Usage`` object (mutated in place).
        delta: ``Usage`` from the latest completion, may be ``None``.

    Returns:
        The updated ``total`` object.
    """
    if delta is None:
        return total
    total.input = (total.input or 0) + (delta.input or 0)
    total.output = (total.output or 0) + (delta.output or 0)
    total.total = (total.total or 0) + (delta.total or 0)
    return total


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------


async def _agent_loop(
    adapter: Adapter,
    logger: Logger,
    session: Session,
) -> AgentRunResult:
    """Run the multi-turn completion/tool-call loop (Responses API).

    After each completion, raw output items are appended to the session
    history.  Tool results are injected as ``function_call_output`` items
    so the Responses API receives a valid continuation.

    Args:
        adapter: LLM adapter to use for completions.
        logger: Logger bound to this agent run.
        session: Active session whose ``messages`` list is updated in place.

    Returns:
        ``AgentRunResult`` with the final text response, turn count, and
        accumulated token usage.
    """
    accumulated_usage = Usage(input=0, output=0, total=0)
    turns = 0

    for turn in range(1, MAX_TURNS + 1):
        turns = turn
        logger.debug("agent turn", {"turn": turn})

        params = CompletionParams(
            input=list(session.messages),
            instructions=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
        )

        result = await adapter.complete(params)

        if not isinstance(result, Ok):
            error = result.error
            record_trace_error({"code": error.code, "message": error.message})
            logger.error("completion failed", {"code": error.code, "message": error.message})
            raise RuntimeError(f"Model call failed: {error.message}")

        cr = result.value
        _accumulate_usage(accumulated_usage, cr.usage)

        # Append all raw output items to the session so future turns see
        # the full conversation in Responses API format.
        session.messages.extend(cr.output)

        if not cr.tool_calls:
            # No tool calls — this is the final text response
            logger.debug("agent done", {"turns": turns, "response_len": len(cr.text)})
            return AgentRunResult(
                response=cr.text or "No response from model",
                turns=turns,
                usage=accumulated_usage,
            )

        # Execute each tool and inject its output as a function_call_output item
        for tc in cr.tool_calls:
            async def _exec(tc=tc) -> str:  # default arg captures tc by value
                return await execute_tool(tc.name, tc.arguments)

            tool_output = await with_tool(
                {
                    "name": tc.name,
                    "input": {"call_id": tc.call_id, "arguments": tc.arguments},
                },
                _exec,
            )
            logger.debug("tool result", {"name": tc.name, "result": tool_output})

            # Inject tool result in Responses API format
            session.messages.append(
                {
                    "type": "function_call_output",
                    "call_id": tc.call_id,
                    "output": tool_output,
                }
            )

    raise RuntimeError("Exceeded maximum turns before a final assistant answer")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_agent(
    adapter: Adapter,
    logger: Logger,
    session: Session,
    message: str,
) -> AgentRunResult:
    """Push a user message and run the agent loop inside a Langfuse agent span.

    Args:
        adapter: LLM adapter to use for completions.
        logger: Logger for this request.
        session: Active conversation session (mutated in place).
        message: User message text to append.

    Returns:
        ``AgentRunResult`` with response, turn count, and usage.
    """
    # Append the user message in Responses API format
    session.messages.append({"role": "user", "content": message})

    # Resolve and store prompt reference for tracing
    prompt_ref = get_prompt_ref_by_name(_ALICE_PROMPT_NAME)
    set_prompt_ref(prompt_ref)

    agent_id = str(uuid.uuid4())
    agent_logger = logger.child({"agentId": agent_id, "sessionId": session.id})

    async def _run() -> AgentRunResult:
        return await _agent_loop(adapter, agent_logger, session)

    return await with_agent(
        {
            "name": "alice",
            "agent_id": agent_id,
            "task": message,
            "metadata": {"max_turns": MAX_TURNS, "session_id": session.id},
        },
        _run,
    )
