# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Entry point for the 03_01_evals module — mirrors src/index.ts.

Start-up sequence:
  1. Load module-level .env (Langfuse keys, PORT override)
  2. Initialise Langfuse tracing (non-fatal if keys absent)
  3. Sync prompts to Langfuse (non-fatal)
  4. Build adapter resolver (OpenAI Responses API)
  5. Create FastAPI app and start uvicorn
  6. Handle SIGINT/SIGTERM with graceful tracing shutdown

Usage:
    .venv/Scripts/python 03_01_evals/app.py

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/index.ts

"""

import asyncio
import os
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Root config provides AI_API_KEY, AI_PROVIDER, EXTRA_API_HEADERS
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import AI_API_KEY, AI_PROVIDER, EXTRA_API_HEADERS  # noqa: E402

import uvicorn  # noqa: E402

from src.core.logger import create_logger  # noqa: E402
from src.core.tracing.init import init_tracing, shutdown_tracing  # noqa: E402
from src.core.tracing.prompts import sync_prompts  # noqa: E402
from src.core.adapters.index import build_adapters  # noqa: E402
from src.app import create_app  # noqa: E402

_PORT = int(os.environ.get("PORT", "3010"))
_logger = create_logger({"service": "03_01_evals"})


def _setup_signal_handlers(loop: asyncio.AbstractEventLoop) -> None:
    """Register SIGINT/SIGTERM handlers that flush and shut down tracing.

    Args:
        loop: The running event loop to schedule shutdown on.
    """
    def _handle_signal(sig: int) -> None:
        print(f"\n[server] Received signal {sig} — shutting down")
        shutdown_tracing()
        loop.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal, sig)
        except (NotImplementedError, OSError):
            # Windows does not support loop.add_signal_handler for SIGTERM
            pass


async def main() -> None:
    """Initialise all subsystems and start the uvicorn server."""
    _logger.info("starting 03_01_evals")

    # Step 1: Initialise tracing
    init_tracing()

    # Step 2: Sync prompts (non-fatal)
    try:
        await sync_prompts()
    except Exception as exc:
        _logger.warn("prompt sync failed (non-fatal)", {"error": str(exc)})

    # Step 3: Build adapter resolver (Responses API)
    base_url = "https://openrouter.ai/api/v1" if AI_PROVIDER == "openrouter" else None
    adapter_resolver = build_adapters(
        config={
            "openai": {
                "api_key": AI_API_KEY,
                "base_url": base_url,
                "default_headers": EXTRA_API_HEADERS,
                "default_model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
            }
        },
        enable_tracing=True,
    )

    # Step 4: Create FastAPI app
    app = create_app(logger=_logger, adapter_resolver=adapter_resolver)

    # Step 5: Start server
    print()
    print("=" * 42)
    print("  03_01 Evals")
    print(f"  http://localhost:{_PORT}")
    print("=" * 42)
    print()
    print("  Endpoints:")
    print(f"    GET  http://localhost:{_PORT}/api/health")
    print(f"    GET  http://localhost:{_PORT}/api/sessions")
    print(f"    POST http://localhost:{_PORT}/api/chat")
    print()

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    loop = asyncio.get_event_loop()
    _setup_signal_handlers(loop)

    try:
        await server.serve()
    finally:
        shutdown_tracing()
        _logger.info("server stopped")


if __name__ == "__main__":
    asyncio.run(main())
