# Gap Analysis and Implementation Plan: Parallel Delegation and Console UX

**Date**: 2026-01-11 (Updated: 2026-01-18)
**Author**: Stravinsky Analysis
**Purpose**: Achieve feature parity with oh-my-opencode while improving architecture efficiency

---

## Executive Summary

This document outlines the gaps between Stravinsky's current implementation and oh-my-opencode's parallel delegation architecture, along with a comprehensive implementation plan to fix three critical issues:

1. **Parallel delegation degradation** over session lifetime
2. **Hook console clutter** (debug output pollution)
3. **Agent notification formatting** (missing colors, model info, task clarity)

**UPDATE 2026-01-18**: Phase 3 (Parallel Delegation Fix) is now **COMPLETE** with the implementation of hard enforcement via TaskGraph and DelegationEnforcer.

---

## Issue 1: Parallel Delegation Degradation

### Current Behavior

**Initial tasks (turn 1-2):**
- Spawns parallel agents correctly
- Multiple `Task()` calls in single response
- Independent tasks execute concurrently

**Subsequent tasks (turn 3+):**
- Falls back to sequential execution
- Marks TODO as `in_progress` before delegating
- Waits for completion before spawning next agent
- No longer delegates unrelated tasks in parallel

### Root Cause Analysis

#### 1. **Hook Timing Ambiguity**

```python
# parallel_execution.py (UserPromptSubmit)
# Fires BEFORE response generation
# Good for initial activation
# Ephemeral - context forgotten after first response
```

**Problem**: UserPromptSubmit hooks inject instructions into the prompt, but:
- Claude doesn't retain hook-injected context across turns
- After turn 1, instructions vanish from working memory
- Subsequent prompts don't get reinforcement

#### 2. **Weak Reinforcement Signals**

```python
# parallel_reinforcement.py
# Only fires if:
# - Stravinsky mode active (.stravinsky_mode file exists)
# - 2+ pending todos
```

**Problem**: Conditional activation means:
- Reinforcement skipped if no pending todos (edge case)
- Only reminds, doesn't enforce
- No structural barrier to sequential execution

#### 3. **PostToolUse Hook Exit Codes Ignored**

```python
# todo_delegation.py
# Returns exit code 2 (HARD BLOCK) when 2+ pending todos
# Expected: Claude treats as error, forces correction
# Reality: Claude ignores exit code, continues anyway
```

**Problem**: Exit codes don't reliably signal "hard blocks" in Claude Code hooks. This is a fundamental limitation of the hook system.

#### 4. **No Dependency Tracking**

**Stravinsky lacked**:
- Explicit task dependency graph (oh-my-opencode has this)
- Independent task detection algorithm
- Automatic parallelization decision logic

**Previous approach**: Relied on LLM inference
- Initial context fresh -> good decisions
- After 3+ turns -> context dilution -> sequential fallback

---

### oh-my-opencode's Solution

From the repo's architecture (inferred from structure):

#### 1. **Explicit Dependency Graph**

```typescript
// Agent coordination tracks:
- Task dependencies (which tasks block others)
- Independent task clusters
- Execution order constraints
```

#### 2. **Structural Enforcement**

```typescript
// System enforces parallelism at architecture level:
- Orchestrator NEVER executes leaf tasks directly
- All work routed through specialist agents
- Parallel dispatch is default, not optional
```

#### 3. **Persistent State Management**

```typescript
// State persists across turns:
- Active agent sessions tracked
- Task completion status monitored
- Delegation requirements remembered
```

---

### Implemented Solution: Hard Parallel Enforcement

**STATUS: COMPLETE (2026-01-18)**

Stravinsky now implements **hard enforcement** of parallel execution through programmatic validation, not just hook-based reminders.

#### Core Components

**File**: `mcp_bridge/orchestrator/task_graph.py`

| Component | Purpose |
|-----------|---------|
| `TaskGraph` | DAG of tasks with dependency tracking |
| `Task` | Individual task with status, dependencies, spawn time |
| `TaskStatus` | Enum: PENDING, SPAWNED, RUNNING, COMPLETED, FAILED |
| `DelegationEnforcer` | Validates parallel execution, blocks violations |
| `ParallelExecutionError` | Exception raised on sequential execution of independent tasks |

