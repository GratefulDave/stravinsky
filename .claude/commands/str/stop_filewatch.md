# Stop File Watcher

Disable automatic reindexing for a project.

## What This Does

Stops and removes a file watcher that was previously started with `/str:start_filewatch`:

- Gracefully shuts down the background watcher thread
- Releases file system resources
- Stops automatic reindexing for the specified project
- Returns status (true if watcher was active, false if none was running)

## Usage

Use the `stop_file_watcher` MCP tool to disable automatic reindexing:

**Parameters:**
- `project_path`: Root directory that was being watched (default: "." - current directory)

## Example Usage

**Stop watcher on current project:**
```
stop_file_watcher()
```

**Stop watcher on specific directory:**
```
stop_file_watcher(project_path="/path/to/project")
```

## Status

The tool returns:
- `True` if a watcher was active and has been stopped
- `False` if no watcher was active for that project path

## Checking Watchers

**List all active watchers before stopping:**
```
list_file_watchers()
```

This shows:
- Project paths being watched
- Provider for each watcher
- Number of changes detected
- Watch status (running/stopped)

**Get status of specific watcher:**
```
get_file_watcher(project_path=".")
```

Returns the CodebaseFileWatcher object if active, None otherwise.

## When to Stop

- Stop when you're done with a project
- Stop if you need to change provider settings
- Stop to reduce resource usage
- Stop before shutting down to clean shutdown the watcher thread

## Restarting

You can restart the watcher at any time:

```
# Stop current watcher
stop_file_watcher()

# Start new watcher with different settings
start_file_watcher(project_path=".", provider="gemini", debounce_seconds=3.0)
```

## Workflow

1. Start watcher with `/str:start_filewatch`
2. Code and make changes (automatically indexed)
3. Use `/search` for semantic queries
4. When done: **Stop watcher with `/str:stop_filewatch`**

## Related Commands

- `/str:start_filewatch` - Enable automatic reindexing
- `/search` - Query indexed code with natural language
- `/index` - Create/rebuild semantic search index
