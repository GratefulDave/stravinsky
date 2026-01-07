# Auto-Indexing Test Plan - Complete Artifacts

## Overview

This directory contains comprehensive test artifacts for auto-indexing functionality in the semantic search system. These tests validate that the vector database automatically updates when code changes are detected.

## Files Created

### 1. Main Test Plan (500 lines)
**File**: `/Users/davidandrews/PycharmProjects/stravinsky/TEST_PLAN_AUTO_INDEXING.md`

Comprehensive test planning document covering:
- 6 test scenario categories with 15+ specific scenarios
- Unit vs integration testing approaches
- Mocking strategies for isolated testing
- Performance benchmarks and expectations
- Manual testing procedures with bash examples
- Error handling and edge cases
- Debugging techniques
- Known limitations and future enhancements

**Key Sections**:
1. Test Scenarios (File creation, modification, deletion, debouncing, errors)
2. Test Implementation Approach (Unit/integration/mocking)
3. Manual Testing Steps (with bash examples)
4. Performance Benchmarks (expected timings)
5. Expected Behaviors and Outputs
6. Test Checklist
7. Debugging Guide
8. Known Issues & Limitations
9. Future Enhancements

### 2. Pytest Test Suite (567 lines)
**File**: `/Users/davidandrews/PycharmProjects/stravinsky/tests/test_auto_indexing.py`

Complete pytest-asyncio implementation with 24 test cases organized into:

**Fixtures** (3):
- `temp_project_dir`: Temporary test project directory
- `mock_provider`: Mock embedding provider (returns dummy vectors)
- `vector_store`: Pre-configured vector store with mock provider

**Unit Tests** (10):
- Chunking: simple files, classes, methods, syntax error fallback
- Change detection: new chunks, modified chunks, hash stability
- Pattern matching: directory exclusion, file extensions

**Integration Tests** (10):
- Indexing: single/multiple files, incremental, force reindex
- Deletion: file and directory removal
- Error recovery: service unavailability, retry logic
- Search: finding indexed content, empty index

**Stress Tests** (2):
- 50 small files
- 100+ function definitions in large file

**Stats Tests** (2):
- Statistics reporting
- Provider factory pattern

**Running Tests**:
```bash
# All tests
pytest tests/test_auto_indexing.py -v

# Specific test
pytest tests/test_auto_indexing.py::test_chunk_simple_python_file -v

# With coverage
pytest tests/test_auto_indexing.py --cov=mcp_bridge.tools.semantic_search

# Quick tests only (skip stress tests)
pytest tests/test_auto_indexing.py -k "not stress" -v
```

### 3. Manual Testing Checklist (368 lines)
**File**: `/Users/davidandrews/PycharmProjects/stravinsky/MANUAL_TESTING_CHECKLIST.md`

11 detailed manual test scenarios with step-by-step procedures:

1. **Basic File Creation**: New files trigger indexing
2. **File Modification**: Code changes update index
3. **File Deletion**: Deleted files removed from index
4. **Debouncing**: Rapid changes are batched
5. **Mass Operations**: 50+ file changes don't hang system
6. **Search Accuracy**: Semantic search quality
7. **Error Handling**: Graceful degradation when service unavailable
8. **Statistics**: Stats accuracy and consistency
9. **Excluded Directories**: .venv/node_modules properly skipped
10. **Concurrent Access**: File lock prevents corruption
11. **Health Checks**: Status reporting accurate

Each test includes:
- Clear objective
- Step-by-step procedures
- Expected outputs
- Verification checkboxes
- Pass/fail criteria

**Estimated Time**: 10-20 minutes for full checklist

### 4. Test Summary (353 lines)
**File**: `/Users/davidandrews/PycharmProjects/stravinsky/AUTO_INDEXING_TEST_SUMMARY.md`

Executive summary covering:
- Overview of all test artifacts
- Test scenarios covered
- Implementation approach details
- Key testing concepts (debouncing, hashing, incremental indexing)
- Performance expectations with benchmarks
- Running the tests
- Verification checklist
- Coverage summary
- Next steps and future enhancements

