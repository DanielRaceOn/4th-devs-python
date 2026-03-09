# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Module-level configuration for 01_01_grounding: file paths, model names,
API settings, and CLI argument parsing.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Created based on:  `src/config.js`

"""

import argparse
import sys
from pathlib import Path
from typing import Any

_SRC_DIR = Path(__file__).parent
_PROJECT_DIR = _SRC_DIR.parent
_ROOT_DIR = _PROJECT_DIR.parent

sys.path.insert(0, str(_ROOT_DIR))

from config import RESPONSES_API_ENDPOINT, resolve_model_for_provider  # noqa: E402

paths: dict[str, Path] = {
    "root": _ROOT_DIR,
    "project": _PROJECT_DIR,
    "notes": _PROJECT_DIR / "notes",
    "output": _PROJECT_DIR / "output",
    "template": _PROJECT_DIR / "template.html",
    "concepts": _PROJECT_DIR / "output" / "concepts.json",
    "dedupe": _PROJECT_DIR / "output" / "dedupe.json",
    "search": _PROJECT_DIR / "output" / "search_results.json",
    "grounded": _PROJECT_DIR / "output" / "grounded.html",
}

models: dict[str, str] = {
    "extract": resolve_model_for_provider("gpt-5.4"),
    "search": resolve_model_for_provider("gpt-5.4"),
    "ground": resolve_model_for_provider("gpt-5.4"),
}

api: dict[str, Any] = {
    "endpoint": RESPONSES_API_ENDPOINT,
    "timeout_ms": 180_000,
    "retries": 3,
    "retry_delay_ms": 1000,
}

# --- CLI argument parsing ---
_parser = argparse.ArgumentParser(description="01_01_grounding: ground markdown notes via AI")
_parser.add_argument("input_file", nargs="?", default=None, help=".md file in notes/ directory")
_parser.add_argument("--force", action="store_true", help="Rebuild all cached outputs from scratch")
_parser.add_argument(
    "--batch",
    type=int,
    default=None,
    metavar="N",
    help="Parallel batch size (1-10, default 3)",
)
_parser.add_argument("--no-batch", action="store_true", help="Disable batching (batch size = 1)")

_args, _unknown = _parser.parse_known_args()


def _parse_batch_size() -> int:
    if _args.no_batch:
        return 1
    if _args.batch is not None:
        value = _args.batch
        return 3 if value < 1 else min(value, 10)
    return 3


cli: dict[str, Any] = {
    "force": _args.force,
    "input_file": _args.input_file,
    "batch_size": _parse_batch_size(),
}