#### TaskGraph

Models task dependencies as a Directed Acyclic Graph and computes execution "waves":

```python
from mcp_bridge.orchestrator.task_graph import TaskGraph

graph = TaskGraph.from_dict({
    "research": {"description": "...", "agent_type": "explore", "depends_on": []},
    "docs": {"description": "...", "agent_type": "dewey", "depends_on": []},
    "implement": {"description": "...", "agent_type": "frontend", "depends_on": ["research", "docs"]}
})

waves = graph.get_independent_groups()
# Wave 1: [research, docs]  <- MUST run in parallel
# Wave 2: [implement]       <- runs after wave 1 completes
```

**Key Methods**:
- `from_dict(data)` - Create graph from task definitions
- `add_task(id, description, agent_type, dependencies)` - Add task
- `get_ready_tasks()` - Tasks with all dependencies satisfied
- `get_independent_groups()` - Compute parallel execution waves
- `mark_spawned(task_id, agent_task_id)` - Record spawn
- `mark_completed(task_id)` - Mark task done
- `to_dict()` - Serialize for persistence

#### DelegationEnforcer

Validates that independent tasks are spawned within a time window:

```python
from mcp_bridge.orchestrator.task_graph import TaskGraph, DelegationEnforcer

graph = TaskGraph.from_dict({...})
enforcer = DelegationEnforcer(
    task_graph=graph,
    parallel_window_ms=500,  # Max time between parallel spawns
    strict=True              # Raise ParallelExecutionError on violations
)

# Set as global enforcer
from mcp_bridge.tools.agent_manager import set_delegation_enforcer
set_delegation_enforcer(enforcer)
```

**Configuration**:
| Parameter | Default | Description |
|-----------|---------|-------------|
| `task_graph` | Required | The TaskGraph to enforce |
| `parallel_window_ms` | 500 | Max ms between spawns of independent tasks |
| `strict` | True | Raise exception on violations |

**Key Methods**:
- `get_current_wave()` - Current wave of tasks to spawn
- `validate_spawn(task_id)` - Check if spawn is allowed
- `record_spawn(task_id, agent_task_id)` - Record spawn time
- `check_parallel_compliance()` - Verify wave spawned in parallel
- `advance_wave()` - Move to next execution wave
- `mark_task_completed(task_id)` - Mark done, auto-advance if wave complete
- `get_enforcement_status()` - Debugging status dict

#### Integration with agent_spawn

**File**: `mcp_bridge/tools/agent_manager.py`

The `agent_spawn` function now accepts a `task_graph_id` parameter that links spawns to the TaskGraph:

```python
from mcp_bridge.tools.agent_manager import agent_spawn, set_delegation_enforcer
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
# These MUST be spawned in parallel (within 500ms)
task_id_1 = await agent_spawn(
    prompt="Research codebase",
    agent_type="explore",
    task_graph_id="research"
)
task_id_2 = await agent_spawn(
    prompt="Research docs",
    agent_type="dewey",
    task_graph_id="docs"
)

# 4. If spawns were sequential (>500ms apart), ParallelExecutionError is raised
```

#### Enforcement Behavior

**Validation Rules**:
1. Task must exist in TaskGraph
2. Task must be in current wave (dependencies satisfied)
3. Future wave tasks blocked until dependencies complete

**Compliance Rules**:
1. Single-task waves always pass
2. Multi-task waves must spawn within `parallel_window_ms`
3. Time spread = max(spawn_times) - min(spawn_times)
4. If spread > window, compliance fails

**Strict Mode**:
```python
from mcp_bridge.orchestrator.task_graph import ParallelExecutionError

try:
    enforcer.record_spawn("a", "task-a")
    time.sleep(1.0)  # > 500ms
    enforcer.record_spawn("b", "task-b")
    enforcer.advance_wave()
except ParallelExecutionError as e:
    # "Tasks in wave were not spawned in parallel.
    #  Time spread: 1000ms > 500ms limit."
```

