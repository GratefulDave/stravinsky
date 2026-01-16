# FileWatcher Architecture Deep Dive

## Component Overview

```
┌────────────────────────────────────────────────────────────────┐
│                   CodebaseFileWatcher                          │
│                  (Main Orchestrator)                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  project_path: Path          Store: CodebaseVectorStore       │
│  debounce_seconds: float     _observer: Observer              │
│  _event_handler: Handler     _lock: threading.Lock            │
│  _pending_files: set[str]    _pending_reindex_timer: Timer    │
│                                                                │
│  Methods:                                                      │
│  • start()                   Initializes observer              │
│  • stop()                    Cleans up observer                │
│  • is_running() -> bool      Check if active                   │
│  • _on_file_changed(path)    Queue file for reindex           │
│  • _trigger_reindex()        Execute reindex operation         │
│  • _create_debounce_timer()  Create debounce timer            │
│                                                                │
└────────────────────────────────────────────────────────────────┘
              ↓
┌────────────────────────────────────────────────────────────────┐
│              _FileChangeHandler                                │
│         (watchdog.events.FileSystemEventHandler)              │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  watcher: CodebaseFileWatcher                                 │
│  project_path: Path                                           │
│                                                                │
│  Methods:                                                      │
│  • on_created(event)    File created                          │
│  • on_modified(event)   File modified                         │
│  • on_deleted(event)    File deleted                          │
│  • on_moved(event)      File renamed/moved                    │
│  • _should_index_file() Filter check                          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
              ↓
┌────────────────────────────────────────────────────────────────┐
│           CodebaseVectorStore                                  │
│      (Semantic Search Index)                                   │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  async index_codebase()     Reindex all files                 │
│  async search()             Semantic search                    │
│  _chunk_file()              Split file into chunks             │
│  collection                 ChromaDB collection                │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Event Flow Diagram

### File Modification Event

```
[Disk: File Written]
         ↓
[watchdog.Observer detects change]
         ↓
[FileSystemEventHandler.on_modified()]
         ↓
[_should_index_file() filter]
         │
         ├─ True: Continue to FileWatcher
         └─ False: Ignore event
         ↓
[CodebaseFileWatcher._on_file_changed()]
         ↓
[_lock.acquire()]
         ├─ Add file to _pending_files
         ├─ Cancel existing _pending_reindex_timer
         └─ _create_debounce_timer()
         ↓
[threading.Timer._run()]
         │
         ├─ Wait debounce_seconds
         │
         └─ Timeout or cancellation
         ↓
[CodebaseFileWatcher._trigger_reindex()]
         ↓
[asyncio.run_until_complete()]
         ↓
[CodebaseVectorStore.index_codebase(force=False)]
         ├─ Get all indexable files
         ├─ Extract existing document IDs
         ├─ Generate chunks for current files
         ├─ Calculate delta (new, stale, deleted)
         ├─ Delete stale chunks
         ├─ Embed new chunks
         └─ Store embeddings in ChromaDB
         ↓
[Index Updated]
```

### Multi-File Batch Processing

```
Time  Event                  Pending Files          Timer         Chunks Processed
────────────────────────────────────────────────────────────────────────────────
0.0s  main.py modified       {main.py}              START(2.0s)   -
0.3s  utils.py modified      {main.py, utils}       RESET(2.0s)   -
0.7s  auth.py modified       {main.py, utils, auth} RESET(2.0s)   -
2.7s  (timeout)              {}                     FIRED         3 files, 15 chunks
      REINDEX STARTS
3.2s  (still reindexing)     {}                     IDLE          Chunking...
3.8s  (embedding)            {}                     IDLE          Embedding...
4.5s  REINDEX COMPLETE       {}                     IDLE          ✅ 15 chunks indexed
```

## Thread Safety

The implementation uses multiple synchronization mechanisms:

### 1. Lock-Protected State (_lock)

```python
with self._lock:
    # Access to shared state is protected
    self._pending_files.add(file_path)
    if self._pending_reindex_timer is not None:
        self._pending_reindex_timer.cancel()
    self._pending_reindex_timer = self._create_debounce_timer()
```

**Protected members**:
- `_pending_files`: Set of files awaiting reindex
- `_pending_reindex_timer`: Reference to current debounce timer

### 2. Daemon Thread Mode

```python
self._observer = Observer()
self._observer.daemon = True  # Won't block program exit
self._observer.start()
```

**Benefits**:
- Watcher thread exits when main thread exits
- Never deadlocks on shutdown
- Clean program termination

### 3. Stop Event

```python
self._stop_event = threading.Event()

# Before operations
if self._stop_event.is_set():
    return

