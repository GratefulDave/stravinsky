# Semantic Watcher Usage Guide

The Semantic File Watcher automatically monitors your codebase and updates the semantic search index whenever you make changes. No manual reindexing needed.

## Overview

**What it does:**
- Monitors Python files for changes (create, modify, delete, move)
- Debounces rapid changes to batch them efficiently
- Triggers incremental reindexing automatically
- Runs in background threads for non-blocking operation
- Auto-starts on first semantic search (no manual setup required)

**Key features:**
- 2-second default debounce (configurable)
- Skips hidden directories (.git, __pycache__, venv, etc.)
- Uses native file watching when available (falls back to watchdog)
- Thread-safe with daemon threads for clean shutdown
- Dedicated indexing worker prevents concurrent access issues

## Quick Start

### Automatic Mode (Recommended)

The file watcher starts automatically on your first semantic search:

```python
from mcp_bridge.tools.semantic_search import semantic_search

# First search auto-creates index and starts watcher
results = await semantic_search(
    query="authentication logic",
    project_path="."
)

# Files are now auto-reindexed on change
```

### Manual Control

```python
from mcp_bridge.tools.semantic_search import (
    start_file_watcher,
    stop_file_watcher,
    list_file_watchers,
    get_file_watcher,
)

# Start watching
watcher = await start_file_watcher(
    project_path=".",
    provider="ollama",
    debounce_seconds=2.0
)

# Check if watcher exists
active = get_file_watcher(".")
if active:
    print(f"Watcher active for {active.project_path}")

# List all watchers
watchers = list_file_watchers()
for w in watchers:
    print(f"{w['project_path']}: {w['status']}, provider: {w['provider']}")

# Stop watching
stopped = stop_file_watcher(".")
print(f"Stopped: {stopped}")
```

## API Reference

### start_file_watcher

Start watching a project directory for file changes.

```python
async def start_file_watcher(
    project_path: str,
    provider: EmbeddingProvider = "ollama",
    debounce_seconds: float = 2.0,
) -> CodebaseFileWatcher
```

**Parameters:**
- `project_path`: Path to the project root
- `provider`: Embedding provider to use for reindexing
- `debounce_seconds`: Time to wait before reindexing after changes (default: 2.0)

**Returns:** The started CodebaseFileWatcher instance

**Behavior:**
- If an index exists, performs an incremental reindex on startup
- If watcher already exists and is running, returns existing watcher
- If watcher exists but stopped, restarts it

**Example:**
```python
# Start with default settings
watcher = await start_file_watcher(".")

# Start with custom debounce
watcher = await start_file_watcher(
    project_path="/path/to/project",
    provider="mxbai",
    debounce_seconds=5.0
)
```

### stop_file_watcher

Stop watching a project directory.

```python
def stop_file_watcher(project_path: str) -> bool
```

**Parameters:**
- `project_path`: Path to the project root

**Returns:** True if watcher was stopped, False if no watcher was active

**Example:**
```python
stopped = stop_file_watcher(".")
if stopped:
    print("Watcher stopped")
else:
    print("No active watcher found")
```

### get_file_watcher

Get an active file watcher for a project.

```python
def get_file_watcher(project_path: str) -> CodebaseFileWatcher | None
```

**Parameters:**
- `project_path`: Path to the project root

**Returns:** The CodebaseFileWatcher if active, None otherwise

**Example:**
```python
watcher = get_file_watcher(".")
if watcher:
    print(f"Watching: {watcher.project_path}")
    print(f"Running: {watcher.is_running()}")
```

### list_file_watchers

List all active file watchers.

```python
def list_file_watchers() -> list[dict]
```

**Returns:** List of dicts with watcher info:
- `project_path`: Path being watched
- `debounce_seconds`: Debounce time setting
- `provider`: Embedding provider in use
- `status`: "running" or "stopped"

**Example:**
```python
watchers = list_file_watchers()
for w in watchers:
    print(f"{w['project_path']}")
    print(f"  Status: {w['status']}")
    print(f"  Provider: {w['provider']}")
    print(f"  Debounce: {w['debounce_seconds']}s")
```

## Architecture

