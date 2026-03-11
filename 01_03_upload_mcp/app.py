# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
MCP Upload Agent — scans workspace files and uploads them via MCP servers.
Demonstrates connecting to multiple MCP servers simultaneously:
  - files (stdio):       local filesystem via files-mcp
  - uploadthing (http):  remote upload service via StreamableHTTP

Tool names are prefixed with the server name (e.g. files__fs_read,
uploadthing__upload_files) so the agent loop routes calls to the correct server.

Run:
    python app.py

Required setup:
    Edit mcp.json and replace the uploadthing URL placeholder with the
    real MCP deployment URL from the AI_devs lesson.

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

from src.helpers.logger import log
from src.helpers.stats import log_stats
from src.mcp.client import (
    ConfigurationError,
    close_all_clients,
    create_all_mcp_clients,
    list_all_mcp_tools,
)
from src.agent import run

MODEL = resolve_model_for_provider("gpt-5.4")
MAX_OUTPUT_TOKENS = 16384
INSTRUCTIONS = """You are a file upload assistant.

Use the {{file:path}} placeholder for the base64 field when uploading — the system resolves it automatically.

Example: { "files": [{ "base64": "{{file:example.md}}", "name": "example.md", "type": "text/markdown" }] }

Workflow:
1. fs_read with mode:"list" to see workspace files
2. Upload each file not already in uploaded.md using {{file:path}} syntax
3. Update uploaded.md with a table of filename, URL, and timestamp

Rules:
- Never read or encode file content yourself — always use {{file:path}}
- Skip uploaded.md itself and files already listed in it
- Handle errors gracefully

When done, say "Upload complete: X files uploaded, Y skipped.\""""


async def main() -> None:
    log.box("MCP Upload Agent\nUpload workspace files via uploadthing")

    mcp_clients = None

    try:
        # Connect to all servers defined in mcp.json
        log.start("Connecting to MCP servers...")
        mcp_clients = await create_all_mcp_clients()
        mcp_tools = await list_all_mcp_tools(mcp_clients)
        log.success(
            f"Connected with {len(mcp_tools)} tools from {len(mcp_clients)} servers"
        )

        # Run the upload task — agent lists files, uploads, updates uploaded.md
        log.start("Starting upload task...")
        conversation = [
            {
                "role": "user",
                "content": (
                    "Check the workspace for files, upload any that haven't been "
                    "uploaded yet, and update uploaded.md with the results."
                ),
            }
        ]
        await run(
            conversation,
            mcp_clients=mcp_clients,
            mcp_tools=mcp_tools,
            model=MODEL,
            instructions=INSTRUCTIONS,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        log_stats()

    except ConfigurationError as error:
        log.error(str(error))
        sys.exit(1)
    except Exception as error:
        log.error(str(error))
        print(error)
        sys.exit(1)
    finally:
        if mcp_clients:
            log.start("Closing connections...")
            await close_all_clients(mcp_clients)


if __name__ == "__main__":
    asyncio.run(main())