# On shutdown
self._stop_event.set()
```

**Usage**: Signals reindex operations to abort early if watcher is stopping

### 4. ChromaDB File Lock

```python
@property
def file_lock(self):
    if self._file_lock is None:
        filelock = get_filelock()
        self._file_lock = filelock.FileLock(
            str(self._lock_path),
            timeout=30  # 30-second timeout
        )
    return self._file_lock
```

**Purpose**: Prevents concurrent access to ChromaDB (which isn't thread-safe)

## Code Walkthrough

### Initialization

```python
def __init__(
    self,
    project_path: str | Path,
    store: CodebaseVectorStore,
    debounce_seconds: float = 2.0,
):
    """Initialize the file watcher."""
    self.project_path = Path(project_path).resolve()
    self.store = store  # Existing vector store to reindex
    self.debounce_seconds = debounce_seconds  # Delay before reindexing
    
    # Threading components
    self._observer: Observer | None = None  # Watchdog observer
    self._event_handler: _FileChangeHandler | None = None
    self._watch_handle = None  # Schedule handle
    self._lock = threading.Lock()  # Protect shared state
    self._stop_event = threading.Event()  # Signal shutdown
    
    # Debouncing state
    self._pending_reindex_timer: threading.Timer | None = None
    self._pending_files: set[str] = set()  # Files to reindex
```

### Starting the Watcher

```python
def start(self) -> None:
    """Start watching the project directory for changes."""
    if self._observer is not None:
        logger.warning("FileWatcher is already running")
        return
    
    try:
        self._stop_event.clear()  # Clear stop signal
        self._observer = Observer()  # Create watchdog observer
        self._event_handler = _FileChangeHandler(
            watcher=self,  # Pass reference to self
            project_path=str(self.project_path),
        )
        
        # Schedule recursive monitoring
        self._watch_handle = self._observer.schedule(
            self._event_handler,
            path=str(self.project_path),
            recursive=True,  # Watch subdirectories
        )
        
        # Start in daemon thread (non-blocking)
        self._observer.daemon = True
        self._observer.start()
        
        logger.info(f"FileWatcher started for {self.project_path}")
    except Exception as e:
        logger.error(f"Failed to start FileWatcher: {e}")
        self._observer = None
        raise
```

### File Change Detection

```python
def _on_file_changed(self, file_path: str) -> None:
    """Called when a file changes. Schedules a debounced reindex."""
    if self._stop_event.is_set():
        return  # Watcher is shutting down
    
    rel_path = str(Path(file_path).relative_to(self.project_path))
    logger.debug(f"File changed: {rel_path}")
    
    with self._lock:  # Protect shared state
        # Queue the file for reindexing
        self._pending_files.add(rel_path)
        
        # Cancel existing timer and set new one
        if self._pending_reindex_timer is not None:
            self._pending_reindex_timer.cancel()
        
        # Reset debounce timer
        self._pending_reindex_timer = self._create_debounce_timer()
```

### Debounce Timer Creation

```python
def _create_debounce_timer(self):
    """Create a timer that triggers reindex after debounce period."""
    timer = threading.Timer(
        self.debounce_seconds,  # Wait this long
        self._trigger_reindex,   # Call this method
    )
    timer.daemon = True  # Don't block exit
    timer.start()  # Start countdown
    return timer
```

### Triggering Reindex

```python
def _trigger_reindex(self) -> None:
    """Trigger the actual reindexing (called after debounce period)."""
    if self._stop_event.is_set():
        return  # Watcher is shutting down
    
    with self._lock:
        files_to_log = list(self._pending_files)
        self._pending_reindex_timer = None
        self._pending_files.clear()  # Clear pending set
    
    if not files_to_log:
        return  # No files changed
    
    try:
        logger.info(f"Reindexing codebase due to changes: {files_to_log}")
        
        # Get or create event loop (we're in background thread)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run async reindex operation
        loop.run_until_complete(
            self.store.index_codebase(force=False)  # Incremental, not full reindex
        )
        
        logger.info("Reindexing completed")
    except Exception as e:
        logger.error(f"Error during reindex: {e}")
```

### Event Handler Filter

```python
class _FileChangeHandler(watchdog.events.FileSystemEventHandler):
    """Filter file events for only .py files in project."""
    
    def _should_index_file(self, file_path: str) -> bool:
        """Determine if a file should trigger reindexing."""
        path = Path(file_path)
        
        # Only Python files
        if path.suffix.lower() not in {".py"}:
            return False
        
        # Skip hidden files/dirs
        if any(part.startswith(".") for part in path.parts):
            return False
        
        # Skip excluded directories
        if any(skip_dir in path.parts for skip_dir in CodebaseVectorStore.SKIP_DUW):
            return False
        
        # Skip files outside project
        try:
            path.relative_to(self.project_path)
        except ValueError:
            return False
        
        return True
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and self._should_index_file(event.src_path):
            logger.debug(f"File modified: {event.src_path}")
            self.watcher._on_file_changed(event.src_path)
