# Auto-Indexing Test Plan for Semantic Search

## Overview

This test plan covers auto-indexing functionality for the semantic search system. Auto-indexing automatically updates the vector database when code changes are detected in the project, enabling real-time semantic search capabilities without manual re-indexing.

## 1. Test Scenarios

### 1.1 File Creation Tests

**Scenario: Create new Python file**
- **Expected**: Auto-indexer detects new file, triggers re-indexing
- **Verification**:
  - File watcher event fires
  - New chunks are created for the file
  - Vector store is updated with new embeddings
  - Semantic search finds content from new file

**Scenario: Create new file in subdirectory**
- **Expected**: Nested file changes trigger indexing
- **Verification**:
  - Watcher respects directory traversal
  - Relative path correctly resolved
  - Chunks include correct file_path metadata

**Scenario: Create multiple files rapidly**
- **Expected**: Debouncing prevents excessive re-indexing
- **Verification**:
  - Only one indexing operation per debounce window
  - All files are included in single index pass

### 1.2 File Modification Tests

**Scenario: Add new function to existing file**
- **Expected**: Incremental update identifies new chunks
- **Verification**:
  - Old chunks retained
  - New function chunks added
  - Content hash detects actual changes (not just timestamps)

**Scenario: Modify existing function signature**
- **Expected**: Content hash changes trigger re-embedding
- **Verification**:
  - Modified chunk detected (different hash)
  - Old chunk ID removed from index
  - New chunk added with updated embedding

**Scenario: Add docstring to existing function**
- **Expected**: Semantic search finds improved content
- **Verification**:
  - Chunk content updated
  - Embedding reflects docstring content
  - Search quality improves for related queries

### 1.3 File Deletion Tests

**Scenario: Delete Python file**
- **Expected**: Chunks from deleted file removed from index
- **Verification**:
  - File no longer appears in file list
  - Chunk IDs prefixed with file path are removed
  - Vector store count decreases

**Scenario: Delete directory with multiple files**
- **Expected**: All chunks in directory removed
- **Verification**:
  - Watcher detects directory deletion
  - All affected chunk IDs identified
  - Batch deletion from vector store

### 1.4 Debouncing & Performance Tests

**Scenario: Rapid consecutive file modifications**
- **Initial**: Create and modify file 10 times in 2 seconds
- **Expected**: Debouncing prevents thrashing
- **Verification**:
  - Only 1-2 indexing operations observed
  - Total time < 5 seconds
  - No duplicate work

**Scenario: Mass file operations (git checkout branch)**
- **Initial**: Simulate branch switch (many file changes)
- **Expected**: Debouncing prevents hanging
- **Verification**:
  - Single consolidated index operation
  - Handles 50+ file changes gracefully
  - User can continue working during re-index

**Scenario: Ignore excluded directories**
- **Initial**: Create files in .venv, node_modules, __pycache__
- **Expected**: Watcher ignores excluded directories
- **Verification**:
  - Changes in excluded dirs don't trigger indexing
  - Performance not impacted by ignored directories

### 1.5 Error Recovery Tests

**Scenario: Embedding service becomes unavailable**
- **Initial**: Ollama service stopped during indexing
- **Expected**: Graceful error handling
- **Verification**:
  - Error logged with clear message
  - Indexing aborted (not corrupted)
  - User notified via stderr
  - Next file change retries indexing

**Scenario: Vector database lock contention**
- **Initial**: Force concurrent access attempts
- **Expected**: File lock prevents corruption
- **Verification**:
  - Lock acquired before each operation
  - Timeout error if lock unavailable
  - Database remains consistent

**Scenario: Interrupted indexing (user cancels)**
- **Initial**: Start indexing, interrupt after 2 seconds
- **Expected**: Graceful cancellation without corruption
- **Verification**:
  - Partial index not committed
  - Vector store remains in consistent state
  - Retry attempts full re-index

### 1.6 Notification Tests

**Scenario: Index operation completion**
- **Expected**: Notification shows chunks added/removed
- **Verification**:
  - stderr message: "Indexed N chunks from M files"
  - Includes count of pruned chunks
  - Shows database path

**Scenario: Error notifications**
- **Expected**: Clear error messages for debugging
- **Verification**:
  - Provider unavailability shown
  - File lock timeout reported
  - Missing dependency instructions

## 2. Test Implementation Approach

### 2.1 Unit Tests vs Integration Tests

**Unit Tests** (mocked file system):
- Test chunking logic with synthetic files
- Test vector store operations with mock ChromaDB
- Test debounce timer logic
- Test file pattern matching (includes/excludes)

**Integration Tests** (real file system):
- Test watcher with actual file operations
- Test with real ChromaDB in temp directory
- Test with mock embedding provider
- Test error scenarios (service unavailable)

### 2.2 Mocking Strategy

