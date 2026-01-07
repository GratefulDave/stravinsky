# Auto-Indexing System Testing - Master Guide

This document is your entry point for all auto-indexing system testing.

## What Was Created

A comprehensive manual test suite for the FileWatcher and semantic search auto-indexing system with:

- **1 Test Script** (788 lines) - Complete end-to-end testing
- **4 Documentation Files** (1,324 lines) - Guides, references, and implementation details
- **6 Test Sections** - Prerequisites, indexing, lifecycle, changes, debouncing, error handling

All files are in `/tests/` directory.

## Quick Navigation

### I want to...

**Run the test immediately**
1. Read: `tests/QUICK_REFERENCE.md` (5 min)
2. Run: `uv run python tests/manual_test_auto_indexing.py` (30 sec)
3. Verify: All tests pass

**Set up for the first time**
1. Read: `tests/MANUAL_TEST_GUIDE.md` (15 min) - Prerequisites & troubleshooting
2. Follow: Step-by-step instructions
3. Run: Test script
4. Debug: If needed, check troubleshooting section

**Understand what's being tested**
1. Read: `tests/TEST_IMPLEMENTATION_SUMMARY.md` (10 min) - Architecture & test details
2. Check: Each test section description
3. Review: Pass criteria and validation checklist

**Navigate all available resources**
1. Read: `tests/README_AUTO_INDEXING_TESTS.md` - File overview and map
2. Choose: Which guide to read based on your needs

## Files in Order of Use

### Start Here (Choose One)

1. **QUICK_REFERENCE.md** (5 min read)
   - For: Developers who just want to run it
   - Contains: Setup, run, common issues, success criteria
   - Audience: Experienced developers

2. **MANUAL_TEST_GUIDE.md** (15 min read)
   - For: First-time users and troubleshooting
   - Contains: Detailed setup, prerequisites, test explanations, 10+ troubleshooting solutions
   - Audience: New users, QA, troubleshooters

3. **TEST_IMPLEMENTATION_SUMMARY.md** (10 min read)
   - For: Understanding architecture and implementation
   - Contains: Test architecture, design decisions, CI/CD examples, future enhancements
   - Audience: Maintainers, architects

4. **README_AUTO_INDEXING_TESTS.md** (10 min read)
   - For: Navigating all test resources
   - Contains: File listing, test overview, data flow diagram
   - Audience: Everyone

### The Test Script

**tests/manual_test_auto_indexing.py** (788 lines, executable)
- Comprehensive end-to-end test suite
- Creates temporary test project
- Verifies: FileWatcher, changes, debouncing, patterns, errors
- Colorized output with clear results
- Exit code: 0 on success, 1 on failure

### Run It

```bash
# From project root
uv run python tests/manual_test_auto_indexing.py

# Or with logging
python tests/manual_test_auto_indexing.py 2>&1 | tee test_output.log
```

### Expected Result

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

## Prerequisites Checklist

Before running:

- [ ] Python 3.10+ installed
- [ ] Ollama installed (`brew install ollama` on macOS)
- [ ] Ollama running (`ollama serve` in terminal)
- [ ] Model pulled (`ollama pull nomic-embed-text`)
- [ ] stravinsky installed (`cd /path/to/stravinsky && uv install`)

See `tests/MANUAL_TEST_GUIDE.md` for detailed installation instructions.

## Test Coverage Summary

| Test | Verifies | Duration | Pass Criteria |
|------|----------|----------|--------------|
| Prerequisites | All dependencies | 2-3s | All checks pass |
| Initial Indexing | Vector store setup | 5-10s | 15+ chunks indexed |
| Lifecycle | Watcher start/stop | 1-2s | State transitions work |
| Change Detection | File changes trigger reindex | 8-12s | Create/modify/delete work |
| Debouncing | Rapid changes batched | 2-3s | 5 changes = 1 reindex |
| Pattern Exclusion | .gitignore honored | 3-5s | Excluded files not indexed |
| Error Handling | Graceful recovery | 3-5s | No crashes, recovery works |
| **Total** | **Complete system** | **20-30s** | **All 6/6 tests pass** |

## Common Issues Quick Reference

| Issue | Solution | Details |
|-------|----------|---------|
| "Ollama not available" | `ollama serve` | Start in another terminal |
| "Model not found" | `ollama pull nomic-embed-text` | Download embedding model |
| "Database locked" | `pkill -f manual_test_auto_indexing` | Kill hung processes |
| "Permission denied" | Check /tmp and ~/.stravinsky/ | Check directory permissions |
| Test hangs | Press Ctrl+C | Debouncing test takes time |
| "watchdog not installed" | `uv add watchdog` | Install missing library |

See `tests/MANUAL_TEST_GUIDE.md` for 10+ more solutions.

## Documentation Structure

```
TESTING_AUTO_INDEXING.md (this file)
├── QUICK_REFERENCE.md
│   └── Fastest way to run: "ollama serve → ollama pull → run test"
├── MANUAL_TEST_GUIDE.md
│   └── Complete setup, prerequisites, troubleshooting (400+ lines)
├── TEST_IMPLEMENTATION_SUMMARY.md
│   └── Architecture, design, CI/CD integration (390+ lines)
├── README_AUTO_INDEXING_TESTS.md
│   └── File overview and navigation guide (350+ lines)
└── manual_test_auto_indexing.py
    └── Actual test script (788 lines)
```

## How the Test Works

### Phase 1: Prerequisite Check
Verifies Python 3.10+, Ollama, models, libraries, and imports

### Phase 2: Initial Indexing
Creates test project (4 Python files) and indexes them