```mermaid
flowchart TB
    subgraph "File System"
        FILES[Python Source Files]
    end

    subgraph "File Watcher"
        OBS[watchdog Observer<br/>or Native Watcher]
        HANDLER[Event Handler]
        DEB[Debounce Timer<br/>2 seconds]
    end

    subgraph "Indexing Worker"
        QUEUE[Request Queue<br/>max size: 1]
        WORKER[Dedicated Thread]
        IDX[index_codebase()]
    end

    subgraph "Storage"
        DB[(ChromaDB<br/>~/.stravinsky/vectordb/)]
    end

    FILES -->|file events| OBS
    OBS --> HANDLER
    HANDLER --> DEB
    DEB -->|batch files| QUEUE
    QUEUE --> WORKER
    WORKER --> IDX
    IDX --> DB
```

### Components

**File Watcher (CodebaseFileWatcher):**
- Uses native file watching when available (efficient kernel-level notifications)
- Falls back to watchdog library if native watcher not available
- Filters for .py files only
- Skips hidden directories and common non-code directories

**Debounce Timer:**
- Waits 2 seconds (configurable) after last file change
- Batches multiple rapid changes into single reindex
- Prevents excessive reindexing during active development

**Indexing Worker (DedicatedIndexingWorker):**
- Single-threaded worker prevents concurrent database access
- Queue size of 1 provides natural debouncing (drops duplicate requests)
- Uses asyncio.run() for each operation to avoid event loop issues
- Logs errors to ~/.stravinsky/logs/file_watcher.log

## Common Workflows

### Development Session

```python
from mcp_bridge.tools.semantic_search import (
    index_codebase,
    start_file_watcher,
    stop_file_watcher,
)

async def setup_dev_session():
    """Set up semantic search for a development session."""

    # Initial index (if needed)
    await index_codebase(".")

    # Start file watcher
    watcher = await start_file_watcher(".", provider="mxbai")
    print(f"Watching {watcher.project_path}")

    return watcher

async def cleanup_dev_session():
    """Clean up at end of session."""
    stop_file_watcher(".")
```

### Multi-Project Workspace

```python
from mcp_bridge.tools.semantic_search import (
    start_file_watcher,
    list_file_watchers,
)
from pathlib import Path

async def watch_workspace(workspace_dir: str):
    """Watch all git repos in a workspace."""

    workspace = Path(workspace_dir)

    # Find all subdirectories with git repos
    for project in workspace.iterdir():
        if (project / ".git").exists():
            watcher = await start_file_watcher(
                str(project),
                provider="ollama"
            )
            print(f"Watching: {project.name}")

    # Show status
    watchers = list_file_watchers()
    print(f"\nWatching {len(watchers)} projects")
```

### CI/CD Integration

```python
from mcp_bridge.tools.semantic_search import (
    index_codebase,
    start_file_watcher,
    stop_file_watcher,
)

async def ci_pipeline():
    """Ensure index is current for CI checks."""

    # Start watcher
    await start_file_watcher(".")

    # Run tests (any file changes are tracked)
    await run_tests()

    # Ensure index is up-to-date before deployment
    stop_file_watcher(".")

    # Final reindex to catch any test-generated files
    await index_codebase(".", force=False)
```

## Configuration

### Debounce Settings

| Project Size | Recommended Debounce | Rationale |
|--------------|---------------------|-----------|
| Small (<100 files) | 0.5-1.0s | Fast feedback, low overhead |
| Medium (100-1000 files) | 2.0s (default) | Balance speed and efficiency |
| Large (>1000 files) | 5.0-10.0s | Reduce reindex frequency |
| Very Large (>10k files) | Consider manual | Disable watcher, reindex on demand |

```python
# Small project - fast feedback
await start_file_watcher(".", debounce_seconds=0.5)

# Large project - conservative
await start_file_watcher(".", debounce_seconds=5.0)
```

### Ignored Directories

The watcher automatically skips these directories:

```python
SKIP_DIRS = {
    # Python
    "__pycache__", ".venv", "venv", "env", ".env",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",

    # Node.js
    "node_modules", ".npm", ".yarn",

    # Build outputs
    "dist", "build", "out", ".next", ".nuxt",

    # Version control
    ".git", ".svn", ".hg",

    # IDE/Editor
    ".idea", ".vscode", ".vs",

    # Test/coverage
    "coverage", "htmlcov", ".nyc_output",

    # Misc
    ".stravinsky", "logs", "tmp", "temp"
}
```