## Quick Start

### Run Pytest Tests (Fast)

```bash
cd /Users/davidandrews/PycharmProjects/stravinsky

# Install test dependencies
uv sync

# Run all tests
uv run pytest tests/test_auto_indexing.py -v

# Run with coverage
uv run pytest tests/test_auto_indexing.py --cov=mcp_bridge.tools.semantic_search --cov-report=html
```

Expected: 24/24 tests pass in < 2 minutes

### Run Manual Tests (Comprehensive)

```bash
# 1. Set up test environment
ollama serve &  # Start Ollama
ollama pull nomic-embed-text  # Pull embedding model
mkdir -p /tmp/test_semantic_project

# 2. Follow MANUAL_TESTING_CHECKLIST.md
# Complete 11 test scenarios

# 3. Review results
# Update checklist with pass/fail status
```

Expected: All 11 tests pass in 15-20 minutes

## Test Coverage

### Scenarios Covered

File Operations:
- Create single/multiple files
- Create files in subdirectories
- Modify existing code
- Delete single/multiple files
- Change function signatures
- Add docstrings

Indexing Behavior:
- Incremental indexing (only new chunks)
- Content hash detection
- Chunk deduplication
- Force re-indexing
- Debounce timer validation
- Batch processing

Error Scenarios:
- Embedding service unavailable
- Vector DB lock timeout
- Interrupted indexing
- Syntax errors in code
- Service recovery

Advanced Features:
- Semantic search accuracy
- Large file handling (100+ functions)
- Excluded directory patterns (.venv, node_modules)
- File lock (concurrent access)
- Statistics and diagnostics

### Metrics

**Total Test Cases**: 35
- Unit tests: 10
- Integration tests: 10
- Manual tests: 11
- Stress tests: 2
- Stats tests: 2

**Performance Benchmarks**:
- Index 50-line file: < 1s
- Index 500-line file: < 2s
- Debounce delay: 2-3s
- 10 file creates: < 5s
- 50 file changes: < 10s

**Code Coverage**: Target > 80%
- semantic_search.py: Core functionality
- CodebaseVectorStore: Indexing logic
- Chunking: AST parsing and line-based fallback
- Provider pattern: Embedding abstraction

## Test Artifacts Breakdown

### By Purpose

**Design & Planning** (TEST_PLAN_AUTO_INDEXING.md):
- Defines what to test
- Specifies test approaches
- Documents expected behaviors
- Provides debugging guidance

**Implementation** (tests/test_auto_indexing.py):
- Automated tests for CI/CD
- Mock-based isolation
- Fast execution
- High coverage

**Manual Validation** (MANUAL_TESTING_CHECKLIST.md):
- Real-world scenarios
- User-observable behavior
- Performance characteristics
- Integration with Ollama

**Documentation** (AUTO_INDEXING_TEST_SUMMARY.md):
- Executive overview
- How to run tests
- Known limitations
- Future enhancements

### By Test Type

**Chunking Tests**:
- Simple Python files
- Classes and methods
- Syntax error handling
- Small file skipping

**Change Detection Tests**:
- New chunk detection
- Modified chunk detection
- Content hash stability
- File pattern matching

**Indexing Tests**:
- Single/multiple files
- Incremental updates
- Force reindexing
- Deletion handling

**Error Recovery Tests**:
- Service unavailability
- Retry logic
- Lock contention
- Data integrity

**Search Tests**:
- Finding indexed content
- Empty index handling
- Relevance scoring

**Stress Tests**:
- 50+ small files
- 100+ functions per file
- Deep directory nesting

## Key Testing Concepts

### Mocking Strategy

Tests use a MockEmbeddingProvider that:
- Returns deterministic vectors based on text length
- Doesn't require Ollama running
- Tracks all embedding calls
- Simulates provider unavailability

Benefits:
- Fast test execution (< 2 minutes)
- No external dependencies
- Repeatable results
- Easy to debug