```python
# Mock file system events
from watchdog.events import FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

# Mock embedding provider
class MockEmbeddingProvider(BaseEmbeddingProvider):
    async def get_embedding(self, text: str) -> list[float]:
        # Return deterministic dummy vector
        return [0.1] * 768

# Mock ChromaDB
from unittest.mock import MagicMock, patch
mock_collection = MagicMock()
mock_collection.add = MagicMock()
mock_collection.delete = MagicMock()
mock_collection.count = MagicMock(return_value=10)
```

### 2.3 Watcher Verification

```python
# Capture fired events
captured_events = []

class TestEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        captured_events.append(('modified', event.src_path))
    
    def on_created(self, event):
        captured_events.append(('created', event.src_path))
    
    def on_deleted(self, event):
        captured_events.append(('deleted', event.src_path))

# Create file, verify event fired
temp_file = temp_dir / "test.py"
temp_file.write_text("def foo(): pass")
await asyncio.sleep(0.1)  # Allow watcher to fire
assert ('created', str(temp_file)) in captured_events
```

### 2.4 Vector DB Verification

```python
# Verify database was updated
async def verify_indexing():
    stats_before = store.get_stats()
    count_before = stats_before['chunks_indexed']
    
    # Trigger indexing
    temp_file.write_text("def new_function(): pass")
    await asyncio.sleep(debounce_delay + 0.5)
    
    # Verify count increased
    stats_after = store.get_stats()
    count_after = stats_after['chunks_indexed']
    assert count_after > count_before
```

## 3. Manual Testing Steps

### 3.1 Setup

```bash
# Start Ollama
ollama serve &

# Pull embedding model
ollama pull nomic-embed-text

# Initialize test project
cd /tmp/test_semantic_project
git init
mkdir -p src tests
touch README.md
```

### 3.2 Basic Auto-Indexing

1. Start semantic search in watch mode:
   ```bash
   python -m mcp_bridge.tools.semantic_search --watch --project /tmp/test_semantic_project
   ```

2. Create a new Python file:
   ```bash
   cat > /tmp/test_semantic_project/src/auth.py << 'PYEOF'
   def authenticate_user(username, password):
       """Authenticate a user against the database."""
       # Simulate auth logic
       return True
   PYEOF
   ```

3. Observe stderr output:
   - Should see: "File created: src/auth.py"
   - Should see: "Indexing triggered"
   - Should see: "Indexed 1 chunks"

4. Query semantic search:
   ```bash
   python -m mcp_bridge.tools.semantic_search --search "authentication logic" --project /tmp/test_semantic_project
   ```
   - Should find src/auth.py with high relevance

### 3.3 Observe Notifications

```bash
# Tail stderr to see all notifications
python -m mcp_bridge.tools.semantic_search --watch --project /tmp/test_semantic_project 2>&1 | grep "SEMANTIC"
```

Expected output:
```
SEMANTIC-INDEX: /tmp/test_semantic_project
  Indexed 5 chunks from 3 files
SEMANTIC-SEARCH: 'authentication logic'
  Found 1 result: src/auth.py (relevance: 0.95)
```

### 3.4 Check Vector DB

```bash
python -c "
from mcp_bridge.tools.semantic_search import get_store
store = get_store('/tmp/test_semantic_project', 'ollama')
print(store.get_stats())
"
```

Expected output:
```
{
  'project_path': '/tmp/test_semantic_project',
  'db_path': '/home/user/.stravinsky/vectordb/abc123_ollama',
  'chunks_indexed': 15,
  'embedding_provider': 'ollama',
  'embedding_dimension': 768
}
```

### 3.5 Mass File Operations

```bash
# Simulate branch checkout (many changes)
cd /tmp/test_semantic_project
for i in {1..20}; do
    echo "def func_$i(): pass" >> src/module_$i.py
done

# Should see single consolidated re-index, not 20 separate operations
# Monitor stderr for debouncing effect
```

### 3.6 Error Scenarios

1. **Stop Ollama**:
   ```bash
   pkill -f "ollama serve"
   # Try to trigger indexing
   touch /tmp/test_semantic_project/new_file.py
   # Should see: "Ollama not available" error
   # Indexing should not crash the watcher
   ```

2. **Restart Ollama**:
   ```bash
   ollama serve &
   # Indexing should automatically retry and succeed
   ```

## 4. Performance Benchmarks

### Expected Performance

| Operation | Size | Time | Notes |
|-----------|------|------|-------|
| Index new file | 50 lines | < 1s | Single function |
| Index new file | 500 lines | < 2s | Class + methods |
| Debounce window | - | 2-3s | Wait before indexing |
| 10 file creates | - | < 5s | Debounced to single pass |
| 50 file changes | - | < 10s | Branch switch scenario |
| Embedding lookup | 1 chunk | < 100ms | Ollama call |
| ChromaDB insert | 100 chunks | < 500ms | Batch operation |

### Measurement Script

