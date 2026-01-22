# Implementation Plan - Refactor Routing Sisyphus 20260121

## Phase 1: Recon & Agent Config Update
*Goal: Analyze current agent dependencies and update configuration files.*

- [ ] Task: Create a reproduction script to verify current agent behavior
    - [ ] Create `tests/repro_agent_spawn.py` to spawn a dummy agent and capture its output
    - [ ] Verify it uses the wrong model/format currently
- [ ] Task: Update `mcp_bridge/routing/config.py`
    - [ ] Define the definitive `AGENT_MODEL_ROUTING` dictionary
    - [ ] Implement `load_routing_config` to prefer project-local config
- [ ] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## Phase 2: Orchestrator Logic Implementation
*Goal: Implement the Sisyphus 7-phase logic in the orchestrator.*

- [ ] Task: Update `mcp_bridge/prompts/stravinsky.py`
    - [ ] Rewrite the system prompt to enforce the 7-phase loop
    - [ ] Add specific instructions for "Recon", "LSP Refactor", "UI/UX", "Strategy", etc.
    - [ ] Implement the Dual-Model Architecture Strategy (Planner + Delphi)
- [ ] Task: Verify Orchestrator Prompt
    - [ ] Use `mcp_bridge.server.get_prompt` to fetch and verify the new prompt
- [ ] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## Phase 3: Agent Manager Refactor
*Goal: Update `agent_manager.py` to use the new routing config and fix display.*

- [ ] Task: Inject Router into AgentManager
    - [ ] Modify `mcp_bridge/tools/agent_manager.py` to accept a `Router` instance
    - [ ] Remove hardcoded `AGENT_MODEL_ROUTING` and `AGENT_DISPLAY_MODELS`
- [ ] Task: Implement Parallel Delegation
    - [ ] Update `agent_spawn` to handle `background=True` (non-blocking)
    - [ ] Ensure `explore` and `dewey` agents default to background execution
- [ ] Task: Fix CLI Output Format
    - [ ] Replace `format_spawn_output` with `display_agent_execution`
    - [ ] Ensure output matches `agent/modelname/task('summary')`
- [ ] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)

## Phase 4: Integration & Verification
*Goal: Verify the entire system works as expected.*

- [ ] Task: End-to-End Test
    - [ ] Run a sample architectural request (e.g., "Design a new caching system")
    - [ ] Verify it spawns `planner` (Opus) and `delphi` (GPT-5.2)
    - [ ] Verify it correctly synthesizes the plan
- [ ] Task: Verify Parallel Exploration
    - [ ] Run a sample "explore" request
    - [ ] Verify multiple `explore` agents run in parallel
- [ ] Task: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)
