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
| `01_01_interaction` | `python "01_01_interaction/app.py"` | Multi-turn conversation via input history |
| `01_01_structured` | `python "01_01_structured/app.py"` | Structured JSON output with schema validation |
| `01_01_grounding` | `python "01_01_grounding/app.py"` | Fact-checked HTML from markdown notes |

Run examples from the project root:

```bash
python  "01_01_interaction/app.py"
python  "01_01_structured/app.py"
python  "01_01_grounding/app.py"
```

The grounding example accepts optional arguments:

```bash
# Process a specific note file
python "01_01_grounding/app.py" my-note.md

# Force rebuild from scratch (ignore cache)
python "01_01_grounding/app.py" --force

# Combine both
python "01_01_grounding/app.py" my-note.md --force

# Control parallel batch size (default 3, max 10)
python "01_01_grounding/app.py" --batch=5

# Disable batching entirely
python "01_01_grounding/app.py" --no-batch
```

## Lesson 02

| Example | Run | Description |
|---------|-----|-------------|
| `01_02_tools` | `python "01_02_tools/app.py"` | Minimal tool-use: weather lookup + send email with web search |
| `01_02_tool_use` | `python "01_02_tool_use/app.py"` | Sandboxed filesystem assistant (list, read, write, delete files) |

Run examples from the project root:

```bash
python "01_02_tools/app.py"
python "01_02_tool_use/app.py"
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
| `01_03_mcp_core` | `python "01_03_mcp_core/app.py"` | Full MCP demo over stdio: tools, resources, prompts, sampling |
| `01_03_mcp_native` | `python "01_03_mcp_native/app.py"` | Unified agent with in-memory MCP tools and native Python tools |
| `01_03_mcp_translator` | `python "01_03_mcp_translator/app.py"` | Polish→English file-watching translation agent with HTTP API |
| `01_03_upload_mcp` | `python "01_03_upload_mcp/app.py"` | Multi-server upload agent (files-mcp stdio + uploadthing HTTP) |

Run examples from the project root:

```bash
python  "01_03_mcp_core/app.py"
python  "01_03_mcp_native/app.py"
python  "01_03_mcp_translator/app.py"
python  "01_03_upload_mcp/app.py"
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
<<<<<<< HEAD
=======

## Lesson 04 — Audio Processing

The Lesson 04 examples use the **Google Gemini API** for audio/image generation. Set the key before running:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

`01_04_image_editing` additionally requires either `GEMINI_API_KEY` or `OPENROUTER_API_KEY` for the image generation backend.

| Example | Run | Description |
|---------|-----|-------------|
| `01_04_audio` | `python "01_04_audio/app.py"` | Interactive audio agent — transcribe, analyze, query, and generate audio via Gemini |
| `01_04_image_recognition` | `python "01_04_image_recognition/app.py"` | Autonomous image classification agent — reads character knowledge profiles and classifies images into category folders using vision analysis |
| `01_04_image_editing` | `python "01_04_image_editing/app.py"` | Interactive image editing agent — generate or edit images via Gemini/OpenRouter, auto-analyze quality, maintain multi-turn conversation history |
| `01_04_image_guidance` | `python "01_04_image_guidance/app.py"` | Pose-guided cell-shaded character generation — copies JSON templates, selects pose references, generates and analyzes characters via Gemini/OpenRouter |
| `01_04_json_image` | `python "01_04_json_image/app.py"` | Token-efficient JSON-based image generation — copies style templates, edits only the subject section, generates images via Gemini/OpenRouter |
| `01_04_reports` | `python "01_04_reports/app.py"` | Autonomous PDF report generation — reads HTML template and style guide, generates images for visual consistency, converts final HTML to PDF via Playwright |
<<<<<<< HEAD
=======
| `01_04_video` | `python "01_04_video/app.py"` | Interactive video analysis agent — analyze, transcribe, extract scenes/objects/text from local video files or YouTube URLs via Gemini |
| `01_04_video_generation` | `python "01_04_video_generation/app.py"` | Frame-based video generation agent — generate start/end frames with Gemini, animate transitions with Kling AI via Replicate |
>>>>>>> b4eb695 (Convert JS module 01_04_video_generation to Python)

