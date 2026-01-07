# FileWatcher + CodebaseVectorStore Integration Design

## Executive Summary

Design for integrating a file watcher with CodebaseVectorStore to enable real-time incremental indexing. The watcher should be lifecycle-managed with the store, auto-start on first index, and cleanly shutdown with the MCP server.

---

## 1. Current State Analysis

### 1.1 CodebaseVectorStore Structure (semantic_search.py:638-750)

```python
class CodebaseVectorStore:
    """Persistent vector store for a single codebase."""
    
    def __init__(self, project_path: str, provider: EmbeddingProvider = "ollama"):
        self.project_path = Path(project_path).resolve()
        self.project_hash = hashlib.md5(...)
        self.provider_name = provider
        self.provider = get_embedding_provider(provider)
        self.db_path = Path.home() / ".stravinsky" / "vectordb" / ...
        self._lock_path = self.db_path / ".chromadb.lock"
        self._file_lock = None
        self._client = None
        self._collection = None
```

**Key observations:**
- No file watcher instance variable
- No `__del__` method (requires cleanup)
- No context manager support (`__enter__`/`__exit__`)
- Lazy initialization of client/collection
- File-based locking for concurrency

### 1.2 Module-Level Cache (semantic_search.py:1269-1282)

```python
_stores: dict[str, CodebaseVectorStore] = {}

def get_store(project_path: str, provider: EmbeddingProvider = "ollama"):
    """Get or create a vector store for a project."""
    cache_key = f"{path}:{provider}"
    if cache_key not in _stores:
        _stores[cache_key] = CodebaseVectorStore(path, provider)
    return _stores[cache_key]
```

**Key observations:**
- Global cache with no cleanup mechanism
- No watchers registry
- Stores persist for entire session

### 1.3 Server Lifecycle (server.py:628-663)

```python
async def async_main():
    # Initialize hooks
    initialize_hooks()
    
    # Start background token refresh
    asyncio.create_task(background_token_refresh(...))
    
    # Run MCP server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(...)
    
    # Cleanup on shutdown
    finally:
        lsp_manager = get_lsp_manager()
        await lsp_manager.shutdown()
```

**Key observations:**
- No semantic indexing trigger
- Clear shutdown pattern with finally block
- Async background tasks pattern exists
- Good place to hook watcher startup/shutdown

---

## 2. FileWatcher Requirements

### 2.1 Capabilities

- **Watch specific project directory** for code file changes
- **Debounce rapid changes** (e.g., editor autosave)
- **Incremental updates only** (call `index_codebase(force=False)`)
- **Skip ignored directories** (node_modules, .git, venv, etc.)
- **Graceful shutdown** when store is removed or server exits

### 2.2 Implementation Options

#### Option A: Use `watchdog` (Recommended)

```python
# Pros: Robust, cross-platform, supports subdirectories
# Cons: Additional dependency
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
```

#### Option B: Use `pathlib` + background thread

```python
# Pros: No new dependencies, simple
# Cons: Less efficient for large codebases
import asyncio
while True:
    current_mtime = path.stat().st_mtime
    if current_mtime > last_mtime:
        trigger_index()
```

#### Option C: Use `asyncio` file descriptor polling

```python
# Pros: Pure asyncio, efficient
# Cons: Complex, platform-specific
```

**Recommendation: Option A (watchdog)** - Industry standard, well-tested, minimal complexity.

---

## 3. Design: FileWatcher Class

### 3.1 Implemented in: `mcp_bridge/tools/semantic_search.py`

(Note: Implementation merged into semantic_search.py to avoid circular imports and simplify management)

