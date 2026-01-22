# Parallel Execution Fix - /strav Command Architecture

## Problem Summary

When users invoke `/strav` in other repositories, the system was "failing to use agents by default, opting for native Claude Read instead of agent_spawn."

## Root Cause

**Hook Context Mismatch** in `~/.claude/hooks/parallel_execution.py`

The hook was instructing the WRONG delegation tool for the execution context:

- **Stravinsky MCP Skill** (`/strav` command): Requires `agent_spawn()` (routes to Gemini/GPT)
- **Claude Native Agents** (`.claude/agents/`): Requires `Task()` (routes to Claude subagents)

**BUG:** Hook always instructed `Task()` regardless of context, causing:

1. Hook creates `~/.stravinsky_mode` marker
2. Hook blocks Read/Grep/Bash
3. **Hook instructs using `Task()`**
4. `/strav` skill says "NEVER use Task, use agent_spawn"
5. **Conflict**: Claude blocked from Read, told not to use Task, confused about agent_spawn
6. **Result**: Claude gives up, tries Read anyway, blocked, error loop, user sees "opting for native Read"

## The Fix (3 Parts)

### Part 1: Context-Aware Hook Instructions

**File:** `~/.claude/hooks/parallel_execution.py`

**Change:** Detect execution context and inject correct tool name

```python
# Before (WRONG - always used Task):
Use: Task(subagent_type="explore", ...)

# After (CORRECT - context-aware):
if is_stravinsky:  # /strav MCP skill
    tool_name = "agent_spawn"
    tool_params = 'agent_type="explore"|"dewey"|...'
else:  # Native agents
    tool_name = "Task"
    tool_params = 'subagent_type="Explore"|...'
```

**Effect:** Hook now injects the RIGHT instructions based on whether `/strav` was invoked.

### Part 2: Cleanup Instructions

**File:** `.claude/commands/strav.md`

**Change:** Added cleanup step to remove marker file when task completes

```markdown
Before final answer:
1. Cancel ALL running agents via `agent_cancel`
2. Cleanup stravinsky mode: Run `python3 -c "from pathlib import Path; Path.home().joinpath('.stravinsky_mode').unlink(missing_ok=True); print('Stravinsky mode deactivated')"`
```

**Effect:** Prevents marker file from persisting across sessions and blocking tools in subsequent work.

### Part 3: Detection Keywords

**File:** `~/.claude/hooks/parallel_execution.py`

**Existing:** Already had detection for `/stravinsky` and `ultrawork`

```python
patterns = [
    r"/stravinsky",
    r"<command-name>/stravinsky</command-name>",
    r"stravinsky orchestrator",
    r"\bultrawork\b",  # "ultrawork" mode trigger
]
```

**Effect:** Activates stravinsky mode when user includes "ultrawork" in their prompt.

## How It Works Now

### Before Fix (BROKEN)

```
User: /strav implement feature X
    |
Hook: Create ~/.stravinsky_mode
Hook: Inject "Use Task()"
    |
Claude reads /strav prompt: "NEVER use Task"
Claude blocked from Read/Grep/Bash
    |
CONFLICT: Can't use Read (blocked), told not to use Task
    |
Claude confused -> tries Read -> error -> "opting for native Read"
```

### After Fix (WORKING)

```
User: /strav implement feature X
    |
Hook: Detect /strav -> is_stravinsky = True
Hook: Create ~/.stravinsky_mode
Hook: Inject "Use agent_spawn()"
    |
Claude reads /strav prompt: "Use agent_spawn"
Claude blocked from Read/Grep/Bash
    |
ALIGNMENT: Can't use Read (blocked), USE agent_spawn
    |
Claude: TodoWrite -> agent_spawn x 4 (parallel)
```

---

## Hard Parallel Enforcement (NEW)

In addition to the hook-based soft enforcement, Stravinsky now includes a **hard enforcement** system that programmatically validates and blocks sequential execution of independent tasks.

### Architecture Overview

The hard enforcement system consists of three components:

1. **TaskGraph** - Directed Acyclic Graph of tasks with dependencies
2. **DelegationEnforcer** - Runtime validator for parallel execution
3. **agent_spawn Integration** - Enforcement at the spawn point

### TaskGraph

**File:** `mcp_bridge/orchestrator/task_graph.py`

The TaskGraph models task dependencies as a DAG and computes execution "waves" - groups of tasks that can run in parallel.

