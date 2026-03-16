# -*- coding: utf-8 -*-

#   shutdown.py

"""
### Description:
Graceful shutdown handler — registers SIGINT/SIGTERM signal handlers that call
an async cleanup coroutine before exiting.

---

@Author:        Claude Sonnet 4.6
@Created on:    16.03.2026
@Based on:      src/helpers/shutdown.js

"""

import asyncio
import signal
import sys
from typing import Callable, Coroutine, Any


def on_shutdown(cleanup: Callable[[], Coroutine[Any, Any, None]]) -> Callable[[], Coroutine[Any, Any, None]]:
    """Register SIGINT and SIGTERM handlers that run an async cleanup coroutine.

    The returned coroutine can be awaited manually to trigger the same cleanup
    path (e.g. at the end of a normal run).

    Args:
        cleanup: Async zero-argument coroutine to run on shutdown.

    Returns:
        Async handler coroutine that can also be awaited directly.
    """
    shutting_down = False

    async def handler() -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        print("\n")
        await cleanup()
        sys.exit(0)

    def _sync_handler(signum: int, frame: Any) -> None:
        # Schedule async handler on the running event loop.
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(handler())
        except RuntimeError:
            pass

    signal.signal(signal.SIGINT, _sync_handler)
    # SIGTERM is not available on Windows; ignore ImportError/OSError gracefully.
    try:
        signal.signal(signal.SIGTERM, _sync_handler)
    except (OSError, AttributeError):
        pass

    return handler
