# MCP Tool Call Injection Points - Formatted Output Logging

**Objective**: Add formatted tool call output like `Explore:gemini-3-flash('Find abc code') task_id=xyz` at key integration points where agents and models are invoked.

---

## Tool Categories Overview

### Complete Tool List (54 tools)

| Category | Count | Tools |
|----------|-------|-------|
| Model Invoke | 3 | invoke_gemini, invoke_gemini_agentic, invoke_openai |
| Agents | 7 | agent_spawn, agent_output, agent_cancel, agent_list, agent_progress, agent_retry, agent_cleanup |
| Code Search | 5 | ast_grep_search, ast_grep_replace, grep_search, glob_files, find_code |
| Semantic | 11 | semantic_search, semantic_index, semantic_stats, hybrid_search, multi_query_search, decomposed_search, enhanced_search, start_file_watcher, stop_file_watcher, list_file_watchers, cancel_indexing, delete_index |
| LSP | 12 | lsp_diagnostics, lsp_hover, lsp_goto_definition, lsp_find_references, lsp_document_symbols, lsp_workspace_symbols, lsp_prepare_rename, lsp_rename, lsp_code_actions, lsp_code_action_resolve, lsp_extract_refactor, lsp_servers |
| File Ops | 6 | list_directory, read_file, write_file, replace, run_shell_command, tool_search |
| Environment | 2 | get_project_context, get_system_health |
| Sessions | 3 | session_list, session_read, session_search |
| Skills | 2 | skill_list, skill_get |

---

## Priority 1: Agent Spawn (HIGHEST IMPACT)

### Location 1a: Agent Tool Dispatch
**File**: `/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/server.py`
**Lines**: 313-316
**Current Code**:
```python
elif name == "agent_spawn":
    from .tools.agent_manager import agent_spawn

    result_content = await agent_spawn(**arguments)
```

**Injection Point**: After dispatch, before awaiting agent_spawn
**Enhancement**: Extract agent_type, description, and display emoji+formatted message
```python
elif name == "agent_spawn":
    from .tools.agent_manager import agent_spawn
    from .tools.agent_manager import AGENT_DISPLAY_MODELS, get_agent_emoji

    agent_type = arguments.get("agent_type", "explore")
    description = arguments.get("description", "")[:50]
    display_model = AGENT_DISPLAY_MODELS.get(agent_type, "default")
    cost_emoji = get_agent_emoji(agent_type)

    # Log formatted spawn message
    logger.info(f"AGENT_SPAWN: {cost_emoji} {agent_type}:{display_model}('{description}')")

    result_content = await agent_spawn(**arguments)
```

### Location 1b: Agent Spawn Implementation
**File**: `/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/agent_manager.py`
**Lines**: 1050-1124 (agent_spawn function)
**Current Output** (colorize_agent_spawn_message):
```python
return format_spawn_output(agent_type, display_model, task_id)
```

**Status**: ALREADY HAS formatted output for user!
- Uses AGENT_DISPLAY_MODELS (lines 80-95)
- Uses cost_emoji indicators (lines 97-110)
- Returns formatted string with agent:model('description') and task_id
- **No changes needed** - output is already well-formatted

### NEW: task_graph_id Parameter
**File**: `/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/agent_manager.py`
**Lines**: 1050-1064

The `agent_spawn` function now accepts a `task_graph_id` parameter for parallel execution enforcement:

```python
async def agent_spawn(
    prompt: str,
    agent_type: str = "explore",
    description: str = "",
    # ... other params ...
    task_graph_id: str | None = None,  # NEW: Task ID from TaskGraph for parallel enforcement
) -> str:
```

**DelegationEnforcer Integration** (lines 1072-1083):
```python
# Parallel execution enforcement
enforcer = get_delegation_enforcer()
if enforcer and task_graph_id:
    # Validate this spawn is allowed by the task graph
    is_valid, error = enforcer.validate_spawn(task_graph_id)
    if not is_valid:
        from ..orchestrator.task_graph import ParallelExecutionError
        raise ParallelExecutionError(
            f"Spawn blocked: {error}\n"
            f"Independent tasks MUST be spawned in parallel.\n"
            f"Current wave: {[t.id for t in enforcer.get_current_wave()]}"
        )
```

---

## Priority 2: Model Invocation (ALREADY PARTIALLY DONE)