```python
import time
from pathlib import Path

async def benchmark_indexing(num_files: int, lines_per_file: int):
    start = time.time()
    
    # Create test files
    for i in range(num_files):
        file_path = test_dir / f"bench_{i}.py"
        content = "\n".join([f"def func_{j}(): pass" for j in range(lines_per_file)])
        file_path.write_text(content)
    
    # Trigger indexing
    await asyncio.sleep(debounce_delay + 0.5)
    
    elapsed = time.time() - start
    stats = store.get_stats()
    
    print(f"Indexed {stats['chunks_indexed']} chunks from {num_files} files in {elapsed:.2f}s")
    print(f"Rate: {stats['chunks_indexed'] / elapsed:.0f} chunks/sec")
```

## 5. Expected Behaviors and Outputs

### 5.1 Successful Indexing

**File Created**:
```
File modified event: tests/test_new.py
Debounce: Postponing indexing (1.5s remaining)
Debounce: Indexing now
SEMANTIC-INDEX: /home/user/my_project
  Pruning 0 stale chunks...
  Indexed 3/3 chunks...
  Index complete: 3 new, 0 pruned, 42 total chunks
```

**File Deleted**:
```
File deleted event: src/old_module.py
Debounce: Postponing indexing (1.5s remaining)
Debounce: Indexing now
SEMANTIC-INDEX: /home/user/my_project
  Pruning 5 stale chunks (from src/old_module.py)...
  No new chunks to index
  Index complete: 0 new, 5 pruned, 37 total chunks
```

### 5.2 Error States

**Embedding Service Unavailable**:
```
SEMANTIC-INDEX: /home/user/my_project
Error: Embedding service not available
Hint: Start Ollama with: ollama serve
Waiting for service... (retry in 30s)
```

**File Lock Timeout**:
```
SEMANTIC-INDEX: /home/user/my_project
Error: Could not acquire ChromaDB lock
Hint: Another process is using the vector database
Waiting for lock release... (timeout in 30s)
```

## 6. Test Checklist

- [ ] Unit: File chunking (new, modified, deleted)
- [ ] Unit: Debounce timer (single vs multiple triggers)
- [ ] Unit: Pattern matching (includes/excludes)
- [ ] Unit: Content hash detection
- [ ] Integration: Watcher with real file operations
- [ ] Integration: Vector store updates
- [ ] Integration: Error recovery
- [ ] Manual: Observe stderr notifications
- [ ] Manual: Verify semantic search accuracy
- [ ] Manual: Check vector DB statistics
- [ ] Manual: Test mass file operations
- [ ] Manual: Test service unavailability
- [ ] Performance: Measure indexing speed
- [ ] Performance: Verify debouncing effectiveness
- [ ] Stress: 100+ file changes
- [ ] Stress: Large files (1MB+)
- [ ] Stress: Deep directory nesting

## 7. Debugging

### Enable verbose logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("mcp_bridge.tools.semantic_search").setLevel(logging.DEBUG)
logging.getLogger("watchdog").setLevel(logging.DEBUG)
```

### Monitor vector database

```bash
# Check ChromaDB files
ls -lh ~/.stravinsky/vectordb/

# Inspect database size
du -sh ~/.stravinsky/vectordb/*/

# Check for lock files
find ~/.stravinsky/vectordb/ -name "*.lock"
```

### Trace file watcher

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DebugEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        print(f"CREATED: {event.src_path}")
    
    def on_modified(self, event):
        print(f"MODIFIED: {event.src_path}")
    
    def on_deleted(self, event):
        print(f"DELETED: {event.src_path}")

observer = Observer()
observer.schedule(DebugEventHandler(), path=project_path, recursive=True)
observer.start()
```

## 8. Known Issues & Limitations

1. **File System Event Ordering**: Some systems may fire events out of order. Create + modify might appear as modify only.
   - Mitigation: Use content hash to detect actual changes

2. **Debounce Window**: 2-3 second window optimal for most use cases, but user can configure.
   - Tuning: Too short = excessive re-indexing; Too long = delayed search results

3. **Symlinks**: Watcher may not follow symlinks by default.
   - Workaround: Configure with `follow_symlinks=True`

4. **Network Paths**: Watcher may have issues on network-mounted directories.
   - Workaround: Copy project to local disk

5. **Very Large Codebases**: 10,000+ files may exceed memory/time limits.
   - Workaround: Implement chunked indexing in future releases

## 9. Future Enhancements

1. **Partial Indexing**: Index only changed lines instead of entire files
2. **Incremental Embeddings**: Reuse existing embeddings for unchanged content
3. **Index Versioning**: Track vector DB version and auto-migrate on upgrade
4. **Selective Watch**: Allow user to exclude specific patterns (e.g., `*.test.py`)
5. **Distributed Indexing**: Support multiple workers for large codebases
6. **Index Compression**: Reduce storage footprint for large projects