Run from the project root:

```bash
python "01_04_audio/app.py"
python "01_04_image_recognition/app.py"
python "01_04_image_editing/app.py"
python "01_04_json_image/app.py"
python "01_04_reports/app.py"
<<<<<<< HEAD
=======
python "01_04_video/app.py"
python "01_04_video_generation/app.py"
>>>>>>> b4eb695 (Convert JS module 01_04_video_generation to Python)
```

`01_04_audio` — An interactive REPL agent powered by Google Gemini. Supports transcription (with timestamps, speaker detection, emotion detection, and translation), audio analysis (general, music, speech, sounds), custom audio queries, and text-to-speech generation with 30+ voices. Accepts local audio files (MP3, WAV, AIFF, AAC, OGG, FLAC, M4A, WebM) and YouTube URLs. Files larger than 20 MB use Gemini's resumable upload API. Also connects to a `files-mcp` stdio server for filesystem access.

`01_04_image_recognition` — A single-run autonomous agent that classifies images from the `images/` folder into character-named subfolders based on knowledge profile files in `knowledge/`. Uses the Responses API for both orchestration and vision analysis (`understand_image` native tool). Connects to a `files-mcp` stdio server for all filesystem operations (read, copy, list).

`01_04_image_guidance` — A pose-guided cell-shaded character generation agent. The model follows a structured workflow: list available pose references in `workspace/reference/`, copy `workspace/template.json` to `workspace/prompts/`, edit only the subject section, then call `create_image` with the JSON prompt and pose reference. Supports both OpenRouter (preferred) and native Gemini backends. Includes `analyze_image` for quality review with ACCEPT/RETRY verdicts. Place pose reference images (e.g. `walking-pose.png`, `running-pose.png`) in `workspace/reference/` before running.

`01_04_image_editing` — An interactive REPL image editing agent. Uses two native tools: `create_image` (generate from scratch or edit with reference images) and `analyze_image` (quality analysis with ACCEPT/RETRY verdict). Supports both native Gemini and OpenRouter backends for image generation. Maintains full conversation history across REPL turns. Place source images in `workspace/input/`, results are saved to `workspace/output/`. Edit `workspace/style-guide.md` to define visual style constraints.