### Location 2a: Gemini Model Invoke
**File**: `/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/model_invoke.py`
**Lines**: 301-544 (invoke_gemini function)
**Current Output** (Lines 363-367):
```python
# Log with agent context and prompt summary
logger.info(f"[{agent_type}] -> {model}: {prompt_summary}")

# USER-VISIBLE NOTIFICATION (stderr) - Shows when Gemini is invoked
import sys
task_info = f" task={task_id}" if task_id else ""
desc_info = f" | {description}" if description else ""
print(f"GEMINI: {model} | agent={agent_type}{task_info}{desc_info}", file=sys.stderr)
```

**Status**: ALREADY HAS formatted output to stderr!
- Shows model name
- Shows agent type
- Shows task_id and description
- **No changes needed** - output is functional but could be enhanced with cost tier emoji

**Enhancement** (Optional, for consistency with agent_spawn):
Replace line 367 with:
```python
cost_emoji = get_model_emoji(model)  # Add to imports
print(f"{cost_emoji} GEMINI -> {model} | agent={agent_type}{task_info}{desc_info}", file=sys.stderr)
```

### Location 2b: OpenAI Model Invoke
**File**: `/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/model_invoke.py`
**Lines**: 838-1002 (invoke_openai function)
**Current Output** (Lines 890-897):
```python
# Log with agent context and prompt summary
logger.info(f"[{agent_type}] -> {model}: {prompt_summary}")

# USER-VISIBLE NOTIFICATION (stderr) - Shows when OpenAI is invoked
import sys
task_info = f" task={task_id}" if task_id else ""
desc_info = f" | {description}" if description else ""
print(f"OPENAI: {model} | agent={agent_type}{task_info}{desc_info}", file=sys.stderr)
```

**Status**: ALREADY HAS formatted output to stderr!
- Shows model name
- Shows agent type
- Shows task_id and description
- **No changes needed** - output is functional

---

## Priority 3: Task Spawn (MEDIUM IMPACT)

### Location 3a: Task Tool Dispatch
**File**: `/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/server.py`
**Lines**: 354-360
**Current Code**:
```python
elif name == "task_spawn":
    from .tools.background_tasks import task_spawn

    result_content = await task_spawn(
        prompt=arguments["prompt"],
        model=arguments.get("model", "gemini-3-flash"),
    )
```

**Injection Point**: Before awaiting task_spawn
**Enhancement**:
```python
elif name == "task_spawn":
    from .tools.background_tasks import task_spawn

    model = arguments.get("model", "gemini-3-flash")
    prompt = arguments.get("prompt", "")
    short_desc = prompt[:50]

    # Log formatted spawn message
    logger.info(f"TASK_SPAWN: task [{model}] ('{short_desc}')")

    result_content = await task_spawn(
        prompt=prompt,
        model=model,
    )
```

### Location 3b: Task Spawn Implementation
**File**: `/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/background_tasks.py`
**Lines**: 132-137 (task_spawn function)
**Current Code**:
```python
async def task_spawn(prompt: str, model: str = "gemini-3-flash") -> str:
    """Spawns a new background task."""
    manager = BackgroundManager()
    task_id = manager.create_task(prompt, model)
    manager.spawn(task_id)
    return f"Task spawned with ID: {task_id}. Use task_status('{task_id}') to check progress."
```

**Status**: Returns plain text with task_id
**Enhancement**: Add formatted output similar to agent_spawn
```python
async def task_spawn(prompt: str, model: str = "gemini-3-flash") -> str:
    """Spawns a new background task."""
    manager = BackgroundManager()
    task_id = manager.create_task(prompt, model)
    manager.spawn(task_id)

    # Format with emoji and model info (like agent_spawn does)
    short_desc = prompt[:50]
    return f"task [{model}]('{short_desc}') spawned\ntask_id={task_id}"
```

---

## Priority 4: Tool Call Logging (Existing Infrastructure)

