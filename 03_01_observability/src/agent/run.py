# -*- coding: utf-8 -*-

#   run.py

"""
### Description:
Agent loop and run entry point — mirrors src/agent/run.ts.

``run_agent`` pushes the user message onto the session, resolves the
prompt reference, and runs the multi-turn tool-call loop inside a
Langfuse agent span.  The loop terminates when the model returns a plain
text response or the ``MAX_TURNS`` guard is reached.

``build_alice_system_prompt`` is exported for use by the prompt sync
subsystem (see ``src/core/tracing/prompts.py``).

---

@Author:        Claude Sonnet 4.6
@Created on:    08.04.2026
@Based on:      src/agent/run.ts

"""

import uuid
from typing import Any, Optional

from ..core.logger import Logger
from ..core.result import Ok
from ..core.tracing.context import set_prompt_ref
from ..core.tracing.prompts import get_prompt_ref_by_name
from ..core.tracing.tracer import with_agent, with_tool
from ..types import (
    Adapter,
    AgentRunResult,
    CompletionParams,
    Session,
    ToolCall,
    Usage,
)
from .tools import TOOL_DEFINITIONS, execute_tool

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_TURNS = 8
_ALICE_PROMPT_NAME = "agents/alice"


def build_alice_system_prompt() -> str:
    """Return Alice's system prompt string.

    Returns:
        The system prompt used by the Alice agent.
    """
    return (
        "You are Alice, a concise and practical assistant.\n"
        "Use tools when they improve correctness.\n"
        "Never invent tool outputs."
    )


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
    """Run the multi-turn completion/tool-call loop.

    Args:
        adapter: LLM adapter to use for completions.
        logger: Logger bound to this agent run.
        session: Active session whose ``messages`` list is updated in place.

    Returns:
        ``AgentRunResult`` with the final text response, turn count, and
        accumulated token usage.
    """
    instructions = build_alice_system_prompt()
    accumulated_usage = Usage(input=0, output=0, total=0)
    turns = 0

    for turn in range(1, MAX_TURNS + 1):
        turns = turn
        logger.debug("agent turn", {"turn": turn})

        params = CompletionParams(
            input=list(session.messages),
            instructions=instructions,
            tools=TOOL_DEFINITIONS,
        )

        result = await adapter.complete(params)

        if not isinstance(result, Ok):
            error = result.error
            logger.error("completion failed", {"code": error.code, "message": error.message})
            return AgentRunResult(
                response=f"Error: {error.message}",
                turns=turns,
                usage=accumulated_usage,
            )

        cr = result.value
        _accumulate_usage(accumulated_usage, cr.usage)

        # Append assistant message to session history
        if cr.tool_calls:
            # Build the assistant message with tool_calls
            tool_call_items = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": tc.arguments},
                }
                for tc in cr.tool_calls
            ]
            session.messages.append(
                {"role": "assistant", "content": cr.text or None, "tool_calls": tool_call_items}
            )

            # Execute each tool and append results
            for tc in cr.tool_calls:
                tool_result = await _run_tool(tc, logger)
                session.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_result,
                    }
                )
        else:
            # Final text response — append and exit loop
            session.messages.append({"role": "assistant", "content": cr.text})
            logger.debug("agent done", {"turns": turns, "response_len": len(cr.text)})
            return AgentRunResult(
                response=cr.text,
                turns=turns,
                usage=accumulated_usage,
            )

    # Max turns reached without a clean text response
    logger.warn("max turns reached", {"max_turns": MAX_TURNS})
    return AgentRunResult(
        response="I reached the maximum number of steps without completing your request.",
        turns=turns,
        usage=accumulated_usage,
    )


async def _run_tool(tc: ToolCall, logger: Logger) -> str:
    """Execute a single tool call inside a tracing span.

    Args:
        tc: The ``ToolCall`` emitted by the model.
        logger: Logger for debug output.

    Returns:
        JSON-encoded tool result string.
    """
    logger.debug("tool call", {"name": tc.name, "args": tc.arguments})

    async def _exec() -> str:
        return await execute_tool(tc.name, tc.arguments)

    result = await with_tool(
        {
            "name": tc.name,
            "input": {"arguments": tc.arguments},
        },
        _exec,
    )
    logger.debug("tool result", {"name": tc.name, "result": result})
    return result


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
    # Append the user message
    session.messages.append({"role": "user", "content": message})

    # Resolve and store prompt reference for tracing
    prompt_ref = get_prompt_ref_by_name(_ALICE_PROMPT_NAME)
    set_prompt_ref(prompt_ref)

    agent_id = str(uuid.uuid4())
    agent_logger = logger.child({"agentId": agent_id, "sessionId": session.id})

    async def _run() -> AgentRunResult:
        return await _agent_loop(adapter, agent_logger, session)

    result = await with_agent(
        {
            "name": "Alice",
            "agent_id": agent_id,
            "task": message,
            "metadata": {"session_id": session.id},
        },
        _run,
    )

    return result
