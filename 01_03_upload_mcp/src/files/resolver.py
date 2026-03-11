# -*- coding: utf-8 -*-

#   resolver.py

"""
### Description:
File reference resolver — replaces {{file:path}} placeholders with base64.
The model references workspace files using {{file:path}} syntax in tool
arguments. Before calling the MCP server, this resolver walks the argument
tree and replaces each placeholder with the actual base64-encoded content.
This avoids the model having to read and encode files itself.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/files/resolver.js`

"""

import base64
import re
from pathlib import Path
from typing import Any

from ..helpers.logger import log

_FILE_REF_PATTERN = re.compile(r"\{\{file:([^}]+)\}\}")


async def _read_as_base64(workspace_root: Path, relative_path: str) -> str:
    """Read a workspace file and return its content as a base64 string.

    Args:
        workspace_root: Absolute path to the workspace directory.
        relative_path: File path relative to the workspace root.

    Returns:
        Base64-encoded file content.
    """
    full_path = workspace_root / relative_path
    data = full_path.read_bytes()
    return base64.b64encode(data).decode("ascii")


async def _resolve_in_string(s: str, workspace_root: Path) -> str:
    """Replace all ``{{file:path}}`` placeholders in a string with base64 data.

    Args:
        s: String potentially containing placeholders.
        workspace_root: Workspace directory for resolving relative paths.

    Returns:
        String with all valid placeholders replaced.
    """
    matches = list(_FILE_REF_PATTERN.finditer(s))
    if not matches:
        return s

    result = s
    for match in matches:
        placeholder, file_path = match.group(0), match.group(1)
        try:
            b64 = await _read_as_base64(workspace_root, file_path)
            log.info(f"   📎 Resolved: {file_path} → {len(b64)} chars")
            result = result.replace(placeholder, b64)
        except Exception as error:
            log.warn(f"   ⚠️ Failed: {file_path} - {error}")

    return result


async def resolve_file_refs(value: Any, workspace_root: Path) -> Any:
    """Recursively resolve ``{{file:path}}`` placeholders in any value.

    Walks strings, lists, and dicts, replacing placeholders with base64
    content from the workspace. Non-string primitives are returned as-is.

    Args:
        value: Argument value to resolve (string, list, dict, or primitive).
        workspace_root: Absolute path to the workspace directory.

    Returns:
        Value with all string placeholders resolved.
    """
    if isinstance(value, str):
        return await _resolve_in_string(value, workspace_root)
    if isinstance(value, list):
        import asyncio
        return list(await asyncio.gather(*[resolve_file_refs(v, workspace_root) for v in value]))
    if isinstance(value, dict):
        import asyncio
        entries = await asyncio.gather(
            *[resolve_file_refs(v, workspace_root) for v in value.values()]
        )
        return dict(zip(value.keys(), entries))
    return value
