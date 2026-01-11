# Parallel Execution Fix - /strav Command Architecture

## Problem Summary

When users invoke `/strav` in other repositories, the system was "failing to use agents by default, opting for native Claude Read instead of agent_spawn."

## Root Cause

**Hook Context Mismatch** in `~/.claude/hooks/parallel_execution.py`

The hook was instructing the WRONG delegation tool for the execution context:

- **Stravinsky MCP Skill** (`/strav` command): Requires `agent_spawn()` (routes to Gemini/GPT)
- **Claude Native Agents** (`.claude/agents/`): Requires `Task()` (routes to Claude subagents)

**BUG:** Hook always instructed `Task()` regardless of context, causing:

1. Hook creates `~/.stravinsky_mode` marker ✅
2. Hook blocks Read/Grep/Bash ✅
3. **Hook instructs using `Task()` ❌**
4. `/strav` skill says "NEVER use Task, use agent_spawn" ❌
5. **Conflict**: Claude blocked from Read, told not to use Task, confused about agent_spawn
6. **Result**: Claude gives up → tries Read anyway → blocked → error loop → user sees "opting for native Read"

## The Fix (3 Parts)

### Part 1: Context-Aware Hook Instructions ✅

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

### Part 2: Cleanup Instructions ✅

**File:** `.claude/commands/strav.md`

**Change:** Added cleanup step to remove marker file when task completes

```markdown
Before final answer:
1. Cancel ALL running agents via `agent_cancel`
2. Cleanup stravinsky mode: Run `python3 -c "from pathlib import Path; Path.home().joinpath('.stravinsky_mode').unlink(missing_ok=True); print('✅ Stravinsky mode deactivated')"`
```

**Effect:** Prevents marker file from persisting across sessions and blocking tools in subsequent work.

### Part 3: Detection Keywords ✅

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
    ↓
Hook: Create ~/.stravinsky_mode ✅
Hook: Inject "Use Task()" ❌
    ↓
Claude reads /strav prompt: "NEVER use Task" ❌
Claude blocked from Read/Grep/Bash ✅
    ↓
CONFLICT: Can't use Read (blocked), told not to use Task
    ↓
Claude confused → tries Read → error → "opting for native Read"
```

### After Fix (WORKING)

```
User: /strav implement feature X
    ↓
Hook: Detect /strav → is_stravinsky = True ✅
Hook: Create ~/.stravinsky_mode ✅
Hook: Inject "Use agent_spawn()" ✅
    ↓
Claude reads /strav prompt: "Use agent_spawn" ✅
Claude blocked from Read/Grep/Bash ✅
    ↓
ALIGNMENT: Can't use Read (blocked), USE agent_spawn ✅
    ↓
Claude: TodoWrite → agent_spawn × 4 (parallel) ✅
```

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

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│ User Input                                      │
│  ├─ "/strav implement X"                        │
│  └─ "implement X" (no /strav)                   │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ UserPromptSubmit Hook                           │
│  ~/.claude/hooks/parallel_execution.py          │
│                                                  │
│  ┌─────────────────────────────────────────┐   │
│  │ 1. Detect context:                      │   │
│  │    is_stravinsky = detect_stravinsky()  │   │
│  └─────────────────┬───────────────────────┘   │
│                    │                             │
│    ┌───────────────┴──────────────┐             │
│    ▼                               ▼             │
│  TRUE                           FALSE            │
│  (MCP Skill)                    (Native)         │
│    │                               │             │
│    ├─ Create marker file           │             │
│    │  (~/.stravinsky_mode)          │             │
│    │                                 │             │
│    ├─ tool = "agent_spawn"          ├─ tool = "Task"│
│    │  params = agent_type=...       │  params = subagent_type=...│
│    └─────────────┬──────────────────┘             │
│                  │                                 │
│  ┌───────────────┴─────────────────────────────┐ │
│  │ 2. Inject instruction with correct tool    │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│ Modified Prompt (with injected instructions)    │
│  "[PARALLEL MODE] Use {tool_name}()..."         │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ Claude Response Generation                      │
│  ├─ Reads skill/agent prompt                    │
│  ├─ Sees injected instructions (correct tool)   │
│  └─ Creates TodoWrite + multiple agent_spawn    │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ PreToolUse Hook (stravinsky_mode.py)            │
│  Blocks: Read, Grep, Bash (if marker exists)    │
│  Allows: agent_spawn, Task, invoke_*            │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ PostToolUse Hook (todo_delegation.py)           │
│  After TodoWrite: Enforces immediate delegation │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ Parallel Execution ✅                            │
│  agent_spawn() × N (if /strav)                  │
│  Task() × N (if native)                         │
└─────────────────────────────────────────────────┘
```

## Key Takeaways

1. **Two Execution Contexts**:
   - MCP Skill (`/strav`): Use `agent_spawn()` → Gemini/GPT
   - Native Agent: Use `Task()` → Claude subagents

2. **Hook Coordination**:
   - `parallel_execution.py`: Detects context, creates marker, injects instructions
   - `stravinsky_mode.py`: Blocks direct tools when marker exists
   - `todo_delegation.py`: Enforces immediate delegation after TodoWrite

3. **Cost Optimization**:
   - `agent_spawn` routes to Gemini Flash ($0.075/1M) vs Claude Sonnet ($3/1M)
   - Multi-model routing is the whole point of Stravinsky MCP

4. **The Bug Was Simple**:
   - Hook always said "use Task"
   - Skill said "never use Task, use agent_spawn"
   - Confusion → fallback to Read → blocked → error loop

5. **The Fix Was Simple**:
   - Make hook context-aware
   - Inject correct tool name based on execution context
   - Add cleanup step to prevent marker file leakage