### Location 4: Tool Dispatcher Log Formatting
**File**: `/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/server.py`
**Lines**: 98-141 (_format_tool_log function)
**Current Code**:
```python
def _format_tool_log(name: str, arguments: dict[str, Any]) -> str:
    """Format a concise log message for tool calls."""
    # LSP tools - show file:line
    if name.startswith("lsp_"):
        # ... LSP formatting ...

    # Model invocation - show agent context if present
    if name in ("invoke_gemini", "invoke_openai"):
        agent_ctx = arguments.get("agent_context", {})
        agent_type = agent_ctx.get("agent_type", "direct") if agent_ctx else "direct"
        model = arguments.get("model", "default")
        prompt = arguments.get("prompt", "")
        summary = " ".join(prompt.split())[:80] + "..." if len(prompt) > 80 else prompt
        return f"[{agent_type}] -> {model}: {summary}"

    # Agent tools - show agent type/task_id
    if name == "agent_spawn":
        agent_type = arguments.get("agent_type", "explore")
        desc = arguments.get("description", "")[:40]
        return f"-> {name}: [{agent_type}] {desc}"
```

**Status**: Already formats most tools nicely
**Used At**: Line 147 - `logger.info(_format_tool_log(name, arguments))`
**Enhancement Opportunity**: Add cost tier emoji to agent_spawn formatting (line 132-135)
```python
if name == "agent_spawn":
    agent_type = arguments.get("agent_type", "explore")
    desc = arguments.get("description", "")[:40]
    from .agent_manager import get_agent_emoji, AGENT_DISPLAY_MODELS
    cost_emoji = get_agent_emoji(agent_type)
    display_model = AGENT_DISPLAY_MODELS.get(agent_type, "default")
    return f"{cost_emoji} agent_spawn: {agent_type}:{display_model} [{desc}]"
```

---

## Integration Points Summary

| Tool | Location | Current Status | Enhancement Priority |
|------|----------|---------------|--------------------|
| **agent_spawn** | server.py:313-316 | Basic dispatch | Add emoji+model to logger |
|  | agent_manager.py:1050-1124 | Full formatted output + task_graph_id | None needed |
|  | agent_manager.py:1072-1083 | DelegationEnforcer validation | NEW feature |
| **invoke_gemini** | server.py:158-168 | Basic dispatch | None - already in model_invoke |
|  | model_invoke.py:363-367 | Formatted stderr | Optional emoji enhancement |
| **invoke_openai** | server.py:170-180 | Basic dispatch | None - already in model_invoke |
|  | model_invoke.py:890-897 | Formatted stderr | None needed |
| **task_spawn** | server.py:354-360 | Basic dispatch | Add model info to logger |
|  | background_tasks.py:132-137 | Plain text | Add formatted output |
| **Tool dispatch log** | server.py:147 | Uses _format_tool_log | Add cost emoji to agent_spawn |

---

## Recommended Implementation Order

### Phase 1: Zero-Risk (Logging Only)
1. **server.py:313-316** - Add formatted logging to agent_spawn dispatcher
2. **server.py:98-141** - Enhance _format_tool_log for cost emoji on agent_spawn
3. **server.py:354-360** - Add formatted logging to task_spawn dispatcher

### Phase 2: Enhanced User Visibility (stderr)
1. **agent_manager.py:295** - Add stderr notification when agent starts
2. **background_tasks.py:117-127** - Add stderr notification when task spawns
3. **model_invoke.py:367** - Enhance Gemini notification with cost emoji

### Phase 3: Result Formatting
1. **background_tasks.py:132-137** - Enhance task_spawn result format
2. **agent_manager.py:915-916** - Already optimal, no changes

---

## Code Examples Ready to Implement

### Example 1: Enhanced Agent Spawn Logger (server.py:313-316)
```python
elif name == "agent_spawn":
    from .tools.agent_manager import agent_spawn, AGENT_DISPLAY_MODELS, get_agent_emoji

    agent_type = arguments.get("agent_type", "explore")
    description = arguments.get("description", "")[:50]
    display_model = AGENT_DISPLAY_MODELS.get(agent_type, "default")
    cost_emoji = get_agent_emoji(agent_type)

    logger.info(f"-> agent_spawn: {cost_emoji} {agent_type}:{display_model}('{description}')")
    result_content = await agent_spawn(**arguments)
```

### Example 2: Enhanced _format_tool_log for agent_spawn (server.py:132-135)
```python
if name == "agent_spawn":
    from .tools.agent_manager import get_agent_emoji, AGENT_DISPLAY_MODELS
    agent_type = arguments.get("agent_type", "explore")
    desc = arguments.get("description", "")[:40]
    cost_emoji = get_agent_emoji(agent_type)
    display_model = AGENT_DISPLAY_MODELS.get(agent_type, "default")
    return f"{cost_emoji} {name}: {agent_type}:{display_model}['{desc}']"
```

