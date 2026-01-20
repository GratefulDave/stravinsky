# Implementation Plan - 7-Phase Orchestrator

## Phase 1: Core Infrastructure & Output Hygiene (Rust)
- [x] Task: Define Native Truncation Interface (Rust) [aabcb85]
    - [x] Create `rust_native/src/truncator.rs`
    - [x] Implement `auto_tail` logic (Keep first N, last M lines)
    - [x] Implement `smart_summary` logic (Heuristic based)
    - [x] Expose via PyO3 bindings
- [x] Task: Integrate Native Truncation in Python Bridge [4111d14]
    - [x] Update `mcp_bridge/utils/truncation.py` to use Rust bindings
    - [x] Write tests for truncation scenarios (Logs, Large Files)
- [x] Task: Conductor - User Manual Verification 'Core Infrastructure & Output Hygiene' (Protocol in workflow.md) [Manual Verification Passed]

## Phase 2: Orchestrator State Machine
- [x] Task: Define Orchestrator Phases & State [f2b7d61]
    - [x] Create `mcp_bridge/orchestrator/enums.py` (Phase definitions)
    - [x] Create `mcp_bridge/orchestrator/state.py` (State tracking)
- [x] Task: Implement Wisdom & Critique Logic [75cf645]
    - [x] Implement `WisdomLoader` to read `.stravinsky/wisdom.md`
    - [x] Create `CritiqueGenerator` prompt template
- [x] Task: Implement Model Routing Logic [8fb362f]
    - [x] Define `ModelVariant` config (Planning vs Execution models)
    - [x] Implement `Router` class to select model based on Phase
- [x] Task: Conductor - User Manual Verification 'Orchestrator State Machine' (Protocol in workflow.md) [checkpoint: f70b325]

## Phase 3: Workflow Enforcement & UX
- [x] Task: Implement Phase Gates (Optional) [bacfadd]
    - [x] Add configuration toggle `enable_phase_gates`
    - [x] Implement pause/resume logic in Agent Loop
- [x] Task: Connect Orchestrator to Agent Loop [f86e14c]
    - [x] Modify `agent_manager.py` to consult Orchestrator before actions
    - [x] Enforce artifact checks (e.g., `plan.md` must exist before Code phase)
- [x] Task: Add Progress Visualization [9a0d825]
    - [x] Update CLI output to show `[Phase X/7]` status
- [ ] Task: Conductor - User Manual Verification 'Workflow Enforcement & UX' (Protocol in workflow.md)
