"""
Templates for Stravinsky repository initialization.
"""

CLAUDE_MD_TEMPLATE = """## Stravinsky MCP (Parallel Agents)

Use Stravinsky MCP tools. **DEFAULT: spawn parallel agents for multi-step tasks.**

### Agent Tools
- `agent_spawn(prompt, agent_type, description)` - Spawn background agent with full tool access
- `agent_output(task_id, block)` - Get results (block=True to wait)
- `agent_progress(task_id)` - Check real-time progress
- `agent_list()` - Overview of all running agents
- `agent_cancel(task_id)` - Stop a running agent

### Parallel Execution (ULTRAWORK)
For ANY task with 2+ independent steps:
1. **Immediately use agent_spawn** for each independent component
2. Fire all agents simultaneously, don't wait
3. Monitor with agent_progress, collect with agent_output

### Trigger Commands
- **ULTRAWORK**: Maximum parallel execution - spawn agents aggressively for every subtask
- **ULTRATHINK**: Engage exhaustive deep reasoning, multi-dimensional analysis
"""

# Slash Commands
COMMAND_STRAVINSKY = """---
description: Trigger the Stravinsky Orchestrator for complex workflows.
---

Use the `stravinsky` prompt to initialize our session, assess the environment, and begin orchestration of the requested task. Stravinsky will manage todos and delegate work to specialized sub-agents.
"""

COMMAND_PARALLEL = """---
description: Execute a task with multiple parallel agents for speed.
---

Use the Stravinsky MCP tools to execute this task with PARALLEL AGENTS.

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
description: Consult the Delphi Strategic Advisor for architecture and hard debugging.
---

Use the `delphi` prompt to analyze the current problem. This triggers a GPT-based consulting phase focused on strategic reasoning, architectural trade-offs, and root-cause analysis for difficult bugs.
"""

COMMAND_DEWEY = """---
description: Trigger Dewey for documentation research and implementation examples.
---

Use the `dewey` prompt to find evidence and documentation for the topic at hand. Dewey specializes in multi-repository search and official documentation retrieval.
"""

SLASH_COMMANDS = {
    "stravinsky.md": COMMAND_STRAVINSKY,
    "parallel.md": COMMAND_PARALLEL,
    "context.md": COMMAND_CONTEXT,
    "health.md": COMMAND_HEALTH,
    "delphi.md": COMMAND_DELPHI,
    "dewey.md": COMMAND_DEWEY,
}
