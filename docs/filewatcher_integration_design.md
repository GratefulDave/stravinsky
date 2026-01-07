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

### 3.1 New File: `mcp_bridge/tools/file_watcher.py`

```python
"""File change watcher for incremental semantic indexing.

Watches for file changes in a project directory and triggers
incremental re-indexing when code files change.
"""

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime, timedelta

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
except ImportError:
    # Graceful degradation if watchdog not installed
    Observer = None
    FileSystemEventHandler = None

logger = logging.getLogger(__name__)


class CodeFileEventHandler(FileSystemEventHandler):
    """Handles file system events for code changes.
    
    Filters events to only code files and debounces rapid changes.
    """
    
    # Code extensions to monitor
    CODE_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".rb",
        ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift", ".kt",
        ".scala", ".vue", ".svelte", ".md", ".yaml", ".yml", ".json", ".toml"
    }
    
    # Directories to ignore
    SKIP_DIRS = {
        "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
        "dist", "build", ".next", ".nuxt", "target", ".tox",
        ".pytest_cache", ".mypy_cache", ".ruff_cache", "coverage",
        ".stravinsky"
    }
    
    def __init__(self, on_change: Callable[[], None], debounce_seconds: float = 2.0):
        """Initialize event handler.
        
        Args:
            on_change: Async callback to invoke on file changes
            debounce_seconds: Debounce window for rapid changes (default: 2 seconds)
        """
        super().__init__()
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds
        self.last_change_time: Optional[datetime] = None
        self._debounce_timer: Optional[asyncio.Task] = None
    
    def _should_watch(self, file_path: str) -> bool:
        """Check if file should be watched."""
        path = Path(file_path)
        
        # Only watch code files
        if path.suffix.lower() not in self.CODE_EXTENSIONS:
            return False
        
        # Skip hidden files
        if any(part.startswith(".") for part in path.parts):
            if path.suffix not in {".md", ".txt"}:  # Allow .github docs
                return False
        
        # Skip ignored directories
        if any(skip_dir in path.parts for skip_dir in self.SKIP_DIRS):
            return False
        
        return True
    
    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        if not self._should_watch(event.src_path):
            return
        
        # Debounce rapid changes
        now = datetime.now()
        if self.last_change_time:
            elapsed = (now - self.last_change_time).total_seconds()
            if elapsed < self.debounce_seconds:
                logger.debug(f"Debouncing file change: {event.src_path}")
                return
        
        self.last_change_time = now
        logger.debug(f"File changed: {event.src_path}")
        
        # Schedule async callback
        asyncio.create_task(self._schedule_callback())
    
    async def _schedule_callback(self):
        """Schedule callback with debouncing."""
        if self._debounce_timer:
            self._debounce_timer.cancel()
        
        self._debounce_timer = asyncio.create_task(
            asyncio.sleep(self.debounce_seconds)
        )
        
        try:
            await self._debounce_timer
            await self.on_change()
        except asyncio.CancelledError:
            pass  # Debounce timer was cancelled (another change came in)


class FileWatcher:
    """Watches for file changes and triggers incremental indexing.
    
    Lifecycle:
    - Created: On CodebaseVectorStore init
    - Started: On first index_codebase() call
    - Stopped: On store removal or shutdown
    
    Usage:
        watcher = FileWatcher(project_path, on_change_callback)
        await watcher.start()
        # ... file changes trigger on_change_callback ...
        await watcher.stop()
    """
    
    def __init__(
        self,
        project_path: str,
        on_change: Callable[[], None],
        debounce_seconds: float = 2.0,
        auto_start: bool = False
    ):
        """Initialize file watcher.
        
        Args:
            project_path: Directory to watch
            on_change: Async callback when files change
            debounce_seconds: Debounce window (default: 2 seconds)
            auto_start: Start watching immediately (default: False)
        """
        if Observer is None:
            raise ImportError(
                "watchdog is required for file watching. "
                "Install: pip install watchdog"
            )
        
        self.project_path = Path(project_path).resolve()
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds
        
        self._observer: Optional[Observer] = None
        self._event_handler: Optional[CodeFileEventHandler] = None
        self._watch: Optional[int] = None
        self._running = False
    
    async def start(self) -> None:
        """Start watching the project directory.
        
        Safe to call multiple times (idempotent).
        """
        if self._running:
            logger.debug(f"Watcher already running for {self.project_path}")
            return
        
        try:
            # Create event handler and observer
            self._event_handler = CodeFileEventHandler(
                on_change=self.on_change,
                debounce_seconds=self.debounce_seconds
            )
            self._observer = Observer()
            
            # Watch recursively
            self._watch = self._observer.schedule(
                self._event_handler,
                path=str(self.project_path),
                recursive=True
            )
            
            # Start observer thread
            self._observer.start()
            self._running = True
            
            logger.info(
                f"Started file watcher for {self.project_path} "
                f"(debounce: {self.debounce_seconds}s)"
            )
        
        except Exception as e:
            logger.error(f"Failed to start file watcher: {e}")
            self._running = False
            raise
    
    async def stop(self) -> None:
        """Stop watching the project directory.
        
        Safe to call multiple times (idempotent).
        """
        if not self._running:
            return
        
        try:
            if self._observer:
                self._observer.stop()
                self._observer.join(timeout=5)  # Wait up to 5 seconds
                self._observer = None
            
            self._running = False
            logger.info(f"Stopped file watcher for {self.project_path}")
        
        except Exception as e:
            logger.error(f"Error stopping file watcher: {e}")
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()
    
    @property
    def is_running(self) -> bool:
        """Check if watcher is currently running."""
        return self._running
```

