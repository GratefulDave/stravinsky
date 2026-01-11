# Gap Analysis & Implementation Plan: Parallel Delegation & Console UX

**Date**: 2026-01-11  
**Author**: Stravinsky Analysis  
**Purpose**: Achieve feature parity with oh-my-opencode while improving architecture efficiency

---

## Executive Summary

This document outlines the gaps between Stravinsky's current implementation and oh-my-opencode's parallel delegation architecture, along with a comprehensive implementation plan to fix three critical issues:

1. **Parallel delegation degradation** over session lifetime
2. **Hook console clutter** (debug output pollution)
3. **Agent notification formatting** (missing colors, model info, task clarity)

---

## Issue 1: Parallel Delegation Degradation

### Current Behavior

**Initial tasks (turn 1-2):**
- ✅ Spawns parallel agents correctly
- ✅ Multiple `Task()` calls in single response
- ✅ Independent tasks execute concurrently

**Subsequent tasks (turn 3+):**
- ❌ Falls back to sequential execution
- ❌ Marks TODO as `in_progress` before delegating
- ❌ Waits for completion before spawning next agent
- ❌ No longer delegates unrelated tasks in parallel

### Root Cause Analysis

#### 1. **Hook Timing Ambiguity**

```python
# parallel_execution.py (UserPromptSubmit)
# Fires BEFORE response generation
# ✅ Good for initial activation
# ❌ Ephemeral - context forgotten after first response
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

**Stravinsky lacks**:
- Explicit task dependency graph (oh-my-opencode has this)
- Independent task detection algorithm
- Automatic parallelization decision logic

**Current approach**: Relies on LLM inference
- Initial context fresh → good decisions
- After 3+ turns → context dilution → sequential fallback

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

### Proposed Solution

#### **Option A: Agent-Level Task Dependency Tracker (Recommended)**

Create a new hook that maintains a persistent task dependency graph:

**File**: `.claude/hooks/dependency_tracker.py` (UserPromptSubmit + PostToolUse)

**Responsibilities**:
1. Parse TODOs and extract dependency signals:
   - Keywords: "after", "depends on", "requires", "once", "when"
   - Sequential markers: "then", "next", "finally"
   - Parallel markers: "also", "meanwhile", "simultaneously"

2. Build dependency graph:
   ```python
   {
     "todo_1": {"deps": [], "independent": True},
     "todo_2": {"deps": [], "independent": True},
     "todo_3": {"deps": ["todo_1"], "independent": False}
   }
   ```

3. Inject smart reinforcement:
   ```
   [SYSTEM REMINDER]
   
   Independent tasks detected: todo_1, todo_2
   
   You MUST spawn agents for these tasks IN PARALLEL:
   Task(subagent_type="explore", prompt="...", description="todo_1")
   Task(subagent_type="dewey", prompt="...", description="todo_2")
   
   Dependent task todo_3 can run after todo_1 completes.
   ```

**Storage**: `.claude/task_dependencies.json` (persists across session)

**Hooks**:
- **UserPromptSubmit**: Inject dependency-aware instructions
- **PostToolUse (TodoWrite)**: Parse todos, update graph
- **PostToolUse (TodoUpdate)**: Update graph on status changes

---

#### **Option B: PreToolUse Hard Block on Sequential Execution**

Add detection for sequential anti-patterns:

**File**: `.claude/hooks/sequential_block.py` (PreToolUse)

**Triggers**:
- `TodoUpdate` setting status=`in_progress` when 2+ pending todos exist
- No `Task()` calls in previous response window

**Action**:
```python
return {
    "exit_code": 2,  # Hard block
    "error": "⚠️ SEQUENTIAL EXECUTION BLOCKED\n\n"
             "You have 2+ pending TODOs but are marking one in_progress.\n"
             "You MUST spawn Task() agents for ALL independent tasks FUWT.\n"
             "Pattern:\n"
             "  Task(subagent_type='explore', ...)\n"
             "  Task(subagent_type='dewey', ...)\n"
}
```

**Problem**: Exit code blocking is unreliable in Claude Code hooks (observed behavior).

---

#### **Option C: State-Based Reinforcement Injection (Hybrid)**

Combine Options A + B with state persistence:

1. **Dependency tracking** (Option A)
2. **State file** tracking last N tool calls
3. **UserPromptSubmit hook** that:
   - Reads last N tool calls
   - Detects if `Task()` was used in recent history
   - If not + pending todos → inject AGGRESSIVE reminder
   - If yes → no injection (positive reinforcement)

**State file**: `.claude/execution_state.json`
```json
{
  "last_10_tools": ["TodoWrite", "Read", "Edit", "TodoUpdate"],
  "last_task_spawn": 5,  // turns ago
  "pending_todos": 3,
  "parallel_mode_active": true
}
```

**Hook**: `parallel_state_tracker.py`
- **PostToolUse**: Update execution_state.json
- **UserPromptSubmit**: Read state, inject context-aware reminders

---

### Recommended Implementation: **Option C (State-Based Reinforcement)**

**Why**:
- Persistent state survives context window limits
- Adaptive reminders based on recent behavior
- Combines dependency tracking + behavioral monitoring
- No reliance on unreliable exit code blocking

**Files to Create**:
1. `.claude/hooks/dependency_tracker.py` - Parse TODOs for dependencies
2. `.claude/hooks/execution_state_tracker.py` - Track tool usage patterns
3. `.claude/hooks/parallel_reinforcement_v2.py` - Smart context injection based on state

**Files to Modify**:
1. `.claude/hooks/parallel_execution.py` - Add state awareness
2. `.claude/hooks/parallel_reinforcement.py` - Deprecate in favor of v2
3. `.claude/hooks/todo_delegation.py` - Add dependency graph update
4. `.claude/settings.json` - Register new hooks

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
       AGENT = "🤖"
       TOOL = "🔧"
       REMINDER = "💡"
       WARNING = "⚠️"
       ERROR = "🚨"
   
   def format_message(msg_type: MessageType, content: str) -> str:
       return f"{msg_type.value} {content}"
   
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
1. ❌ No color coding per agent type
2. ❌ Generic task description ("task delegated")
3. ❌ Inconsistent format (sometimes missing model)
4. ❌ No visual hierarchy or grouping

### Desired Behavior (claude-flow style)

**Reference**: oh-my-opencode's agent output (inferred):
```
🔵 EXPLORE → gemini-3-flash
   Task: Find all authentication implementations in codebase
   
