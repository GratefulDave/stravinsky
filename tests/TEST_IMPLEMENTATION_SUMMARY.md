# Auto-Indexing System Manual Test - Implementation Summary

## Overview

A comprehensive manual test script has been created to verify the auto-indexing system functionality. The test validates all critical components of the FileWatcher and semantic search integration.

## Files Created

### 1. Test Script
**Location:** `tests/manual_test_auto_indexing.py` (1,100+ lines)

**Description:** Comprehensive test suite with 6 major test sections:
- Prerequisite checking
- Vector store initialization
- File watcher lifecycle
- File change detection
- Debouncing verification
- Error handling and recovery

**Features:**
- Colorized terminal output for clear test status
- Temporary project creation and cleanup
- Async/await integration with vector store
- Detailed logging and error messages
- Graceful failure handling

### 2. Comprehensive Guide
**Location:** `tests/MANUAL_TEST_GUIDE.md` (400+ lines)

**Contains:**
- Prerequisites and installation instructions
- Step-by-step running instructions
- Expected output examples
- Detailed explanation of each test section
- Interpretation guide for results
- Extensive troubleshooting section
- Debugging techniques
- Expected timing and statistics

### 3. Quick Reference
**Location:** `tests/QUICK_REFERENCE.md`

**Contains:**
- One-minute setup instructions
- Quick test summary table
- Common issues and solutions
- File locations
- Debug commands
- Success criteria
- Typical output example

## Test Coverage

### Test 1: Prerequisite Check
**Validates:** All dependencies are installed and services are running

**Checks:**
- Python 3.10+
- Ollama service availability
- nomic-embed-text model installed
- watchdog library
- ChromaDB
- filelock
- stravinsky imports

**Failure Mode:** Test exits early with installation instructions

### Test 2: Initial Indexing
**Validates:** Vector store correctly indexes initial project files

**Setup:**
- Creates 4 Python files (main.py, utils.py, config.py, src/lib.py)
- Initializes CodebaseVectorStore with ollama provider
- Runs initial indexing

**Pass Criteria:**
- Indexes 15+ chunks from 4 files
- No errors from embedding service

### Test 3: FileWatcher Lifecycle
**Validates:** FileWatcher can start and stop properly

**Sequence:**
1. Verify initial state (not running)
2. Start watcher
3. Verify running state
4. Stop watcher
5. Verify stopped state

**Pass Criteria:**
- All state transitions succeed
- is_running() returns correct values

### Test 4: File Change Detection
**Validates:** File changes trigger reindexing correctly

**Tests:**
1. **File Creation**
   - Create new_module.py
   - Verify reindexing detects it
   - Expect 3+ new chunks

2. **File Modification**
   - Modify utils.py with changes
   - Verify reindexing updates it
   - Expect 4+ chunks updated

3. **File Deletion**
   - Delete config.py
   - Verify reindexing removes chunks
   - Expect 2+ chunks pruned

**Pass Criteria:**
- All changes detected within debounce period
- Correct chunk counts modified

### Test 5: Debouncing
**Validates:** Rapid changes are batched together efficiently

**Sequence:**
1. Create watcher with 0.3s debounce
2. Make 5 rapid file modifications (50ms apart)
3. Verify accumulated in _pending_files
4. Wait for debounce to expire
5. Verify single reindex triggered

**Pass Criteria:**
- All 5 changes present in pending_files
- Timer reset after each change
- Single reindex call (not 5)

### Test 6: Pattern Exclusion
**Validates:** .gitignore and SKIP_DUW patterns are respected

