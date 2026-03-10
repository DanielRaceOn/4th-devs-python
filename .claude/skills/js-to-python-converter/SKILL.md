---
name: js-to-python-converter
model: sonnet
description: Converts JavaScript/Node.js lesson modules from the 4th-devs project into fully working Python equivalents, placing them in 4TH-DEVS-PYTHON/. On every invocation, automatically detects which JS modules are new or missing from the Python mirror and converts only those — skipping modules that already exist. Use this skill whenever the user says anything like "convert to Python", "sync the Python project", "port the JS modules", "translate to Python", "what's not in Python yet", or invokes /js-to-python. Also trigger proactively when new JS modules appear in the project that have no Python counterpart.
---

# JS → Python Converter

## Overview

This skill converts course examples written as JS into fully working Python equivalents, keeping them in sync with the source JS project.

## Source and target directories

- ***Source JS project root***: `C:\Users\Daniel Szczepanski\Software Dev\04_Trainings\AI_Devs 4\4th-devs-js`
- ***Python mirror root*** (local project root): `C:\Users\Daniel Szczepanski\Software Dev\04_Trainings\AI_Devs 4\4th-devs-python\` 

## Workflow

Every invocation follows the same incremental workflow:

1. **Discover** — find all JS lesson modules and their supporting files
2. **Diff** — find which ones are missing in the ***Python mirror root***
3. **Analyze** — read the source files in the missing modules to understand their logic, dependencies, and structure
4. **Convert** — port only the missing ones
5. **Report** — summarise what was done

---

## Step 1 — Discover JS modules

Use `Glob` or `Bash ls` to list directories in the project root that match the lesson naming pattern `NN_NN_*` (two digit groups separated by underscores, followed by a name).

Example matches:
- `01_01_interaction/`
- `01_01_structured/`
- `01_01_grounding/`

Build a sorted list, e.g.: `[01_01_interaction, 01_01_structured, 01_01_grounding]`

Analyze also the files in the root of the project (like `config.js`, `.env.example`, `package.json`) to understand global dependencies and configuration that may affect the modules.

**Exclude** not related directories like `node_modules/`, `__pycache__/`, `.git/`, etc.

---

## Step 2 — Discover existing Python modules

List directories inside *Python mirror root* that match the same `NN_NN_*` pattern.

---

## Step 3 — Compute the delta

```
to_convert = JS_modules − Python_modules
```

- If `to_convert` is **empty**: report "All modules already converted. Nothing to do." and stop.
- Otherwise: tell the user which modules will be converted, then proceed.

---

## Step 4 — Convert each missing module

For each module in `to_convert`, read **all** source files recursively — this includes `.js` files, `config.js`, `.env.example`, `package.json`, and any other file that affects how the module works or what it needs.

### What to read before converting

Before writing a single line of Python, read these files if they exist in the module (or at the project root):

- All `.js` files (source logic)
- `config.js` / `src/config.js` — contains env var names, provider logic, defaults, CLI args
- `.env.example` — documents required environment variables; port these as comments or into a `config.py`
- `package.json` — reveals third-party deps to find Python equivalents for
- Any `.md`, `.html`, or data files that are inputs/outputs (copy as-is — do not convert)

Understanding what the module does end-to-end matters more than mechanically translating each line. Read everything first, then convert.

### Conversion philosophy

The goal is a **functionally equivalent Python module** — not a line-by-line transliteration. Use idiomatic Python:

- Preserve all business logic, error handling, retry strategies, caching, and CLI arguments
- Replace Node.js patterns with their natural Python equivalents
- Keep the same observable behaviour: same inputs produce the same outputs

**Key library choices** (use these consistently across all modules):
- HTTP calls → `httpx` with `AsyncClient` (not `requests`, not the Anthropic SDK)
- Async → `asyncio` (`async def`, `await`, `asyncio.gather`, `asyncio.Semaphore`)
- Environment loading → `python-dotenv` (`load_dotenv()`)
- File paths → `pathlib.Path` (never `os.path`)
- File I/O → `Path.read_text()` / `Path.write_text()`
- Hashing → `hashlib`
- CLI args → `argparse`
- Logging → `logging` module

For everything else, choose the most idiomatic Python approach that preserves the original behaviour. When in doubt, keep the logic identical and just change the syntax.

### Inline comments

Put comments explaining non-obvious logic even if it was not commented in the original JS. The Python code should be self-explanatory and well-documented.

### Internal file structure

Mirror the JS module's directory layout using the same relative paths, replacing `.js` with `.py`. Do not impose a structure that doesn't exist in the source.

- Every directory that contains Python modules needs an `__init__.py`
- Non-code assets (`.html`, `.md`, data/input files) → copy as-is, no conversion
- `config.js` (at module or project root) → `config.py` at the same level, reproducing its logic faithfully

### Async strategy

The JS source uses `async/await` throughout. Mirror this in Python:

- Module-level entry point: `asyncio.run(main())`
- All async functions: `async def` + `await`
- Parallel calls: `asyncio.gather(*coros)`
- Concurrency-limited batching: `asyncio.Semaphore(batch_size)` + `asyncio.gather`

### Python code style requirements

Every generated `.py` file must follow the user's CLAUDE.md standards:

**File header** (required on every new file):
```python
# -*- coding: utf-8 -*-

#   filename.py

"""
### Description:
[Brief description of the file's purpose]

---

@Author:        [Model used for conversion, e.g. "Claude Sonnet 4.6"]
@Created on:    [DD.MM.YYYY — use today's date]
@Based on:      [Name of the JS source file(s) that were converted, e.g. `app.js`, `config.js`]


"""
```


**Style rules:**
- Python 3.8+, PEP 8, 88-char line length (Black)
- Type hints on all function signatures
- Google-style docstrings on all public functions/classes
- `pathlib.Path` for all path operations — never `os.path`
- Import order: stdlib → third-party → local (blank line between groups)
- Logging: `logging.debug()` default; `logging.info()` for major steps only

---

## Step 5 — Generate/update requirements.txt

Create or update a project global `requirements.txt` file. Base it on what the module actually imports — check `package.json` for the JS deps list, then map to Python equivalents.
Add any additional packages the module needs based on what you find in the source.

Check if all dependencies from `requirements.txt` are already installed using `pip list`. If any are missing, report them to the user with instructions on how to install:

```Missing dependencies:
  — httpx
  — python-dotenv
Install with:
  pip install httpx python-dotenv
```

---

## Step 6 - Update README.md in the Python mirror root

Add a section to the README.md in the Python mirror root that lists all the converted modules, their descriptions (from the original JS README or inferred from the code), and instructions on how to run them.

## Step 7 — Report

After conversion, print a clear summary:

```
Converted modules:
  ✓ 01_01_interaction  →  4TH-DEVS-PYTHON/01_01_interaction/  (2 files)
  ✓ 01_01_grounding    →  4TH-DEVS-PYTHON/01_01_grounding/    (15 files)

Already present (skipped):
  — none

```

## Step 8 [optional] — git commit
If the user wants, create a git commit with comment:

```
Convert JS modules [converted modules e.g. 01_01_interaction, 01_01_grounding] to Python.
```
Propose to push to the remote repository if there are changes to commit.
