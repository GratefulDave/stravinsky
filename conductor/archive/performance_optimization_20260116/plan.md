# Implementation Plan - Track: performance_optimization_20260116

## Phase 1: Smart Truncation & Output Management [checkpoint: bc60506]
- [x] Task: Implement core truncation utility. [ee5092d]
    - [x] Create `mcp_bridge/utils/truncation.py`.
    - [x] Write tests for middle-truncation and tail-truncation logic.
    - [x] Implement `truncate_output(text, limit, strategy)` with agent-facing guidance messages.
- [x] Task: Enhance `read_file` with Log-Awareness. [93e520b]
    - [x] Update `read_file` to detect log files and default to `tail` mode.
    - [x] Write tests verifying `.log` files are read from the end.
    - [x] Implement `read_file` truncation using the core utility.
- [x] Task: Apply Universal Output Cap. [656716e]
    - [x] Integrate `truncate_output` into the central tool execution dispatcher (via `TruncationPolicy`).
    - [x] Verify `grep` and `ls` outputs are correctly capped.
- [x] Task: Conductor - User Manual Verification 'Smart Truncation' (Protocol in workflow.md)

## Phase 2: Smart I/O Caching Layer [checkpoint: 76b0ea6]
- [x] Task: Implement `IOCache` utility. [fc38c93]
    - [x] Create `mcp_bridge/utils/cache.py` with TTL-based storage.
    - [x] Implement `get`, `set`, and `invalidate(path)` methods.
    - [x] Write unit tests for TTL expiration and manual invalidation.
- [x] Task: Integrate Caching into Read Tools. [7c05558]
    - [x] Wrap `read_file` and `list_directory` with caching logic.
    - [x] Write tests verifying that subsequent reads hit the cache.
- [x] Task: Implement Write-Through Invalidation. [96f70fc]
    - [x] Add `cache.invalidate()` calls to `write_file` and `replace`.
    - [x] Add invalidation to `run_shell_command` (broad invalidation if command looks like a write).
    - [x] Verify cache consistency after a file write.
- [x] Task: Conductor - User Manual Verification 'Smart I/O Caching' (Protocol in workflow.md)

## Phase 3: Verification & Benchmarking [checkpoint: 215afcd]

- [x] Task: Performance Benchmarking. [6c8f711]

    - [x] Measure latency reduction for repeated `list_directory` calls.

    - [x] Measure token savings for large file reads.

- [x] Task: Integration Testing. [b44510f]

    - [x] Run end-to-end agentic tasks to ensure agents correctly "understand" truncation messages.

- [x] Task: Conductor - User Manual Verification 'Verification & Benchmarking' (Protocol in workflow.md)
