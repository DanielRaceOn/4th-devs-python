# -*- coding: utf-8 -*-

#   prompts.py

"""
### Description:
Langfuse prompt synchronisation — mirrors src/core/tracing/prompts.ts.

``sync_prompts()`` collects all local prompt sources (Alice system prompt),
hashes each one, compares against a local state file
(``.langfuse-prompt-state.json`` in the module root), and pushes changed
prompts to Langfuse.  On success the new version is stored in the state
file.

``get_prompt_ref_by_name()`` returns a cached PromptRef for in-request use.

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/core/tracing/prompts.ts

"""

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from .context import PromptRef
from .init import get_langfuse_client, is_tracing_active

# Module root is three levels up from this file:
# tracing/ -> core/ -> src/ -> 03_01_evals/
_MODULE_ROOT = Path(__file__).parent.parent.parent.parent
_STATE_FILE = _MODULE_ROOT / ".langfuse-prompt-state.json"

# In-memory cache of name -> PromptRef
_prompt_cache: dict[str, PromptRef] = {}


def _load_state() -> dict[str, Any]:
    """Load the persisted prompt hash/version state from disk."""
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_state(state: dict[str, Any]) -> None:
    """Persist the prompt state dict to disk."""
    try:
        _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"[prompts] Failed to save state: {exc}")


def _sha256(text: str) -> str:
    """Return the SHA-256 hex digest of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def _collect_prompt_sources() -> list[dict[str, Any]]:
    """Collect all local prompt sources to sync to Langfuse.

    The import of ``build_alice_system_prompt`` is deferred here to break
    the circular import between prompts.py (tracing) and agent/run.py.

    Returns:
        List of dicts with keys ``name``, ``content``, ``tags``.
    """
    # Lazy import to avoid circular dependency: prompts -> agent/run -> tracer
    from ...agent.run import build_alice_system_prompt  # noqa: PLC0415

    return [
        {
            "name": "agents/alice",
            "content": build_alice_system_prompt(),
            "tags": ["agent-template"],
        }
    ]


async def sync_prompts() -> None:
    """Sync local prompt sources to Langfuse if they have changed.

    Compares SHA-256 hashes against ``.langfuse-prompt-state.json``.
    Only prompts whose content has changed since the last sync are pushed.
    """
    if not is_tracing_active():
        print("[prompts] Tracing inactive — skipping prompt sync")
        return

    client = get_langfuse_client()
    if client is None:
        return

    try:
        sources = await _collect_prompt_sources()
    except Exception as exc:
        print(f"[prompts] Failed to collect prompt sources: {exc}")
        return

    state = _load_state()

    for source in sources:
        name: str = source["name"]
        content: str = source["content"]
        tags: list[str] = source.get("tags", [])
        new_hash = _sha256(content)

        existing = state.get(name, {})
        if existing.get("hash") == new_hash:
            stored_version = existing.get("version", 0)
            _prompt_cache[name] = PromptRef(name=name, version=stored_version, is_fallback=False)
            print(f"[prompts] '{name}' unchanged (version {stored_version})")
            continue

        try:
            prompt_obj = client.create_prompt(  # type: ignore[union-attr]
                name=name,
                prompt=content,
                labels=["production"],
                tags=tags,
                type="text",
            )
            version: int = getattr(prompt_obj, "version", 1)
            _prompt_cache[name] = PromptRef(name=name, version=version, is_fallback=False)
            state[name] = {"hash": new_hash, "version": version}
            _save_state(state)
            print(f"[prompts] '{name}' pushed to Langfuse as version {version}")
        except Exception as exc:
            print(f"[prompts] Failed to push '{name}': {exc}")
            stored_version = existing.get("version", 0)
            if stored_version:
                _prompt_cache[name] = PromptRef(name=name, version=stored_version, is_fallback=True)


def get_prompt_ref_by_name(name: str) -> Optional[PromptRef]:
    """Return the cached PromptRef for a named prompt.

    Args:
        name: Prompt name as registered in Langfuse (e.g. ``"agents/alice"``).

    Returns:
        The cached ``PromptRef``, or ``None`` if not yet synced.
    """
    return _prompt_cache.get(name)
