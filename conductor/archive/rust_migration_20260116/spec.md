# Track Specification: Rust Migration (Phase 1)

## Overview
Migrate core performance-critical utilities from Python to Rust to reduce latency, improve concurrency safety, and establish a unified high-performance native layer for Stravinsky. This track focuses on Search, AST parsing, and File Watching.

## Functional Requirements
- **Unified Native Module:** Create a Rust crate (`stravinsky_native`) that exposes functionality to Python via PyO3/Maturin.
- **Search Optimization:**
    - Implement native `grep` and `glob` functionality using the `ignore` and `globset` crates.
    - Integrate these into `mcp_bridge/tools/code_search.py`, replacing external `rg`/`find` calls.
- **AST-Aware Chunking:**
    - Implement code chunking logic in Rust using `tree-sitter`.
    - Support Python and TypeScript initially.
    - Integrate into `mcp_bridge/tools/semantic_search.py` for faster indexing.
- **Native File Watcher:**
    - Develop a standalone Rust-based file watcher using the `notify` crate.
    - Provide a mechanism to communicate changes back to the Python environment (e.g., via shared state or a simple IPC).

## Non-Functional Requirements
- **Performance:** Native calls via PyO3 should have sub-microsecond overhead.
- **Efficiency:** Drastically reduced CPU and memory usage for long-running file watching tasks.
- **Portability:** Ensure the Rust components build and run on `darwin` (macOS), matching the current environment.

## Acceptance Criteria
- [ ] `stravinsky_native` compiles and is importable in the project's Python environment.
- [ ] All existing tests in `test_code_search.py` pass using the Rust-backed implementation.
- [ ] AST chunking demonstrates measurable speed improvements over the current Python-based logic.
- [ ] The file watcher correctly identifies file additions, modifications, and deletions.
- [ ] No regressions in `semantic_search.py` indexing accuracy.

## Out of Scope
- Migrating the core MCP server orchestration or `AgentManager` logic.
- Support for languages beyond Python/TypeScript for AST chunking in this specific phase.
