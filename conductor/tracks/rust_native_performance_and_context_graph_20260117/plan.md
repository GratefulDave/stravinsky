# Implementation Plan - Rust Native Performance and Context Graph

## Phase 1: Inception
- [x] Task: Initialize track structure.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Inception' (Protocol in workflow.md)

## Phase 2: Static Analysis & Hybrid Core
- [x] Task: Implement `get_imports` in `rust_native` using `tree-sitter` (Support for Python `import`/`from` and TS/JS `import`/`require`).
- [x] Task: Create `HybridGraph` logic in `rust_native` that combines `git_analysis` results with `get_imports` validation.
- [x] Task: Implement scoring algorithm:
    -   High Score: Co-occurrence + Import.
    -   Medium Score: Import only.
    -   Filter: Co-occurrence without Import (unless frequency is very high).
- [x] Task: Expose `get_hybrid_context` function to Python via PyO3.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Static Analysis & Hybrid Core' (Protocol in workflow.md)

## Phase 3: Integration & Safety
- [x] Task: Add `context_graph` section to `.stravinsky/model_config.yaml` with `enabled: boolean` toggle.
- [x] Task: Update `mcp_bridge/tools/search_enhancements.py` to respect the config toggle and use `get_hybrid_context`.
- [x] Task: Update `find_code.py` to expose the new logic safely.
- [x] Task: Write comprehensive tests covering the config toggle (enabled/disabled) and the scoring logic (mocking git/files).
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Integration & Safety' (Protocol in workflow.md)
