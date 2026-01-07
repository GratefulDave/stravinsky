# Auto-Indexing System Test Suite

This directory contains comprehensive testing for the automatic file indexing system, including the FileWatcher and semantic search integration.

## Files in This Test Suite

### Test Implementation

**`manual_test_auto_indexing.py`** (1,100+ lines)
- Comprehensive manual test script for the auto-indexing system
- Tests FileWatcher lifecycle, change detection, debouncing, and error handling
- Creates temporary test project and verifies all functionality
- Colorized terminal output with clear pass/fail indicators
- Exit code 0 on success, 1 on failure
- Ready to run: `uv run python tests/manual_test_auto_indexing.py`

### Documentation

**`MANUAL_TEST_GUIDE.md`** (400+ lines)
- Complete guide for running manual tests
- Prerequisite setup instructions (Ollama, Python 3.10+)
- Step-by-step test execution guide
- Expected output examples
- Detailed explanation of each test section
- Comprehensive troubleshooting guide with 10+ solutions
- Debugging techniques and monitoring commands
- Expected timing and performance statistics
- Integration instructions for CI/CD

**`QUICK_REFERENCE.md`**
- One-minute quick setup guide
- Summary table of all tests
- Common issues and quick solutions
- File locations reference
- Debug commands
- Success criteria checklist
- Typical output example
- Expected timing

**`TEST_IMPLEMENTATION_SUMMARY.md`** (500+ lines)
- Implementation overview and architecture
- Detailed description of each test
- Test architecture and class structure
- Integration with CI/CD examples
- Current limitations and future enhancements
- Validation checklist
- Support and debugging reference

**`README_AUTO_INDEXING_TESTS.md`** (this file)
- File listing and descriptions
- How to choose which documentation to read
- Quick navigation guide

### Existing Unit Tests

**`test_auto_indexing.py`**
- Unit tests for CodebaseVectorStore indexing functionality
- Tests chunking, file pattern matching, deletion detection
- Tests error recovery and search functionality
- Run with: `pytest tests/test_auto_indexing.py -v`

**`test_file_watcher.py`**
- Unit tests for CodebaseFileWatcher class
- Tests lifecycle, file filtering, debouncing
- Tests module-level watcher management
- Run with: `pytest tests/test_file_watcher.py -v`

## Quick Start

### For the Impatient

```bash
# 1. Start Ollama in terminal 1
ollama serve

# 2. In terminal 2, pull the model
ollama pull nomic-embed-text

# 3. Run the test
cd /path/to/stravinsky
uv run python tests/manual_test_auto_indexing.py
```

See `QUICK_REFERENCE.md` for more.

### For Detailed Setup

Read `MANUAL_TEST_GUIDE.md` for:
- Complete prerequisite installation
- Troubleshooting specific errors
- Debugging techniques
- Post-test analysis

### For Understanding the Implementation

Read `TEST_IMPLEMENTATION_SUMMARY.md` for:
- What each test does and why
- Architecture and design decisions
- Integration examples
- Future enhancement ideas

## Test Coverage

The manual test script verifies:

1. **Prerequisite Check** - All dependencies installed and services running
2. **Initial Indexing** - Vector store correctly indexes files (15+ chunks)
3. **FileWatcher Lifecycle** - Proper start/stop behavior
4. **File Change Detection** - Create/modify/delete trigger reindexing
5. **Debouncing** - Rapid changes batched into single reindex
6. **Pattern Exclusion** - .gitignore patterns honored
7. **Error Handling** - Graceful recovery from syntax errors

See `TEST_IMPLEMENTATION_SUMMARY.md` for detailed pass criteria for each test.

## Expected Output

