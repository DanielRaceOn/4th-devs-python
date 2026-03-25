# -*- coding: utf-8 -*-

#   shutdown.py

"""
### Description:
Graceful shutdown handler — registers SIGINT/SIGTERM handlers that run a
cleanup coroutine once and then exit cleanly.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/helpers/shutdown.js`

"""

import asyncio
import signal
import sys
from collections.abc import Callable, Coroutine
from typing import Any


def on_shutdown(cleanup: Callable[[], Coroutine[Any, Any, None]]) -> Callable:
    """Register SIGINT/SIGTERM handlers that call ``cleanup`` once then exit.

    Args:
        cleanup: Async callable to invoke before process exit.

    Returns:
        The handler coroutine (also usable as a manual shutdown trigger).
    """
    shutting_down = False

    async def handler() -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        print()
        await cleanup()
        sys.exit(0)

    def _sync_handler(signum: int, frame: Any) -> None:
        """Synchronous signal wrapper — schedules the async handler."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(handler())
        else:
            loop.run_until_complete(handler())

    signal.signal(signal.SIGINT, _sync_handler)
    # SIGTERM is not available on Windows — ignore if missing
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _sync_handler)

    return handler
