---
description: Stop file watching for semantic search index updates
allowed-tools: mcp__stravinsky__stop_file_watcher, mcp__stravinsky__list_file_watchers
---

# Stop File Watcher

Stop automatic reindexing for a project's semantic search index.

## What This Does

Stops the background file watcher that monitors code changes and triggers reindexing.

## Usage

Call `stop_file_watcher` with parameter:
- `project_path`: "." (current directory)

## Example

```python
# Stop watching current project
stop_file_watcher(project_path=".")
```

Returns: Boolean indicating if watcher was stopped (true) or wasn't running (false)

## List Active Watchers

Use `list_file_watchers()` to see all active watchers across projects:

```python
list_file_watchers()
```

Returns JSON with active watcher details (project path, provider, status).

## Notes

- Watcher automatically cleans up on process exit
- Stopping a non-existent watcher returns false
- Any pending debounced reindex is cancelled when stopping