```python
from mcp_bridge.orchestrator.task_graph import TaskGraph

# Create a task graph from a dictionary
graph = TaskGraph.from_dict({
    "research": {
        "description": "Research codebase patterns",
        "agent_type": "explore",
        "depends_on": []
    },
    "docs": {
        "description": "Research documentation",
        "agent_type": "dewey",
        "depends_on": []
    },
    "implement": {
        "description": "Implement the feature",
        "agent_type": "frontend",
        "depends_on": ["research", "docs"]
    }
})

# Get execution waves
waves = graph.get_independent_groups()
# Wave 1: [research, docs]  <- MUST run in parallel
# Wave 2: [implement]       <- runs after wave 1 completes
```

**Key Methods:**

| Method | Description |
|--------|-------------|
| `from_dict(data)` | Create graph from task definitions |
| `add_task(id, description, agent_type, dependencies)` | Add a task to the graph |
| `get_ready_tasks()` | Get tasks with all dependencies satisfied |
| `get_independent_groups()` | Return execution waves for parallel scheduling |
| `mark_spawned(task_id, agent_task_id)` | Record task spawn with agent ID |
| `mark_completed(task_id)` | Mark task as completed |
| `to_dict()` | Serialize graph for persistence |

### DelegationEnforcer

The DelegationEnforcer validates that independent tasks are spawned within a time window, ensuring true parallel execution.

```python
from mcp_bridge.orchestrator.task_graph import TaskGraph, DelegationEnforcer

# Create graph and enforcer
graph = TaskGraph.from_dict({
    "research": {"agent_type": "explore", "depends_on": []},
    "docs": {"agent_type": "dewey", "depends_on": []},
    "implement": {"agent_type": "frontend", "depends_on": ["research", "docs"]}
})

enforcer = DelegationEnforcer(
    task_graph=graph,
    parallel_window_ms=500,  # Max 500ms between parallel spawns
    strict=True              # Raise ParallelExecutionError on violations
)
```

**Configuration:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `task_graph` | Required | The TaskGraph to enforce |
| `parallel_window_ms` | 500 | Maximum time (ms) between spawns of independent tasks |
| `strict` | True | If True, raises `ParallelExecutionError` on violations |

**Key Methods:**

| Method | Description |
|--------|-------------|
| `get_current_wave()` | Get the current wave of tasks to spawn |
| `validate_spawn(task_id)` | Check if spawning a task is allowed |
| `record_spawn(task_id, agent_task_id)` | Record spawn time for compliance checking |
| `check_parallel_compliance()` | Verify wave was spawned in parallel |
| `advance_wave()` | Move to next execution wave |
| `mark_task_completed(task_id)` | Mark complete and auto-advance if wave done |
| `get_enforcement_status()` | Get debugging status dict |

### Integration with agent_spawn

The `agent_spawn` function integrates with the enforcer via a new `task_graph_id` parameter.

**File:** `mcp_bridge/tools/agent_manager.py`

```python
from mcp_bridge.tools.agent_manager import (
    agent_spawn,
    set_delegation_enforcer,
    clear_delegation_enforcer,
    get_delegation_enforcer,
)
from mcp_bridge.orchestrator.task_graph import TaskGraph, DelegationEnforcer

# 1. Create task graph
graph = TaskGraph.from_dict({
    "research": {"agent_type": "explore", "depends_on": []},
    "docs": {"agent_type": "dewey", "depends_on": []},
})

# 2. Create and activate enforcer
enforcer = DelegationEnforcer(task_graph=graph, strict=True)
set_delegation_enforcer(enforcer)

# 3. Spawn agents with task_graph_id
# These MUST be spawned in parallel (within 500ms of each other)
task_id_1 = await agent_spawn(
    prompt="Research codebase",
    agent_type="explore",
    task_graph_id="research"  # Links to TaskGraph task
)
task_id_2 = await agent_spawn(
    prompt="Research docs",
    agent_type="dewey",
    task_graph_id="docs"
)

# 4. Check compliance and advance wave
is_compliant, error = enforcer.check_parallel_compliance()
if is_compliant:
    enforcer.advance_wave()

# 5. Clear enforcer when done
clear_delegation_enforcer()
```

### Enforcement Behavior

When enforcement is active, the following rules apply:

**Validation Rules:**

1. **Task must exist** in the TaskGraph
2. **Task must be in current wave** (dependencies satisfied)
3. **Future wave tasks are blocked** until dependencies complete

**Compliance Rules:**