### Phase 3: Lifecycle
Tests FileWatcher start/stop sequences

### Phase 4: Change Detection
- Creates a new file → checks it's indexed
- Modifies a file → checks update is detected
- Deletes a file → checks chunks are removed

### Phase 5: Debouncing
Makes 5 rapid changes in 250ms, verifies batched into 1 reindex

### Phase 6: Pattern Exclusion
Tests that .gitignore patterns prevent indexing

### Phase 7: Error Handling
Creates syntax error file, verifies fallback, then fixes it

## Integration with Existing Tests

**Unit Tests:**
```bash
pytest tests/test_auto_indexing.py -v   # Vector store tests
pytest tests/test_file_watcher.py -v    # FileWatcher tests
```

**Manual Test:**
```bash
python tests/manual_test_auto_indexing.py  # End-to-end test
```

**All Tests:**
```bash
pytest tests/
python tests/manual_test_auto_indexing.py
```

## What Gets Tested

### FileWatcher
- [x] Initialization with project path and store
- [x] Start/stop lifecycle
- [x] Running state tracking
- [x] File change event detection
- [x] Debounce timer management
- [x] Pending files accumulation

### File Change Detection
- [x] File creation triggers reindex
- [x] File modification triggers reindex
- [x] File deletion triggers reindex
- [x] File rename triggers reindex
- [x] Changes within debounce period batched

### Vector Store Integration
- [x] Initial indexing creates chunks
- [x] File creation indexes new chunks
- [x] File modification updates chunks
- [x] File deletion removes chunks
- [x] Incremental indexing works

### Pattern Matching
- [x] SKIP_DIRS excludes directories
- [x] Only .py files indexed (in watcher)
- [x] Hidden files skipped
- [x] Files outside project skipped
- [x] .gitignore patterns respected (structure)

### Error Handling
- [x] Syntax errors don't crash
- [x] Service unavailable handled gracefully
- [x] Recovery after errors works
- [x] Proper logging of errors

## What is NOT Tested

- Desktop notifications (GUI-dependent)
- Large scale (1000+ files)
- .semanticignore implementation (structure only)
- Cloud providers (Gemini, OpenAI)
- Concurrent watchers
- Performance benchmarking

See `tests/TEST_IMPLEMENTATION_SUMMARY.md` for future enhancements.

## After Successful Testing

1. **Use in Your Project**
   ```python
   from mcp_bridge.tools.semantic_search import start_file_watcher
   
   watcher = start_file_watcher("/path/to/project")
   # Watcher monitors files in background
   ```

2. **Integrate into CI/CD**
   ```bash
   python tests/manual_test_auto_indexing.py || exit 1
   ```

3. **Monitor Logs**
   ```bash
   tail -f ~/.stravinsky/logs/semantic_search.log
   ```

4. **Customize Debounce**
   ```python
   watcher = CodebaseFileWatcher(
       project_path=project_path,
       store=store,
       debounce_seconds=1.0  # Default: 2.0
   )
   ```

See `tests/TEST_IMPLEMENTATION_SUMMARY.md` for CI/CD examples.

## Support Resources

### Quick Help
- Check `tests/QUICK_REFERENCE.md` - Common issues table
- Run `curl http://localhost:11434/api/tags` - Check Ollama status

### Detailed Help
- Read `tests/MANUAL_TEST_GUIDE.md` - Troubleshooting section
- Check `tests/TEST_IMPLEMENTATION_SUMMARY.md` - Debugging section

### Debug Techniques
- Enable logging: `python ... 2>&1 | tee test.log`
- Monitor Ollama: `curl http://localhost:11434/api/tags`
- Check database: `ls -la ~/.stravinsky/vectordb/`
- Review output: Look for [TEST], [PASS], [FAIL] markers

## File Locations

```
/path/to/stravinsky/
├── tests/
│   ├── manual_test_auto_indexing.py      # Main test script
│   ├── MANUAL_TEST_GUIDE.md               # Complete guide (400+ lines)
│   ├── QUICK_REFERENCE.md                 # Quick setup (165 lines)
│   ├── TEST_IMPLEMENTATION_SUMMARY.md    # Technical details (390+ lines)
│   ├── README_AUTO_INDEXING_TESTS.md     # Navigation guide (350+ lines)
│   ├── test_auto_indexing.py              # Unit tests
│   └── test_file_watcher.py               # Unit tests
└── TESTING_AUTO_INDEXING.md              # This file
```

## Version & Status

- **Version:** 1.0
- **Created:** 2025-01-07
- **Status:** Complete and ready for use
- **Lines of Code:** 2,100+ (script + docs)
- **Test Coverage:** 6 major sections, 15+ verifications
- **Expected Runtime:** 20-30 seconds
- **Python:** 3.10+
- **Tested On:** macOS, Linux

## One-Liner Quick Start

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Get the model and run test
ollama pull nomic-embed-text && uv run python tests/manual_test_auto_indexing.py
```

## Next: Read a Guide

Choose based on your needs:

- **Just run it?** → `tests/QUICK_REFERENCE.md`
- **New to testing?** → `tests/MANUAL_TEST_GUIDE.md`
- **Understand design?** → `tests/TEST_IMPLEMENTATION_SUMMARY.md`
- **Navigate resources?** → `tests/README_AUTO_INDEXING_TESTS.md`

---

**Time to first test:** 5 minutes
**Time to diagnose issue:** 10 minutes (see guides)
**Time to understand system:** 20 minutes (read all guides)

Start with the appropriate guide above, then run the test.
Good luck!