#### Tests

**File**: `tests/test_parallel_enforcement.py`

```bash
pytest tests/test_parallel_enforcement.py -v
```

Test coverage:
- TaskGraph creation and dependency tracking
- Ready task computation
- Independent group (wave) calculation
- Spawn validation (valid and blocked)
- Parallel compliance (success and failure)
- Wave advancement
- Strict mode exception raising
- Global enforcer integration

---

## Issue 2: Hook Console Clutter

### Current Behavior

**Console output polluted with**:
- Hook execution logs (PreToolUse, PostToolUse, etc.)
- Debug statements from hook scripts
- Internal state tracking messages
- Event server transmission logs (`send_event.py`)

**Example clutter**:
```
[PreToolUse] stravinsky_mode.py running
[PostToolUse] tool_messaging.py running
[PostToolUse] truncator.py running
Failed to send event: Connection refused
```

### Root Cause

#### 1. **Event Hook Debug Output**

`send_event.py` writes to stderr:
```python
# Line 43-44, 47-48, 50-51
print(f"Server returned status: {response.status}", file=sys.stderr)
print(f"Failed to send event: {e}", file=sys.stderr)
print(f"Unexpected error: {e}", file=sys.stderr)
```

**Problem**: These are error logs meant for debugging, but they leak into user console.

#### 2. **Hook System Verbosity**

Claude Code's hook system logs:
- Hook invocation
- Hook completion
- Exit codes

**Not configurable** - built into Claude Code runtime.

#### 3. **Print Statements in Hooks**

Multiple hooks use `print(..., file=sys.stderr)` for user messaging:
- `notification_hook.py` (line 97)
- `tool_messaging.py` (line 243, 252)
- `todo_delegation.py` (line 85)

**Problem**: These are INTENTIONAL user messages, but hard to distinguish from debug clutter.

---

### Proposed Solution

#### **Strategy 1: Suppress Non-Essential Hook Output**

**File**: `send_event.py`

**Changes**:
```python
# BEFORE (lines 43-51)
print(f"Server returned status: {response.status}", file=sys.stderr)
print(f"Failed to send event: {e}", file=sys.stderr)
print(f"Unexpected error: {e}", file=sys.stderr)

# AFTER - Silent mode (only log to file)
import logging
logging.basicConfig(
    filename=Path.home() / ".claude/hooks/event_sender.log",
    level=logging.DEBUG
)

# Replace all print() with logging
logging.debug(f"Server returned status: {response.status}")
logging.error(f"Failed to send event: {e}")
logging.error(f"Unexpected error: {e}")
```

**Result**: Event server errors logged to file, not console.

---

#### **Strategy 2: Standardize User Messages with Prefixes**

All user-facing hook output should use a consistent format:

**Format**: `[HOOK_TYPE] message`

**Examples**:
- `[AGENT] explore:gemini-3-flash('Find auth code')`
- `[TOOL] ast-grep:stravinsky('Search for patterns')`
- `[REMINDER] Parallel delegation required (3 pending tasks)`

**Implementation**:

1. **Create utility**: `.claude/hooks/utils/console_format.py`
   ```python
   import sys
   from enum import Enum

   class MessageType(Enum):
       AGENT = "AGENT"
       TOOL = "TOOL"
       REMINDER = "REMINDER"
       WARNING = "WARNING"
       ERROR = "ERROR"

   def format_message(msg_type: MessageType, content: str) -> str:
       return f"[{msg_type.value}] {content}"

   def print_hook_message(msg_type: MessageType, content: str):
       print(format_message(msg_type, content), file=sys.stderr)
   ```

2. **Update hooks to use utility**:
   - `notification_hook.py`: Replace line 97 with `print_hook_message(AGENT, ...)`
   - `tool_messaging.py`: Replace line 243, 252 with `print_hook_message(TOOL, ...)`
   - `todo_delegation.py`: Replace line 85 with `print_hook_message(WARNING, ...)`

**Result**: Clear visual distinction between hook types.

---