```python
class CodebaseFileWatcher:
    """Watch a project directory for file changes and trigger reindexing.


---

## 4. Design: CodebaseVectorStore Integration

### 4.1 Modified CodebaseVectorStore Class

```python
class CodebaseVectorStore:
    """Persistent vector store with optional file watching."""
    
    def __init__(self, project_path: str, provider: EmbeddingProvider = "ollama"):
        self.project_path = Path(project_path).resolve()
        # ... existing initialization ...
        
        # File watching (NEW)
        self._watcher: "CodebaseFileWatcher | None" = None
        self._watcher_lock = threading.Lock()
        
    # ...
    
    def start_watching(self, debounce_seconds: float = 2.0) -> "CodebaseFileWatcher":
        """Start watching the project directory for file changes."""
        with self._watcher_lock:
            if self._watcher is None:
                # Avoid circular import by importing here
                from .semantic_search import CodebaseFileWatcher
                self._watcher = CodebaseFileWatcher(
                    project_path=self.project_path,
                    store=self,
                    debounce_seconds=debounce_seconds,
                )
                self._watcher.start()
            # ...
            return self._watcher
```

---

## 5. Design: Module-Level Cleanup

### 5.1 Modified get_store() Function

```python
# Global registry of active stores and watchers
_stores: dict[str, CodebaseVectorStore] = {}
_watchers: dict[str, "CodebaseFileWatcher"] = {}  # Cache for watchers

def get_store(
    project_path: str,
    provider: EmbeddingProvider = "ollama",
) -> CodebaseVectorStore:
    """Get or create a vector store for a project."""
    path = str(Path(project_path).resolve())
    cache_key = f"{path}:{provider}"
    
    if cache_key not in _stores:
        _stores[cache_key] = CodebaseVectorStore(path, provider)
    
    return _stores[cache_key]

def start_file_watcher(
    project_path: str,
    provider: EmbeddingProvider = "ollama",
    debounce_seconds: float = 2.0,
) -> "CodebaseFileWatcher":
    """Start watching a project directory."""
    # (Implementation using store.start_watching)
```

---

## 6. Design: Server Integration

### 6.1 Modified server.py

```python
# File: mcp_bridge/server.py