Successful test run:
```
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

Expected runtime: 20-30 seconds

## File Locations

| File | Purpose | Audience |
|------|---------|----------|
| `manual_test_auto_indexing.py` | Main test script | Everyone |
| `QUICK_REFERENCE.md` | Fast setup guide | Impatient developers |
| `MANUAL_TEST_GUIDE.md` | Complete guide | First-time users |
| `TEST_IMPLEMENTATION_SUMMARY.md` | Technical details | Maintainers |
| `test_auto_indexing.py` | Unit tests | CI/CD, automation |
| `test_file_watcher.py` | Unit tests | CI/CD, automation |

## Common Issues

### "Ollama not available"
Solution: Start Ollama with `ollama serve` in another terminal

### "Model not found"
Solution: Run `ollama pull nomic-embed-text`

### "Database locked"
Solution: `pkill -f manual_test_auto_indexing`

### "Permission denied"
Solution: Check write access to /tmp and ~/.stravinsky/

See `MANUAL_TEST_GUIDE.md` Troubleshooting section for 10+ more solutions.

## Running Tests

### Manual Test (Comprehensive)
```bash
uv run python tests/manual_test_auto_indexing.py
```
- Full end-to-end testing
- Verifies all functionality
- Creates temporary project
- ~20-30 seconds runtime

### Unit Tests (Fast)
```bash
pytest tests/test_auto_indexing.py -v
pytest tests/test_file_watcher.py -v
```
- Fast unit-level tests
- No temporary files created
- ~5 seconds runtime
- Can run without Ollama

### All Tests
```bash
pytest tests/
python tests/manual_test_auto_indexing.py
```

## Next Steps

After successful testing:

1. **Integration** - Use FileWatcher in your project:
   ```python
   from mcp_bridge.tools.semantic_search import start_file_watcher
   
   watcher = start_file_watcher("/path/to/project")
   # Watcher runs in background, reindexing on changes
   ```

2. **Automation** - Add to CI/CD pipeline (see `TEST_IMPLEMENTATION_SUMMARY.md`)

3. **Monitoring** - Check logs for warnings:
   ```bash
   tail -f ~/.stravinsky/logs/semantic_search.log
   ```

4. **Customization** - Adjust debounce period (default: 2.0s):
   ```python
   watcher = CodebaseFileWatcher(
       project_path="/path/to/project",
       store=store,
       debounce_seconds=1.0  # Shorter for faster feedback
   )
   ```

## Architecture Overview

### Components Tested

- **CodebaseVectorStore** - Persistent vector database for code
- **CodebaseFileWatcher** - File system monitoring and debouncing
- **OllamaProvider** - Local embedding service integration
- **_FileChangeHandler** - Watchdog event processing

### Data Flow

```
File changes (create/modify/delete)
        ↓
watchdog observes events
        ↓
_FileChangeHandler filters Python files
        ↓
CodebaseFileWatcher._on_file_changed()
        ↓
Accumulate in _pending_files
        ↓
Debounce timer (2s default)
        ↓
_trigger_reindex()
        ↓
CodebaseVectorStore.index_codebase()
        ↓
OllamaProvider.get_embedding()
        ↓
ChromaDB stores vectors
```

See `TEST_IMPLEMENTATION_SUMMARY.md` for architecture diagrams and details.

## Documentation Map

- **Just want to run it?** → Start with `QUICK_REFERENCE.md`
- **New to testing?** → Read `MANUAL_TEST_GUIDE.md`
- **Understanding design?** → Check `TEST_IMPLEMENTATION_SUMMARY.md`
- **Running tests?** → This file

## Support and Help

### Quick Problems
1. Check `QUICK_REFERENCE.md` common issues table
2. Check `MANUAL_TEST_GUIDE.md` troubleshooting section

### Deep Issues
1. Enable debug logging (see `MANUAL_TEST_GUIDE.md`)
2. Check Ollama status with `curl http://localhost:11434/api/tags`
3. Review test output and logs
4. Check `TEST_IMPLEMENTATION_SUMMARY.md` debugging section

### Still Need Help?
1. Check inline comments in `manual_test_auto_indexing.py`
2. Read source: `mcp_bridge/tools/semantic_search.py`
3. Review existing unit tests: `test_auto_indexing.py`, `test_file_watcher.py`

## Testing on Different Platforms

### macOS
- Prerequisites: Ollama via `brew install ollama`
- FileWatcher: Supported via watchdog
- Shell: Use bash or zsh
- All tests pass

### Linux
- Prerequisites: Install Ollama from website
- FileWatcher: Supported via inotify
- Shell: Use bash, zsh, or fish
- All tests pass

### Windows
- Prerequisites: Install Ollama from website
- FileWatcher: Supported via watchdog
- Shell: Use PowerShell or cmd
- Note: Path separators may differ

## Performance Baseline

Typical run on modern hardware:

| Test | Time | Notes |
|------|------|-------|
| Prerequisites | 2-3s | Network call to Ollama |
| Initial Index | 5-10s | Embedding 4 files |
| Lifecycle | 1-2s | State transitions |
| Change Detection | 8-12s | 3 changes + reindex |
| Debouncing | 2-3s | Timer waits |
| Pattern Exclude | 3-5s | File checks |
| Error Handling | 3-5s | Recovery index |
| **Total** | **20-30s** | Variable |

## Version Information

- **Test Version:** 1.0
- **Created:** 2025-01-07
- **Status:** Complete and ready for use
- **Python:** 3.10+
- **Ollama:** 0.1+
- **Tested On:** macOS, Linux

## Checklist for Success

Before considering tests complete:

```
Prerequisite Check:
  [ ] Python 3.10+ available
  [ ] Ollama running and accessible
  [ ] nomic-embed-text model installed
  [ ] watchdog library installed
  [ ] All imports successful

Test Execution:
  [ ] Initial indexing succeeds (15+ chunks)
  [ ] FileWatcher lifecycle works
  [ ] File changes detected and reindexed
  [ ] Debouncing batches changes
  [ ] Pattern exclusion works
  [ ] Error recovery succeeds

Results:
  [ ] Exit code 0 (success)
  [ ] All 6 tests passed
  [ ] No leftover temp files
  [ ] No leftover processes
```

---

**For questions or issues:** See the relevant guide above or check `TEST_IMPLEMENTATION_SUMMARY.md`
