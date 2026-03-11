# -*- coding: utf-8 -*-

#   translator.py

"""
### Description:
Main watch loop — detects files in workspace/translate/ and asks the
agent to translate them to English into workspace/translated/.
Prevents duplicate in-flight translations using an in-progress set.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/translator.js`

"""

import asyncio
from typing import Any

from mcp import ClientSession

from .agent import run
from .config import translator as config
from .helpers.logger import log
from .helpers.stats import log_stats
from .mcp.client import call_mcp_tool

# Track files currently being translated to prevent duplicates
_in_progress: set[str] = set()
# Track files we've already logged as skipped (to reduce noise)
_logged_skipped: set[str] = set()


async def _list_files(
    mcp_client: ClientSession,
    directory: str,
    filter_by_extension: bool = False,
) -> list[str]:
    """List filenames in a directory via the MCP file server.

    Args:
        mcp_client: Connected MCP session.
        directory: Relative directory path (within the workspace root).
        filter_by_extension: When True, only return files whose extension is
            in ``config.supported_extensions``.

    Returns:
        List of filenames (basename only).
    """
    try:
        result = await call_mcp_tool(mcp_client, "fs_read", {"path": directory, "mode": "list"})
        if not isinstance(result, dict) or "entries" not in result:
            return []

        entries = result["entries"]

        def get_name(entry: dict) -> str:
            return entry.get("name") or (entry.get("path") or "").split("/")[-1]

        names = [
            get_name(e)
            for e in entries
            if (e.get("kind") == "file" or e.get("type") == "file")
        ]

        if filter_by_extension:
            names = [
                n for n in names
                if any(n.endswith(ext) for ext in config.supported_extensions)
            ]

        return names
    except Exception:
        return []


async def _ensure_directories(mcp_client: ClientSession) -> None:
    """Ensure source and target directories exist."""
    for path in (config.source_dir, config.target_dir):
        try:
            await call_mcp_tool(
                mcp_client, "fs_manage",
                {"operation": "mkdir", "path": path, "recursive": True},
            )
        except Exception:
            pass  # Directory may already exist — ignore


async def _translate_file(
    filename: str,
    mcp_client: ClientSession,
    mcp_tools: list[Any],
) -> Any:
    """Translate a single file using the agent.

    Args:
        filename: Filename to translate (relative to source_dir).
        mcp_client: Connected MCP session.
        mcp_tools: Available MCP tools.

    Returns:
        Agent result dict, or None if skipped/failed.
    """
    if filename in _in_progress:
        if filename not in _logged_skipped:
            log.debug(f"{filename} - translation in progress, waiting...")
            _logged_skipped.add(filename)
        return None

    # Clear the skipped flag when starting fresh
    _logged_skipped.discard(filename)
    _in_progress.add(filename)

    source_path = f"{config.source_dir}/{filename}"
    target_path = f"{config.target_dir}/{filename}"

    log.info(f"📄 Translating: {filename}")

    prompt = f'Translate "{source_path}" to English and save to "{target_path}".'

    try:
        result = await run(prompt, mcp_client=mcp_client, mcp_tools=mcp_tools)
        log.success(f"✅ Translated: {filename}")
        log_stats()
        return result
    except Exception as error:
        log.error(f"Translation failed: {filename}", str(error))
        return None
    finally:
        _in_progress.discard(filename)


async def run_translation_loop(
    mcp_client: ClientSession,
    mcp_tools: list[Any],
) -> None:
    """Watch source directory and translate new files indefinitely.

    Polls every ``config.poll_interval`` seconds. Runs concurrently
    with the HTTP server via asyncio tasks.

    Args:
        mcp_client: Connected MCP session.
        mcp_tools: Available MCP tools.
    """
    log.start(f"Watching {config.source_dir} (every {config.poll_interval}s)")
    log.info(f"Output: {config.target_dir}")

    await _ensure_directories(mcp_client)

    async def tick() -> None:
        try:
            source_files = await _list_files(mcp_client, config.source_dir, filter_by_extension=True)
            translated_files = await _list_files(mcp_client, config.target_dir)
            pending = [f for f in source_files if f not in translated_files]

            for filename in pending:
                await _translate_file(filename, mcp_client, mcp_tools)
        except Exception as error:
            log.error("Watch loop error", str(error))

    # Initial run
    await tick()

    # Polling loop
    while True:
        await asyncio.sleep(config.poll_interval)
        await tick()
