# FileWatcher Integration - Design Summary

## Overview

This design enables real-time incremental indexing of semantic search indices through file system monitoring. Files are automatically re-indexed when code changes, keeping the vector store in sync with the codebase.

## Key Design Decisions

### 1. **File Watching Technology: watchdog**
- **Why:** Industry-standard, cross-platform, robust error handling
- **Not watchfiles/notify:** For consistency with existing MCP ecosystem
- **Graceful degradation:** Works without watchdog but disables file watching

### 2. **Lifecycle Management: Store Ownership**
```
FileWatcher is owned by CodebaseVectorStore (composition pattern)
┌─ CodebaseVectorStore
│  ├─ _watcher: Optional[FileWatcher]
│  ├─ _watch_files: bool (enable/disable flag)
│  ├─ _auto_start_watcher: bool (auto-start on first index)
│  └─ _on_file_changed(): async callback
│
└─ FileWatcher (lifecycle tied to store)
   ├─ Starts: On store.start_watching() or auto-start after index
   ├─ Stops: On store.stop_watching() or server shutdown
   └─ Monitored: In module-level cleanup registry
```

### 3. **Auto-Start Behavior**

**Option selected: Lazy auto-start after first index**
```python
store = get_store(project_path, watch_files=True, auto_start_watcher=True)
await store.index_codebase()  # Watcher auto-starts after successful index
```

**Rationale:**
- Doesn't slow down store creation
- Confirms embedding provider works before starting watcher
- User has explicit control via parameters
- Can be enabled by environment variable for auto-indexing

### 4. **Cleanup Strategy: Multi-Level**

**Level 1: Store-owned (immediate)**
- `await store.stop_watching()` - Per-store cleanup
- Used by async context manager exit

**Level 2: Module-level (server shutdown)**
- `cleanup_all_stores()` - Batch cleanup of all watchers
- Called in `server.py` finally block
- Handles all cache keys at once

**Level 3: Emergency (process exit)**
- `atexit` handler - Fallback if async cleanup doesn't happen
- Logs warning but doesn't try to await

### 5. **Debouncing: 2-Second Window**

```python
# Multiple file changes → Single re-index
File A changed: 00:00:00
File B changed: 00:00:01  # Debounced
File C changed: 00:00:01.5  # Debounced
Indexing starts:          00:00:02  # Single batch
```

**Rationale:**
- Prevents excessive re-indexing during editor autosave (typically ~100ms intervals)
- Allows grouping multiple changes
- 2 seconds: Balance between freshness and efficiency

### 6. **Incremental-Only Updates**

```python
# File change callback ALWAYS uses:
await store.index_codebase(force=False)  # Incremental

# Full reindex only when:
await store.index_codebase(force=True)   # User explicitly requests
```

**Rationale:**
- Force=False detects changed files automatically
- Much faster than full reindex
- Protects against embedding API quota usage

### 7. **Concurrency Control: Lock Per Store**

```python
_indexing_lock = asyncio.Lock()  # Prevents concurrent indexing

async def _on_file_changed():
    async with self._indexing_lock:
        await self.index_codebase(force=False)
```

**Rationale:**
- ChromaDB not safe for concurrent writes
- Multiple rapid file changes queue sequentially
- No watcher thread contention (watchdog uses separate thread)

### 8. **Configuration Options**

| Parameter | Default | Scope | Purpose |
|-----------|---------|-------|---------|
| `watch_files` | False | Store | Enable/disable watching |
| `auto_start_watcher` | False | Store | Auto-start after first index |
| `STRAVINSKY_ENABLE_SEMANTIC_WATCHING` | false | Env var | Enable auto-indexing on startup |
| `debounce_seconds` | 2.0 | FileWatcher | Debounce window |

## Architecture Diagram

```
MCP Server Start
│
├─ env: STRAVINSKY_ENABLE_SEMANTIC_WATCHING=true?
│  └─ Yes: index_codebase(watch_files=True, auto_start_watcher=True)
│
├─ get_store(project_path, watch_files=?, auto_start_watcher=?)
│  └─ Creates CodebaseVectorStore with watcher config
│
├─ store.index_codebase()
│  ├─ Do indexing (_do_index)
│  └─ Auto-start watcher? (if conditions met)
│
├─ FileWatcher monitoring project_path/
│  ├─ Debounce rapid changes (2s)
│  ├─ Filter code files
│  └─ On change: _on_file_changed()
│     └─ Acquire lock → incremental re-index
│
└─ MCP Server Shutdown
   └─ cleanup_all_stores()
      └─ For each store: await store.stop_watching()
```

## Module Organization

