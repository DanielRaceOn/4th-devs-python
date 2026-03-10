<img src="../4th-devs-js/assets/logo.svg" alt="AI_devs 4: Builders" width="200">

## Requirements

This project runs on **Python 3.8 or later**. Dependencies are managed with **pip**.

## Setup

Install all dependencies from the project root:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env`.

Set one Responses API key. You can choose between **OpenAI** and **OpenRouter**:

**[OpenRouter](https://openrouter.ai/settings/keys)** (recommended) — create an account and generate an API key. No additional verification required.

```bash
OPENROUTER_API_KEY=your_api_key_here
```

**[OpenAI](https://platform.openai.com/api-keys)** — create an account and generate an API key. Note that OpenAI requires [organization verification](https://help.openai.com/en/articles/10910291-api-organization-verification) before API access is granted, which may take additional time.

```bash
OPENAI_API_KEY=your_api_key_here
```

If both keys are present, provider defaults to OpenAI. Override with `AI_PROVIDER=openrouter`.

## Lesson 01

| Example | Run | Description |
|---------|-----|-------------|
| `01_01_interaction` | `python -m 01_01_interaction.app` | Multi-turn conversation via input history |
| `01_01_structured` | `python -m 01_01_structured.app` | Structured JSON output with schema validation |
| `01_01_grounding` | `python -m 01_01_grounding.app` | Fact-checked HTML from markdown notes |

Run examples from the project root:

```bash
python -m 01_01_interaction.app
python -m 01_01_structured.app
python -m 01_01_grounding.app
```

The grounding example accepts optional arguments:

```bash
# Process a specific note file
python -m 01_01_grounding.app my-note.md

# Force rebuild from scratch (ignore cache)
python -m 01_01_grounding.app --force

# Combine both
python -m 01_01_grounding.app my-note.md --force

# Control parallel batch size (default 3, max 10)
python -m 01_01_grounding.app --batch=5

# Disable batching entirely
python -m 01_01_grounding.app --no-batch
```

## Lesson 02

| Example | Run | Description |
|---------|-----|-------------|
| `01_02_tools` | `python -m 01_02_tools.app` | Minimal tool-use: weather lookup + send email with web search |
| `01_02_tool_use` | `python -m 01_02_tool_use.app` | Sandboxed filesystem assistant (list, read, write, delete files) |

Run examples from the project root:

```bash
python -m 01_02_tools.app
python -m 01_02_tool_use.app
```

`01_02_tools` — The model uses web search to look up the current weather in Kraków, then calls a mocked `send_email` tool to deliver the result to a recipient.

`01_02_tool_use` — A sandboxed filesystem assistant that can list, read, write, and delete files.  All file operations are confined to the `01_02_tool_use/sandbox/` directory; path traversal attempts are blocked.  A sequence of predefined queries exercises every available tool including a security-test query.