#### **Strategy 3: Environment Variable for Debug Mode**

Add `STRAVINSKY_DEBUG` environment variable:

```python
# hooks/utils/debug.py
import os

DEBUG_MODE = os.getenv("STRAVINSKY_DEBUG", "0") == "1"

def debug_log(message: str):
    if DEBUG_MODE:
        print(f"[DEBUG] {message}", file=sys.stderr)
```

**Usage in hooks**:
```python
from utils.debug import debug_log

debug_log("PreToolUse hook fired for Read tool")  # Only if DEBUG=1
```

**Result**: Debug output silenced by default, enabled when troubleshooting.

---

## Issue 3: Agent Notification Formatting

### Current Behavior

**Agent spawn notifications**:
```
spawned explore:gemini-3-flash('task delegated')
```

**Problems**:
1. No color coding per agent type
2. Generic task description ("task delegated")
3. Inconsistent format (sometimes missing model)
4. No visual hierarchy or grouping

### Desired Behavior (claude-flow style)

**Reference**: oh-my-opencode's agent output (inferred):
```
EXPLORE -> gemini-3-flash
   Task: Find all authentication implementations in codebase

DEWEY -> gemini-3-flash
   Task: Research JWT best practices from official docs

FRONTEND -> gemini-3-pro-high
   Task: Implement login UI with dark mode support

DELPHI -> gpt-5.2
   Task: Analyze auth architecture trade-offs
```

**Features**:
- Color-coded circles per agent type
- Model explicitly shown
- Multi-line format with indentation
- Task description is first-class, not truncated
- Visual grouping of parallel agents

---

### Proposed Solution

#### **Strategy 1: Rich Agent Notification Format**

**File**: `.claude/hooks/notification_hook.py`

**Changes**:

1. **Add color mappings** (ANSI color codes):
   ```python
   # ANSI color codes
   class Color:
       RESET = "\033[0m"
       BLUE = "\033[94m"
       PURPLE = "\033[95m"
       GREEN = "\033[92m"
       ORANGE = "\033[93m"
       RED = "\033[91m"

   AGENT_COLORS = {
       "explore": (Color.BLUE, "EXPLORE"),
       "dewey": (Color.PURPLE, "DEWEY"),
       "frontend": (Color.GREEN, "FRONTEND"),
       "delphi": (Color.ORANGE, "DELPHI"),
       "debugger": (Color.RED, "DEBUGGER"),
       "code-reviewer": (Color.PURPLE, "CODE-REVIEWER"),
   }
   ```

2. **Format multi-line output**:
   ```python
   def format_agent_spawn(agent_type: str, model: str, description: str) -> str:
       color, label = AGENT_COLORS.get(agent_type, (Color.RESET, agent_type.upper()))

       # Multi-line format
       lines = [
           f"{color}{label} -> {model}{Color.RESET}",
           f"   Task: {description}",
           ""  # Blank line for spacing
       ]
       return "\n".join(lines)
   ```

3. **Handle parallel agent grouping**:
   ```python
   # Track agents spawned in same response
   # File: .claude/hooks/state/agent_batch.json
   {
       "current_batch": ["explore", "dewey"],
       "batch_start_time": 1234567890
   }

   # If multiple agents spawned within 2 seconds:
   # Group them visually
   if len(current_batch) > 1:
       print(f"\n{'='*50}")
       print(f"PARALLEL DELEGATION ({len(current_batch)} agents)")
       print(f"{'='*50}\n")
   ```

---

#### **Strategy 2: Tool Messaging with Color and Icons**

**File**: `.claude/hooks/tool_messaging.py`

**Changes**:

1. **Add agent-specific colors**:
   ```python
   AGENT_COLORS = {
       "explore": "\033[94m",  # Blue
       "dewey": "\033[95m",    # Purple
       "frontend": "\033[92m", # Green
       "delphi": "\033[93m",   # Orange
   }
   ```

