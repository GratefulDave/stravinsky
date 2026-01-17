# Implementation Plan - Refactor MCP Tools and Documentation for Bridge Alignment

## Phase 1: Configuration Clarity & Standardization
- [x] Task: Update `.claude/commands/stravinsky.md` to remove "NEVER use Task" warning and align with native subagent pattern. [b7703bd]
- [x] Task: Update native subagent configurations in `.claude/agents/` to explicitly endorse the Task tool for delegation. [b7703bd]
- [x] Task: Update `todo_delegation.py` hook messaging to consistently recommend the Task tool. [b7703bd]
- [x] Task: Document agent cost classification (free/cheap/expensive) in agent YAML frontmatter. [b7703bd]
- [x] Task: Conductor - User Manual Verification 'Phase 1: Configuration Clarity & Standardization' (Protocol in workflow.md)

## Phase 2: Hook Unification Layer
- [x] Task: Create `mcp_bridge/hooks/events.py` defining the `ToolCallEvent` dataclass and `HookPolicy` abstract base class.
- [x] Task: Implement `HookPolicy` adapters for native (`from_native_hook`) and MCP (`from_mcp_hook`) hooks.
- [x] Task: Migrate the **Truncation Policy** to the unified `HookPolicy` interface.
- [x] Task: Migrate the **Delegation Reminder Policy** to the unified `HookPolicy` interface.
- [x] Task: Migrate the **Edit Recovery Policy** to the unified `HookPolicy` interface.
- [x] Task: Write unit tests for the unified `HookPolicy` implementations.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Hook Unification Layer' (Protocol in workflow.md)

## Phase 3: Model Proxy Implementation
- [x] Task: specificy `mcp_bridge/proxy/model_server.py` with FastAPI to handle model generation requests.
- [x] Implement `/v1/gemini/generate` endpoint with direct API calls using OAuth tokens.
- [x] Implement `/v1/openai/chat` endpoint with direct API calls.
- [x] specificy observability layer (trace IDs, timing) in the proxy.
- [x] Create a client utility to route `invoke_gemini` and `invoke_openai` calls through the proxy when enabled.
- [x] Add `STRAVINSKY_USE_PROXY` environment variable support to toggle proxy usage.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Model Proxy Implementation' (Protocol in workflow.md)

## Phase 4: Soft Parallel Enforcement
- [x] Task: specificy session state tracking in `todo_delegation.py` (timestamp, pending count).
- [x] Task: Update `todo_delegation.py` to display warnings if no delegation occurs after `TodoWrite` with multiple tasks.
- [x] Task: Enhance hook messaging with improved formatting (ASCII borders, clear sections) for better visibility.
- [x] Task: Conductor - User Manual Verification 'Phase 4: Soft Parallel Enforcement' (Protocol in workflow.md)

## Phase 5: Documentation & Polish
- [x] Task: Update `README.md` to emphasize the Native Subagent Pattern and document the new Model Proxy.
- [x] Task: Update `WARP.md` (and other docs) to remove legacy `agent_spawn` references and emphasize the Task tool.
- [x] Task: Update `docs/AGENTS.md` with cost metadata and delegation decision trees.
- [x] Task: Create a migration guide for users transitioning from legacy slash commands.
- [x] Task: Mark legacy slash commands as deprecated in their documentation.
- [x] Task: Conductor - User Manual Verification 'Phase 5: Documentation & Polish' (Protocol in workflow.md)
