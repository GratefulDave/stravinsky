# Remediation Plan: Parallel Delegation & Agent Orchestration

## Issue Summary
The current parallel delegation logic fails because:
1. **Invalid Syntax**: Hooks recommend `run_in_background=true` for the `Task` tool, which is not supported by the native Claude Code `Task` tool in the current environment.
2. **Synchronous Bottleneck**: Native `Task` calls are sequential. True parallelism is only achievable via the MCP `agent_spawn` tool.
3. **Ambiguous Routing**: No clear rule on when to use native `Task` vs. MCP `agent_spawn`.

## Proposed Solutions

### 1. Standardize Orchestration Language
- **Remove** all references to `run_in_background=true` in `.claude/hooks/` and `mcp_bridge/hooks/`.
- **Recommendation**: For true parallel discovery, the orchestrator should use `agent_spawn` (MCP) for async background work. For gating/synchronous delegation, use native `Task`.

### 2. Implement "Gate-then-Spawn" State Management
Adopt Oracle's suggestion for a state-based gating mechanism:
- **State File**: Create `.claude/state/fanout.json` to track orchestration state.
- **`PostToolUse` (TodoWrite)**:
  - If 2+ pending items exist, write `{"status": "needs_fanout"}` to the state file.
  - Return exit code 2 to force the assistant to spawn tasks.
- **`PreToolUse` (Read/Grep/Bash)**:
  - If state is `needs_fanout`, block the tool with exit code 2 and a message: "Parallel delegation required before doing direct work."
- **`PostToolUse` (Task/agent_spawn)**:
  - When a task is spawned, update state: `{"status": "fanout_in_progress", "active_tasks": [...]}`.

### 3. Explicit Fan-in Strategy
- Update `stravinsky.md` (orchestrator) instructions:
  - "When spawning multiple background agents, you MUST explicitly wait for their results in a subsequent turn using `agent_output(task_id, block=true)` or checking `agent_list()`."
  - "Do NOT proceed to implementation until all discovery tasks are complete."

### 4. Correct Parameter Usage
- **Native Task**: `Task(subagent_type="...", prompt="...", description="...")` (Always sequential/blocking).
- **MCP Agent**: `agent_spawn(agent_type="...", prompt="...", blocking=false)` (Async/Background).

## Implementation Steps (No Code Changes Yet)
1. **Sync Hook Content**: Ensure `.claude/hooks/` and `mcp_bridge/native_hooks/` are identical and use the latest logic.
2. **Update Agent Metadata**: Add `execution: async` to `.claude/agents/` configs for `explore` and `dewey` to signal intent, even if implemented via MCP tools.
3. **Refine Orchestrator System Prompt**: In `.claude/agents/stravinsky.md`, strictly define the use of `agent_spawn` for parallel execution and `Task` for blocking delegation.