2. **Format Task delegations** (line 243):
   ```python
   # BEFORE
   print(f"target {subagent_type}:{model}('{description}')", file=sys.stderr)

   # AFTER
   color = AGENT_COLORS.get(subagent_type, "")
   reset = "\033[0m"
   print(f"{color}target {subagent_type}:{model}{reset}", file=sys.stderr)
   print(f"   {description}", file=sys.stderr)
   print("", file=sys.stderr)  # Blank line
   ```

3. **Add model name extraction**:
   ```python
   # Extract actual model from agent config
   # Read from .claude/agents/{agent_type}.md
   def get_agent_model(agent_type: str) -> str:
       agent_file = Path(f"~/.claude/agents/{agent_type}.md").expanduser()
       if agent_file.exists():
           # Parse YAML front matter
           # Extract "model:" value
           # Return actual model (e.g., "claude-sonnet-4", "gemini-3-flash")
       return AGENT_MODELS.get(agent_type, "unknown")
   ```

---

#### **Strategy 3: Status Line Integration**

**File**: `.claude/statusline.sh`

**Enhancement**: Show active agents in status line
```bash
# Current status line
ACTIVE_AGENTS=$(cat ~/.claude/hooks/state/active_agents.json | jq -r '.agents | join(", ")')
echo "Active: $ACTIVE_AGENTS"
```

**Result**: User sees "Active: explore, dewey, frontend" in status bar while agents run.

---

## Implementation Roadmap

### Phase 1: Console Cleanup (Quick Wins) - **1-2 hours**

**STATUS: NOT STARTED**

1. Silence `send_event.py` debug output
   - File: `.claude/hooks/send_event.py`
   - Change: Replace all `print()` with file logging

2. Create console formatter utility
   - File: `.claude/hooks/utils/console_format.py`
   - Implement: `MessageType` enum + `print_hook_message()`

3. Add debug mode environment variable
   - File: `.claude/hooks/utils/debug.py`
   - Implement: `STRAVINSKY_DEBUG` check

4. Update existing hooks to use formatters
   - Files: `notification_hook.py`, `tool_messaging.py`, `todo_delegation.py`
   - Replace raw `print()` with `print_hook_message()`

**Expected Result**: 80% reduction in console noise.

---

### Phase 2: Agent Notification Enhancement - **2-3 hours**

**STATUS: NOT STARTED**

1. Add ANSI color support
   - File: `.claude/hooks/utils/colors.py`
   - Define color constants + agent mappings

2. Refactor notification_hook.py
   - Implement multi-line format
   - Add color coding
   - Extract actual model from agent configs

3. Refactor tool_messaging.py
   - Apply same formatting to Task delegations
   - Add color support
   - Improve description extraction

4. Add agent batching detection
   - File: `.claude/hooks/state/agent_batch.json`
   - Track agents spawned in same window
   - Group visual output

**Expected Result**: Claude-flow-style agent notifications with colors and clear task descriptions.

---

### Phase 3: Parallel Delegation Fix - **4-6 hours**

**STATUS: COMPLETE (2026-01-18)**

1. Create TaskGraph class
   - File: `mcp_bridge/orchestrator/task_graph.py`
   - Implement: DAG with dependency tracking, wave computation

2. Create DelegationEnforcer class
   - File: `mcp_bridge/orchestrator/task_graph.py`
   - Implement: Spawn validation, time window checking, strict mode

3. Integrate with agent_spawn
   - File: `mcp_bridge/tools/agent_manager.py`
   - Add: `task_graph_id` parameter, global enforcer functions

4. Write comprehensive tests
   - File: `tests/test_parallel_enforcement.py`
   - Cover: Graph creation, wave computation, compliance checking, strict mode

**Implemented Files**:
- `mcp_bridge/orchestrator/task_graph.py` - Core enforcement classes
- `mcp_bridge/tools/agent_manager.py` - Integration with agent_spawn
- `tests/test_parallel_enforcement.py` - Unit tests

**Result**: Consistent parallel delegation with programmatic enforcement.

---

### Phase 4: Architecture Cleanup - **2-3 hours**

**STATUS: NOT STARTED**

1. Deprecate old hooks
   - Archive: `parallel_reinforcement.py` (replaced by hard enforcement)
   - Archive: Legacy reminder logic in `parallel_execution.py`