### Gitignore Support

The watcher respects `.gitignore` and `.stravignore` patterns:

```bash
# .stravignore - additional patterns for semantic indexing
*.generated.py
test_data/
experimental/
```

## Troubleshooting

### Watcher Does Not Start

**Symptom:** `start_file_watcher()` fails or returns None

**Solutions:**
1. Check that watchdog is installed: `pip list | grep watchdog`
2. Verify project path exists: `ls /path/to/project`
3. Check file permissions: `ls -la /path/to/project`

### Reindexing Fails

**Symptom:** "Error during file watcher reindex" in logs

**Solutions:**
1. Check embedding service is running:
   - Ollama: `ollama serve`
   - Cloud providers: `stravinsky-auth status`
2. Check database is not locked (wait a few seconds, watcher retries)
3. Check available disk space

### Too Many Reindexes (Slow)

**Symptom:** Constant reindexing during active development

**Solutions:**
1. Increase debounce period:
   ```python
   await start_file_watcher(".", debounce_seconds=5.0)
   ```
2. Stop watcher during heavy editing:
   ```python
   stop_file_watcher(".")
   # ... heavy editing ...
   await start_file_watcher(".")
   ```

### Watcher Does Not Detect Changes

**Possible causes:**
1. File is in ignored directory (.git, __pycache__, venv, etc.)
2. File is not a .py file (only Python files are watched)
3. File is hidden (starts with .)
4. File matches .gitignore or .stravignore pattern

**Verify:**
```python
from mcp_bridge.tools.semantic_search import CodebaseVectorStore

# Check if directory is skipped
skipped = CodebaseVectorStore.SKIP_DIRS
print(f"Skipped directories: {skipped}")
```

### Watcher Uses High CPU

**Symptom:** High CPU usage from file watching

**Solutions:**
1. Increase debounce to reduce reindex frequency
2. Check for large directories being watched
3. Use .stravignore to exclude large generated directories

## Logging

Watcher errors are logged to: `~/.stravinsky/logs/file_watcher.log`

**Enable debug logging:**
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("mcp_bridge.tools.semantic_search").setLevel(logging.DEBUG)
```

**Sample log output:**
```
[2026-01-22 10:15:30] File watcher started for /path/to/project
[2026-01-22 10:15:35] File modified: src/auth.py
[2026-01-22 10:15:37] Queued reindex for 1 files: [auth.py]
[2026-01-22 10:15:38] Reindex completed for /path/to/project
```

## Best Practices

### 1. Let Auto-Start Handle It

The watcher auto-starts on first search. No manual setup needed.

```python
# Just search - watcher starts automatically
results = await semantic_search("authentication", project_path=".")
```

### 2. Use Appropriate Debounce

Match debounce to your workflow:
- Fast iteration: 0.5-1.0s
- Normal development: 2.0s (default)
- Large projects: 5.0-10.0s

### 3. Stop When Not Needed

Stop watchers you don't need to free resources:

```python
# Stop specific project
stop_file_watcher("/path/to/inactive/project")

# Check what's running
for w in list_file_watchers():
    if w['status'] == 'running':
        print(f"Active: {w['project_path']}")
```

### 4. Handle Errors Gracefully

Watcher errors should not crash your application:

```python
try:
    watcher = await start_file_watcher(".")
except Exception as e:
    print(f"Watcher failed: {e}")
    # Semantic search still works, just without auto-updates
```

### 5. Monitor Health

Check watcher status before critical operations:

```python
watcher = get_file_watcher(".")
if watcher and watcher.is_running():
    print("Watcher healthy")
else:
    print("Watcher not running - consider restarting")
```

## See Also

- [Quick Start Guide](./SEMANTIC_SEARCH_QUICK_START.md) - Get started with semantic search
- [Best Practices Guide](./SEMANTIC_SEARCH_BEST_PRACTICES.md) - Search optimization tips
- [Indexing Quick Start](./semantic_indexing_quick_start.md) - Manual indexing options

---

**Last Updated:** January 2026
**Status:** Complete guide for file watcher usage
