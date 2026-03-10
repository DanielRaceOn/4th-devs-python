# -*- coding: utf-8 -*-

#   definitions.py

"""
### Description:
Tool definitions (JSON Schema) for the sandboxed filesystem assistant.
These are sent to the Responses API so the model knows which tools it can
call and what arguments each one expects.

---

@Author:        Claude Sonnet 4.6
@Created on:    10.03.2026
@Based on:      `src/tools/definitions.js`


"""

from typing import Any, Dict, List

tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "name": "list_files",
        "description": "List files and directories at a given path within the sandbox",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path within sandbox. Use '.' for root directory.",
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read the contents of a file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file within sandbox",
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "write_file",
        "description": "Write content to a file (creates or overwrites)",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file within sandbox",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "delete_file",
        "description": "Delete a file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file to delete",
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "create_directory",
        "description": "Create a directory (and parent directories if needed)",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path for the new directory",
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "file_info",
        "description": "Get metadata about a file or directory",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file or directory",
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]
