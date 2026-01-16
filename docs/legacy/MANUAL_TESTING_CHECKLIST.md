# Manual Testing Checklist for Auto-Indexing

## Pre-Test Setup

### Prerequisites
- [ ] Python 3.11+ installed
- [ ] Stravinsky project cloned and dependencies installed (uv sync)
- [ ] Ollama installed and running (ollama serve)
- [ ] Embedding model pulled (ollama pull nomic-embed-text)
- [ ] Temporary test project created at /tmp/test_semantic_project

### Initialize Test Project

Create test project structure:

```bash
cd /tmp/test_semantic_project
git init
mkdir -p src tests docs
```

## Test 1: Basic File Creation

**Objective**: Verify that creating a new file triggers indexing and makes content searchable.

### Steps

1. Create new Python file with authentication logic
2. Wait 2-3 seconds for auto-indexing
3. Search for "authenticate user"
4. Verify file appears in results

### Expected Output

- stderr shows "Indexed 1 chunks from 1 files"
- Search result includes auth.py with relevance 0.7+
- Code preview shows the authenticate function

### Checkboxes

- [ ] File creation detected by watcher
- [ ] stderr message shows indexing operation
- [ ] Semantic search finds new content
- [ ] Relevance score is meaningful (0.7+)
- [ ] File path is correct in results

---

## Test 2: File Modification

**Objective**: Verify that modifying existing code updates the index.

### Steps

1. Append new function to existing file
2. Wait 2-3 seconds for re-indexing
3. Search for the new function
4. Verify it appears in results

### Expected Output

- stderr shows "Indexed 1-2 chunks"
- Search finds both old and new functions
- Results show correct file path

### Checkboxes

- [ ] File modification detected
- [ ] Index updated with new content
- [ ] New function is searchable
- [ ] Old content still indexed
- [ ] No duplicate chunks

---

## Test 3: File Deletion

**Objective**: Verify that deleting a file removes its content from the index.

### Steps

1. Create file with "deprecated function"
2. Verify it indexes and is searchable
3. Delete the file
4. Search for it again - should NOT appear

### Expected Behavior

- Before delete: deprecated.py in results
- stderr shows "Pruning N stale chunks"
- After delete: deprecated.py NOT in results

### Checkboxes

- [ ] File deletion detected
- [ ] Chunks marked for deletion
- [ ] Vector store updated
- [ ] Search no longer finds deleted content
- [ ] No orphaned entries in database

---

## Test 4: Debouncing (Rapid Changes)

**Objective**: Verify that debouncing prevents excessive re-indexing.

### Steps

1. Monitor indexing operations in stderr
2. Rapidly create 10 files (one every 100ms)
3. Count number of "Indexed" messages
4. Verify only 1-2 indexing operations total

### Expected Behavior

- Only 1-2 indexing operations for 10 file creations
- All 10 files indexed in single pass
- Total time < 10 seconds
- NOT 10 separate operations

### Checkboxes

- [ ] Multiple file creations grouped
- [ ] Single indexing operation triggered
- [ ] All files included in index
- [ ] Debounce delay observed (2-3 seconds)
- [ ] No wasted re-indexing

---

## Test 5: Mass File Operations (Branch Simulation)

**Objective**: Verify that 50+ file changes don't hang the system.

### Steps

1. Start timer before changes
2. Create 50 new files in directory
3. Monitor for completion
4. Note total time elapsed

### Expected Behavior

- Single consolidated re-index operation
- Completes in < 15 seconds
- Handles 50+ file changes gracefully
- User can continue working (not hanging)

### Checkboxes

- [ ] Mass operation detected
- [ ] Single index pass (not multiple)
- [ ] All changes processed
- [ ] Reasonable performance (< 15s)
- [ ] No "hanging" or unresponsive state

---

## Test 6: Search Accuracy Verification

**Objective**: Verify that semantic search finds relevant content.

### Steps

1. Create database.py with DatabaseConnection class
2. Test queries: "database connection", "SQL query", "SQLite operations"
3. Verify all find database.py
4. Check relevance scores vary by similarity

