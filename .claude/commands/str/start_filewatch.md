# Start File Watcher for Automatic Reindexing

Enable automatic reindexing of your codebase when Python files change.

## What This Does

Starts a background file watcher that monitors your project for file changes and automatically triggers reindexing:

- Watches for create, modify, delete, and move events
- Debounces rapid changes to batch reindexing efficiently
- Automatically reindexes modified files for semantic search
- Runs as a daemon thread (non-blocking)
- Thread-safe with clean shutdown

## Prerequisites

**Recommended**: Run `/index` first to create an initial index before starting the file watcher.

## Usage

Use the `start_file_watcher` MCP tool to enable automatic reindexing:

**Parameters:**
- `project_path`: Root directory to watch (default: "." - current directory)
- `provider`: Embedding provider to use for reindexing (default: "ollama")
  - "ollama" - Free, local (recommended)
  - "gemini" - Cloud-based, requires OAuth
  - "openai" - Cloud-based, requires ChatGPT Plus/Pro
  - "huggingface" - Cloud-based, requires API token
- `debounce_seconds`: Wait time before reindexing after changes (default: 2.0)

## Example Usage

**Start watcher on current project with default settings:**
```
start_file_watcher()
```

**Start watcher with custom debounce:**
```
start_file_watcher(project_path=".", provider="ollama", debounce_seconds=3.0)
```

**Start watcher on specific directory:**
```
start_file_watcher(project_path="/path/to/project", provider="gemini")
```

## File System Monitoring

The file watcher automatically monitors:
- All `.py` files in your project
- File creation, modification, deletion, and moves
- Batches changes within the debounce window

The watcher **skips**:
- Virtual environments (`venv/`)
- Python cache (`__pycache__/`, `.pyc` files)
- Git metadata (`.git/`)
- Node modules (`node_modules/`)
- Build artifacts (`dist/`, `build/`)

## Managing Watchers

**Check active watchers:**
```
list_file_watchers()
```

**Get specific watcher status:**
```
get_file_watcher(project_path=".")
```

**Stop a watcher:**
```
stop_file_watcher(project_path=".")
```

## Workflow

1. Create initial index with `/index` (optional but recommended)
2. Start file watcher with `/str:start_filewatch`
3. Continue coding - changes are automatically indexed
4. Use `/search` for semantic queries
5. Stop when done with `/str:stop_filewatch`

## Provider Selection

Choose based on your needs:

- **ollama** (default): Free, local, no setup required
  - Best for development
  - Requires `ollama` installed and running
  - Run: `ollama pull nomic-embed-text`

- **gemini**: Cloud-based, excellent quality
  - Best for production
  - Requires: `stravinsky-auth login gemini`

- **openai**: Cloud-based, excellent quality
  - Requires: ChatGPT Plus/Pro subscription
  - Run: `stravinsky-auth login openai`

## Performance Tips

- **Debounce value**: 
  - 2.0s (default): Good balance for most projects
  - 1.0s: For fast, continuous indexing (higher CPU)
  - 3.0-5.0s: For large projects or slower systems

- **Provider choice**:
  - Local (ollama) if indexing many files frequently
  - Cloud (gemini/openai) if network latency is acceptable

## Troubleshooting

**Watcher not working:**
- Ensure provider is accessible (run `ollama` if using ollama)
- Check logs: Look for errors in tool output
- Try higher debounce value if system is slow

**Too much reindexing:**
- Increase `debounce_seconds` (e.g., 3.0 or 5.0)
- This batches more changes before reindexing

**Memory usage:**
- File watchers run as daemon threads
- Memory is low (typically <50MB per watcher)
- Stop unused watchers to free resources

## Related Commands

- `/index` - Create/rebuild semantic search index
- `/search` - Query indexed code with natural language
- `/str:stop_filewatch` - Stop automatic reindexing
