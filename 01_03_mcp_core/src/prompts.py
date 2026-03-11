# -*- coding: utf-8 -*-

#   prompts.py

"""
### Description:
MCP prompt definitions for the demo server.
Prompts are reusable message templates with parameters that clients can
discover via listPrompts and instantiate via getPrompt with arguments.

---

@Author:        Claude Sonnet 4.6
@Created on:    11.03.2026
@Based on:      `src/prompts.js`

"""

from mcp.types import GetPromptResult, PromptMessage, TextContent


_FOCUS_MAP = {
    "security": "Focus on security vulnerabilities and input validation.",
    "performance": "Focus on performance and optimization.",
    "readability": "Focus on code clarity and maintainability.",
    "all": "Review for security, performance, and readability.",
}


def get_code_review_prompt(
    code: str,
    language: str = "unknown",
    focus: str = "all",
) -> GetPromptResult:
    """Build the code-review prompt with runtime arguments.

    Args:
        code: Source code to review.
        language: Programming language label (e.g. ``"javascript"``).
        focus: Review focus area — one of ``"security"``, ``"performance"``,
            ``"readability"``, or ``"all"``.

    Returns:
        A ``GetPromptResult`` with a single user message.
    """
    focus_instruction = _FOCUS_MAP.get(focus, _FOCUS_MAP["all"])

    text = (
        f"Review this {language} code.\n\n"
        f"{focus_instruction}\n\n"
        f"```{language}\n{code}\n```"
    )

    return GetPromptResult(
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=text),
            )
        ]
    )