### Expected Behavior

- All queries find database.py
- Relevance scores vary by query similarity
- Specific queries have higher relevance

### Checkboxes

- [ ] "database connection" finds class
- [ ] "SQL query" finds method
- [ ] "SQLite" finds operations
- [ ] Relevance scores make sense
- [ ] False positives minimal

---

## Test 7: Error Handling - Service Unavailable

**Objective**: Verify graceful handling when Ollama is unavailable.

### Steps

1. Verify Ollama works: run a search
2. Stop Ollama (pkill -f "ollama serve")
3. Try to index
4. Check error message
5. Restart Ollama
6. Verify indexing works again

### Expected Behavior

- Error message shown (not crash)
- Clear recovery instructions
- Watcher doesn't crash
- Works after restart

### Checkboxes

- [ ] Service unavailability detected
- [ ] Error message is clear
- [ ] Application doesn't crash
- [ ] Helpful recovery instructions
- [ ] Can retry after restart
- [ ] No data corruption

---

## Test 8: Vector Database Statistics

**Objective**: Verify that stats accurately reflect indexed content.

### Steps

1. Get initial stats (chunks, db path, provider)
2. Add new Python file
3. Get updated stats
4. Verify chunk count increased

### Expected Behavior

- Chunks count increases
- DB path consistent
- Provider info correct

### Checkboxes

- [ ] Chunks indexed count is positive
- [ ] DB path points to .stravinsky
- [ ] Provider name is correct
- [ ] Dimension matches provider (768)
- [ ] Stats update after changes

---

## Test 9: Excluded Directories

**Objective**: Verify that excluded directories are not indexed.

### Steps

1. Create files in .venv, node_modules, __pycache__
2. Force re-index
3. Search for content from excluded dirs
4. Verify NOT found

### Expected Behavior

- .venv files not indexed
- node_modules not indexed
- __pycache__ not indexed
- Only source files indexed

### Checkboxes

- [ ] .venv directory skipped
- [ ] node_modules directory skipped
- [ ] __pycache__ directory skipped
- [ ] Excluded files not searchable
- [ ] Performance not impacted

---

## Test 10: Concurrent Access (File Lock)

**Objective**: Verify file lock prevents corruption.

### Steps

1. Start background indexing operation
2. Attempt concurrent access while indexing
3. Verify lock is respected
4. Verify database integrity after

### Expected Behavior

- Lock acquired on first operation
- Concurrent attempts wait or timeout
- No database corruption
- Database usable after

### Checkboxes

- [ ] File lock exists during indexing
- [ ] Concurrent operations respect lock
- [ ] No crashes from contention
- [ ] Database integrity maintained
- [ ] Lock released after operation

---

## Test 11: Health Checks

**Objective**: Verify health check reporting.

### Steps

1. Run health check command
2. Verify output format
3. Check both provider and database status

### Expected Output

```
Provider (ollama): Online
Vector DB: Online (XX documents)
```

### Checkboxes

- [ ] Provider status shown correctly
- [ ] Database status shown correctly
- [ ] Document count matches stats

---

## Cleanup

After all tests:

```bash
# Kill any remaining processes
pkill -f "python -m mcp_bridge" 2>/dev/null || true

# Clean test project
rm -rf /tmp/test_semantic_project
```

---

## Test Summary

### Passed Tests

- [ ] Test 1: Basic File Creation
- [ ] Test 2: File Modification
- [ ] Test 3: File Deletion
- [ ] Test 4: Debouncing
- [ ] Test 5: Mass File Operations
- [ ] Test 6: Search Accuracy
- [ ] Test 7: Error Handling
- [ ] Test 8: Statistics
- [ ] Test 9: Excluded Directories
- [ ] Test 10: Concurrent Access
- [ ] Test 11: Health Checks

### Overall Assessment

- **Total Tests**: 11
- **Passed**: __/11
- **Status**: PASS or FAIL

### Notes

(Add observations or recommendations)

_________________________________

Tester: __________________________ Date: __________

