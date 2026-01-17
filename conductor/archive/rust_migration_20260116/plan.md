# Implementation Plan - Track: rust_migration_20260116

## Phase 1: Environment & Scaffolding [checkpoint: 9c72088]
- [x] Task: Set up Rust project structure (`stravinsky_native`) within the repo. 0259431
    - [x] Initialize Cargo workspace.
    - [x] Configure `maturin` for PyO3 Python bindings.
    - [x] Create initial dummy function to verify Python importability.
- [x] Task: Conductor - User Manual Verification 'Environment & Scaffolding' (Protocol in workflow.md) [checkpoint: 5949e1f]

## Phase 2: Search Tools Migration [checkpoint: f42da41]
- [x] Task: Implement `grep_search` and `glob_files` in Rust. [5cf709e]
    - [x] Integrate `ignore` and `globset` crates.
    - [x] Expose functions via PyO3.
    - [x] Write Rust unit tests for search logic.
- [x] Task: Wire Rust Search into `mcp_bridge`. [5b21b9c]
    - [x] Create `mcp_bridge/native_search.py` wrapper.
    - [x] Update `mcp_bridge/tools/code_search.py` to optionally use native implementation.
    - [x] Verify `test_code_search.py` passes.
- [x] Task: Conductor - User Manual Verification 'Search Tools Migration' (Protocol in workflow.md) [checkpoint: 5b21b9c]

## Phase 3: AST Chunking Migration [checkpoint: 1d0a050]
- [x] Task: Implement `tree-sitter` chunking in Rust. [27914f3]
    - [x] Add `tree-sitter`, `tree-sitter-python`, `tree-sitter-typescript` dependencies.
    - [x] Implement AST traversal and text slicing logic.
    - [x] Expose `chunk_code(content, language)` via PyO3.
- [x] Task: Wire Rust Chunking into `semantic_search.py`. [27914f3]
    - [x] Update `mcp_bridge/tools/semantic_search.py` to use native chunker.
    - [x] Benchmark vs legacy implementation.
- [x] Task: Conductor - User Manual Verification 'AST Chunking Migration' (Protocol in workflow.md) [checkpoint: 27914f3]

## Phase 4: Native File Watcher
- [x] Task: Implement File Watcher in Rust. [360db85]
    - [x] Use `notify` crate to watch project root.
    - [x] Implement debouncing logic.
    - [x] Define IPC mechanism (likely stdout/stdin or shared file update) to signal Python.
- [x] Task: Integrate Watcher with Stravinsky. [360db85]
    - [x] Create `start_watcher` hook in `mcp_bridge`.
    - [x] Ensure clean shutdown of Rust watcher process.
- [x] Task: Conductor - User Manual Verification 'Native File Watcher' (Protocol in workflow.md) [checkpoint: 360db85]
