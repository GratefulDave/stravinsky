# FileWatcher Integration - Quick Reference Guide

## What This Adds

Real-time incremental indexing of semantic search indices. When you modify code files, the index automatically updates.

**Before:** Manual trigger required
```python
await index_codebase(project_path=".")  # You must call this
```

**After:** Automatic updates (optional)
```python
# Enable once, then indexing happens automatically
await index_codebase(project_path=".", watch_files=True, auto_start_watcher=True)
# Files change → Index updates automatically
```

---

## Quick Start

### Enable Auto-Indexing on Startup

Set environment variable before starting MCP server:

```bash
export STRAVINSKY_ENABLE_SEMANTIC_WATCHING=true
stravinsky
```

This will:
1. Index the project on startup
2. Start file watcher
3. Re-index incrementally when files change
4. Clean up watcher on shutdown

### Manual Control

```python
# Get store (default)
store = get_store(project_path=".")

# Start watching explicitly
from mcp_bridge.tools.semantic_search import start_file_watcher
start_file_watcher(project_path=".", provider="ollama")

# Stop watching
from mcp_bridge.tools.semantic_search import stop_file_watcher
stop_file_watcher(project_path=".")
```

### Context Manager (Recommended)

```python
async with CodebaseVectorStore(project_path=".", watch_files=True) as store:
    await store.index_codebase()
    # Watcher runs here automatically
    await store.search("find authentication")
    # ... do searches ...
# Watcher auto-stops on context exit
```

---

## Configuration

### Environment Variables

```bash
# Enable automatic semantic indexing on server startup
STRAVINSKY_ENABLE_SEMANTIC_WATCHING=true

# Default: false (manual indexing only)
```

### Store Parameters

```python
store = get_store(
    project_path=".",           # Where to watch
    provider="ollama",          # Embedding provider
    watch_files=True,           # Enable watching
    auto_start_watcher=True,    # Start watcher on first index
)
```

### FileWatcher Customization

```python
# Adjust debouncing (default: 2 seconds)
watcher = FileWatcher(
    project_path=".",
    on_change=callback,
    debounce_seconds=1.0,  # Faster updates (less batching)
)
```

---

## How It Works

### File Watching Flow

```
1. File is modified (save, create, delete)
   ↓
2. watchdog detects change
   ↓
3. CodeFileEventHandler filters:
   - Only code files (.py, .js, .ts, etc.)
   - Skip ignored dirs (node_modules, .git, etc.)
   ↓
4. Debounce window (2 seconds):
   - Collect multiple changes into one batch
   - Prevents excessive re-indexing
   ↓
5. Callback: _on_file_changed()
   ↓
6. Acquire lock (prevent concurrent indexing)
   ↓
7. index_codebase(force=False)  [INCREMENTAL]
   - Only re-indexes changed files
   - Very fast compared to full reindex
   ↓
8. Release lock, next changes can start indexing
```

### Lifecycle

**Startup:**
```
async_main()
  ├─ env: STRAVINSKY_ENABLE_SEMANTIC_WATCHING=true?
  │  └─ index_codebase(watch_files=True, auto_start_watcher=True)
  │     ├─ Do initial indexing
  │     └─ Start watcher
  └─ Run MCP server
```

**Running:**
```
User modifies file
  ↓
Watcher detects (10-100ms)
  ↓
Debounce (2 seconds)
  ↓
Re-index changed files (100-500ms)
  ↓
Index updated in vector DB
  ↓
Next semantic_search() uses fresh index
```

**Shutdown:**
```
Server shutdown signal
  ↓
finally block in async_main()
  ↓
cleanup_all_stores()
  ↓
For each store: await store.stop_watching()
  ↓
Observer threads stopped
  ↓
Normal shutdown
```

---

## What Gets Watched

### Watched Extensions
```
.py, .js, .ts, .tsx, .jsx, .go, .rs, .rb, .java, .c, .cpp,
.h, .hpp, .cs, .swift, .kt, .scala, .vue, .svelte, .md, .txt,
.yaml, .yml, .json, .toml
```

### Ignored Directories
```
node_modules, .git, __pycache__, .venv, venv, env,
dist, build, .next, .nuxt, target, .tox,
.pytest_cache, .mypy_cache, .ruff_cache, coverage, .stravinsky
```

### Example: Project Structure

```
my_project/
├── src/
│   ├── auth.py           ← WATCHED (code file)
│   ├── database.py       ← WATCHED
│   └── __pycache__/      ← IGNORED
├── node_modules/         ← IGNORED
├── tests/
│   └── test_auth.py      ← WATCHED
├── README.md             ← WATCHED (documentation)
└── .git/                 ← IGNORED
```

---

## Common Scenarios

### Scenario 1: Enable Auto-Indexing Globally

```bash
# In .env file or shell profile
export STRAVINSKY_ENABLE_SEMANTIC_WATCHING=true

# Then start server normally
stravinsky

# Now file changes automatically update the index
```

