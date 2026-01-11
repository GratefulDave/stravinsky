"""
Templates for stravinsky repository initialization.
"""

CLAUDE_MD_TEMPLATE = """## stravinsky MCP (Multi-Model Orchestration)

Stravinsky provides multi-model AI orchestration with parallel agent execution.

### Architecture
- **Native Subagent**: Stravinsky orchestrator (.claude/agents/stravinsky.md) auto-delegates complex tasks
- **MCP Tools**: agent_spawn, invoke_gemini, invoke_openai, LSP tools, code search
- **Specialist Agents**: explore, dewey, frontend, delphi, multimodal, document_writer

### Agent Tools (via MCP)
- `agent_spawn(prompt, agent_type, description)` - Spawn background agent with full tool access
- `agent_output(task_id, block)` - Get results (block=True to wait)
- `agent_progress(task_id)` - Check real-time progress
- `agent_list()` - Overview of all running agents
- `agent_cancel(task_id)` - Stop a running agent

### Agent Types
- `explore` - Codebase search, structural analysis (Gemini 3 Flash)
- `dewey` - Documentation research, web search (Gemini 3 Flash + Web)
- `frontend` - UI/UX implementation (Gemini 3 Pro High)
- `delphi` - Strategic advice, architecture review (GPT-5.2 Medium)
- `multimodal` - Visual analysis, screenshots (Gemini 3 Flash Vision)
- `document_writer` - Technical documentation (Gemini 3 Flash)

### Parallel Execution (MANDATORY)
For ANY task with 2+ independent steps:
1. **Immediately use agent_spawn** for each independent component
2. Fire all agents simultaneously in ONE response, don't wait
3. Monitor with agent_progress, collect with agent_output

### Trigger Commands
- **ULTRAWORK** / **UW**: Maximum parallel execution - spawn agents aggressively for every subtask
- **ULTRATHINK**: Engage exhaustive deep reasoning, multi-dimensional analysis
- **SEARCH**: Maximize search effort across codebase and external resources
- **ANALYZE**: Deep analysis mode with delphi consultation for complex issues

### Native Subagent Benefits
- ✅ Auto-delegation (no manual /stravinsky invocation)
- ✅ Context isolation (orchestrator runs as subagent)
- ✅ Full MCP tool access (agent_spawn, invoke_gemini/openai, LSP, etc.)
- ✅ Multi-model routing (Gemini for UI/research, GPT for strategy)
"""

COMMAND_STRAVINSKY = """---
description: stravinsky Orchestrator - Parallel agent execution for complex workflows.
---

## CRITICAL: USE STRAVINSKY MCP TOOLS

You MUST use the Stravinsky MCP server tools for ALL file reading, searching, and parallel work.

### MANDATORY TOOL USAGE:

**For ANY file reading or searching:**
```
stravinsky:agent_spawn(
  prompt="Read and analyze [file path]. Return: [what you need]",
  agent_type="explore",
  description="Read [file]"
)
```

**For documentation/library research:**
```
stravinsky:agent_spawn(
  prompt="Find documentation for [topic]",
  agent_type="dewey",
  description="Research [topic]"
)
```

**For 2+ independent tasks (ALWAYS parallel):**
```
// Fire ALL at once in ONE response - NEVER sequential
stravinsky:agent_spawn(prompt="Task 1...", agent_type="explore", description="Task 1")
stravinsky:agent_spawn(prompt="Task 2...", agent_type="explore", description="Task 2")
stravinsky:agent_spawn(prompt="Task 3...", agent_type="dewey", description="Task 3")
// Then immediately continue - don't wait
```

**To get results:**
```
stravinsky:agent_output(task_id="[id]", block=true)
```

### Recommended Tool Usage:
- For file operations within agents: Use standard Read/Edit tools
- For parallel agent spawning: Use stravinsky:agent_spawn (supports nesting, unlike native Task tool)
- For collecting results: Use stravinsky:agent_output
- For monitoring agents: Use stravinsky:agent_list

### Native Subagent Integration:
- Stravinsky orchestrator configured as native Claude Code subagent (.claude/agents/stravinsky.md)
- Native subagents CAN call Stravinsky MCP tools (agent_spawn, invoke_gemini, etc.)
- This enables auto-delegation without manual /stravinsky invocation

### Execution Modes:
- `ultrawork` / `irs` - Maximum parallel execution (10+ agents)
- `ultrathink` - Deep reasoning with delphi consultation
- `search` - Exhaustive multi-agent search

**Your FUWT action must be spawning agents, not using Read/Search tools.**
"""

COMMAND_PARALLEL = """---
description: Execute a task with multiple parallel agents for speed.
---

Use the stravinsky MCP tools to execute this task with PARALLEL AGENTS.

**MANDATORY:** For the following task items, spawn a SEPARATE `agent_spawn` call for EACH independent item. Do not work on them sequentially - fire all agents simultaneously:

$ARGUMENTS

After spawning all agents:
1. Use `agent_list` to show running agents
2. Use `agent_progress(task_id)` to monitor each
3. Collect results with `agent_output(task_id, block=True)` when ready
"""

COMMAND_CONTEXT = """---
description: Refresh project situational awareness (Git, Rules, Top Todos).
---

Call the `get_project_context` tool to retrieve the current Git branch, modified files, local project rules from `.claude/rules/`, and any pending `[ ]` todos in the current scope.
"""

COMMAND_HEALTH = """---
description: Perform a comprehensive system health and dependency check.
---

Call the `get_system_health` tool to verify that all CLI dependencies (rg, fd, sg, tsc, etc.) are installed and that authentication for Gemini and OpenAI is active.
"""

COMMAND_DELPHI = """---
description: Consult the delphi Strategic Advisor for architecture and hard debugging.
---

Use the `delphi` prompt to analyze the current problem. This triggers a GPT-based consulting phase focused on strategic reasoning, architectural trade-offs, and root-cause analysis for difficult bugs.

**When to use delphi:**
- Complex architecture design decisions
- After 2+ failed fix attempts
- Multi-system tradeoffs
- Security/performance concerns
- Unfamiliar code patterns
"""

COMMAND_LIST = """---
description: List all active and recent background agent tasks.
---

Call the `agent_list` tool to see an overview of all currently running and completed background agents, including their Task IDs and statuses.
"""

COMMAND_DEWEY = """---
description: Trigger dewey for documentation research and implementation examples.
---

Use the `dewey` prompt to find evidence and documentation for the topic at hand. dewey specializes in multi-repository search and official documentation retrieval.

**When to use dewey:**
- Unfamiliar npm/pip/cargo packages
- "How do I use [library]?"
- "What's the best practice for [framework feature]?"
- Finding OSS implementation examples
"""

COMMAND_VERSION = """---
description: Returns the current version and diagnostic info for stravinsky.
---

Display the stravinsky MCP version, registered hooks, available agents, and system health status.
"""

SLASH_COMMANDS = {
    "stravinsky.md": COMMAND_STRAVINSKY,
    "parallel.md": COMMAND_PARALLEL,
    "list.md": COMMAND_LIST,
    "context.md": COMMAND_CONTEXT,
    "health.md": COMMAND_HEALTH,
    "delphi.md": COMMAND_DELPHI,
    "dewey.md": COMMAND_DEWEY,
    "version.md": COMMAND_VERSION,
}