```

### Module-Level API

```python
_watchers: dict[str, CodebaseFileWatcher] = {}

def start_file_watcher(
    project_path: str = ".",
    provider: EmbeddingProvider = "ollama",
    debounce_seconds: float = 2.0,
) -> CodebaseFileWatcher:
    """Start a file watcher for automatic codebase reindexing."""
    path = str(Path(project_path).resolve())
    
    # Avoid duplicate watchers
    if path in _watchers and _watchers[path].is_running():
        logger.info(f"FileWatcher already running for {path}")
        return _watchers[path]
    
    # Get or create vector store
    store = get_store(project_path, provider)
    
    # Create and start watcher
    watcher = CodebaseFileWatcher(
        project_path=path,
        store=store,
        debounce_seconds=debounce_seconds,
    )
    watcher.start()
    
    # Cache for later access
    _watchers[path] = watcher
    
    return watcher
```

## Performance Characteristics

### Memory Usage

```
Component              Memory        Notes
────────────────────────────────────────────────────────
Observer               ~1-2 MB       Watchdog internals
Handler                ~0.1 MB       Event filter
Pending files set      ~1 KB/file    Temporary during debounce
ThreadPool             ~0.5 MB       Observer threads
────────────────────────────────────────────────────────
Total per project      ~2-3 MB       Base overhead
```

### CPU Usage

```
Scenario               CPU Impact    Duration
────────────────────────────────────────────────────────
Idle (no changes)      ~0%          Indefinite
Debounce period        ~0%          debounce_seconds
Reindex small proj     ~80% (1 core) ~0.5-1s
Reindex large proj     ~80% (1 core) ~10-30s
```

### Disk I/O

```
Operation              I/O Pattern   Frequency
────────────────────────────────────────────────────────
Watch directory        Minimal       Continuous
Reindex (read code)    ~100 MB/s     Per change event
ChromaDB update        Depends on    Per reindex
                       embedding size
```

## Error Recovery

### Graceful Degradation

```python
# If reindex fails, watcher continues monitoring
try:
    await self.store.index_codebase(force=False)
except Exception as e:
    logger.error(f"Reindex failed: {e}")
    # Watcher continues running
    # Will retry on next file change
```

### Automatic Retry

```
File Change → Reindex Starts
    ↓
Reindex Fails (e.g., Ollama down)
    ↓
Error Logged
    ↓
Watcher Continues Monitoring
    ↓
Next File Change → Reindex Retried
```

### Shutdown Handling

```python
def stop(self) -> None:
    """Stop watching for changes and clean up resources."""
    # Cancel any pending reindex
    if self._pending_reindex_timer is not None:
        self._pending_reindex_timer.cancel()
    
    # Stop the observer (waits up to 5 seconds)
    self._observer.stop()
    self._observer.join(timeout=5.0)
    
    # Signal to any running reindex
    self._stop_event.set()
```

## Integration Points

### With CodebaseVectorStore

```python
# FileWatcher uses existing store's methods
await store.index_codebase(force=False)

# Store uses file_lock for ChromaDB access
with self.store.file_lock:
    collection.add(...)
```

### With Embedding Providers

```python
# Provider determines reindex speed
provider = store.provider  # e.g., OllamaProvider

# Reindex calls provider async methods
embeddings = await store.get_embeddings_batch(documents)
```

### With CLI Integration

```python
# Module-level API for CLI access
from mcp_bridge.tools.semantic_search import (
    start_file_watcher,
    stop_file_watcher,
    list_file_watchers,
)

# CLI can start/stop/list watchers
watcher = start_file_watcher(".")
```

## Future Optimization Opportunities

1. **Selective Chunk Updates**
   - Track which files changed
   - Only recompute embeddings for affected chunks
   - Current: Full reindex of all files

2. **Smart Debouncing**
   - Increase debounce for large projects
   - Decrease for small, rapid edits
   - Based on file change frequency

3. **Parallel Embedding**
   - Use asyncio.gather for concurrent embeddings
   - Currently: Sequential batch processing

4. **Change Tracking**
   - Remember file hashes
   - Skip files that haven't actually changed
   - Reduce unnecessary reindexing

5. **Incremental Chunking**
   - Only rechunk modified files
   - Preserve chunks from unchanged files
   - Faster processing for large projects
