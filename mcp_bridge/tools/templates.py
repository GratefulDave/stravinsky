"""
Templates for stravinsky repository initialization.
"""

CLAUDE_MD_TEMPLATE = """## stravinsky MCP (Parallel Agents)

Use stravinsky MCP tools. **DEFAULT: spawn parallel agents for multi-step tasks.**

### Agent Tools
- `agent_spawn(prompt, agent_type, description)` - Spawn background agent with full tool access
- `agent_output(task_id, block)` - Get results (block=True to wait)
- `agent_progress(task_id)` - Check real-time progress
- `agent_list()` - Overview of all running agents
- `agent_cancel(task_id)` - Stop a running agent

### Agent Types
- `explore` - Codebase search, "where is X?" questions
- `dewey` - Documentation research, implementation examples
- `frontend` - UI/UX work, component design
- `delphi` - Strategic advice, architecture review

### Parallel Execution (IRONSTAR)
For ANY task with 2+ independent steps:
1. **Immediately use agent_spawn** for each independent component
2. Fire all agents simultaneously, don't wait
3. Monitor with agent_progress, collect with agent_output

### Trigger Commands
- **IRONSTAR** / **IRS**: Maximum parallel execution - spawn agents aggressively for every subtask
- **ULTRATHINK**: Engage exhaustive deep reasoning, multi-dimensional analysis
- **SEARCH**: Maximize search effort across codebase and external resources
- **ANALYZE**: Deep analysis mode with delphi consultation for complex issues
"""

COMMAND_STRAVINSKY = """---
description: stravinsky Orchestrator - Parallel agent execution for complex workflows.
---

Use the `stravinsky` prompt to initialize our session, assess the environment, and begin orchestration of the requested task. stravinsky will manage todos and delegate work to specialized sub-agents.

**Behavior Triggers:**
- Creates todos BEFORE any multi-step task
- Spawns parallel agents for independent components
- Delegates frontend visual work to frontend-ui-ux-engineer
- Consults delphi for architecture decisions and hard debugging
- Uses dewey for external documentation and library research

**Execution Modes:**
- `ironstar` / `irs` - Maximum parallel execution
- `ultrathink` - Deep reasoning mode
- `search` - Exhaustive search mode
- `analyze` - Deep analysis with delphi consultation
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