1. **Single-task waves** always pass (no parallelism required)
2. **Multi-task waves** must spawn within `parallel_window_ms`
3. **Time spread** = `max(spawn_times) - min(spawn_times)`
4. If time spread > window, compliance fails

**Strict Mode:**

When `strict=True`, violations raise `ParallelExecutionError`:

```python
from mcp_bridge.orchestrator.task_graph import ParallelExecutionError

try:
    # Sequential spawns of independent tasks
    enforcer.record_spawn("a", "task-a")
    time.sleep(1.0)  # > 500ms default window
    enforcer.record_spawn("b", "task-b")
    enforcer.advance_wave()
except ParallelExecutionError as e:
    print(f"Blocked: {e}")
    # "Tasks in wave were not spawned in parallel.
    #  Time spread: 1000ms > 500ms limit.
    #  Independent tasks MUST be spawned simultaneously."
```

### TaskStatus Enum

Tasks transition through the following statuses:

```python
class TaskStatus(Enum):
    PENDING = "pending"      # Not yet spawned
    SPAWNED = "spawned"      # Spawned, waiting for completion
    RUNNING = "running"      # Actively executing
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"        # Execution failed
```

---

## Testing

### Test 1: /strav Command

```bash
# In any repo (even without .stravinsky/ folder)
/strav implement parallel execution for task X and Y
```

**Expected:**
1. Hook creates `~/.stravinsky_mode`
2. Hook injects `agent_spawn` instructions
3. Claude uses `agent_spawn()` for delegation
4. No "opting for native Read" errors

### Test 2: Native Agent (No /strav)

```bash
# Regular implementation request (no /strav)
implement feature X
```

**Expected:**
1. Hook detects implementation keywords
2. Hook injects `Task()` instructions (NOT agent_spawn)
3. Claude uses `Task()` for delegation
4. No marker file created

### Test 3: Cleanup

```bash
# After /strav task completes
# Claude should run cleanup command
```

**Expected:**
1. `~/.stravinsky_mode` removed
2. Subsequent sessions don't have blocked tools

### Test 4: Hard Enforcement (Unit Tests)

```bash
pytest tests/test_parallel_enforcement.py -v
```

**Test Cases:**
- `test_create_task_graph` - Graph creation from dictionary
- `test_get_ready_tasks` - Task readiness with dependencies
- `test_get_independent_groups` - Wave computation
- `test_validate_spawn_valid` - Valid spawn allowed
- `test_validate_spawn_invalid_dependency` - Blocked on unmet deps
- `test_parallel_compliance_success` - Parallel spawns pass
- `test_parallel_compliance_failure` - Sequential spawns fail
- `test_strict_mode_raises` - ParallelExecutionError raised
- `test_set_and_get_enforcer` - Global enforcer integration

---

## Architecture Diagram

