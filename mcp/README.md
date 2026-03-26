# MCP Servers

This directory contains local MCP (Model Context Protocol) servers used by lesson modules.

## `files-mcp` — Sandboxed Filesystem Server

A Python MCP server that exposes four filesystem tools (`fs_read`, `fs_write`, `fs_search`, `fs_manage`) scoped to a configurable sandbox root directory. It is a Python port of the original Node.js `files-mcp` server from the `4th-devs-js` project.

### Package Structure

```
files-mcp/
├── server.py            Entry point — FastMCP instance, tool registration, if __name__ == "__main__" runner
├── config.py            Env var resolution (FS_ROOT, LOG_LEVEL), logging setup, constants
├── __init__.py          Package marker
├── __main__.py          Unused currently; reserved for future python -m invocation (pattern 2)
│
├── tools/               One file per MCP tool
│   ├── fs_read.py       Read files and list directories
│   ├── fs_write.py      Create and update files
│   ├── fs_search.py     Search by filename or file content
│   └── fs_manage.py     Delete, rename, move, copy, mkdir, stat
│
├── lib/                 Shared library modules
│   ├── paths.py         Sandbox path resolution (resolve_safe, rel, is_sandbox_root)
│   ├── checksum.py      SHA-256 file checksum, matches JS server algorithm
│   ├── lines.py         Line range parsing and numbered-line formatting
│   ├── diff.py          Unified diff generation (wraps difflib)
│   ├── filetypes.py     Text/binary detection, extension type matching, glob filtering
│   ├── ignore.py        .gitignore pattern support (uses pathspec if installed, falls back to fnmatch)
│   └── search.py        Fuzzy filename search with scored ranking
│
└── utils/
    └── errors.py        Standard error response helpers (OUT_OF_SCOPE_ERROR, error_response())
```

> **Note on import strategy:** The folder name `files-mcp` contains a hyphen, which makes it an invalid Python package identifier. `server.py` therefore adds its own directory to `sys.path` at startup so all submodules can use direct imports (`from config import ...`, `from lib.paths import ...`) rather than relative imports. This is a known limitation — renaming to `files_mcp` and migrating to `python -m` invocation would allow clean relative imports.

---

### Configuration (`mcp.json`)

Each lesson module that uses `files-mcp` needs a `mcp.json` file in its directory.

#### Minimal configuration

```json
{
  "mcpServers": {
    "files": {
      "command": "python",
      "args": ["../mcp/files-mcp/server.py"],
      "env": {
        "FS_ROOT": "./workspace"
      }
    }
  }
}
```

#### Full configuration with all options

```json
{
  "mcpServers": {
    "files": {
      "transport": "stdio",
      "command": "python",
      "args": ["../mcp/files-mcp/server.py"],
      "env": {
        "FS_ROOT": "./workspace",
        "LOG_LEVEL": "info"
      }
    }
  }
}
```

#### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FS_ROOT` | `./workspace` | Sandbox root directory. Relative paths resolve against the MCP client's working directory (i.e. the lesson module folder). All tool operations are confined to this directory. |
| `LOG_LEVEL` | `info` | Logging verbosity: `debug`, `info`, `warning`, `error`. Logs go to stderr. |

---

### Tools Reference

All tools return a JSON-encoded string. On error, the response includes `success: false` and an `error` field. On path escape attempts, `code: "OUT_OF_SCOPE"` is returned.

---

#### `fs_read` — Read files and list directories

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | — | Relative path within sandbox. `"."` = root |
| `mode` | string | `"auto"` | `"auto"` \| `"tree"` \| `"list"` \| `"content"`. Auto detects file vs directory |
| `lines` | string | `null` | Line range: `"10"` (single line) or `"10-50"` (range). Negative values return an error |
| `limit` | int | `100` | Max directory entries to return |
| `offset` | int | `0` | Skip first N directory entries (pagination) |
| `depth` | int | `1` | Recursion depth for directory listing |
| `details` | bool | `false` | Include `size` and `modified` in directory entries |
| `types` | list[str] | `null` | Filter files by type: `["py", "js", "md", ...]` |
| `glob` | string | `null` | Glob pattern to include, e.g. `"*.py"` |
| `exclude` | list[str] | `null` | Glob patterns to exclude |
| `respectIgnore` | bool | `false` | Skip files matched by `.gitignore` |

