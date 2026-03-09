# -*- coding: utf-8 -*-

#   app.py

"""
### Description:
Structured outputs example — the model returns guaranteed valid JSON matching
a provided schema. Extracts person information (name, age, occupation, skills)
from a natural-language description.

---

@Author:        Daniel Szczepanski
@Created on:    09.03.2026
@Based on:      `app.js`

"""

import asyncio
import json
import sys
from typing import Any

import httpx

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from config import AI_API_KEY, EXTRA_API_HEADERS, RESPONSES_API_ENDPOINT, resolve_model_for_provider  # noqa: E402
from helpers import extract_response_text  # noqa: E402

MODEL = resolve_model_for_provider("gpt-5.4")

PERSON_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "name": "person",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": ["string", "null"],
                "description": "Full name of the person. Use null if not mentioned.",
            },
            "age": {
                "type": ["number", "null"],
                "description": "Age in years. Use null if not mentioned or unclear.",
            },
            "occupation": {
                "type": ["string", "null"],
                "description": "Job title or profession. Use null if not mentioned.",
            },
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of skills, technologies, or competencies. "
                    "Empty array if none mentioned."
                ),
            },
        },
        "required": ["name", "age", "occupation", "skills"],
        "additionalProperties": False,
    },
}


async def extract_person(text: str) -> dict[str, Any]:
    """Extract structured person information from a text description.

    Args:
        text: Natural-language description of a person.

    Returns:
        Dict with keys ``name``, ``age``, ``occupation``, ``skills``.

    Raises:
        RuntimeError: If the API returns an error or no text output.
    """
    payload = {
        "model": MODEL,
        "input": f'Extract person information from: "{text}"',
        "text": {"format": PERSON_SCHEMA},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            RESPONSES_API_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}",
                **EXTRA_API_HEADERS,
            },
            json=payload,
            timeout=120.0,
        )

    data = response.json()

    if not response.is_success or data.get("error"):
        message = (
            data.get("error", {}).get("message")
            or f"Request failed with status {response.status_code}"
        )
        raise RuntimeError(message)

    output_text = extract_response_text(data)
    if not output_text:
        raise RuntimeError("Missing text output in API response")

    return json.loads(output_text)


async def main() -> None:
    """Run the structured extraction demo."""
    text = (
        "John is 30 years old and works as a software engineer. "
        "He is skilled in JavaScript, Python, and React."
    )
    person = await extract_person(text)

    print(f"Name: {person.get('name') or 'unknown'}")
    print(f"Age: {person.get('age') or 'unknown'}")
    print(f"Occupation: {person.get('occupation') or 'unknown'}")
    skills: list[str] = person.get("skills") or []
    print(f"Skills: {', '.join(skills) if skills else 'none'}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
