# Implementation Plan - Implement Hard Enforcement and Advanced Capabilities

## Phase 1: Hard Parallel Enforcement
- [x] Task: Implement `mcp_bridge/hooks/post_tool/parallel_validation.py` to track pending tasks after `TodoWrite`.
- [x] Task: Implement `mcp_bridge/hooks/pre_tool/agent_spawn_validator.py` to block sequential execution when independent tasks are pending.
- [x] Task: Add `enforce_parallel_delegation` configuration toggle to `.stravinsky/model_config.yaml`.
- [x] Task: Implement the `{"parallel": false}` override in `TodoWrite` and `STRAVINSKY_ALLOW_SEQUENTIAL` environment variable.
- [x] Task: Write comprehensive tests for hard enforcement (3 pending -> must spawn, 1 pending -> allow next tool).
- [~] Task: Conductor - User Manual Verification 'Phase 1: Hard Parallel Enforcement' (Protocol in workflow.md)

## Phase 2: Core Capability Enhancements
- [x] Task: Integrate `thinking_budget` support in `stravinsky.md` and `delphi.md` agent configurations.
- [x] Task: Implement `reasoning_effort` for GPT models and extended thinking for Claude/Gemini in `invoke_` tools.
- [x] Task: Finalize agent session isolation logic to ensure strict separation of local state files.
- [x] Task: Write verification tests for session isolation and extended thinking.
- [~] Task: Conductor - User Manual Verification 'Phase 2: Core Capability Enhancements' (Protocol in workflow.md)

## Phase 3: Semantic Search Evolution
- [ ] Task: Implement `hybrid_search` combining ChromaDB semantic results with BM25 keyword matching.
- [ ] Task: Implement `multi_query_search` using LLM query expansion variations.
- [ ] Task: Implement `decomposed_search` for breaking complex queries into parallel sub-searches.
- [ ] Task: Implement `enhanced_search` as the unified entry point with automatic strategy selection.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Semantic Search Evolution' (Protocol in workflow.md)

## Phase 4: Observability & Visual UX
- [ ] Task: Implement visual tool output formatting (tables/graphs) using `rich` for terminal rendering.
- [ ] Task: specificy the Agent Cost Tracker hook to collect token/cost metrics per session.
- [ ] Task: Build the Agent Cost Dashboard (Terminal UI or local web view).
- [ ] Task: Document all new search and observability tools in `docs/`.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Observability & Visual UX' (Protocol in workflow.md)
