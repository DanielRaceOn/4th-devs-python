#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#   server.py

"""
### Description:
MCP Server — registers tools, resources, and prompts, then listens over stdio.
In MCP, the server is a capability provider. It exposes:
  - tools:      actions the LLM can invoke (e.g. calculate, summarize)
  - resources:  read-only data (e.g. config, runtime stats)
  - prompts:    reusable message templates with parameters

The server runs as a subprocess, communicating with the client via stdin/stdout.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/server.js`

"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    GetPromptResult,
    ListPromptsResult,
    ListResourcesResult,
    ListToolsResult,
    Prompt,
    PromptArgument,
    ReadResourceResult,
    Resource,
    TextContent,
    Tool,
)

# Import capability definitions from sibling modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from resources import get_project_config, get_runtime_stats
from prompts import get_code_review_prompt

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

_server = Server("mcp-core-demo")


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="calculate",
            description="Performs basic arithmetic operations",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                        "description": "The operation",
                    },
                    "a": {"type": "number", "description": "First operand"},
                    "b": {"type": "number", "description": "Second operand"},
                },
                "required": ["operation", "a", "b"],
            },
        ),
        Tool(
            name="summarize_with_confirmation",
            description="Summarizes text after getting user confirmation. Demonstrates elicitation and sampling.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to summarize"},
                    "maxLength": {
                        "type": "number",
                        "description": "Maximum summary length in words",
                    },
                },
                "required": ["text"],
            },
        ),
    ]


@_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "calculate":
        return _handle_calculate(arguments)
    if name == "summarize_with_confirmation":
        return await _handle_summarize(arguments)
    raise ValueError(f"Unknown tool: {name}")


def _handle_calculate(args: dict) -> list[TextContent]:
    operation = args["operation"]
    a = args["a"]
    b = args["b"]

    ops: dict[str, Any] = {
        "add": lambda: a + b,
        "subtract": lambda: a - b,
        "multiply": lambda: a * b,
        "divide": lambda: a / b if b != 0 else "Error: Division by zero",
    }

    result = ops[operation]()
    return [TextContent(
        type="text",
        text=json.dumps({"operation": operation, "a": a, "b": b, "result": result}),
    )]


async def _handle_summarize(args: dict) -> list[TextContent]:
    """Summarize tool — demonstrates sampling.

    Note: elicitation is a newer MCP feature with limited Python SDK support.
    This implementation skips elicitation and goes straight to sampling.
    """
    text = args["text"]
    max_length = args.get("maxLength", 50)

    # Build a sampling/createMessage request to ask the client to call an LLM
    summary_prompt = (
        f"Summarize in a concise style. Max {max_length} words.\n\nText: {text}"
    )

    try:
        # Use the low-level request mechanism to ask the client to sample
        response = await _server.request_context.session.create_message(
            messages=[{"role": "user", "content": {"type": "text", "text": summary_prompt}}],
            max_tokens=200,
        )
        summary_text = response.content.text if hasattr(response.content, "text") else str(response.content)
        return [TextContent(type="text", text=f"Summary (concise style):\n\n{summary_text}")]
    except Exception as error:
        return [TextContent(
            type="text",
            text=f"Error: {error}. Sampling may not be supported by the client.",
        )]


# ---------------------------------------------------------------------------
# Resource definitions
# ---------------------------------------------------------------------------

@_server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="config://project",
            name="Project Configuration",
            description="Current project settings",
            mimeType="application/json",
        ),
        Resource(
            uri="data://stats",
            name="Runtime Statistics",
            description="Dynamic server stats",
            mimeType="application/json",
        ),
    ]


@_server.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "config://project":
        return get_project_config()["text"]
    if uri == "data://stats":
        return get_runtime_stats()["text"]
    raise ValueError(f"Unknown resource: {uri}")


# ---------------------------------------------------------------------------
# Prompt definitions
# ---------------------------------------------------------------------------

@_server.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="code-review",
            description="Template for code review requests",
            arguments=[
                PromptArgument(name="code", description="The code to review", required=True),
                PromptArgument(name="language", description="Programming language", required=False),
                PromptArgument(
                    name="focus",
                    description="Review focus: security, performance, readability, or all",
                    required=False,
                ),
            ],
        )
    ]


@_server.get_prompt()
async def get_prompt(name: str, arguments: dict) -> GetPromptResult:
    if name == "code-review":
        return get_code_review_prompt(
            code=arguments.get("code", ""),
            language=arguments.get("language", "unknown"),
            focus=arguments.get("focus", "all"),
        )
    raise ValueError(f"Unknown prompt: {name}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await _server.run(
            read_stream,
            write_stream,
            _server.create_initialization_options(),
        )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
