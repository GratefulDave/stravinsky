# Auto-Indexing System Manual Test Guide

This guide explains how to run the comprehensive manual test script for the auto-indexing system.

## Overview

The `manual_test_auto_indexing.py` script provides end-to-end testing of the FileWatcher and semantic search auto-indexing system, verifying:

1. **FileWatcher Initialization** - Proper setup and lifecycle management
2. **File Change Detection** - Create, modify, delete, and rename operations
3. **Debouncing** - Rapid changes are batched together efficiently
4. **Pattern Exclusion** - .gitignore and .semanticignore patterns are respected
5. **Error Handling** - Graceful recovery from syntax errors and exceptions
6. **Vector Store Integration** - Changes trigger proper re-indexing

## Prerequisites

### 1. Ollama (Embedding Service)

The test requires a local embedding service running via Ollama.

**Install Ollama:**
- macOS: `brew install ollama`
- Linux: Download from https://ollama.ai
- Windows: Download from https://ollama.ai

**Start Ollama:**
```bash
ollama serve
```

This starts the service on `http://localhost:11434`

**Pull the embedding model:**
```bash
ollama pull nomic-embed-text
```

The test expects the `nomic-embed-text` model (768 dimensions). This is a ~274MB download.

### 2. Python 3.10+

```bash
python3 --version  # Should be 3.10 or higher
```

### 3. Dependencies

Install stravinsky in development mode:

```bash
cd /path/to/stravinsky
uv install  # or: pip install -e .
```

Required packages:
- `watchdog` - File system event monitoring
- `chromadb` - Vector storage
- `filelock` - Concurrent access control
- `ollama` - Ollama client
- `tenacity` - Retry logic

## Running the Test

### Basic Usage

```bash
# From the stravinsky project root
uv run python tests/manual_test_auto_indexing.py
```

Or:

```bash
# Or use standard Python
python tests/manual_test_auto_indexing.py
```

### Expected Output

The test produces colorized output showing progress through each test section:

```
[INFO] Python version >= 3.10
[PASS] Python 3.11

[INFO] Ollama service availability
[PASS] Ollama running with nomic-embed-text model

[INFO] watchdog library for file monitoring
[PASS] watchdog 3.0.0 installed

...

=====================================================================
                   TEST 1: INITIAL INDEXING
=====================================================================

[TEST] Indexing initial project files
[PASS] Indexed 15 chunks from 4 file(s)
[INFO] Database at: /home/user/.stravinsky/vectordb/a1b2c3d4e5f6_ollama

[TEST] Re-indexing after file creation
[PASS] New file indexed: 3 new chunks

[TEST] Re-indexing after file modification
[PASS] Modified file re-indexed: 4 chunks updated

[TEST] Re-indexing after file deletion
[PASS] Deleted file removed from index: 2 chunks pruned

...

=====================================================================
                       TEST SUMMARY
=====================================================================

[PASS] Test 1: Initial Indexing
[PASS] Test 2: FileWatcher Lifecycle
[PASS] Test 3: File Change Detection
[PASS] Test 4: Debouncing
[PASS] Test 5: Pattern Exclusion
[PASS] Test 6: Error Handling

Results:
  Passed: 6/6
  Failed: 0/6

All tests passed!
```

## Test Sections Explained

### Prerequisite Check
Verifies all required dependencies and services are available:
- Python 3.10+
- Ollama with nomic-embed-text
- watchdog library
- ChromaDB
- filelock
- stravinsky modules

**If this fails:** Install missing dependencies or start Ollama service.

### Test 1: Initial Indexing
Indexes the initial test project (main.py, utils.py, config.py, src/lib.py).

**Expected:** Should index 15+ chunks from 4 Python files.

**If this fails:** Check that Ollama is running and embedding service is available.

### Test 2: FileWatcher Lifecycle
Tests starting and stopping the file watcher:
1. Verify initial state (not running)
2. Start watcher
3. Verify running state
4. Stop watcher
5. Verify stopped state

**Expected:** All state transitions should succeed.

**If this fails:** Check watchdog library and file system permissions.

### Test 3: File Change Detection
Tests that file changes trigger re-indexing:
1. Create a new Python file → should be indexed
2. Modify an existing file → should update index
3. Delete a file → chunks should be removed from index

**Expected:** 
- New file: 3+ new chunks
- Modified file: 4+ chunks updated
- Deleted file: 2+ chunks pruned

**If this fails:** Check that watcher is properly detecting file system events.

### Test 4: Debouncing
Verifies that rapid changes are batched together:
1. Make 5 rapid file modifications
2. Verify they accumulate in pending files
3. Wait for debounce period
4. Verify reindex was triggered once (not 5 times)

**Expected:** All 5 changes should be in `_pending_files` before reindex.

**If this fails:** Check that debounce timer is being created and cancelled properly.

### Test 5: Pattern Exclusion
Tests that .gitignore and SKIP_DUW patterns are respected:
1. Create .gitignore with exclusion patterns
2. Create files matching those patterns
3. Create included files
4. Verify excluded files are not indexed

**Expected:** .log files and build/ directory should be excluded; included.py should be indexed.

**If this fails:** Check that SKIP_DUW is properly configured.

