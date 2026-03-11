# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
MCP Core Demo — exercises all MCP capabilities via stdio transport.

The client spawns the server as a subprocess and communicates via stdin/stdout.
This is how real MCP integrations work (e.g. Claude Desktop, Cursor).

Run:
    python app.py

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `app.js`

"""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CreateMessageResult, TextContent

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import resolve_model_for_provider

from src.ai import completion
from src.log import client_log, heading, log, parse_tool_result

MODEL = resolve_model_for_provider("gpt-5.1")


async def sampling_callback(request):
    """Handle sampling/createMessage requests from the server.

    The server calls this when it needs an LLM completion — the client
    owns the AI provider relationship.
    """
    messages = request.params.messages
    max_tokens = request.params.maxTokens

    client_log.sampling_request(messages, max_tokens)

    # Convert MCP message format → Responses API input format
    input_messages = []
    for msg in messages:
        content = msg.content
        text = content.text if hasattr(content, "text") else str(content)
        input_messages.append({"role": msg.role, "content": text})

    try:
        text = await completion(
            model=MODEL,
            input=input_messages,
            max_output_tokens=max_tokens or 500,
        )
        client_log.sampling_response(text)
        return CreateMessageResult(
            role="assistant",
            content=TextContent(type="text", text=text),
            model=MODEL,
        )
    except Exception as error:
        client_log.sampling_error(error)
        raise


async def main() -> None:
    server_script = Path(__file__).parent / "src" / "server.py"

    server_params = StdioServerParameters(
        command="python",
        args=[str(server_script)],
    )

    client_log.spawning_server(str(server_script))

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read, write, sampling_callback=sampling_callback
        ) as session:
            await session.initialize()
            client_log.connected()

            # --- TOOLS ---
            heading("TOOLS", "Actions the server exposes for the LLM to invoke")

            tools_result = await session.list_tools()
            log(
                "listTools",
                [f"{t.name} — {t.description}" for t in tools_result.tools],
            )

            calc_result = await session.call_tool(
                "calculate",
                {"operation": "multiply", "a": 42, "b": 17},
            )
            log(
                "callTool(calculate)",
                parse_tool_result(
                    {"content": [c.model_dump() for c in calc_result.content]}
                ),
            )

            summary_result = await session.call_tool(
                "summarize_with_confirmation",
                {
                    "text": (
                        "The Model Context Protocol (MCP) is a standardized protocol that "
                        "allows applications to provide context for LLMs. It separates the "
                        "concerns of providing context from the actual LLM interaction. MCP "
                        "servers expose tools, resources, and prompts that clients can discover "
                        "and use."
                    ),
                    "maxLength": 30,
                },
            )
            log(
                "callTool(summarize_with_confirmation)",
                parse_tool_result(
                    {"content": [c.model_dump() for c in summary_result.content]}
                ),
            )

            # --- RESOURCES ---
            heading("RESOURCES", "Read-only data the server makes available to clients")

            resources_result = await session.list_resources()
            log(
                "listResources",
                [f"{r.uri} — {r.name or r.description}" for r in resources_result.resources],
            )

            config_resource = await session.read_resource("config://project")
            import json
            log(
                "readResource(config://project)",
                json.loads(config_resource.contents[0].text),
            )

            stats_resource = await session.read_resource("data://stats")
            log(
                "readResource(data://stats)",
                json.loads(stats_resource.contents[0].text),
            )

            # --- PROMPTS ---
            heading("PROMPTS", "Reusable message templates with parameters")

            prompts_result = await session.list_prompts()
            log(
                "listPrompts",
                [f"{p.name} — {p.description}" for p in prompts_result.prompts],
            )

            prompt_result = await session.get_prompt(
                "code-review",
                {
                    "code": "function add(a, b) { return a + b; }",
                    "language": "javascript",
                    "focus": "readability",
                },
            )
            log(
                "getPrompt(code-review)",
                [
                    f"[{m.role}] {m.content.text if hasattr(m.content, 'text') else str(m.content)}"
                    for m in prompt_result.messages
                ],
            )


if __name__ == "__main__":
    asyncio.run(main())