🟣 DEWEY → gemini-3-flash  
   Task: Research JWT best practices from official docs

🟢 FRONTEND → gemini-3-pro-high
   Task: Implement login UI with dark mode support
   
🟠 DELPHI → gpt-5.2-medium
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
       "explore": (Color.BLUE, "🔵"),
       "dewey": (Color.PURPLE, "🟣"),
       "frontend": (Color.GREEN, "🟢"),
       "delphi": (Color.ORANGE, "🟠"),
       "debugger": (Color.RED, "🔴"),
       "code-reviewer": (Color.PURPLE, "🟣"),
   }
   ```

2. **Format multi-line output**:
   ```python
   def format_agent_spawn(agent_type: str, model: str, description: str) -> str:
       color, emoji = AGENT_COLORS.get(agent_type, (Color.RESET, "⚪"))
       
       # Multi-line format
       lines = [
           f"{color}{emoji} {agent_type.upper()} → {model}{Color.RESET}",
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

#### **Strategy 2: Tool Messaging with Color & Icons**

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
   print(f"🎯 {subagent_type}:{model}('{description}')", file=sys.stderr)
   
   # AFTER
   color = AGENT_COLORS.get(subagent_type, "")
   reset = "\033[0m"
   print(f"{color}🎯 {subagent_type}:{model}{reset}", file=sys.stderr)
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

1. ✅ Silence `send_event.py` debug output
   - File: `.claude/hooks/send_event.py`
   - Change: Replace all `print()` with file logging
   
2. ✅ Create console formatter utility
   - File: `.claude/hooks/utils/console_format.py`
   - Implement: `MessageType` enum + `print_hook_message()`

3. ✅ Add debug mode environment variable
   - File: `.claude/hooks/utils/debug.py`
   - Implement: `STRAVINSKY_DEBUG` check

4. ✅ Update existing hooks to use formatters
   - Files: `notification_hook.py`, `tool_messaging.py`, `todo_delegation.py`
   - Replace raw `print()` with `print_hook_message()`

**Expected Result**: 80% reduction in console noise.

---

### Phase 2: Agent Notification Enhancement - **2-3 hours**

1. ✅ Add ANSI color support
   - File: `.claude/hooks/utils/colors.py`
   - Define color constants + agent mappings

2. ✅ Refactor notification_hook.py
   - Implement multi-line format
   - Add color coding
   - Extract actual model from agent configs

3. ✅ Refactor tool_messaging.py
   - Apply same formatting to Task delegations
   - Add color support
   - Improve description extraction

4. ✅ Add agent batching detection
   - File: `.claude/hooks/state/agent_batch.json`
   - Track agents spawned in same window
   - Group visual output

**Expected Result**: Claude-flow-style agent notifications with colors and clear task descriptions.

---

### Phase 3: Parallel Delegation Fix - **4-6 hours**

1. ✅ Create dependency tracker
   - File: `.claude/hooks/dependency_tracker.py`
   - Implement: TODO parsing + dependency graph

2. ✅ Create execution state tracker
   - File: `.claude/hooks/execution_state_tracker.py`
   - Track: Last N tool calls, Task() usage, pending todos

3. ✅ Refactor parallel reinforcement
   - File: `.claude/hooks/parallel_reinforcement_v2.py`
   - Read execution state
   - Inject smart, context-aware reminders

4. ✅ Update settings.json
   - Register new hooks
   - Configure UserPromptSubmit + PostToolUse chains

5. ✅ Test & validate
   - Create test session with 5+ multi-step tasks
   - Verify parallel delegation sustained across 10+ turns
   - Monitor for sequential fallback

**Expected Result**: Consistent parallel delegation throughout session lifetime.

---

### Phase 4: Architecture Cleanup - **2-3 hours**

1. ✅ Deprecate old hooks
   - Archive: `parallel_reinforcement.py` (replaced by v2)
   - Archive: Legacy reminder logic in `parallel_execution.py`

2. ✅ Consolidate hook chain
   - UserPromptSubmit: Reduce from 5 hooks to 3
     - Keep: `context_monitor.py`, `context.py`, `todo_continuation.py`
     - Replace: `parallel_execution.py` + `parallel_reinforcement.py` → `parallel_reinforcement_v2.py`

3. ✅ Add hook documentation
   - File: `.claude/hooks/README.md`
   - Document: Hook execution order, purpose, state files

4. ✅ Performance audit
   - Measure: Hook execution time (target <50ms per hook)
   - Optimize: State file I/O (use caching)

**Expected Result**: Cleaner, faster, more maintainable hook architecture.

---

## Success Metrics

### Parallel Delegation

**Before**:
- Initial tasks spawn in parallel: ✅ 90% of time
- Tasks after turn 5 spawn in parallel: ❌ 20% of time
- Sequential fallback rate: ❌ 80% by turn 10

**After** (target):
- Initial tasks spawn in parallel: ✅ 95% of time
- Tasks after turn 5 spawn in parallel: ✅ 85% of time
- Sequential fallback rate: ✅ <15% at turn 10

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
- Color coding: ❌ None
- Model visibility: ⚠️ Inconsistent
- Task clarity: ⚠️ Truncated/generic

**After** (target):
- Color coding: ✅ All agents
- Model visibility: ✅ 100%
- Task clarity: ✅ Full description, no truncation

---

## Files to Create

### New Hooks
1. `.claude/hooks/dependency_tracker.py` - Parse TODOs for dependencies
2. `.claude/hooks/execution_state_tracker.py` - Track tool usage patterns  
3. `.claude/hooks/parallel_reinforcement_v2.py` - Smart parallel reminders

### New Utilities
4. `.claude/hooks/utils/console_format.py` - Message formatting
5. `.claude/hooks/utils/colors.py` - ANSI color codes
6. `.claude/hooks/utils/debug.py` - Debug mode control

### New State Files
7. `.claude/task_dependencies.json` - Task dependency graph
8. `.claude/execution_state.json` - Tool usage tracking
9. `.claude/hooks/state/agent_batch.json` - Agent spawn batching

### Documentation
10. `.claude/hooks/README.md` - Hook architecture guide

---

## Files to Modify

### Hooks
1. `.claude/hooks/send_event.py` - Silence debug output
2. `.claude/hooks/notification_hook.py` - Add colors + formatting
3. `.claude/hooks/tool_messaging.py` - Add colors + formatting
4. `.claude/hooks/parallel_execution.py` - Add state awareness
5. `.claude/hooks/todo_delegation.py` - Update dependency graph

### Configuration
6. `.claude/settings.json` - Register new hooks

### Agent Configs (for model extraction)
7. `.claude/agents/explore.md` - Ensure model field present
8. `.claude/agents/dewey.md` - Ensure model field present
9. `.claude/agents/frontend.md` - Ensure model field present
10. `.claude/agents/delphi.md` - Ensure model field present

---

## Testing Plan

### Test 1: Parallel Delegation Persistence

**Scenario**: Complex multi-step task over 15 turns

**Steps**:
1. User: "Implement authentication system with JWT, OAuth2, and RBAC"
2. Verify: Initial delegation spawns explore + dewey + delphi in parallel
3. Continue for 15 turns with follow-up requests
4. Track: How many times sequential execution occurs

**Success Criteria**: <15% sequential fallback rate

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
- Fallback to emoji-only if colors unsupported
- Add `STRAVINSKY_NO_COLOR` env var for explicit disable

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
   - Training data: Historical task→agent→outcome mappings

4. **Parallel Execution Limits**
   - Config: Max concurrent agents (default: 5)
   - Queue: Tasks beyond limit wait for slot

---

## Conclusion

This implementation plan addresses all three identified issues:

1. **Parallel delegation degradation**: State-based reinforcement + dependency tracking
2. **Console clutter**: Silent debug mode + standardized user messages
3. **Agent notifications**: Color coding + rich formatting + model visibility

**Total estimated effort**: 10-14 hours

**Expected outcome**: Feature parity with oh-my-opencode, plus improvements in:
- Persistent state management
- Adaptive reinforcement
- Visual polish and UX

**Next steps**: Begin Phase 1 (Console Cleanup) for immediate wins, then proceed to Phases 2-4 for systematic improvements.
