# Hook Context Detection System

## Overview

The `parallel_execution.py` hook now detects the execution context (MCP skill vs native agent) and injects context-appropriate parallel execution instructions.

## Architecture

### Marker Files

1. **`~/.stravinsky_mode`** (Global - Hard Blocking)
   - Purpose: Enables hard blocking of direct tools (Read, Grep, Bash)
   - Scope: Global (affects all projects)
   - Created by: `/strav` or `/stravinsky` invocation
   - Used by: `stravinsky_mode.py` PreToolUse hook

2. **`.stravinsky/mcp_mode`** (Project - Instruction Routing)
   - Purpose: Indicates MCP skill execution context for instruction routing
   - Scope: Project-specific (current working directory)
   - Created by: `/strav` or `/stravinsky` invocation
   - Used by: `parallel_execution.py` UserPromptSubmit hook

### Detection Flow

```
User invokes /strav
    ↓
parallel_execution.py hook detects invocation
    ↓
Creates TWO markers:
    1. ~/.stravinsky_mode (global blocking)
    2. .stravinsky/mcp_mode (context routing)
    ↓
Hook checks for .stravinsky/mcp_mode
    ↓
If EXISTS → Inject agent_spawn() instructions (MCP tools)
If MISSING → Inject Task() instructions (Claude Code tools)
```

## Instruction Differences

### MCP Context (agent_spawn)

When `.stravinsky/mcp_mode` exists:

```python
agent_spawn(agent_type="explore", prompt="...", description="...")
  → explore:gemini-3-flash('...') task_id=agent_abc123

agent_spawn(agent_type="dewey", prompt="...", description="...")
  → dewey:gemini-3-flash('...') task_id=agent_def456

agent_spawn(agent_type="frontend", prompt="...", description="...")
  → frontend:gemini-3-pro-high('...') task_id=agent_ghi789
```

**Why?**
- Routes to Gemini/GPT models via MCP (cheap)
- Multi-model orchestration is the core feature
- `/strav` command runs in MCP skill context

### Native Context (Task)

When `.stravinsky/mcp_mode` is missing:

```python
Task(subagent_type="Explore", prompt="...", description="...", run_in_background=true)
Task(subagent_type="Plan", prompt="...", description="...", run_in_background=true)
Task(subagent_type="Explore", prompt="...", description="...", run_in_background=true)
```

**Why?**
- Uses Claude Code's native subagent system
- Runs Claude models (Sonnet/Haiku/Opus)
- `.claude/agents/` native agents use this

## Testing

### Test 1: Native Mode (No Marker)

```bash
cd /opt  # Clean directory
echo '{"prompt": "implement feature"}' | python3 ~/.claude/hooks/parallel_execution.py | grep "Spawn"
# Output: Spawn Task() for EACH independent pending TODO
```

### Test 2: MCP Mode (With Marker)

```bash
cd /var/tmp
echo '{"prompt": "/strav implement feature"}' | python3 ~/.claude/hooks/parallel_execution.py > /dev/null
test -f .stravinsky/mcp_mode && echo "✅ Marker created"
# Output: ✅ Marker created

echo '{"prompt": "implement feature"}' | python3 ~/.claude/hooks/parallel_execution.py | grep "Spawn"
# Output: Spawn agent_spawn() for EACH independent pending TODO
```

### Test 3: Marker File Contents

```bash
cat .stravinsky/mcp_mode
# Output: {"active": true, "context": "mcp_skill", "reason": "invoked via /strav command"}
```

## Edge Cases Handled

1. **Missing `.stravinsky` directory**: Hook creates it automatically via `mkdir(parents=True, exist_ok=True)`
2. **IOError during marker creation**: Silently fails, falls back to native mode
3. **Hook runs in different projects**: Each project gets its own `.stravinsky/mcp_mode` marker
4. **Global blocking vs context routing**: Separation of concerns - two different marker files

## Success Criteria

✅ Hook detects `/strav` invocation
✅ Creates `.stravinsky/mcp_mode` marker in project root
✅ Injects `agent_spawn()` instructions when marker exists
✅ Injects `Task()` instructions when marker is missing
✅ No syntax errors in hook
✅ Doesn't break existing parallel delegation logic
✅ Clean separation from global `~/.stravinsky_mode` blocking

## Implementation Details

### Key Functions

- `detect_stravinsky_invocation(prompt)`: Detects `/strav` or `/stravinsky` in prompt
- `activate_mcp_mode()`: Creates `.stravinsky/mcp_mode` marker file
- `is_mcp_mode()`: Checks if marker file exists
- `main()`: Orchestrates detection and instruction injection

### Pattern Matching

Detects these patterns:
- `/strav` or `/stravinsky`
- `<command-name>/strav</command-name>` or `<command-name>/stravinsky</command-name>`
- `stravinsky orchestrator`
- `ultrawork`
- `ultrathink`

### File Locations

- Hook: `~/.claude/hooks/parallel_execution.py`
- Global marker: `~/.stravinsky_mode`
- Project marker: `{cwd}/.stravinsky/mcp_mode`

## Future Enhancements

- [ ] Auto-cleanup of stale marker files
- [ ] Marker expiration (TTL)
- [ ] Diagnostic command to show current context
- [ ] Hook status in /strav output
