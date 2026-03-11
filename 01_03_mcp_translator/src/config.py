# -*- coding: utf-8 -*-

#   config.py

"""
### Description:
Module-level configuration for the MCP translator agent.
Contains API model settings, server binding, and translator watch parameters.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/config.js`

"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config import resolve_model_for_provider


@dataclass
class ApiConfig:
    """AI provider configuration."""

    model: str = field(default_factory=lambda: resolve_model_for_provider("gpt-5.2"))
    max_output_tokens: int = 16384
    instructions: str = (
        "You are a professional Polish-to-English translator with expertise in "
        "technical and educational content.\n\n"
        "PHILOSOPHY\n"
        "Great translation is invisible — natural, fluent, as if originally written "
        "in English. You translate meaning and voice, not just words.\n\n"
        "PROCESS\n"
        "1. SCAN — Check file metadata first (use mode:\"list\" with details:true to see "
        "line count). Never load the full file blindly.\n"
        "2. PLAN — If file ≤100 lines: read and translate in one pass. If file >100 lines: "
        "work in chunks of ~80 lines.\n"
        "3. TRANSLATE — For each chunk: read it, translate it, write/append it. Move to next "
        "chunk. Repeat until done.\n"
        "4. VERIFY — Read the translated file. Compare line counts with source. Ensure nothing "
        "was skipped.\n\n"
        "CHUNKING RULES (for files >100 lines):\n"
        "- First chunk: read lines 1-80, translate, write with operation:\"create\"\n"
        "- Next chunks: read lines 81-160, etc., translate, append using operation:\"update\" "
        "with action:\"insert_after\"\n"
        "- Continue until all lines are translated\n\n"
        "CRAFT\n"
        "- Sound native, not translated\n"
        "- Preserve author's voice and tone\n"
        "- Adapt idioms naturally\n"
        "- Keep all formatting: headers, lists, code blocks, links, images\n\n"
        "Only say \"Done: <filename>\" after verification."
    )


@dataclass
class ServerConfig:
    """HTTP server binding configuration."""

    port: int = field(default_factory=lambda: int(os.environ.get("PORT", "3000")))
    host: str = field(default_factory=lambda: os.environ.get("HOST", "localhost"))


@dataclass
class TranslatorConfig:
    """File-watching translation configuration."""

    source_dir: str = "translate"
    target_dir: str = "translated"
    poll_interval: float = 5.0  # seconds
    supported_extensions: List[str] = field(
        default_factory=lambda: [".md", ".txt", ".html", ".json"]
    )


api = ApiConfig()
server = ServerConfig()
translator = TranslatorConfig()