---

## 4. Design: CodebaseVectorStore Integration

### 4.1 Modified CodebaseVectorStore Class

```python
class CodebaseVectorStore:
    """Persistent vector store with optional file watching."""
    
    def __init__(
        self,
        project_path: str,
        provider: EmbeddingProvider = "ollama",
        watch_files: bool = False,  # NEW: Enable file watching
        auto_start_watcher: bool = False,  # NEW: Start watcher on first index
    ):
        self.project_path = Path(project_path).resolve()
        self.project_hash = hashlib.md5(str(self.project_path).encode()).hexdigest()[:12]
        
        # Embedding provider setup (existing)
        self.provider_name = provider
        self.provider = get_embedding_provider(provider)
        self.db_path = Path.home() / ".stravinsky" / "vectordb" / f"{self.project_hash}_{provider}"
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # File watching (NEW)
        self._watch_files = watch_files
        self._auto_start_watcher = auto_start_watcher
        self._watcher: Optional[FileWatcher] = None
        self._indexing_lock = asyncio.Lock()  # Prevent concurrent indexing
        
        # Existing fields
        self._lock_path = self.db_path / ".chromadb.lock"
        self._file_lock = None
        self._client = None
        self._collection = None
    
    # Existing properties and methods...
    
    async def _on_file_changed(self) -> None:
        """Callback when watched files change.
        
        Triggers incremental re-indexing.
        """
        async with self._indexing_lock:
            logger.info(f"File change detected in {self.project_path}, re-indexing...")
            try:
                stats = await self.index_codebase(force=False)  # Incremental
                logger.info(f"Incremental index updated: {stats}")
            except Exception as e:
                logger.error(f"Incremental indexing failed: {e}")
    
    async def start_watching(self) -> None:
        """Start watching files for changes.
        
        Safe to call multiple times. Returns immediately if already watching.
        """
        if not self._watch_files:
            logger.debug("File watching disabled for this store")
            return
        
        if self._watcher is None:
            try:
                from .file_watcher import FileWatcher
                
                self._watcher = FileWatcher(
                    project_path=str(self.project_path),
                    on_change=self._on_file_changed,
                    debounce_seconds=2.0,
                    auto_start=False  # We'll start explicitly
                )
                logger.debug(
                    f"Created file watcher for {self.project_path} "
                    f"(auto_start_watcher={self._auto_start_watcher})"
                )
            except ImportError:
                logger.warning(
                    "watchdog not installed - file watching disabled. "
                    "Install: pip install watchdog"
                )
                self._watch_files = False
                return
        
        if not self._watcher.is_running:
            await self._watcher.start()
    
    async def stop_watching(self) -> None:
        """Stop watching files for changes.
        
        Safe to call multiple times. Returns immediately if not watching.
        """
        if self._watcher and self._watcher.is_running:
            await self._watcher.stop()
    
    async def index_codebase(self, force: bool = False) -> dict:
        """Index the codebase and optionally start watching.
        
        Args:
            force: If True, reindex everything. Otherwise, only new/changed files.
        
        Returns:
            Statistics about the indexing operation.
        """
        # Existing indexing logic...
        stats = await self._do_index(force=force)
        
        # NEW: Start watching on first successful index (if enabled)
        if self._auto_start_watcher and self._watch_files and not self._watcher:
            try:
                await self.start_watching()
            except Exception as e:
                logger.warning(f"Failed to auto-start watcher: {e}")
        
        return stats
    
    async def _do_index(self, force: bool = False) -> dict:
        """Existing indexing implementation (renamed from index_codebase)."""
        # (Move existing index_codebase logic here)
        print(f"🔍 SEMANTIC-INDEX: {self.project_path}", file=sys.stderr)
        # ... rest of existing implementation ...
    
    async def __aenter__(self):
        """Context manager entry (async)."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup on exit."""
        await self.stop_watching()
    
    def __del__(self):
        """Cleanup on deletion (synchronous)."""
        # Note: Can't await in __del__, so we just log
        if self._watcher and self._watcher.is_running:
            logger.warning(
                f"CodebaseVectorStore for {self.project_path} being deleted "
                "with active watcher. Use await store.stop_watching() for clean shutdown."
            )
```