**Setup:**
- Create .gitignore with patterns
- Create excluded files (.log, build/*)
- Create included files

**Pass Criteria:**
- Excluded patterns not indexed
- Included files indexed correctly

### Test 7: Error Handling
**Validates:** Graceful recovery from errors

**Tests:**
1. Create Python file with syntax errors
2. Attempt indexing (should fallback to line-based)
3. Fix syntax errors
4. Re-index successfully

**Pass Criteria:**
- No crash on syntax errors
- Recovery successful
- Re-indexing completes

## Test Architecture

### Class Structure

```
TestProject
├── setup() - Create temp directory
├── _create_initial_files() - Setup test files
├── create_file() - Add new file
├── modify_file() - Update existing file
├── delete_file() - Remove file
├── create_gitignore() - Add patterns
└── cleanup() - Remove temp directory

TestResults
├── add() - Track test result
└── print_summary() - Display results
```

### Async Integration

Tests use asyncio for:
- Initializing vector store
- Running reindex operations
- Waiting for debounce periods
- Parallel testing capabilities

### Error Handling

- Try/catch blocks around critical operations
- Graceful failure with informative messages
- Cleanup in finally blocks
- Exception logging and tracing

## Running the Test

### Minimum Setup

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Install model
ollama pull nomic-embed-text

# Terminal 3: Run test
cd /path/to/stravinsky
uv run python tests/manual_test_auto_indexing.py
```

### Full Command

```bash
# With logging to file
python tests/manual_test_auto_indexing.py 2>&1 | tee test_output.log
```

## Expected Results

### Success Output
```
Results:
  Passed: 6/6
  Failed: 0/6

All tests passed!
```

Exit Code: 0

### Partial Failure Output
```
Results:
  Passed: 5/6
  Failed: 1/6

[FAIL] Test 4: Debouncing
  Details: Timer may still be pending
```

Exit Code: 1

## Test Timing

| Section | Duration | Notes |
|---------|----------|-------|
| Prerequisite Check | 2-3s | Ollama call latency |
| Initial Indexing | 5-10s | Embedding generation |
| Lifecycle Test | 1-2s | State transitions |
| Change Detection | 8-12s | Debounce waits |
| Debouncing Test | 2-3s | Timer waits |
| Pattern Exclusion | 3-5s | File system operations |
| Error Handling | 3-5s | Reindex attempts |
| **Total** | **20-30s** | System dependent |

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run auto-indexing tests
  run: |
    ollama serve &
    sleep 2
    ollama pull nomic-embed-text
    python tests/manual_test_auto_indexing.py
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
python tests/manual_test_auto_indexing.py || exit 1
```

## Limitations and Notes

### What the Test Does NOT Check

1. **Desktop Notifications** - Requires system GUI; skipped in CI
2. **Large Scale** - Tests with ~10 files; doesn't scale to 1000s
3. **Performance** - No benchmarking or timing comparisons
4. **.semanticignore** - Structure created but not validated
5. **Cloud Providers** - Only tests Ollama; not Gemini/OpenAI
6. **Concurrent Watchers** - Single project watching only

### System Requirements

- Python 3.10+ (uses match statements, asyncio features)
- Write access to /tmp and ~/.stravinsky/
- Ollama running on localhost:11434
- Network access to Ollama API (internal)
- File system that supports watchdog (all modern systems)

### Temporary Files

Test creates:
- Temp directory in /tmp
- Vector database in ~/.stravinsky/vectordb/
- Lock files during execution

All cleaned up on success or error.

## Future Enhancements

Potential improvements to the test:

1. **Performance Benchmarking**
   - Track indexing speed
   - Measure debounce accuracy
   - Monitor memory usage

2. **Extended Testing**
   - Large codebases (1000+ files)
   - Multiple concurrent projects
   - Cloud provider integration

3. **Desktop Notifications**
   - Test notification delivery
   - Verify sound/visual alerts
   - Check notification persistence

4. **.semanticignore**
   - Implement pattern reading
   - Verify exclusion logic
   - Test override behaviors

5. **CI/CD Integration**
   - GitHub Actions template
   - GitLab CI/CD example
   - Jenkins integration guide

6. **Stress Testing**
   - Rapid file creation storms
   - Very large files (100MB+)
   - Deep directory structures

## References

### Source Files

- `mcp_bridge/tools/semantic_search.py` - CodebaseFileWatcher, CodebaseVectorStore
- `tests/test_file_watcher.py` - Unit tests for file watcher
- `tests/test_auto_indexing.py` - Unit tests for auto-indexing

### Documentation

- `MANUAL_TEST_GUIDE.md` - Complete guide with troubleshooting
- `QUICK_REFERENCE.md` - Quick setup and reference
- `mcp_bridge/tools/semantic_search.py` - Inline documentation

## Support and Debugging

### Enable Debug Logging

```bash
export PYTHONPATH=/path/to/stravinsky:$PYTHONPATH
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
exec(open('tests/manual_test_auto_indexing.py').read())
"
```

### Common Failure Points

1. **Ollama Connection** - Check `curl http://localhost:11434/api/tags`
2. **Model Missing** - Run `ollama pull nomic-embed-text`
3. **Database Locked** - Kill existing processes: `pkill -f manual_test`
4. **Permissions** - Check /tmp and ~/.stravinsky/ permissions
5. **Timeouts** - Increase debounce waits for slow systems

## Validation Checklist

Before considering tests complete:

- [ ] All prerequisites check pass
- [ ] Initial indexing succeeds (15+ chunks)
- [ ] FileWatcher lifecycle works (start/stop)
- [ ] File changes detected (create/modify/delete)
- [ ] Debouncing batches changes properly
- [ ] Pattern exclusion honored
- [ ] Error recovery works
- [ ] Exit code 0 on success
- [ ] No leftover temp files
- [ ] No leftover processes

---

**Version:** 1.0
**Created:** 2025-01-07
**Status:** Complete and ready for use
**Test Coverage:** 6 major test sections, 15+ individual verifications