### Example 3: Stderr Notification for Agent Spawn (agent_manager.py:~295)
```python
# In _execute_agent, after line 294:
import sys
display_model = AGENT_DISPLAY_MODELS.get(agent_type, "default")
cost_emoji = get_agent_emoji(agent_type)
short_desc = (description or prompt[:50]).strip()
print(f"{cost_emoji} SPAWNING_AGENT: {agent_type}:{display_model}('{short_desc}') ...", file=sys.stderr)
```

---

## Key Constants Available for Import

```python
# From mcp_bridge/tools/agent_manager.py
AGENT_MODEL_ROUTING = { ... }  # Maps agent_type to CLI model
AGENT_COST_TIERS = { ... }     # Maps agent_type to cost tier
AGENT_DISPLAY_MODELS = { ... } # Maps agent_type to display name
COST_TIER_EMOJI = { ... }      # Maps cost tier to emoji
MODEL_FAMILY_EMOJI = { ... }   # Maps model name to emoji

def get_agent_emoji(agent_type: str) -> str:  # Returns cost tier emoji
def get_model_emoji(model_name: str) -> str:  # Returns model emoji

# DelegationEnforcer functions
def set_delegation_enforcer(enforcer: DelegationEnforcer) -> None
def clear_delegation_enforcer() -> None
def get_delegation_enforcer() -> DelegationEnforcer | None
```

---

## Output Format Specification

Standardized format for all tool calls:

```
[EMOJI] [ACTION]: [AGENT_TYPE]:[MODEL]('[DESCRIPTION]') [STATUS]
```

Examples:
- `SPAWNING_AGENT: explore:gemini-3-flash('Find auth handler') ...`
- `GEMINI: gemini-3-flash | agent=explore task=agent_xyz | Find..`
- `OPENAI: gpt-5.2-codex | agent=delphi task=agent_abc | Analyze..`
- `TASK_SPAWN: gemini-3-flash('Generate README') spawned task_id=xyz`

Emoji meanings:
- `CHEAP` tier = Gemini Flash, Haiku
- `MEDIUM` tier = Gemini Pro High
- `EXPENSIVE` tier = GPT-5.2, Opus
- `CLAUDE` tier = Sonnet, Opus via CLI

---

## DelegationEnforcer Integration

### Purpose
Enforces hard parallel execution for independent tasks in the 7-phase orchestrator.

### How It Works

1. **During DELEGATE phase**: Orchestrator creates a TaskGraph and sets the DelegationEnforcer
2. **On agent_spawn**: If `task_graph_id` is provided, the spawn is validated against the graph
3. **Validation**: Independent tasks in the same wave MUST be spawned together
4. **Error**: If sequential spawn detected for parallel tasks, `ParallelExecutionError` is raised

### Integration Points

| File | Function | Purpose |
|------|----------|---------|
| `agent_manager.py` | `set_delegation_enforcer()` | Activate enforcer |
| `agent_manager.py` | `clear_delegation_enforcer()` | Deactivate after execution |
| `agent_manager.py` | `get_delegation_enforcer()` | Get current enforcer |
| `agent_manager.py` | `agent_spawn()` | Validate spawns with `task_graph_id` |

### Example Usage

```python
from mcp_bridge.tools.agent_manager import (
    agent_spawn,
    set_delegation_enforcer,
    clear_delegation_enforcer,
)
from mcp_bridge.orchestrator.task_graph import TaskGraph, DelegationEnforcer

# Create task graph with independent tasks
graph = TaskGraph()
task_a = graph.add_task("research_auth", dependencies=[])
task_b = graph.add_task("research_db", dependencies=[])  # Independent of A
task_c = graph.add_task("implement", dependencies=["research_auth", "research_db"])

# Set enforcer
enforcer = DelegationEnforcer(graph)
set_delegation_enforcer(enforcer)

try:
    # These MUST be spawned in the same response (parallel)
    await agent_spawn(prompt="Research auth", task_graph_id="research_auth")
    await agent_spawn(prompt="Research DB", task_graph_id="research_db")

    # Wait for both to complete before task_c
    # ...

    await agent_spawn(prompt="Implement", task_graph_id="implement")
finally:
    clear_delegation_enforcer()
```