`01_04_reports` — An autonomous PDF report generation agent. The model reads `workspace/template.html` and `workspace/style-guide.md` first to understand the design system, then generates HTML documents in `workspace/html/`, optionally creates images with `create_image` (saving to `workspace/output/`), and converts the final HTML to a print-ready PDF via the `html_to_pdf` tool (powered by [Playwright](https://playwright.dev/python/)). Enforces image-style consistency across a document by writing a shared style definition to `workspace/image-style.txt` before generating the first image. Requires Playwright with Chromium installed:

```bash
.venv/Scripts/python -m pip install playwright
.venv/Scripts/python -m playwright install chromium
```

<<<<<<< HEAD
=======
`01_04_video_generation` — A frame-based video generation agent using JSON prompt templates. The model follows a structured workflow: copy `workspace/template.json` to `workspace/prompts/`, edit only the `subject` section, generate a start frame with `create_image`, generate an end frame using the start frame as reference (for character consistency), then call `image_to_video` with both frames to animate the transition using Kling AI (`kwaivgi/kling-v2.5-turbo-pro` via Replicate). Also supports direct text-to-video generation and video quality analysis via Gemini. Requires `REPLICATE_API_TOKEN` and at least one image backend key. Install the `replicate` package first:

```bash
.venv/Scripts/python -m pip install replicate
```

`01_04_video` — An interactive REPL agent for video analysis powered by Google Gemini (`gemini-2.5-flash`). Supports video analysis (general, visual, audio, action), speech transcription with timestamps and speaker detection, scene/keyframe/object/text extraction, and custom natural-language queries. Accepts local video files in `workspace/input/` (MP4, MOV, AVI, WebM, and more) and YouTube URLs. Files larger than 20 MB use Gemini's resumable upload API. Also connects to a `files-mcp` stdio server for filesystem access.

>>>>>>> b4eb695 (Convert JS module 01_04_video_generation to Python)
`01_04_json_image` — A token-efficient JSON-based image generation agent. The model follows a structured workflow: copy `workspace/template.json` (or `workspace/character-template.json`) to `workspace/prompts/`, edit only the `subject` section, read back the full JSON, then call `create_image` with the complete template as the prompt. This approach minimises token usage while preserving rich style/composition constraints encoded in the templates. Supports both OpenRouter (preferred) and native Gemini backends. Output images are saved to `workspace/output/`.

## Lesson 05 — Human-in-the-loop Agents

Lesson 05 examples require a **Resend** account for email sending. Set these env vars before running:

```bash
RESEND_API_KEY=re_your_key_here
RESEND_FROM=noreply@yourdomain.com
```

| Example | Run | Description |
|---------|-----|-------------|
| `01_05_confirmation` | `python "01_05_confirmation/app.py"` | Terminal REPL agent with interactive confirmation gate before sending emails |

Run from the project root:

```bash
python "01_05_confirmation/app.py"
```

`01_05_confirmation` — An interactive terminal REPL agent with filesystem access (via `files-mcp` over stdio) and email sending (via Resend). The key lesson feature is a **human-in-the-loop confirmation gate**: before executing `send_email`, the user sees a formatted preview of the email and chooses `[Y] Send once`, `[T] Trust & Send` (skip confirmations for the rest of the session), or `[N] Cancel`. Edit `01_05_confirmation/workspace/whitelist.json` to add allowed recipient addresses or domain patterns.

| Example | Run | Description |
|---------|-----|-------------|
| `01_05_agent` | `uvicorn 01_05_agent.app:app` | Production-grade multi-agent REST API with SQLite persistence, MCP, and context pruning |

Run from the project root:

```bash
# Create the data directory first (only needed once)
mkdir -p .data

# Start the server (default: http://127.0.0.1:3000)
.venv/Scripts/python -m uvicorn "01_05_agent.app:app" --host 127.0.0.1 --port 3000
```

`01_05_agent` — A production-grade multi-agent API server built with FastAPI. Supports multi-turn conversations, tool use (calculator, delegate, send_message, ask_user), MCP server connections, SQLite persistence for agents/sessions/items, context window pruning with LLM-based summarization, per-IP rate limiting, and Langfuse tracing. Agents are defined as YAML templates in `01_05_agent/workspace/`. Provider support: OpenAI, OpenRouter, Google Gemini.

Configure in `01_05_agent/.env` (or the workspace root `.env`):

```bash
OPENAI_API_KEY=your_key        # or OPENROUTER_API_KEY / GEMINI_API_KEY
DEFAULT_MODEL=openai:gpt-4o    # optional — provider:model format
DATABASE_URL=file:.data/agent.db
```

API endpoints:

```bash
# Health check
curl http://127.0.0.1:3000/health

# Interactive API docs
open http://127.0.0.1:3000/docs
```

## Lesson 01 — Week 2 (Module 02)

### Prerequisites

The `02_01_agentic_rag` example requires the `files-mcp` TypeScript server. Make sure you have Node.js and `npx` available, then install the MCP server's dependencies once:

```bash
cd ../mcp/files-mcp
npm install
```

| Example | Run | Description |
|---------|-----|-------------|
| `02_01_agentic_rag` | `python "02_01_agentic_rag/app.py"` | Agentic RAG — LLM-driven iterative search over a markdown knowledge base via MCP file tools |

Run from the project root:

```bash
python "02_01_agentic_rag/app.py"
```

`02_01_agentic_rag` — An agentic RAG (Retrieval-Augmented Generation) system where the model autonomously decides what to search, how deeply to read, and when it has collected enough evidence to answer. Uses the OpenAI Responses API with reasoning enabled (`effort: medium`) and connects to a local `files-mcp` stdio server that exposes `list`, `search`, and `read` tools. The agent runs up to 50 steps per query, executes parallel tool calls within each step, and maintains full conversation history across turns (enabling follow-up questions). Type `exit` to quit, `clear` to reset conversation and token stats. The knowledge base is a set of Polish-language AI_devs course notes (`S01*.md`); the agent always responds in English.
>>>>>>> 00edc81 (Convert JS module 02_01_agentic_rag to Python)