### Test 6: Error Handling
Tests graceful error recovery:
1. Create a file with syntax errors
2. Attempt to index (should fallback to line-based chunking)
3. Fix the syntax error
4. Re-index successfully

**Expected:** Should complete successfully despite syntax errors.

**If this fails:** Check error handling in semantic_search module.

## Interpreting Results

### All Tests Pass
```
Results:
  Passed: 6/6
  Failed: 0/6

All tests passed!
```
The auto-indexing system is functioning correctly.

### Some Tests Fail
```
Results:
  Passed: 4/6
  Failed: 2/6

[FAIL] Test 4: Debouncing
  Details: Timer may still be pending
```

Check the test section for details. Each failure includes context about what failed.

### Prerequisite Failures
If prerequisites fail, the test will exit early with details about what's missing:
```
[FAIL] Ollama not available: Connection refused
[INFO] Start Ollama with: ollama serve
```

Follow the printed instructions to resolve the issue.

## Debugging

### Enable Verbose Logging

The script logs to stderr. Enable logging by checking stderr output:

```bash
uv run python tests/manual_test_auto_indexing.py 2>&1 | tee test_output.log
```

### Check Vector Store Database

After running tests, the vector store database is stored at:
```
~/.stravinsky/vectordb/<project_hash>_ollama/
```

This is a ChromaDB persistent storage directory. You can inspect it to verify indexing:

```bash
# List available databases
ls -la ~/.stravinsky/vectordb/

# Check the test database size
du -sh ~/.stravinsky/vectordb/*/
```

### Monitor File System Events

During the test, you can monitor file system events in another terminal:

```bash
# macOS: using fs_usage
sudo fs_usage | grep test_auto_indexing

# Linux: using inotifywait
inotifywait -r -m /tmp/tmp*/
```

### Check Ollama Status

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check available models
ollama list

# Test embedding
curl -X POST http://localhost:11434/api/embeddings \
  -d '{
    "model": "nomic-embed-text",
    "prompt": "test"
  }'
```

## Troubleshooting

### "Ollama not available"

**Problem:** The test can't connect to Ollama.

**Solution:**
1. Start Ollama: `ollama serve`
2. Verify it's running: `curl http://localhost:11434/api/tags`
3. Check that nomic-embed-text is installed: `ollama list`
4. If not installed: `ollama pull nomic-embed-text`

### "nomic-embed-text model not found"

**Problem:** The embedding model is not available.

**Solution:**
```bash
ollama pull nomic-embed-text
# This downloads the ~274MB model
```

### "watchdog not installed"

**Problem:** The file system monitoring library is missing.

**Solution:**
```bash
uv add watchdog
# or: pip install watchdog
```

### "ChromaDB error: database locked"

**Problem:** Another process has the vector store database open.

**Solution:**
1. Stop any other instances of the test
2. Kill any Python processes: `pkill -f manual_test_auto_indexing`
3. Delete the lock file: `rm ~/.stravinsky/vectordb/*/.chromadb.lock`
4. Re-run the test

### Test Hangs or Takes Too Long

**Problem:** A test appears to be hanging or taking much longer than expected.

**Solution:**
1. The debouncing test waits for timers. This is normal and takes ~5 seconds.
2. Large file indexing may take a while depending on system resources.
3. If it hangs for >30 seconds in one test, press Ctrl+C and check logs.

### "Permission denied" errors

**Problem:** The test can't create directories or files.

**Solution:**
1. Check /tmp permissions: `ls -la /tmp/ | head -5`
2. Ensure write access to temp directory
3. Check ~/.stravinsky permissions: `ls -la ~/.stravinsky/`
4. If ~/.stravinsky is locked, remove it: `rm -rf ~/.stravinsky/vectordb/`

## Test Statistics

Typical test run statistics:

| Test | Time | Files Indexed | Chunks |
|------|------|---------------|--------|
| Initial Indexing | 5-10s | 4 | 15-20 |
| Debouncing | 2s | 1 | 1-2 |
| File Changes | 8-12s | 3 | 10-15 |
| Error Handling | 3-5s | 2 | 5-8 |
| **Total** | **20-30s** | **~10** | **40-60** |

Times vary based on:
- System performance
- Ollama service latency
- Network conditions (if using cloud providers)
- Vector database size

## Next Steps

After successful testing:

1. **Run Automated Tests:**
   ```bash
   pytest tests/test_auto_indexing.py -v
   pytest tests/test_file_watcher.py -v
   ```

2. **Integrate with CI/CD:**
   Add to your test pipeline:
   ```bash
   python tests/manual_test_auto_indexing.py
   ```

3. **Monitor in Production:**
   ```bash
   from mcp_bridge.tools.semantic_search import start_file_watcher
   
   watcher = start_file_watcher("/path/to/project")
   # Watcher runs in background, reindexing on file changes
   ```

## Support

For issues or questions:
1. Check this guide's Troubleshooting section
2. Review test output and logs
3. Check the mcp_bridge/tools/semantic_search.py source
4. File an issue with test output and logs

---

**Last Updated:** 2025-01-07
**Test Version:** 1.0
**Tested On:** Python 3.10+, macOS/Linux, Ollama 0.1+
