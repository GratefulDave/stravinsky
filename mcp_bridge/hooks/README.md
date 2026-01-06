# Stravinsky Hooks for Claude Code

This directory contains 11 production-ready hooks that integrate with Claude Code to enforce parallel execution, stravinsky mode, and advanced workflow patterns.

## Quick Start

### Option 1: Copy to Local Project

```bash
# In your Claude Code project root
mkdir -p .claude/hooks
cp -r $(python -c "import mcp_bridge; print(mcp_bridge.__path__[0])")/hooks/*.py .claude/hooks/
cp $(python -c "import mcp_bridge; print(mcp_bridge.__path__[0])")/hooks/HOOKS_SETTINGS.json .claude/settings.json
```

### Option 2: Symlink (Development)

```bash
# In your Claude Code project root
mkdir -p .claude
ln -s $(python -c "import mcp_bridge; print(mcp_bridge.__path__[0])")/hooks .claude/hooks
cp .claude/hooks/HOOKS_SETTINGS.json .claude/settings.json
```

## Hook Files (11 Total)

### Core Execution (3)
1. **parallel_execution.py** - UserPromptSubmit hook
   - Detects implementation tasks and injects parallel execution instructions
   - Activates stravinsky mode when `/stravinsky` is invoked
   - Creates `~/.stravinsky_mode` marker file for hard blocking

2. **stravinsky_mode.py** - PreToolUse hook
   - Blocks Read, Grep, Bash, Edit, MultiEdit when stravinsky mode is active
   - Forces delegation via Task tool instead
   - Exit code 2 = hard block

3. **todo_delegation.py** - PostToolUse hook (after TodoWrite)
   - Enforces parallel Task spawning when 2+ pending todos exist
   - Blocks continuation without Task delegation in stravinsky mode
   - Exit code 2 = hard block if stravinsky mode active

### Context Management (3)
4. **context.py** - UserPromptSubmit hook
   - Auto-injects CLAUDE.md, README.md, or AGENTS.md content
   - Prepends project context to every prompt
   - Reduces need for explicit context requests

5. **todo_continuation.py** - UserPromptSubmit hook
   - Reminds about in_progress and pending todos
   - Prevents starting new work when existing todos are incomplete
   - Uses `.claude/todo_state.json` cache

6. **pre_compact.py** - PreCompact hook
   - Preserves critical context before compaction (ARCHITECTURE, DESIGN DECISION, etc.)
   - Logs compaction events to `~/.claude/state/compaction.jsonl`
   - Maintains stravinsky mode state across compactions

### Tool Enhancement (3)
7. **tool_messaging.py** - PostToolUse hook
   - User-friendly messages for MCP tools and Task delegations
   - Format: `🎯 delphi:gpt-5.2-medium('Strategic analysis')`
   - Works with mcp__stravinsky__* and mcp__grep-app__* tools

8. **edit_recovery.py** - PostToolUse hook (after Edit/MultiEdit)
   - Detects Edit failures (oldString not found, multiple matches, etc.)
   - Suggests recovery: re-read file, verify exact match
   - Appends recovery guidance to error messages

9. **truncator.py** - PostToolUse hook (all tools)
   - Truncates responses longer than 30k characters
   - Prevents token overflow and context bloat
   - Adds truncation markers for transparency

### Agent Lifecycle (2)
10. **notification_hook.py** - Notification hook
    - Outputs spawn messages for agent delegations
    - Format: `spawned explore:gemini-3-flash('Find auth code')`
    - Maps agents to their display models

11. **subagent_stop.py** - SubagentStop hook
    - Handles subagent completion events
    - Validates output and detects failures
    - Can block completion for critical agents (delphi, code-reviewer, debugger)

## Configuration

The `HOOKS_SETTINGS.json` file contains the complete hook configuration for `.claude/settings.json`. It includes:

- Hook type mappings (UserPromptSubmit, PreToolUse, PostToolUse, etc.)
- Tool matchers (which tools trigger which hooks)
- Command paths (python3 .claude/hooks/hookname.py)
- Descriptions for each hook

