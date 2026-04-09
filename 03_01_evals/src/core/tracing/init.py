# -*- coding: utf-8 -*-

#   init.py

"""
### Description:
Langfuse tracing initialisation — mirrors src/core/tracing/init.ts.

Reads LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY (and optionally
LANGFUSE_BASE_URL) from the environment.  If either key is missing,
tracing is silently skipped and ``is_tracing_active()`` returns False.

The module exposes a singleton Langfuse client that all other tracing
helpers import via ``get_langfuse_client()``.

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/core/tracing/init.ts

"""

import os
from typing import Optional

_langfuse_client: Optional[object] = None
_initialized: bool = False


def init_tracing() -> bool:
    """Initialise the Langfuse client if both API keys are present.

    Returns:
        ``True`` if the client was initialised successfully, ``False`` otherwise.
    """
    global _langfuse_client, _initialized

    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    host = os.environ.get("LANGFUSE_BASE_URL", "").strip() or None

    if not secret_key or not public_key:
        print(
            "[tracing] LANGFUSE_SECRET_KEY or LANGFUSE_PUBLIC_KEY not set — "
            "tracing disabled"
        )
        _initialized = False
        return False

    try:
        from langfuse import Langfuse  # type: ignore[import]

        kwargs: dict = {"secret_key": secret_key, "public_key": public_key}
        if host:
            kwargs["host"] = host

        _langfuse_client = Langfuse(**kwargs)
        _initialized = True
        print(f"[tracing] Langfuse tracing initialised (host={host or 'cloud'})")
        return True

    except Exception as exc:
        print(f"[tracing] Failed to initialise Langfuse: {exc}")
        _initialized = False
        return False


def is_tracing_active() -> bool:
    """Return True when Langfuse is initialised and ready to accept events."""
    return _initialized and _langfuse_client is not None


def get_langfuse_client() -> Optional[object]:
    """Return the active Langfuse client, or None if tracing is inactive."""
    return _langfuse_client if _initialized else None


def flush() -> None:
    """Flush all pending Langfuse events synchronously."""
    if _langfuse_client is not None and _initialized:
        try:
            _langfuse_client.flush()  # type: ignore[union-attr]
        except Exception as exc:
            print(f"[tracing] flush error: {exc}")


def shutdown_tracing() -> None:
    """Shut down the Langfuse SDK, flushing remaining events."""
    global _langfuse_client, _initialized
    if _langfuse_client is not None and _initialized:
        try:
            _langfuse_client.shutdown()  # type: ignore[union-attr]
            print("[tracing] Langfuse SDK shut down")
        except Exception as exc:
            print(f"[tracing] shutdown error: {exc}")
    _initialized = False
    _langfuse_client = None
