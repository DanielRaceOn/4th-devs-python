# -*- coding: utf-8 -*-

#   shutdown.py

"""
### Description:
Graceful shutdown handler. Registers SIGINT/SIGTERM signal handlers that invoke
an async cleanup coroutine on first signal, with protection against double invocation.

---

@Author:        Claude Sonnet 4.6
@Created on:    19.03.2026
@Based on:      `src/helpers/shutdown.js`


"""

import asyncio
import signal
from typing import Awaitable, Callable


def on_shutdown(
    cleanup: Callable[[], Awaitable[None]],
) -> Callable[[], Awaitable[None]]:
    """Register SIGINT/SIGTERM handlers that run ``cleanup`` once on first signal.

    Mirrors the JavaScript ``onShutdown`` function. Returns an async callable that
    triggers the same cleanup when called at normal exit (so callers do not need
    a separate try/finally block).

    Args:
        cleanup: Async callable invoked on shutdown signal or manual trigger.

    Returns:
        Async callable that runs ``cleanup`` exactly once (idempotent).
    """
    _shutting_down = False

    async def _trigger() -> None:
        nonlocal _shutting_down
        if _shutting_down:
            return
        _shutting_down = True
        print("\n")
        await cleanup()

    def _sync_handler(signum: int, frame: object) -> None:
        """Schedule the async cleanup from inside a synchronous signal handler."""
        nonlocal _shutting_down
        if _shutting_down:
            return
        _shutting_down = True
        print("\n")
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(cleanup())
        except RuntimeError:
            # No running loop — run synchronously as a last resort
            asyncio.run(cleanup())

    try:
        # SIGTERM is not available on Windows; ignore OSError/ValueError.
        # SIGINT is intentionally NOT overridden — Python's default SIGINT
        # behaviour (raise KeyboardInterrupt) is relied upon by app.py.
        signal.signal(signal.SIGTERM, _sync_handler)
    except (OSError, AttributeError, ValueError):
        pass

    return _trigger