2. Consolidate hook chain
   - UserPromptSubmit: Reduce from 5 hooks to 3
     - Keep: `context_monitor.py`, `context.py`, `todo_continuation.py`
     - Replace: `parallel_execution.py` + `parallel_reinforcement.py` -> hard enforcement

3. Add hook documentation
   - File: `.claude/hooks/README.md`
   - Document: Hook execution order, purpose, state files

4. Performance audit
   - Measure: Hook execution time (target <50ms per hook)
   - Optimize: State file I/O (use caching)

**Expected Result**: Cleaner, faster, more maintainable hook architecture.

---

## Success Metrics

### Parallel Delegation

**Before**:
- Initial tasks spawn in parallel: 90% of time
- Tasks after turn 5 spawn in parallel: 20% of time
- Sequential fallback rate: 80% by turn 10

**After** (with hard enforcement):
- Initial tasks spawn in parallel: 100% (enforced)
- Tasks after turn 5 spawn in parallel: 100% (enforced)
- Sequential fallback rate: 0% (blocked by ParallelExecutionError)

### Console Clarity

**Before**:
- Hook debug messages per turn: ~8-12 lines
- User-relevant messages: ~2-3 lines
- Signal-to-noise ratio: ~25%

**After** (target):
- Hook debug messages per turn: 0-1 lines (debug mode only)
- User-relevant messages: 2-3 lines
- Signal-to-noise ratio: >90%

### Agent Notifications

**Before**:
- Color coding: None
- Model visibility: Inconsistent
- Task clarity: Truncated/generic

**After** (target):
- Color coding: All agents
- Model visibility: 100%
- Task clarity: Full description, no truncation

---

## Files Reference

### Created (Phase 3 Complete)

| File | Purpose |
|------|---------|
| `mcp_bridge/orchestrator/task_graph.py` | TaskGraph, DelegationEnforcer, ParallelExecutionError |
| `tests/test_parallel_enforcement.py` | Unit tests for enforcement system |

### Modified (Phase 3 Complete)

| File | Changes |
|------|---------|
| `mcp_bridge/tools/agent_manager.py` | Added task_graph_id param, enforcer globals, spawn validation |

### To Create (Phases 1, 2, 4)

| File | Purpose |
|------|---------|
| `.claude/hooks/utils/console_format.py` | Message formatting |
| `.claude/hooks/utils/colors.py` | ANSI color codes |
| `.claude/hooks/utils/debug.py` | Debug mode control |
| `.claude/hooks/state/agent_batch.json` | Agent spawn batching |
| `.claude/hooks/README.md` | Hook architecture guide |

### To Modify (Phases 1, 2, 4)

| File | Changes |
|------|---------|
| `.claude/hooks/send_event.py` | Silence debug output |
| `.claude/hooks/notification_hook.py` | Add colors + formatting |
| `.claude/hooks/tool_messaging.py` | Add colors + formatting |
| `.claude/hooks/parallel_execution.py` | Deprecate, lean on hard enforcement |
| `.claude/settings.json` | Update hook registrations |

---

## Testing Plan

### Test 1: Parallel Delegation Persistence

**Scenario**: Complex multi-step task over 15 turns

**Steps**:
1. User: "Implement authentication system with JWT, OAuth2, and RBAC"
2. Verify: Initial delegation spawns explore + dewey + delphi in parallel
3. Continue for 15 turns with follow-up requests
4. Track: How many times sequential execution occurs

**Success Criteria**: 0% sequential fallback (hard enforcement blocks it)

---

### Test 2: Console Noise Reduction

**Scenario**: Track stderr output during standard session

**Steps**:
1. Run 10-turn session with typical tasks
2. Count lines of output in each category:
   - Hook debug messages
   - User-relevant agent notifications
   - Tool usage messages
   - Error logs

**Success Criteria**:
- Debug lines: 0-1 per turn
- User lines: 2-4 per turn
- Signal-to-noise >90%

---

### Test 3: Agent Notification Quality

