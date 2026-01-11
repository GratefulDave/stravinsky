---
description: Start automatic file watching for semantic search index updates
allowed-tools: mcp__stravinsky__start_file_watcher, mcp__stravinsky__semantic_index, mcp__stravinsky__semantic_stats
---

# Start File Watcher for Semantic Search

Automatically reindex code changes in the background. The watcher monitors `.py` files and triggers incremental reindexing when changes are detected.

## What This Does

1. **Auto-catches up**: Runs incremental reindex to catch changes since last index
2. **Starts monitoring**: Watches for file create/modify/delete/move events
3. **Debounces changes**: Waits 2 seconds after last change before reindexing
4. **Background operation**: Runs as daemon thread, cleans up on exit

## Prerequisites

- Index must exist first (run `/index` or `semantic_index()` before starting watcher)
- Ollama must be running with embedding model available

## Usage

Call `start_file_watcher` with parameters:
- `project_path`: "." (current directory)
- `provider`: "ollama" (or "mxbai", "gemini", "openai", "huggingface")
- `debounce_seconds`: 2.0 (optional, default is 2.0)

## Example

```python
# Start watching current project
start_file_watcher(project_path=".", provider="ollama")
```

## Stop Watching

Use `/str:unwatch` or call `stop_file_watcher(project_path=".")` to stop the watcher.

## Notes

- Watcher automatically performs incremental reindex on start to catch missed changes
- Only monitors Python files (`.py` extension)
- Skips: venv, __pycache__, .git, node_modules, dist, build
- Thread-safe with automatic cleanup on process exit
