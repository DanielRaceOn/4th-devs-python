# -*- coding: utf-8 -*-

#   dataset.py

"""
### Description:
Langfuse dataset helpers — mirrors experiments/lib/dataset.ts.

Provides:
  - ``load_json_file``     — read and parse a JSON file into a Result
  - ``ensure_dataset``     — create a Langfuse dataset if it does not exist
  - ``sync_dataset_items`` — upsert a list of dataset items into Langfuse

Uses the Langfuse Python SDK directly (no REST client needed since the
Python SDK exposes these operations on the ``Langfuse`` object).

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      experiments/lib/dataset.ts

"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Local imports resolved after sys.path setup in context.py
from src.core.logger import Logger
from src.core.result import Result, err, ok


@dataclass
class DatasetItemSeed:
    """Seed data for a Langfuse dataset item."""

    id: str
    input: Any
    expected_output: Any
    metadata: Optional[dict[str, Any]] = field(default=None)


def load_json_file(path: str | Path) -> "Result[Any, str]":
    """Load and parse a JSON file, returning a Result.

    Args:
        path: Path to the JSON file.

    Returns:
        ``ok(parsed_value)`` on success, ``err(message)`` on failure.
    """
    try:
        content = Path(path).read_text(encoding="utf-8")
        return ok(json.loads(content))
    except Exception as exc:
        return err(str(exc))


def ensure_dataset(
    langfuse: Any,
    name: str,
    description: str,
    logger: Logger,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Create a Langfuse dataset if it does not already exist.

    Attempts to fetch the dataset first; if that fails (does not exist),
    creates it.  Errors during creation are re-raised.

    Args:
        langfuse: ``Langfuse`` client instance.
        name: Dataset name.
        description: Human-readable description.
        logger: Logger for status messages.
        metadata: Optional metadata dict.
    """
    try:
        langfuse.get_dataset(name)
        logger.info("Dataset exists", {"dataset": name})
        return
    except Exception:
        pass  # Dataset does not exist yet — create it

    langfuse.create_dataset(
        name=name,
        description=description,
        metadata=metadata or {},
    )
    logger.info("Dataset created", {"dataset": name})


def sync_dataset_items(
    langfuse: Any,
    dataset_name: str,
    items: list[DatasetItemSeed],
    logger: Logger,
) -> None:
    """Upsert dataset items into Langfuse (create or overwrite by ID).

    Args:
        langfuse: ``Langfuse`` client instance.
        dataset_name: Target dataset name.
        items: List of ``DatasetItemSeed`` objects to sync.
        logger: Logger for status messages.
    """
    for item in items:
        langfuse.create_dataset_item(
            dataset_name=dataset_name,
            id=item.id,
            input=item.input,
            expected_output=item.expected_output,
            metadata=item.metadata,
        )

    logger.info(
        "Dataset items synced",
        {"dataset": dataset_name, "count": len(items)},
    )