```
+--------------------------------------------------+
| User Input                                       |
|  +-- "/strav implement X"                        |
|  +-- "implement X" (no /strav)                   |
+-----------------------+--------------------------+
                        |
                        v
+--------------------------------------------------+
| UserPromptSubmit Hook                            |
|  ~/.claude/hooks/parallel_execution.py           |
|                                                  |
|  +----------------------------------------+      |
|  | 1. Detect context:                     |      |
|  |    is_stravinsky = detect_stravinsky() |      |
|  +-------------------+--------------------+      |
|                      |                           |
|    +-----------------+----------------+          |
|    v                                  v          |
|  TRUE                              FALSE         |
|  (MCP Skill)                       (Native)      |
|    |                                  |          |
|    +-- Create marker file             |          |
|    |   (~/.stravinsky_mode)           |          |
|    |                                  |          |
|    +-- tool = "agent_spawn"           +-- tool = "Task"
|    |   params = agent_type=...        |   params = subagent_type=...
|    +-----------------+----------------+          |
|                      |                           |
|  +-------------------v--------------------+      |
|  | 2. Inject instruction with correct tool|      |
|  +----------------------------------------+      |
+-----------------------+--------------------------+
                        |
                        v
+--------------------------------------------------+
| Modified Prompt (with injected instructions)     |
|  "[PARALLEL MODE] Use {tool_name}()..."          |
+-----------------------+--------------------------+
                        |
                        v
+--------------------------------------------------+
| Claude Response Generation                       |
|  +-- Reads skill/agent prompt                    |
|  +-- Sees injected instructions (correct tool)  |
|  +-- Creates TodoWrite + multiple agent_spawn   |
+-----------------------+--------------------------+
                        |
                        v
+--------------------------------------------------+
| Hard Enforcement Layer (NEW)                     |
|  mcp_bridge/orchestrator/task_graph.py           |
|                                                  |
|  +----------------------------------------+      |
|  | TaskGraph                              |      |
|  |  +-- from_dict(task_definitions)       |      |
|  |  +-- get_independent_groups() -> waves |      |
|  +-------------------+--------------------+      |
|                      |                           |
|  +-------------------v--------------------+      |
|  | DelegationEnforcer                     |      |
|  |  +-- validate_spawn(task_id)           |      |
|  |  +-- record_spawn(task_id, agent_id)   |      |
|  |  +-- check_parallel_compliance()       |      |
|  |  +-- parallel_window_ms=500            |      |
|  |  +-- strict=True -> raises error       |      |
|  +----------------------------------------+      |
+-----------------------+--------------------------+
                        |
                        v
+--------------------------------------------------+
| PreToolUse Hook (stravinsky_mode.py)             |
|  Blocks: Read, Grep, Bash (if marker exists)     |
|  Allows: agent_spawn, Task, invoke_*             |
+-----------------------+--------------------------+
                        |
                        v
+--------------------------------------------------+
| agent_spawn Integration                          |
|  mcp_bridge/tools/agent_manager.py               |
|                                                  |
|  +----------------------------------------+      |
|  | agent_spawn(task_graph_id="research")  |      |
|  |  +-- get_delegation_enforcer()         |      |
|  |  +-- enforcer.validate_spawn(id)       |      |
|  |  +-- spawn agent                       |      |
|  |  +-- enforcer.record_spawn(id, task)   |      |
|  +----------------------------------------+      |
+-----------------------+--------------------------+
                        |
                        v
+--------------------------------------------------+
| PostToolUse Hook (todo_delegation.py)            |
|  After TodoWrite: Enforces immediate delegation  |
+-----------------------+--------------------------+
                        |
                        v
+--------------------------------------------------+
| Parallel Execution                               |
|  agent_spawn() x N (if /strav)                   |
|  Task() x N (if native)                          |
|                                                  |
| ENFORCEMENT: Independent tasks spawn within      |
| 500ms or ParallelExecutionError is raised        |
+--------------------------------------------------+
```

---

## Key Takeaways

1. **Two Execution Contexts**:
   - MCP Skill (`/strav`): Use `agent_spawn()` -> Gemini/GPT
   - Native Agent: Use `Task()` -> Claude subagents

2. **Hook Coordination**:
   - `parallel_execution.py`: Detects context, creates marker, injects instructions
   - `stravinsky_mode.py`: Blocks direct tools when marker exists
   - `todo_delegation.py`: Enforces immediate delegation after TodoWrite

3. **Hard Enforcement**:
   - `TaskGraph`: Models dependencies as DAG, computes parallel waves
   - `DelegationEnforcer`: Validates spawns, checks time windows, blocks violations
   - Integration: `agent_spawn(task_graph_id=...)` links to enforcer

4. **Cost Optimization**:
   - `agent_spawn` routes to Gemini Flash ($0.075/1M) vs Claude Sonnet ($3/1M)
   - Multi-model routing is the whole point of Stravinsky MCP

5. **The Original Bug Was Simple**:
   - Hook always said "use Task"
   - Skill said "never use Task, use agent_spawn"
   - Confusion -> fallback to Read -> blocked -> error loop

6. **The Fixes Are Simple**:
   - Make hook context-aware (soft enforcement)
   - Add TaskGraph + DelegationEnforcer (hard enforcement)
   - Block sequential spawns of independent tasks programmatically

---

## Files Reference

### Core Enforcement

| File | Purpose |
|------|---------|
| `mcp_bridge/orchestrator/task_graph.py` | TaskGraph and DelegationEnforcer classes |
| `mcp_bridge/tools/agent_manager.py` | agent_spawn integration, enforcer globals |
| `tests/test_parallel_enforcement.py` | Unit tests for enforcement system |

### Hooks (Soft Enforcement)

| File | Purpose |
|------|---------|
| `~/.claude/hooks/parallel_execution.py` | Context detection, instruction injection |
| `~/.claude/hooks/stravinsky_mode.py` | Tool blocking when marker exists |
| `~/.claude/hooks/todo_delegation.py` | Post-TodoWrite delegation enforcement |

### Configuration

| File | Purpose |
|------|---------|
| `.claude/commands/strav.md` | /strav skill definition with cleanup |
| `~/.stravinsky_mode` | Marker file for stravinsky mode activation |
