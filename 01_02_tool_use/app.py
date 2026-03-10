# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Entry point for 01_02_tool_use: initialises a clean sandbox, then runs a
sequence of natural-language queries through the sandboxed filesystem assistant.
Each query exercises a different tool (list, create, read, mkdir, delete, etc.)
including a path-traversal security test.

---

@Author:        Claude Sonnet 4.6
@Created on:    10.03.2026
@Based on:      `app.js`


"""

import asyncio

from src.config import API_INSTRUCTIONS, API_MODEL
from src.executor import process_query
from src.tools.definitions import tools
from src.tools.handlers import handlers
from src.utils.sandbox import initialize_sandbox

QUERIES = [
    # List files at sandbox root
    "What files are in the sandbox?",
    # Create a new text file
    "Create a file called hello.txt with content: 'Hello, World!'",
    # Read a file back
    "Read the hello.txt file",
    # Inspect file metadata
    "Get info about hello.txt",
    # Create a subdirectory
    "Create a directory called 'docs'",
    # Write a file inside the subdirectory
    "Create a file docs/readme.txt with content: 'Documentation folder'",
    # List the subdirectory
    "List files in the docs directory",
    # Delete a file
    "Delete the hello.txt file",
    # Security test — should be blocked by sandbox boundary check
    "Try to read ../config.py",
]


async def main() -> None:
    """Initialise the sandbox and run all example queries sequentially."""
    await initialize_sandbox()
    print("Sandbox prepared: empty state\n")

    for query in QUERIES:
        await process_query(
            query,
            model=API_MODEL,
            tools=tools,
            handlers=handlers,
            instructions=API_INSTRUCTIONS,
        )


if __name__ == "__main__":
    asyncio.run(main())