### Modified: `mcp_bridge/tools/semantic_search.py`

**CodeFileEventHandler**
- Filters file events (only code files, skip ignored dirs)
- Handles debouncing (async task-based)
- Invokes async callback on changes

**CodebaseFileWatcher**
- Wraps watchdog.observers.Observer
- Async lifecycle (start/stop)
- Context manager support
- Property: is_running

**CodebaseVectorStore**
- Add: `_watcher`, `_watcher_lock`
- Add: `start_watching()`, `stop_watching()`, `is_watching()`
- Add: `start_watching()` calls `CodebaseFileWatcher`

**Module-level**
- Add: `start_file_watcher()`, `stop_file_watcher()`, `get_file_watcher()`, `list_file_watchers()`
- Update: `get_store()` (no signature change, watcher managed separately)

### Modified: `mcp_bridge/server.py`

**async_main()**
- Add: Optional semantic indexing on startup (env-gated)
- Add: cleanup_all_stores() in finally block

## Implementation Phases

1. **Phase 1 (1-2 hrs):** FileWatcher class + CodeFileEventHandler
2. **Phase 2 (1-2 hrs):** CodebaseVectorStore integration
3. **Phase 3 (1 hr):** Module-level cleanup + atexit
4. **Phase 4 (1 hr):** Server integration
5. **Phase 5 (1-2 hrs):** Tests + documentation

## Testing Approach

**Unit tests (file_watcher.py):**
- Watcher start/stop lifecycle
- Event filtering (code files, ignored dirs)
- Debouncing (rapid changes → single callback)
- Context manager support

**Integration tests (semantic_search.py):**
- Store + watcher lifecycle
- Auto-start on first index
- Incremental indexing on file change
- Cleanup on store removal
- Concurrent file changes (queue behavior)

**Manual testing:**
- Enable env var, start server
- Monitor index growth as files change
- Verify graceful shutdown
- Test error recovery

## Error Scenarios & Recovery

| Scenario | Recovery |
|----------|----------|
| watchdog not installed | Graceful degradation - watching disabled |
| Watcher start fails | Log warning, continue without watching |
| Incremental index fails | Log error, continue watching |
| File permission denied | Watchdog handles (skips event) |
| ChromaDB locked | Async lock queues next index |
| Server shutdown hangs | atexit handler logs warning |

## Performance Expectations

| Operation | Time | Cost |
|-----------|------|------|
| Store creation | <1ms | Minimal |
| start_watching() | 10-50ms | Spawns observer thread |
| First file change | 2s (debounce) | Triggers incremental index |
| Incremental index | 100-500ms | Depends on files changed |
| stop_watching() | 100-500ms | Waits for observer join |
| cleanup_all_stores() | N * stop time | Parallel via gather |

## Future Enhancements

1. **Config file support** - yaml/toml for watch_files, debounce_seconds
2. **Metrics** - Track index latency, file change frequency
3. **Smart prioritization** - Index changed files before unchanged
4. **Batch updates** - Group changes into single ChromaDB transaction
5. **Cloud storage support** - Handle Dropbox/OneDrive file events
6. **Selective watching** - Pattern-based include/exclude
7. **Cache warming** - Pre-embed hot code paths

## Key Files

```
docs/
├── filewatcher_integration_design.md  [This file]
│   ├── Full 14-section design document
│   ├── Code examples for all classes
│   ├── Lifecycle flow diagrams
│   └── Testing strategy
│
├── semantic_indexing_analysis.md
│   └── Current system state analysis
│
└── semantic_indexing_quick_start.md
    └── User guide for semantic search

mcp_bridge/tools/
├── file_watcher.py  [NEW]
│   ├── CodeFileEventHandler
│   └── FileWatcher
│
└── semantic_search.py  [MODIFIED]
    ├── CodebaseVectorStore (add watching)
    └── Module-level cleanup functions

mcp_bridge/
└── server.py  [MODIFIED]
    └── async_main() (add indexing + cleanup)
```

---

## Comparison with Alternatives

### Alternative A: Scheduled Indexing
```
Pro: Simple, no watcher needed
Con: Index goes stale between checks, resource intensive
```

### Alternative B: Git Hooks
```
Pro: Only indexes committed changes
Con: Doesn't catch unsaved edits, complex setup
```

### Alternative C: LSP Notifications
```
Pro: Integrates with editor
Con: Requires editor extension, not all editors supported
```

### Selected: File System Watching (watchdog)
```
Pro: Real-time, all files, cross-platform, simple
Con: Requires watchdog package, consumes file descriptors
Verdict: Best balance of features and complexity
```

