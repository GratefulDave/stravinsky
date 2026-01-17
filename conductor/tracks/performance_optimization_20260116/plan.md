# Implementation Plan - Track: performance_optimization_20260116

## Phase 1: Smart Truncation & Output Management
- [x] Task: Implement core truncation utility. [ee5092d]
    - [x] Create `mcp_bridge/utils/truncation.py`.
    - [x] Write tests for middle-truncation and tail-truncation logic.
    - [x] Implement `truncate_output(text, limit, strategy)` with agent-facing guidance messages.
- [ ] Task: Enhance `read_file` with Log-Awareness.
    - [ ] Update `read_file` to detect log files and default to `tail` mode.
    - [ ] Write tests verifying `.log` files are read from the end.
    - [ ] Implement `read_file` truncation using the core utility.
- [ ] Task: Apply Universal Output Cap.
    - [ ] Integrate `truncate_output` into the central tool execution dispatcher (likely `_execute_tool`).
    - [ ] Verify `grep` and `ls` outputs are correctly capped.
- [ ] Task: Conductor - User Manual Verification 'Smart Truncation' (Protocol in workflow.md)

## Phase 2: Smart I/O Caching Layer
- [ ] Task: Implement `IOCache` utility.
    - [ ] Create `mcp_bridge/utils/cache.py` with TTL-based storage.
    - [ ] Implement `get`, `set`, and `invalidate(path)` methods.
    - [ ] Write unit tests for TTL expiration and manual invalidation.
- [ ] Task: Integrate Caching into Read Tools.
    - [ ] Wrap `read_file` and `list_directory` with caching logic.
    - [ ] Write tests verifying that subsequent reads hit the cache.
- [ ] Task: Implement Write-Through Invalidation.
    - [ ] Add `cache.invalidate()` calls to `write_file` and `replace`.
    - [ ] Add invalidation to `run_shell_command` (broad invalidation if command looks like a write).
    - [ ] Verify cache consistency after a file write.
- [ ] Task: Conductor - User Manual Verification 'Smart I/O Caching' (Protocol in workflow.md)

## Phase 3: Verification & Benchmarking
- [ ] Task: Performance Benchmarking.
    - [ ] Measure latency reduction for repeated `list_directory` calls.
    - [ ] Measure token savings for large file reads.
- [ ] Task: Integration Testing.
    - [ ] Run end-to-end agentic tasks to ensure agents correctly "understand" truncation messages.
- [ ] Task: Conductor - User Manual Verification 'Verification & Benchmarking' (Protocol in workflow.md)