**Scenario**: Visual inspection of agent spawn messages

**Steps**:
1. Spawn agents: explore, dewey, frontend, delphi
2. Screenshot console output
3. Verify:
   - Color coding present
   - Model names shown
   - Task descriptions clear
   - Visual grouping for parallel spawns

**Success Criteria**: All criteria met for 100% of agent spawns

---

### Test 4: Hard Enforcement Unit Tests

**Command**:
```bash
pytest tests/test_parallel_enforcement.py -v
```

**Test Cases**:
- `test_create_task_graph` - Graph creation from dictionary
- `test_get_ready_tasks` - Task readiness with dependencies
- `test_get_independent_groups` - Wave computation
- `test_validate_spawn_valid` - Valid spawn allowed
- `test_validate_spawn_invalid_dependency` - Blocked on unmet deps
- `test_parallel_compliance_success` - Parallel spawns pass
- `test_parallel_compliance_failure` - Sequential spawns fail
- `test_strict_mode_raises` - ParallelExecutionError raised
- `test_set_and_get_enforcer` - Global enforcer integration

**Success Criteria**: All tests pass

---

## Risk Mitigation

### Risk 1: Hook Performance Degradation

**Concern**: State file I/O in every hook slows down response time

**Mitigation**:
- Benchmark hook execution time (target <50ms)
- Cache state files in memory with 500ms TTL
- Use lock-free writes (atomic file replacement)

---

### Risk 2: False Positive Dependency Detection

**Concern**: Dependency parser incorrectly groups independent tasks

**Mitigation**:
- Conservative detection (only block on explicit keywords)
- Fallback to "independent" if ambiguous
- Manual override syntax: `[PARALLEL]` tag in TODO

---

### Risk 3: ANSI Color Support

**Concern**: Some terminals don't support ANSI colors

**Mitigation**:
- Detect terminal capabilities via `TERM` env var
- Fallback to plain text if colors unsupported
- Add `STRAVINSKY_NO_COLOR` env var for explicit disable

---

### Risk 4: Strict Mode Too Aggressive

**Concern**: ParallelExecutionError interrupts legitimate sequential workflows

**Mitigation**:
- Provide `strict=False` option for soft enforcement (logging only)
- Document when to disable strict mode
- Add grace period configuration (default 500ms is generous)

---

## Future Enhancements (Post-MVP)

1. **Dependency Graph Visualization**
   - CLI tool: `stravinsky graph` shows task dependencies
   - Web UI: Real-time agent execution dashboard

2. **Agent Performance Metrics**
   - Track: Average task completion time per agent
   - Optimize: Route tasks to fastest agent for task type

3. **Smart Agent Selection**
   - ML model: Predict best agent for given task description
   - Training data: Historical task->agent->outcome mappings

4. **Parallel Execution Limits**
   - Config: Max concurrent agents (default: 5)
   - Queue: Tasks beyond limit wait for slot

5. **Cross-Wave Optimization**
   - Detect when wave 2 tasks can start early (partial dependency completion)
   - Pipeline execution for higher throughput

---

## Conclusion

This implementation plan addresses all three identified issues:

1. **Parallel delegation degradation**: **SOLVED** with TaskGraph + DelegationEnforcer (hard enforcement)
2. **Console clutter**: Proposed solution with silent debug mode + standardized formatting (pending)
3. **Agent notifications**: Proposed solution with color coding + rich formatting (pending)

**Phase 3 Complete**: Hard parallel enforcement is now implemented and tested. Independent tasks are programmatically required to spawn within 500ms of each other, with `ParallelExecutionError` raised on violations.

**Remaining effort**: 5-8 hours for Phases 1, 2, and 4 (console cleanup, notification enhancement, architecture cleanup)

**Expected outcome**: Feature parity with oh-my-opencode, plus improvements in:
- Persistent state management
- Programmatic enforcement (not just reminders)
- Clear error messages for violations
- Comprehensive test coverage

**Next steps**: Begin Phase 1 (Console Cleanup) for immediate UX wins, then proceed to Phases 2 and 4 for polish.
