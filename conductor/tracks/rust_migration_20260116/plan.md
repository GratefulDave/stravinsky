# Implementation Plan - Track: rust_migration_20260116

## Phase 1: Environment & Scaffolding [checkpoint: 9c72088]
- [x] Task: Set up Rust project structure (`stravinsky_native`) within the repo. 0259431
    - [x] Initialize Cargo workspace.
    - [x] Configure `maturin` for PyO3 Python bindings.
    - [x] Create initial dummy function to verify Python importability.
- [x] Task: Conductor - User Manual Verification 'Environment & Scaffolding' (Protocol in workflow.md) [checkpoint: 5949e1f]

## Phase 2: Search Tools Migration
- [ ] Task: Implement `grep_search` and `glob_files` in Rust.
    - [ ] Integrate `ignore` and `globset` crates.
    - [ ] Expose functions via PyO3.
    - [ ] Write Rust unit tests for search logic.
- [ ] Task: Wire Rust Search into `mcp_bridge`.
    - [ ] Create `mcp_bridge/native_search.py` wrapper.
    - [ ] Update `mcp_bridge/tools/code_search.py` to optionally use native implementation.
    - [ ] Verify `test_code_search.py` passes.
- [ ] Task: Conductor - User Manual Verification 'Search Tools Migration' (Protocol in workflow.md)

## Phase 3: AST Chunking Migration
- [ ] Task: Implement `tree-sitter` chunking in Rust.
    - [ ] Add `tree-sitter`, `tree-sitter-python`, `tree-sitter-typescript` dependencies.
    - [ ] Implement AST traversal and text slicing logic.
    - [ ] Expose `chunk_code(content, language)` via PyO3.
- [ ] Task: Wire Rust Chunking into `semantic_search.py`.
    - [ ] Update `mcp_bridge/tools/semantic_search.py` to use native chunker.
    - [ ] Benchmark vs legacy implementation.
- [ ] Task: Conductor - User Manual Verification 'AST Chunking Migration' (Protocol in workflow.md)

## Phase 4: Native File Watcher
- [ ] Task: Implement File Watcher in Rust.
    - [ ] Use `notify` crate to watch project root.
    - [ ] Implement debouncing logic.
    - [ ] Define IPC mechanism (likely stdout/stdin or shared file update) to signal Python.
- [ ] Task: Integrate Watcher with Stravinsky.
    - [ ] Create `start_watcher` hook in `mcp_bridge`.
    - [ ] Ensure clean shutdown of Rust watcher process.
- [ ] Task: Conductor - User Manual Verification 'Native File Watcher' (Protocol in workflow.md)
