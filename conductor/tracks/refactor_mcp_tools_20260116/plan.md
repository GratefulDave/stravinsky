# Implementation Plan - Refactor MCP Tools and Documentation for Bridge Alignment

## Phase 1: Configuration Clarity & Standardization
- [x] Task: Update `.claude/commands/stravinsky.md` to remove "NEVER use Task" warning and align with native subagent pattern. [b7703bd]
- [x] Task: Update native subagent configurations in `.claude/agents/` to explicitly endorse the Task tool for delegation. [b7703bd]
- [x] Task: Update `todo_delegation.py` hook messaging to consistently recommend the Task tool. [b7703bd]
- [x] Task: Document agent cost classification (free/cheap/expensive) in agent YAML frontmatter. [b7703bd]
- [~] Task: Conductor - User Manual Verification 'Phase 1: Configuration Clarity & Standardization' (Protocol in workflow.md)

## Phase 2: Hook Unification Layer
- [ ] Task: Create `mcp_bridge/hooks/events.py` defining the `ToolCallEvent` dataclass and `HookPolicy` abstract base class.
- [ ] Task: Implement `HookPolicy` adapters for native (`from_native_hook`) and MCP (`from_mcp_hook`) hooks.
- [ ] Task: Migrate the **Truncation Policy** to the unified `HookPolicy` interface.
- [ ] Task: Migrate the **Delegation Reminder Policy** to the unified `HookPolicy` interface.
- [ ] Task: Migrate the **Edit Recovery Policy** to the unified `HookPolicy` interface.
- [ ] Task: Write unit tests for the unified `HookPolicy` implementations.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Hook Unification Layer' (Protocol in workflow.md)

## Phase 3: Model Proxy Implementation
- [ ] Task: specificy `mcp_bridge/proxy/model_server.py` with FastAPI to handle model generation requests.
- [ ] Task: Implement `/v1/gemini/generate` endpoint with direct API calls using OAuth tokens.
- [ ] Task: Implement `/v1/openai/chat` endpoint with direct API calls.
- [ ] Task: specificy observability layer (trace IDs, circuit breakers) in the proxy.
- [ ] Task: Create a client utility to route `invoke_gemini` and `invoke_openai` calls through the proxy when enabled.
- [ ] Task: Add `STRAVINSKY_USE_PROXY` environment variable support to toggle proxy usage.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Model Proxy Implementation' (Protocol in workflow.md)

## Phase 4: Soft Parallel Enforcement
- [ ] Task: specificy session state tracking in `todo_delegation.py` (timestamp, pending count).
- [ ] Task: Update `todo_delegation.py` to display warnings if no delegation occurs after `TodoWrite` with multiple tasks.
- [ ] Task: Enhance hook messaging with improved formatting (ASCII borders, clear sections) for better visibility.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Soft Parallel Enforcement' (Protocol in workflow.md)

## Phase 5: Documentation & Polish
- [ ] Task: Update `README.md` to emphasize the Native Subagent Pattern and document the new Model Proxy.
- [ ] Task: Update `WARP.md` to remove legacy `agent_spawn` references and emphasize the Task tool.
- [ ] Task: Update `docs/AGENTS.md` with cost metadata and delegation decision trees.
- [ ] Task: Create a migration guide for users transitioning from legacy slash commands.
- [ ] Task: Mark legacy slash commands as deprecated in their documentation.
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Documentation & Polish' (Protocol in workflow.md)
