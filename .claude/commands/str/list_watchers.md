---
description: /str:list_watchers - List all active file watchers across projects
allowed-tools: mcp__stravinsky__list_file_watchers
---

# List Active File Watchers

View all currently running file watchers for automatic semantic search reindexing.

## What This Does

Displays information about active file watchers across all projects including:
- Project path being watched
- Embedding provider (ollama, gemini, openai, huggingface)
- Debounce interval (wait time before reindexing)
- Current status (running/stopped)

## Prerequisites

At least one file watcher must be running. Start a watcher with `/str:start_filewatch` first.

## Usage

Call the MCP tool directly (no parameters):

```python
mcp__stravinsky__list_file_watchers()
```

Returns a list of dicts with:
- `project_path`: Root directory being watched
- `provider`: Embedding provider name
- `debounce_seconds`: Wait time before reindexing
- `status`: "running" or "stopped"

## Example Output

```
Active File Watchers
====================

Watcher 1:
  Project: /Users/dev/project1
  Provider: ollama
  Debounce: 2.0s
  Status: running

Watcher 2:
  Project: /Users/dev/project2
  Provider: gemini
  Debounce: 3.0s
  Status: running

Total: 2 active watchers
```

## Use Cases

**Before stopping a watcher:**
```python
# List watchers to get project path
mcp__stravinsky__list_file_watchers()

# Stop specific watcher
mcp__stravinsky__stop_file_watcher(project_path="/Users/dev/project1")
```

**Check status across multiple repos:**
```python
# See all watched projects at once
mcp__stravinsky__list_file_watchers()
```

**Verify watcher started successfully:**
```python
# After starting watcher
mcp__stravinsky__start_file_watcher(project_path=".", provider="ollama")

# Confirm it's running
mcp__stravinsky__list_file_watchers()
```

## Troubleshooting

**"No active watchers"**: Start a watcher with `/str:start_filewatch` first.

**"Watcher shows stopped"**: The watcher encountered an error or was manually stopped. Restart with `/str:start_filewatch`.

**Multiple watchers for same project**: This indicates duplicate watcher processes. Stop and restart with `/str:stop_filewatch`.

## Tips

- Run this before stopping watchers to identify project paths
- Use to verify watchers are running after system restart
- Check status if reindexing seems not to be happening automatically
- Each project can only have ONE active watcher per provider