### Scenario 2: One-Time Watching Session

```python
async def main():
    async with CodebaseVectorStore(".", watch_files=True) as store:
        await store.index_codebase()
        
        # Do searching, file changes trigger re-indexing
        results = await store.search("authentication")
        
    # Watcher auto-stops when exiting context
```

### Scenario 3: Disable Watching if Causing Issues

```python
# Stop watcher
store = get_store(project_path=".", watch_files=True)
await store.stop_watching()

# Use manual indexing instead
await store.index_codebase(force=False)  # Incremental only when needed
```

### Scenario 4: Start Watching Later

```python
# Create store without watching
store = get_store(project_path=".", watch_files=False)

# Manually enable watching later
await store.start_watching()

# Later: disable
await store.stop_watching()
```

---

## Troubleshooting

### "watchdog not installed"

```
Error: ImportError: watchdog is required for file watching

Solution:
  pip install watchdog
```

### Watching doesn't start

```
Possible causes:
1. watch_files=False (default) - Set to True
2. auto_start_watcher=False (default) - Set to True or call start_watching()
3. Index failed - Check embedding provider availability
4. watchdog import error - Install watchdog package
```

### Excessive re-indexing / High CPU

```
Possible causes:
1. Debounce too short (default: 2s) - Increase debounce_seconds
2. Many rapid file changes (IDE refactoring) - Wait for completion
3. Watched directory includes generated files - Add to SKIP_DUW

Solution:
  # Temporarily disable watching
  await store.stop_watching()
  
  # Do bulk operations
  # ... refactor, generate code, etc ...
  
  # Re-enable watching
  await store.start_watching()
```

### Index goes out of sync

```
Possible causes:
1. Watcher crashed silently - Check logs
2. Files changed too quickly (> 2s debounce) - Normal, will catch up
3. Watched directory deleted - Watcher stops gracefully

Solution:
  # Force full re-index
  await store.index_codebase(force=True)
```

### Server shutdown hangs

```
Possible causes:
1. Watcher observer join timeout exceeded - Usually recovers
2. Indexing in progress during shutdown - Waits for lock

Solution:
  # Check logs for cleanup errors
  # Kill server: Ctrl+C
  # Watcher cleanup happens on next startup
```

---

## Performance Tips

### Minimize Re-Indexing Overhead

1. **Use incremental indexing only**
   ```python
   # Good - only updates changed files
   await store.index_codebase(force=False)
   
   # Avoid unless necessary
   await store.index_codebase(force=True)
   ```

2. **Group file changes**
   - Debounce groups rapid changes (default: 2s)
   - Multiple edits → single re-index

3. **Disable watching during bulk operations**
   ```python
   await store.stop_watching()
   # ... large refactor, code generation, etc ...
   await store.start_watching()
   ```

### Optimize for Large Codebases

1. **Use incremental updates only**
   - Auto-watching always uses `force=False`
   - Much faster than full reindex

2. **Consider local embedding provider**
   - Ollama (local) faster than cloud API
   - No network latency

3. **Monitor resources**
   ```bash
   # Check memory usage during indexing
   top -pid $(pgrep -f "stravinsky")
   
   # Check disk usage
   du -sh ~/.stravinsky/vectordb/
   ```

---

## Integration with Workflow

### Claude Code + File Watching

```
1. Enable in environment:
   export STRAVINSKY_ENABLE_SEMANTIC_WATCHING=true
   
2. Start MCP server:
   stravinsky
   
3. In Claude Code:
   - Modify code files
   - Run semantic searches
   - Results use latest index (auto-updated)
   
4. On shutdown:
   - Watcher cleaned up automatically
   - Index persisted to disk
   - Next session uses cached index
```

### With Git Workflow

```
1. Index current state:
   await index_codebase()  # Initial index
   
2. Make changes (watching enabled):
   - Edit files
   - Index updates automatically
   
3. Commit changes:
   git add .
   git commit -m "..."
   
4. Index still fresh (always incremental)
```

---

## When to Use Watching vs Manual

### Use Automatic Watching When:
- Actively developing (file changes frequent)
- Want fresh search results without manual trigger
- Server runs continuously
- Embedding provider is fast (local)

### Use Manual Indexing When:
- Bulk operations (refactoring, migrations)
- Limited resources (embedded systems)
- Embedding provider is slow (cloud)
- Want explicit control

---

## Implementation Status

- [x] Core FileWatcher class design
- [x] CodebaseVectorStore integration design
- [x] Lifecycle management design
- [x] Error handling strategy
- [x] Configuration approach
- [ ] Implementation (Phase 1-5)
- [ ] Testing
- [ ] Documentation

See `/docs/filewatcher_integration_design.md` for full technical details.

---

## Related Documentation

- [Semantic Indexing Quick Start](/docs/semantic_indexing_quick_start.md)
- [Semantic Indexing Analysis](/docs/semantic_indexing_analysis.md)
- [FileWatcher Integration Design](/docs/filewatcher_integration_design.md)
