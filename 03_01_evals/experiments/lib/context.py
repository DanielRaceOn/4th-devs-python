# -*- coding: utf-8 -*-

#   context.py

"""
### Description:
Experiment bootstrap context — mirrors experiments/lib/context.ts.

``bootstrap()`` initialises all shared subsystems needed by an eval script:
  - Logger
  - Langfuse tracing
  - Prompt sync
  - OpenAI Responses API adapter
  - Langfuse client for dataset operations

Returns an ``ExperimentContext`` dataclass and a ``shutdown()`` coroutine
that cleanly flushes and closes both the tracing client and the Langfuse
dataset client.

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      experiments/lib/context.ts

"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Awaitable

# Allow imports from the module root and the project root
_MODULE_ROOT = Path(__file__).parent.parent.parent
_PROJECT_ROOT = _MODULE_ROOT.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_MODULE_ROOT))

from dotenv import load_dotenv

load_dotenv(_MODULE_ROOT / ".env")

from config import AI_API_KEY, AI_PROVIDER, EXTRA_API_HEADERS  # noqa: E402
from src.core.logger import Logger, create_logger  # noqa: E402
from src.core.tracing.init import init_tracing, shutdown_tracing  # noqa: E402
from src.core.tracing.prompts import sync_prompts  # noqa: E402
from src.core.adapters.index import build_adapters  # noqa: E402
from src.types import Adapter  # noqa: E402

import os


@dataclass
class ExperimentContext:
    """All shared resources needed by an eval experiment."""

    logger: Logger
    adapter: Adapter
    langfuse: object  # langfuse.Langfuse instance
    shutdown: Callable[[], Awaitable[None]]


async def bootstrap(experiment_name: str) -> ExperimentContext:
    """Initialise all subsystems for a Langfuse eval experiment.

    Reads LANGFUSE_* and OPENAI_API_KEY from the environment (loaded from
    ``03_01_evals/.env`` by ``context.py`` at import time).

    Args:
        experiment_name: Short experiment identifier used in log bindings
                         and the Langfuse service name suffix.

    Returns:
        An ``ExperimentContext`` with logger, adapter, langfuse client, and
        a ``shutdown`` coroutine.

    Raises:
        RuntimeError: If the OpenAI adapter cannot be constructed (API key
                      missing).
    """
    logger = create_logger({"service": "03_01_evals", "experiment": experiment_name})

    init_tracing()

    try:
        await sync_prompts()
    except Exception as exc:
        logger.warn("prompt sync failed in experiment mode", {"error": str(exc)})

    base_url = "https://openrouter.ai/api/v1" if AI_PROVIDER == "openrouter" else None
    get_adapter = build_adapters(
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

    adapter_result = get_adapter("openai")
    if not adapter_result.ok:
        raise RuntimeError(f"Adapter unavailable: {adapter_result.error.message}")

    # Langfuse client for dataset API operations
    from langfuse import Langfuse  # type: ignore[import]

    lf_kwargs: dict = {
        "secret_key": os.environ.get("LANGFUSE_SECRET_KEY", ""),
        "public_key": os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
    }
    host = os.environ.get("LANGFUSE_BASE_URL", "").strip()
    if host:
        lf_kwargs["host"] = host
    langfuse = Langfuse(**lf_kwargs)

    async def shutdown() -> None:
        """Flush and shut down all clients cleanly."""
        try:
            langfuse.flush()
        except Exception:
            pass
        shutdown_tracing()
        try:
            langfuse.shutdown()
        except Exception:
            pass

    return ExperimentContext(
        logger=logger,
        adapter=adapter_result.value,
        langfuse=langfuse,
        shutdown=shutdown,
    )
