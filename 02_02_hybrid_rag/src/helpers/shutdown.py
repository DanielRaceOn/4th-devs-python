# -*- coding: utf-8 -*-

#   shutdown.py

"""
### Description:
Graceful shutdown helper — registers SIGINT/SIGTERM handlers and returns
an async callable that runs the cleanup coroutine exactly once.

---

@Author:        Claude Sonnet 4.6
@Created on:    17.03.2026
@Based on:      src/helpers/shutdown.js

"""

import asyncio
import signal
from typing import Callable, Coroutine, Any


def on_shutdown(cleanup: Callable[[], Coroutine[Any, Any, None]]) -> Callable:
    """Register SIGINT/SIGTERM handlers that run *cleanup* once on exit.

    Args:
        cleanup: An async callable with no arguments to run during shutdown.

    Returns:
        An async callable that triggers the shutdown sequence when called
        directly (e.g., after the REPL loop exits normally).
    """
    shutting_down = False
    loop = asyncio.get_event_loop()

    async def handler() -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        print()
        await cleanup()

    def _signal_handler() -> None:
        loop.create_task(handler())

    loop.add_signal_handler(signal.SIGINT, _signal_handler)
    loop.add_signal_handler(signal.SIGTERM, _signal_handler)

    return handler
