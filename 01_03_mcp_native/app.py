# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
MCP Native Demo — one agent using both MCP tools and native Python tools.
Shows how MCP tools (from a server) and plain function tools can be unified
behind a single handler map and driven by the same agent loop.
The model doesn't know which tools are MCP and which are native.

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

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import resolve_model_for_provider

from src.mcp.server import mcp_server
from src.mcp.client import create_mcp_client, list_mcp_tools, mcp_tools_to_openai, call_mcp_tool
from src.native.tools import native_tools, native_handlers
from src.agent import create_agent
from src.log import MCP_LABEL, NATIVE_LABEL

MODEL = resolve_model_for_provider("gpt-5.2")
INSTRUCTIONS = """You are a helpful assistant with access to various tools.
You can check weather, get time, perform calculations, and transform text.
Use the appropriate tool for each task. Be concise."""


async def main() -> None:
    # Start in-memory MCP server and connect a client
    mcp_client = await create_mcp_client(mcp_server)
    mcp_tool_list = await list_mcp_tools(mcp_client)

    # Unified handler map — MCP and native tools behind the same {execute, label} interface
    handlers = {
        **{
            tool.name: {
                "execute": lambda args, t=tool: call_mcp_tool(mcp_client, t.name, args),
                "label": MCP_LABEL,
            }
            for tool in mcp_tool_list
        },
        **{
            name: {"execute": fn, "label": NATIVE_LABEL}
            for name, fn in native_handlers.items()
        },
    }

    tools = [*mcp_tools_to_openai(mcp_tool_list), *native_tools]
    agent = create_agent(
        model=MODEL,
        tools=tools,
        instructions=INSTRUCTIONS,
        handlers=handlers,
    )

    print(f"MCP tools: {', '.join(t.name for t in mcp_tool_list)}")
    print(f"Native tools: {', '.join(native_handlers.keys())}")

    queries = [
        "What's the weather in Tokyo?",
        "What time is it in Europe/London?",
        "Calculate 42 multiplied by 17",
        "Convert 'hello world' to uppercase",
        "What's 25 + 17, and what's the weather in Paris?",
    ]

    for query in queries:
        await agent.process_query(query)

    await mcp_client.close()


if __name__ == "__main__":
    asyncio.run(main())
