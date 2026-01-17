# Implementation Plan - Track: parallel_execution_20260116

## Phase 1: Async Subprocess Infrastructure
- [ ] Task: Create Async Process Wrapper.
    - [ ] Create `mcp_bridge/utils/process.py`.
    - [ ] Implement `async_execute(cmd, timeout)` using `asyncio.create_subprocess_exec`.
    - [ ] Write unit tests for successful execution, timeout handling, and error capture.
- [ ] Task: Refactor Search Tools.
    - [ ] Update `mcp_bridge/tools/code_search.py` to use `async_execute`.
    - [ ] Update `mcp_bridge/tools/find_code.py` for full async compatibility.
    - [ ] Verify non-blocking behavior by running a long `grep` and a fast `glob` simultaneously.
- [ ] Task: Conductor - User Manual Verification 'Async Subprocess Migration' (Protocol in workflow.md)

## Phase 2: Native Threading & FFI Offloading
- [ ] Task: Implement Threaded FFI Layer.
    - [ ] Update `mcp_bridge/native_search.py` to wrap all module calls in `run_in_executor`.
    - [ ] Implement a singleton `get_executor()` for shared thread pool management.
    - [ ] Write tests verifying that Rust calls now return `awaitable` objects.
- [ ] Task: Update Call Sites.
    - [ ] Audit `mcp_bridge/tools/` for any direct `native_*` calls and ensure they are `await`ed.
- [ ] Task: Conductor - User Manual Verification 'Native Threading Layer' (Protocol in workflow.md)

## Phase 3: Parallel Agent Orchestration
- [ ] Task: Refactor Agent Spawning.
    - [ ] Update `AgentManager._execute_agent` to be fully non-blocking.
    - [ ] Ensure that the `threading.Thread` currently used in `AgentManager` is correctly integrated with the `asyncio` loop status.
    - [ ] Test spawning 3 agents simultaneously in a single turn.
- [ ] Task: Performance Audit.
    - [ ] Use `asyncio` debug mode or custom timers to ensure the event loop is never blocked by tool calls.
- [ ] Task: Conductor - User Manual Verification 'Parallel Orchestration' (Protocol in workflow.md)
