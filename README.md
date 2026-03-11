# 4th-devs-python 🐍

Repository contains [AI Devs 4](https://www.aidevs.pl/) course code examples, converted from `JavaScript` project to `Python` for educational purposes.

Created with Claude Code with permission from original repository author: [i-am-alice/4th-devs](https://github.com/i-am-alice/4th-devs).

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

## Lesson 03 — MCP (Model Context Protocol)

All Lesson 03 examples use the Python `mcp` SDK. Install it first:

```bash
pip install mcp
```

| Example | Run | Description |
|---------|-----|-------------|
| `01_03_mcp_core` | `python 01_03_mcp_core/app.py` | Full MCP demo over stdio: tools, resources, prompts, sampling |
| `01_03_mcp_native` | `python 01_03_mcp_native/app.py` | Unified agent with in-memory MCP tools and native Python tools |
| `01_03_mcp_translator` | `python 01_03_mcp_translator/app.py` | Polish→English file-watching translation agent with HTTP API |
| `01_03_upload_mcp` | `python 01_03_upload_mcp/app.py` | Multi-server upload agent (files-mcp stdio + uploadthing HTTP) |

Run examples from the project root:

```bash
python 01_03_mcp_core/app.py
python 01_03_mcp_native/app.py
python 01_03_mcp_translator/app.py
python 01_03_upload_mcp/app.py
```

`01_03_mcp_core` — Spawns a local MCP server as a subprocess over stdio. Exercises all MCP primitives: `calculate` and `summarize_with_confirmation` tools (the latter demonstrates server-initiated sampling), `config://project` and `data://stats` resources, and a `code-review` prompt template.

`01_03_mcp_native` — Starts an in-memory MCP server with `get_weather` and `get_time` tools, then adds native Python tools (`calculate`, `uppercase`) in the same agent loop. The model sees all tools as one unified toolset.

`01_03_mcp_translator` — Connects to the `files-mcp` server defined in `mcp.json` via stdio. Watches `workspace/translate/` for files and translates them to English using an agentic loop. Also exposes `POST /api/chat` and `POST /api/translate` HTTP endpoints.

```bash
curl -X POST "http://localhost:3000/api/translate" \
  -H "Content-Type: application/json" \
  -d '{"text":"To jest przykladowy tekst po polsku."}'
```

`01_03_upload_mcp` — Connects to two MCP servers simultaneously: `files` (stdio, local filesystem) and `uploadthing` (HTTP, remote). The agent lists workspace files, uploads untracked ones using `{{file:path}}` placeholders, and records results in `uploaded.md`. Edit `01_03_upload_mcp/mcp.json` and replace the uploadthing URL placeholder before running.
