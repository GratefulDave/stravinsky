# Stravinsky Test Suite

## File Watcher No-Index Test

### Purpose
Verify that `start_file_watcher()` raises a `ValueError` when called without first running `semantic_index()`.

This prevents the silent failure bug where users would start the file watcher but it wouldn't work because no index existed.

### Quick Run

```bash
# From project root
uv run python tests/test_file_watcher_no_index.py
```

### Current Status

**BLOCKED:** The `mcp_bridge.tools.semantic_search` module does not exist yet.

### When It Works

The test will verify:

1. **ValueError on missing index**
   - Calling `start_file_watcher()` without index raises `ValueError`
   - Error message is clear and actionable
   - Contains keywords: "semantic_index", "must", "first"

2. **Success with index**
   - `semantic_index()` creates index successfully
   - `start_file_watcher()` works after indexing
   - Watcher can be stopped cleanly

3. **Error message quality**
   - Message mentions `semantic_index()`
   - Indicates it's required
   - Provides solution
   - Is clear and concise

### Prerequisites

All verified and working:
- Python 3.11+
- Ollama with nomic-embed-text model
- chromadb library
- watchdog library

### Test Output

Expected: All tests pass in 30 seconds
- 3 temporary test projects created and cleaned up
- Clear pass/fail indicators
- Exit code 0 on success, 1 on failure

### Files

- `test_file_watcher_no_index.py` - Main test suite (505 lines)
- `README.md` - This file
- `../TEST_EXECUTION_REPORT.md` - Detailed investigation
- `../TESTING_SUMMARY_FINAL.md` - Complete summary

### The Fix

The semantic_search.py module needs this check:

```python
def start_file_watcher(project_path: str, ...):
    if not _index_exists(project_path):
        raise ValueError(
            f"No semantic index found for '{project_path}'. "
            f"You must run semantic_index('{project_path}') before starting the file watcher."
        )
    # ... rest of implementation
```

### Next Steps

1. Locate or create `mcp_bridge/tools/semantic_search.py`
2. Implement the ValueError check in `start_file_watcher()`
3. Run this test to verify the fix
4. Update README.md if needed (currently says "warning" instead of "ValueError")

### Questions?

See:
- `../TEST_EXECUTION_REPORT.md` - Why test can't run currently
- `../TESTING_SUMMARY_FINAL.md` - Complete overview
- Test file itself - Inline documentation
