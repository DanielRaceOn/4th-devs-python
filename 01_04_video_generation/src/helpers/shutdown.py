# -*- coding: utf-8 -*-

#   shutdown.py

"""
### Description:
Graceful shutdown handler for SIGINT and SIGTERM signals.

---

@Author:        Claude Sonnet 4.6
@Created on:    12.03.2026
@Based on:      helpers/shutdown.js

"""

import signal
import asyncio
from typing import Callable, Awaitable


def on_shutdown(cleanup: Callable[[], Awaitable[None]]) -> Callable[[], Awaitable[None]]:
    """
    Register signal handlers for graceful shutdown.

    Args:
        cleanup: Async function to call on shutdown

    Returns:
        The handler function
    """
    shutting_down = False

    async def handler() -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        print("\n")
        await cleanup()
        exit(0)

    def sync_handler(signum, frame):
        """Sync wrapper for signal handler."""
        asyncio.create_task(handler())

    signal.signal(signal.SIGINT, sync_handler)
    signal.signal(signal.SIGTERM, sync_handler)

    return handler