### Content Hash Detection

Chunk IDs include MD5 hash of content:
- Format: `file_path:start_line-end_line:content_hash`
- Same content = same hash
- Changed content = different hash
- Detects changes at chunk level (not file mtime)

### Incremental Indexing

Mark-sweep algorithm:
1. Generate all chunks for current codebase
2. Identify new chunks (not in index)
3. Identify stale chunks (in index but not in codebase)
4. Add new chunks with embeddings
5. Delete stale chunks

Benefits:
- Only embeds changed content
- Scales with change size, not codebase size
- Prevents duplicate chunks

### Debouncing

File watcher events are debounced:
- Default window: 2-3 seconds
- Rapid changes batched into single indexing operation
- Prevents thrashing on massive file operations

## Running Tests in Different Environments

### CI/CD Pipeline

```bash
# Install dependencies
uv sync

# Run tests with coverage
uv run pytest tests/test_auto_indexing.py \
  --cov=mcp_bridge.tools.semantic_search \
  --cov-report=xml \
  --junit-xml=test-results.xml

# Check coverage threshold
uv run pytest tests/test_auto_indexing.py \
  --cov=mcp_bridge.tools.semantic_search \
  --cov-fail-under=80
```

### Local Development

```bash
# Run tests in watch mode
uv run pytest-watch tests/test_auto_indexing.py

# Run specific test with debugging
uv run pytest tests/test_auto_indexing.py::test_chunk_simple_python_file -vv -s

# Run with detailed output
uv run pytest tests/test_auto_indexing.py -vv --tb=long
```

### Manual Testing Environment

```bash
# Start Ollama
ollama serve &

# Pull model
ollama pull nomic-embed-text

# Run manual test checklist
# Follow MANUAL_TESTING_CHECKLIST.md step by step
```

## Verification Checklist

Before considering auto-indexing production-ready:

- [ ] All 24 pytest tests pass
- [ ] Code coverage > 80%
- [ ] All 11 manual tests pass
- [ ] Performance benchmarks met (< 10s for 50 file changes)
- [ ] Error messages are clear and helpful
- [ ] Concurrent access safe (file lock working)
- [ ] No data loss on service failures
- [ ] Documentation accurate and complete
- [ ] Known limitations documented
- [ ] Future enhancements identified

## Known Limitations

1. **File System Events**: May arrive out of order on some systems
   - Mitigation: Content hash detects actual changes

2. **Debounce Tuning**: 2-3 second window optimal
   - May need adjustment for very fast editing

3. **Symlinks**: Not followed by default
   - Workaround: Configure `follow_symlinks=True`

4. **Large Codebases**: 10,000+ files may hit limits
   - Future: Implement chunked indexing

5. **Network Paths**: Unreliable on network mounts
   - Workaround: Use local disk

## Future Enhancements

- [ ] Partial indexing (only changed lines)
- [ ] Incremental embeddings (reuse unchanged)
- [ ] Index versioning and auto-migration
- [ ] Selective watch patterns
- [ ] Distributed indexing
- [ ] Index compression
- [ ] Background indexing with progress

## File Statistics

```
TEST_PLAN_AUTO_INDEXING.md ........... 500 lines
MANUAL_TESTING_CHECKLIST.md ......... 368 lines
AUTO_INDEXING_TEST_SUMMARY.md ....... 353 lines
tests/test_auto_indexing.py ......... 567 lines
                                   --------
Total ............................ 1,788 lines
```

## Contact & Support

For questions about these test artifacts:

1. **Test Plan Details**: See TEST_PLAN_AUTO_INDEXING.md
2. **Manual Testing**: Follow MANUAL_TESTING_CHECKLIST.md
3. **Quick Overview**: Read AUTO_INDEXING_TEST_SUMMARY.md
4. **Run Tests**: Execute `pytest tests/test_auto_indexing.py -v`
5. **Verbose Output**: Use `pytest -vv --tb=long` for debugging

## License

These test artifacts are part of the Stravinsky project (MIT License).