File response includes `text` (numbered lines: `1|line content`), `checksum`, `totalLines`, `truncated`. Files over 100 lines are truncated by default — use `lines` to read specific ranges.

---

#### `fs_write` — Create and update files

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | — | Relative path within sandbox |
| `operation` | string | — | `"create"` or `"update"` |
| `content` | string | `null` | Text content to write |
| `action` | string | `null` | Update action: `"replace"` \| `"insert_before"` \| `"insert_after"` \| `"delete_lines"` |
| `lines` | string | `null` | Target line range for update, e.g. `"10"` or `"10-15"` |
| `checksum` | string | `null` | Optimistic lock: if provided, write fails if file changed since last read |
| `dryRun` | bool | `false` | Preview diff without writing |
| `createDirs` | bool | `true` | Automatically create parent directories |

**`create`:** Rejects with `ALREADY_EXISTS` if the file exists. Always writes a trailing newline.

**`update`:** Requires `action` and (except for `delete_lines`) `lines`. The checksum from `fs_read` can be passed to prevent overwriting concurrent changes. Response includes a unified diff of the change.

---

#### `fs_search` — Search by filename or file content

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | string | — | Starting directory within sandbox |
| `query` | string | — | Search term |
| `target` | string | `"all"` | `"all"` \| `"filename"` \| `"content"` |
| `patternMode` | string | `"literal"` | `"literal"` \| `"regex"` \| `"fuzzy"` |
| `caseInsensitive` | bool | `false` | Case-insensitive matching |
| `depth` | int | `5` | Maximum directory depth to traverse |
| `maxResults` | int | `100` | Maximum number of results |
| `wholeWord` | bool | `false` | Match whole words only (adds `\b` boundaries) |
| `multiline` | bool | `false` | Dot matches newline in regex/fuzzy patterns |
| `types` | list[str] | `null` | Filter files by type |
| `glob` | string | `null` | Glob pattern to include |
| `exclude` | list[str] | `null` | Glob patterns to exclude |
| `respectIgnore` | bool | `false` | Skip `.gitignore` files |

**Fuzzy filename search** (`patternMode="fuzzy"`, `target="filename"`) uses scored ranking: exact match (100) > prefix (80) > contains (60) > character sequence (40). Results include a `score` field.

---

#### `fs_manage` — Structural filesystem operations

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `operation` | string | — | `"stat"` \| `"mkdir"` \| `"delete"` \| `"rename"` \| `"move"` \| `"copy"` |
| `path` | string | — | Source path within sandbox |
| `target` | string | `null` | Destination path (required for rename/move/copy) |
| `recursive` | bool | `false` | For `mkdir`: create parents. For `copy`: copy directories. For `delete`: remove non-empty directories |
| `force` | bool | `false` | Overwrite target if it exists (rename/move/copy) |

**`stat` response** includes `kind`, `isDirectory`, `size`, `modified` (ISO 8601), `created` (ISO 8601).

**`delete` guards:**
- Deleting the sandbox root returns `FORBIDDEN`
- Deleting a non-empty directory without `recursive=true` returns `NOT_EMPTY`

---

### Security

All paths are resolved against `FS_ROOT` using `resolve_safe()`. Any path that escapes the sandbox via `..` traversal returns `OUT_OF_SCOPE` without touching the filesystem. The sandbox root itself cannot be deleted.

---

### Checksum Algorithm

Checksums use the first 12 hex characters of SHA-256 over the file's UTF-8 text content, matching the JS server:

```
sha256(text.encode("utf-8")).hexdigest()[:12]
```

Always re-read a file with `fs_read` after an `fs_write` update to get the new checksum before the next update.
