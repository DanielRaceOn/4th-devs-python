# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Module-level configuration for 01_02_tool_use: sets the sandbox directory path
and exposes the resolved API model name and system instructions used by the
sandboxed filesystem assistant.

---

@Author:        Claude Sonnet 4.6
@Created on:    10.03.2026
@Based on:      `src/config.js`


"""

import sys
from pathlib import Path

# Add project root to sys.path so the top-level config.py is importable.
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from config import resolve_model_for_provider

# Sandbox directory sits at <module_root>/sandbox/ (created by initializeSandbox).
_MODULE_ROOT = Path(__file__).parent.parent
SANDBOX_ROOT: Path = _MODULE_ROOT / "sandbox"
SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)

# API configuration for the sandboxed filesystem assistant.
API_MODEL: str = resolve_model_for_provider("gpt-4.1")
API_INSTRUCTIONS: str = (
    "You are a helpful assistant with access to a sandboxed filesystem.\n"
    "You can list, read, write, and delete files within the sandbox.\n"
    "Always use the available tools to interact with files.\n"
    "Be concise in your responses."
)