async def async_main():
    """Server execution entry point."""
    # Initialize hooks at runtime
    try:
        from .hooks import initialize_hooks
        initialize_hooks()
    except Exception as e:
        logger.error(f"Failed to initialize hooks: {e}")
    
    # Start background token refresh scheduler
    try:
        from .auth.token_refresh import background_token_refresh
        asyncio.create_task(background_token_refresh(get_token_store()))
        logger.info("Background token refresh scheduler started")
    except Exception as e:
        logger.warning(f"Failed to start token refresh scheduler: {e}")
    
    # NEW: Start optional background semantic indexing
    try:
        from .tools.semantic_search import index_codebase
        enable_semantic_watching = os.getenv(
            "STRAVINSKY_ENABLE_SEMANTIC_WATCHING",
            "false"
        ).lower() in ("true", "1", "yes")
        
        if enable_semantic_watching:
            logger.info("STRAVINSKY_ENABLE_SEMANTIC_WATCHING=true, starting auto-indexing...")
            asyncio.create_task(index_codebase(
                project_path=".",
                force=False,
                provider="ollama"
            ))
    except Exception as e:
        logger.debug(f"Semantic indexing not available: {e}")
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    except Exception as e:
        logger.critical("Server process crashed in async_main", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Initiating shutdown sequence...")
        
        # NEW: Cleanup semantic search watchers
        try:
            from .tools.semantic_search import cleanup_all_stores
            await cleanup_all_stores()
        except Exception as e:
            logger.warning(f"Error during semantic search cleanup: {e}")
        
        # Existing LSP cleanup
        from .tools.lsp.manager import get_lsp_manager
        lsp_manager = get_lsp_manager()
        await lsp_manager.shutdown()
```

---

## 7. Lifecycle Flow Diagram

```
┌─ MCP Server Start (async_main)
│
├─ Initialize hooks
├─ Start token refresh background task
├─ NEW: Start optional auto-indexing (if STRAVINSKY_ENABLE_SEMANTIC_WATCHING=true)
│  │
│  └─ Call: index_codebase(project_path=".")
│     │
│     ├─ get_store(project_path)
│     │  │
│     │  └─ Create CodebaseVectorStore
│     │
│     └─ await store.index_codebase()
│        │
│        └─ Do initial indexing
│
├─ Run MCP server (stdio_server)
│  │
│  └─ Handle tool calls:
│     ├─ semantic_search(query)
│     ├─ semantic_index(project_path)
│     ├─ start_file_watcher(project_path)  <-- Must be called explicitly to start watching
│     └─ ...
│
└─ Shutdown (finally block)
   │
   ├─ cleanup_all_stores()
   │  │
   │  └─ For each store: await store.stop_watching()
   │
   └─ LSP manager shutdown (existing)
```

---

## 8. Configuration

### 8.1 Environment Variables

```bash
# Enable automatic semantic indexing on startup
STRAVINSKY_ENABLE_SEMANTIC_WATCHING=true

# Default: false (manual indexing only)
```

### 8.2 API Configuration

```python
# Disable watching (default)
store = get_store(project_path, watch_files=False)

# Enable watching, start manually
store = get_store(project_path, watch_files=True)
await store.start_watching()

# Enable watching with auto-start on first index
store = get_store(project_path, watch_files=True, auto_start_watcher=True)
await store.index_codebase()  # Watcher auto-starts after index

# Context manager usage
async with CodebaseVectorStore(project_path, watch_files=True) as store:
    await store.index_codebase()
    # Watcher runs while context is active
# Watcher auto-stops on context exit
```

---

## 9. Implementation Checklist

### Phase 1: Core FileWatcher (1-2 hours)

- [ ] Create `mcp_bridge/tools/file_watcher.py`
- [ ] Implement CodeFileEventHandler
- [ ] Implement FileWatcher class
- [ ] Add watchdog dependency to pyproject.toml
- [ ] Unit tests for file watching

### Phase 2: CodebaseVectorStore Integration (1-2 hours)

- [ ] Add watcher instance variable to CodebaseVectorStore.__init__
- [ ] Add `_on_file_changed()` callback
- [ ] Add `start_watching()` method
- [ ] Add `stop_watching()` method
- [ ] Add async context manager support
- [ ] Rename index_codebase to _do_index (keep wrapper)
- [ ] Add auto-start logic to index_codebase

### Phase 3: Module-Level Cleanup (1 hour)

- [ ] Implement cleanup_all_stores()
- [ ] Add atexit handler for emergency cleanup
- [ ] Update get_store() signature

### Phase 4: Server Integration (1 hour)

- [ ] Add semantic indexing to async_main()
- [ ] Add cleanup_all_stores() to shutdown
- [ ] Add STRAVINSKY_ENABLE_SEMANTIC_WATCHING env var

### Phase 5: Documentation & Testing (1-2 hours)

- [ ] Document lifecycle in docstrings
- [ ] Create integration tests
- [ ] Update semantic_indexing_quick_start.md
- [ ] Add configuration examples

---

## 10. Error Handling Strategy

### 10.1 Watchdog Graceful Degradation

```python
try:
    from watchdog.observers import Observer
except ImportError:
    logger.warning("watchdog not installed, file watching disabled")
    # Continue without watching
```

### 10.2 Watcher Startup Failure

```python
try:
    await self.start_watching()
except Exception as e:
    logger.warning(f"Failed to start watcher: {e}")
    # Continue without watching, store still usable
```

### 10.3 Incremental Indexing Failure

```python
async def _on_file_changed(self):
    async with self._indexing_lock:
        try:
            stats = await self.index_codebase(force=False)
        except Exception as e:
            logger.error(f"Incremental indexing failed: {e}")
            # Log error but don't crash, continue watching
```

### 10.4 Shutdown Cleanup

```python
async def cleanup_all_stores():
    for cache_key, store in _stores.items():
        try:
            await store.stop_watching()
        except Exception as e:
            logger.error(f"Error cleaning up {cache_key}: {e}")
            # Continue cleanup for other stores
```

---

## 11. Testing Strategy

### 11.1 Unit Tests (file_watcher.py)

```python
@pytest.mark.asyncio
async def test_file_watcher_start_stop():
    """Test watcher lifecycle."""
    watcher = FileWatcher(project_path, async_callback)
    assert not watcher.is_running
    await watcher.start()
    assert watcher.is_running
    await watcher.stop()
    assert not watcher.is_running

@pytest.mark.asyncio
async def test_file_watcher_debounce():
    """Test debouncing of rapid changes."""
    call_count = 0
    async def callback():
        nonlocal call_count
        call_count += 1
    
    watcher = FileWatcher(project_path, callback, debounce_seconds=1)
    await watcher.start()
    
    # Simulate 5 rapid changes
    for i in range(5):
        watcher._event_handler.on_modified(MockEvent())
        await asyncio.sleep(0.1)
    
    await asyncio.sleep(1.5)  # Wait for debounce
    
    # Should only trigger once
    assert call_count == 1
    await watcher.stop()
```

### 11.2 Integration Tests (semantic_search.py)

```python
@pytest.mark.asyncio
async def test_store_with_watcher():
    """Test store lifecycle with watcher."""
    store = CodebaseVectorStore(
        project_path,
        watch_files=True,
        auto_start_watcher=True
    )
    
    # Initial index
    stats = await store.index_codebase()
    assert stats['indexed'] > 0
    assert store._watcher.is_running
    
    # Modify a file
    test_file = Path(project_path) / "test.py"
    test_file.write_text("# Changed")
    
    # Wait for watcher to trigger
    await asyncio.sleep(3)
    
    # Cleanup
    await store.stop_watching()
    assert not store._watcher.is_running
```

---

## 12. Performance Considerations

### 12.1 Debouncing

- **Default:** 2 seconds between checks
- **Rationale:** Prevents excessive re-indexing during rapid edits
- **Configurable:** Can be adjusted per store

### 12.2 Incremental Indexing

- **Always use:** `force=False` in file change callback
- **Cost:** Only re-indexes changed files
- **Efficiency:** Much cheaper than full reindex

### 12.3 Concurrency Control

- **Lock:** `_indexing_lock` prevents concurrent indexing
- **Purpose:** Protects ChromaDB from concurrent writes
- **Impact:** Second change waits for first indexing to complete

### 12.4 Resource Usage

| Operation | CPU | Memory | Disk I/O |
|-----------|-----|--------|----------|
| Startup (empty project) | Low | ~50MB | Minimal |
| Index 1000 files | Medium | ~200MB | Heavy |
| Watch (idle) | Minimal | ~10MB | Minimal |
| Watch (file change) | High | ~200MB | Heavy |

---

## 13. Future Enhancements

1. **Persistent watch state** - Remember enabled watchers across sessions
2. **Batch indexing** - Group multiple file changes before re-indexing
3. **Priority queue** - Process important files first
4. **Metrics collection** - Track watch/index performance
5. **Cloud sync support** - Handle network file changes (Dropbox, OneDrive, etc.)
6. **Selective watching** - Watch only certain file patterns
7. **Cache warming** - Pre-embed common patterns

---

## 14. Appendix: Code Snippets

### A.1 Minimal Example

```python
# Simple async watching example
async def main():
    # Get store with auto-watching
    store = get_store(
        project_path=".",
        watch_files=True,
        auto_start_watcher=True
    )
    
    # Initial index - watcher auto-starts
    await store.index_codebase()
    
    # Watcher now monitoring project_path/
    # File changes trigger incremental re-indexing automatically
    
    # Clean shutdown
    await store.stop_watching()

asyncio.run(main())
```

### A.2 Context Manager Example

```python
async def main():
    async with CodebaseVectorStore(
        ".",
        watch_files=True
    ) as store:
        await store.index_codebase()
        # Watcher runs here
        # ... do searches ...
    # Watcher auto-stopped on exit
```

### A.3 Manual Control Example

```python
async def main():
    store = get_store(".", watch_files=True)
    
    # Explicit control
    await store.start_watching()
    
    # Disable watching
    await store.stop_watching()
    
    # Re-enable watching
    await store.start_watching()
```

