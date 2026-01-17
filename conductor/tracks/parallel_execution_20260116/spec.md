# Track Specification: Parallel & Non-Blocking Execution

## Overview
Transform the `mcp_bridge` from a blocking sequential server into a highly concurrent async system. This eliminates "lag" during tool execution by offloading CLI processes and Rust FFI calls to non-blocking pathways.

## Functional Requirements
### 1. Async Subprocess Migration
- **Core Refactor:** Replace all synchronous `subprocess.run()` calls with `asyncio.create_subprocess_exec()`.
- **Streaming Output:** Properly handle `stdout` and `stderr` streams asynchronously to prevent buffer deadlocks.
- **Tools Impacted:** `grep_search`, `glob_files`, `ast_grep_*`, and LSP legacy fallbacks.

### 2. Native (Rust) Threading Layer
- **FFI Offloading:** Since Rust/PyO3 calls are synchronous and CPU-bound, wrap them in `loop.run_in_executor(ThreadPoolExecutor, ...)`.
- **Global Executor:** Maintain a shared `ThreadPoolExecutor` within the `mcp_bridge` to manage thread overhead.
- **Tools Impacted:** All wrappers in `native_search.py`.

### 3. Parallel Agent Orchestration
- **Concurrent Spawning:** Update the `AgentManager` to ensure that spawning multiple agents in a single LLM turn (e.g., "Spawn A and B") happens in parallel rather than waiting for A to finish its handshake before starting B.
- **Non-Blocking Handshake:** Ensure the initial shell connection and prompt injection for agents do not block the bridge's main loop.

## Non-Functional Requirements
- **Event Loop Integrity:** The main event loop must never block for more than 50ms.
- **Timeouts:** Every async subprocess and threaded call must enforce a configurable timeout.

## Acceptance Criteria
- [ ] `grep_search` on a large directory does not delay concurrent `lsp_hover` calls.
- [ ] Rust-based native searches return results without freezing the bridge process.
- [ ] Multiple `agent_spawn` tool calls executed in a single `asyncio.gather` (or sequential call turn) do not block each other.
- [ ] No `subprocess.run` calls remain in the `mcp_bridge/tools/` directory (verified via grep).