## Hook Types & Exit Codes

### Hook Types
- **UserPromptSubmit**: Before response generation (can modify prompt)
- **PreToolUse**: Before tool execution (can block with exit 2)
- **PostToolUse**: After tool execution (can modify response)
- **Notification**: On notification events
- **SubagentStop**: When subagent completes
- **PreCompact**: Before context compaction

### Exit Codes
- `0` - Success (allow continuation)
- `1` - Warning (show message but continue)
- `2` - Block/Error (prevents tool in PreToolUse, signals failure in PostToolUse)

## State Files

Hooks use these state files:

| File | Purpose |
|------|---------|
| `~/.stravinsky_mode` | Marker for stravinsky orchestrator mode (enables hard blocking) |
| `~/.claude/state/compaction.jsonl` | Audit log of context compaction events |
| `.claude/todo_state.json` | Cached todo state for continuation enforcement |

## Testing Hooks

Test individual hooks with JSON input:

```bash
# Test parallel_execution
echo '{"prompt": "implement feature X"}' | python3 parallel_execution.py

# Test stravinsky_mode (should block)
touch ~/.stravinsky_mode
echo '{"toolName": "Read", "params": {}}' | python3 stravinsky_mode.py
echo $?  # Should be 2

# Test todo_delegation
echo '{"tool_name": "TodoWrite", "tool_input": {"todos": [{"status": "pending"}, {"status": "pending"}]}}' | python3 todo_delegation.py
```

## Customization

To disable a hook:
1. Open `.claude/settings.json`
2. Find the hook in the hooks array
3. Remove or comment out the hook object

To modify a hook:
1. Copy the hook file to your project's `.claude/hooks/`
2. Edit as needed
3. Update the command path in `.claude/settings.json`

## Environment Variables

Hooks receive these from Claude Code:
- `CLAUDE_CWD` - Current working directory
- `CLAUDE_TOOL_NAME` - Tool being invoked
- `CLAUDE_SESSION_ID` - Active session ID

## Workflow

### Stravinsky Mode Flow
1. User invokes `/stravinsky`
2. `parallel_execution.py` detects it and creates `~/.stravinsky_mode`
3. `stravinsky_mode.py` now blocks Read/Grep/Bash/Edit tools
4. Claude must use Task tool for delegation
5. `todo_delegation.py` enforces parallel Task spawning for 2+ pending todos

### Normal Flow (No Stravinsky Mode)
1. User submits prompt
2. `context.py` injects CLAUDE.md content
3. `todo_continuation.py` reminds about incomplete todos
4. `parallel_execution.py` adds parallel execution guidance if implementation task
5. Claude generates response
6. `tool_messaging.py` outputs friendly tool messages
7. `truncator.py` truncates long responses

## Troubleshooting

### Hooks Not Firing
- Check `.claude/settings.json` exists with hook configuration
- Verify hook scripts are executable: `chmod +x .claude/hooks/*.py`
- Check hook paths are correct (relative to project root)
- Restart Claude Code: `/reload`

### Stravinsky Mode Stuck Active
- Remove marker file: `rm ~/.stravinsky_mode`
- Check for orphaned mode files: `ls -la ~/ | grep stravinsky`

### Hooks Causing Errors
- Test hooks individually (see Testing section above)
- Check Python version: `python3 --version` (requires 3.8+)
- Review hook stderr output in Claude Code logs
- Disable problematic hooks temporarily

## Integration with Stravinsky MCP

These hooks are designed to work seamlessly with the Stravinsky MCP server:

- `tool_messaging.py` recognizes `mcp__stravinsky__*` tools
- `parallel_execution.py` works with `agent_spawn` MCP tool
- `stravinsky_mode.py` forces use of MCP Task delegation
- All hooks respect the parallel execution philosophy

## Version

Version: 0.2.61
Package: stravinsky
Repository: https://github.com/GratefulDave/stravinsky

## License

MIT License - See package LICENSE file

## Support

For issues or questions:
- GitHub Issues: https://github.com/GratefulDave/stravinsky/issues
- Documentation: See CLAUDE.md in package root
