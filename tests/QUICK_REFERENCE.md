# Auto-Indexing Manual Test - Quick Reference

## One-Minute Setup

```bash
# 1. Start Ollama in one terminal
ollama serve

# 2. In another terminal, pull the embedding model
ollama pull nomic-embed-text

# 3. Run the test
cd /path/to/stravinsky
uv run python tests/manual_test_auto_indexing.py
```

## What the Test Does

Creates a temporary project and verifies:

| Test | What It Checks | Pass Criteria |
|------|---|---|
| **Initial Indexing** | Baseline indexing works | 15+ chunks indexed |
| **Lifecycle** | Watcher starts/stops | All state transitions work |
| **Change Detection** | File create/modify/delete trigger reindex | Changes detected within 2s |
| **Debouncing** | Rapid changes are batched | 5 changes = 1 reindex (not 5) |
| **Pattern Exclusion** | .gitignore patterns honored | Excluded files not indexed |
| **Error Handling** | Syntax errors don't crash | Recovery successful |

## Expected Output Format

```
[TEST]  - About to test something
[PASS]  - Test passed
[FAIL]  - Test failed
[INFO]  - Informational message
[WARN]  - Warning (may still pass)
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Ollama not available" | Run `ollama serve` |
| "Model not found" | Run `ollama pull nomic-embed-text` |
| "Database locked" | `pkill -f manual_test_auto_indexing` |
| Test hangs | Press Ctrl+C, check prerequisites |
| "Permission denied" | Check /tmp write permissions |

## File Locations

**Test Script:**
```
tests/manual_test_auto_indexing.py
```

**Test Guide:**
```
tests/MANUAL_TEST_GUIDE.md
```

**Vector Store DB (after test):**
```
~/.stravinsky/vectordb/<hash>_ollama/
```

## Success Criteria

```
Results:
  Passed: 6/6
  Failed: 0/6

All tests passed!
```

## Debug Commands

```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# List available models
ollama list

# Check test database
ls -la ~/.stravinsky/vectordb/

# Tail logs while running test
python tests/manual_test_auto_indexing.py 2>&1 | tee test.log
```

## Expected Timing

- Total runtime: **20-30 seconds**
- Debouncing test: 2-3s (includes timer waits)
- File change detection: 8-12s (includes debounce waits)
- Initial indexing: 5-10s (depends on embedding service)

## Typical Success Run

```
=====================================================================
                   CHECKING PREREQUISITES
=====================================================================

[TEST] Python version >= 3.10
[PASS] Python 3.11

[TEST] Ollama service availability  
[PASS] Ollama running with nomic-embed-text model

[TEST] watchdog library for file monitoring
[PASS] watchdog 3.0.0 installed

...

=====================================================================
                   TEST 1: INITIAL INDEXING
=====================================================================

[TEST] Indexing initial project files
[PASS] Indexed 18 chunks from 4 file(s)

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

## Full Documentation

See `MANUAL_TEST_GUIDE.md` for:
- Detailed setup instructions
- Test section explanations
- Troubleshooting guide
- Debugging techniques
- Next steps after testing

---

**Quick Tip:** Start Ollama before running the test. The test checks for it in prerequisites but can't start it for you.
