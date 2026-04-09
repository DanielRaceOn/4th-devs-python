# -*- coding: utf-8 -*-

#   index.py

"""
### Description:
Adapter registry and resolver — mirrors src/core/adapters/index.ts.

``build_adapters(config)`` constructs a registry of named adapters and
optionally wraps each one with generation tracing.  Returns an
``AdapterResolver`` callable that maps a ``Provider`` name to a Result.

---

@Author:        Claude Sonnet 4.6
@Created on:    09.04.2026
@Based on:      src/core/adapters/index.ts

"""

from typing import Any

from ..result import Err, Ok, err, ok
from ...types import Adapter, AdapterResolver, CompletionError, Provider
from .openai import openai_adapter
from ..tracing.adapter import with_generation_tracing


def build_adapters(
    config: dict[str, Any],
    enable_tracing: bool = True,
) -> AdapterResolver:
    """Build an adapter registry and return a resolver function.

    Args:
        config: Top-level configuration dict.  Expected keys:
            - ``openai`` (dict) — passed directly to ``openai_adapter``.
        enable_tracing: When ``True`` (default), each adapter is wrapped
            with ``with_generation_tracing``.

    Returns:
        A callable ``(provider: Provider) -> Result[Adapter, CompletionError]``
        that resolves a named provider to its adapter.
    """
    registry: dict[str, Adapter] = {}

    openai_cfg = config.get("openai")
    if openai_cfg:
        adapter: Adapter = openai_adapter(openai_cfg)
        if enable_tracing:
            adapter = with_generation_tracing(adapter)
        registry["openai"] = adapter

    def resolver(provider: Provider) -> "Ok[Adapter] | Err[CompletionError]":
        """Resolve a provider name to an Adapter.

        Args:
            provider: Provider identifier, e.g. ``"openai"``.

        Returns:
            ``ok(adapter)`` or ``err(CompletionError)`` if not configured.
        """
        resolved = registry.get(provider)
        if resolved is None:
            return err(
                CompletionError(
                    code="PROVIDER_NOT_CONFIGURED",
                    message=f"No adapter configured for provider '{provider}'",
                    provider=provider,
                )
            )
        return ok(resolved)

    return resolver