---

## 5. Design: Module-Level Cleanup

### 5.1 Modified get_store() Function

```python
# Global registry of active stores and watchers
_stores: dict[str, CodebaseVectorStore] = {}
_active_watchers: set[str] = set()  # Cache keys of stores with active watchers


def get_store(
    project_path: str,
    provider: EmbeddingProvider = "ollama",
    watch_files: bool = False,  # NEW: Enable file watching
    auto_start_watcher: bool = False,  # NEW: Auto-start on first index
) -> CodebaseVectorStore:
    """Get or create a vector store for a project.
    
    Args:
        project_path: Path to the project root
        provider: Embedding provider (ollama, gemini, openai, etc.)
        watch_files: Enable file watching for incremental updates
        auto_start_watcher: Start watcher on first index (requires watch_files=True)
    
    Returns:
        CodebaseVectorStore instance
    """
    path = str(Path(project_path).resolve())
    cache_key = f"{path}:{provider}"
    
    if cache_key not in _stores:
        _stores[cache_key] = CodebaseVectorStore(
            path,
            provider,
            watch_files=watch_files,
            auto_start_watcher=auto_start_watcher
        )
    
    return _stores[cache_key]


async def cleanup_all_stores() -> None:
    """Stop all active watchers and cleanup resources.
    
    Called on MCP server shutdown.
    """
    logger.info("Cleaning up semantic search stores...")
    
    cleanup_tasks = []
    for cache_key, store in _stores.items():
        cleanup_tasks.append(store.stop_watching())
    
    if cleanup_tasks:
        results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        for cache_key, result in zip(_stores.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Error cleaning up store {cache_key}: {result}")
    
    _active_watchers.clear()
    logger.info("Semantic search cleanup complete")


# Module-level atexit handler for emergency cleanup
import atexit

def _emergency_cleanup():
    """Emergency cleanup if async shutdown doesn't happen."""
    for store in _stores.values():
        try:
            if store._watcher and store._watcher.is_running:
                # Can't await in atexit, just log
                logger.warning("Emergency watcher stop in atexit handler")
        except Exception:
            pass

atexit.register(_emergency_cleanup)
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
│     ├─ get_store(project_path, watch_files=True, auto_start_watcher=True)
│     │  │
│     │  └─ Create CodebaseVectorStore with watcher config
│     │
│     └─ await store.index_codebase()
│        │
│        ├─ Do initial indexing
│        └─ NEW: Auto-start watcher (if auto_start_watcher=True)
│           │
│           └─ Watcher monitors project_path recursively
│              │
│              ├─ Debounce rapid changes (2 seconds)
│              ├─ Filter to code files only
│              └─ On change: Trigger _on_file_changed()
│                 │
│                 └─ await index_codebase(force=False) [incremental]
│
├─ Run MCP server (stdio_server)
│  │
│  └─ Handle tool calls:
│     ├─ semantic_search(query) - uses get_store() to access index
│     ├─ semantic_index(project_path) - triggers index + auto-start watcher
│     └─ enhanced_search(...) - leverages indexed data
│
└─ Shutdown (finally block)
   │
   ├─ NEW: cleanup_all_stores() - Stop all active watchers
   │  │
   │  └─ For each store: await store.stop_watching()
   │     │
   │     └─ Observer.stop() + join(timeout=5)
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

