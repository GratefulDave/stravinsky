# Stravinsky Hooks Installation Guide

## Overview

The Stravinsky hook installer provides a one-command solution to install and configure Claude Code hooks for enhanced parallel execution, context management, and tool behavior.

## Installation

### Method 1: Via Command Line (Recommended)

After installing Stravinsky:

```bash
stravinsky-install-hooks
```

### Method 2: Via Python Module

```bash
python3 -m mcp_bridge.cli.install_hooks
```

### Method 3: Programmatic Installation

```python
from mcp_bridge.cli.install_hooks import install_hooks

install_hooks()
```

## What Gets Installed

### Hook Files (15 total)

All hooks are installed to `~/.claude/hooks/`:

1. **truncator.py** - Limits tool output to 30k chars
2. **edit_recovery.py** - Detects edit failures and forces file re-reading
3. **context.py** - Auto-injects CLAUDE.md/README.md into prompts
4. **parallel_execution.py** - Enforces parallel Task spawning for multi-step work
5. **todo_continuation.py** - Prevents stopping with incomplete todos
6. **todo_delegation.py** - Hard blocks sequential work when 2+ pending todos exist
7. **stravinsky_mode.py** - Blocks direct tools (Read/Grep/Bash) in orchestrator mode
8. **tool_messaging.py** - User-friendly tool usage messages
9. **notification_hook_v2.py** - Enhanced agent spawn notifications with colors
10. **subagent_stop.py** - Subagent completion tracking
11. **pre_compact.py** - Context preservation before compaction
12. **dependency_tracker.py** - Tracks task dependencies
13. **execution_state_tracker.py** - Tracks execution state
14. **parallel_reinforcement_v2.py** - Smart parallel reminders
15. **ralph_loop.py** - Auto-continuation loop

### Settings.json Updates

The installer merges hook registrations into `~/.claude/settings.json`:

- **Notification** hooks: Agent spawn messages
- **SubagentStop** hooks: Agent completion tracking
- **PreCompact** hooks: Context preservation
- **PreToolUse** hooks: Stravinsky mode blocking
- **UserPromptSubmit** hooks: Parallel execution, context injection, todo continuation
- **PostToolUse** hooks: Output truncation, tool messaging, edit recovery, todo delegation

## Hook Behavior

### Parallel Execution Enforcement

When you create a TodoWrite with 2+ pending items:

```
✅ CORRECT (Parallel):
TodoWrite([task1, task2, task3])
Task(subagent_type="explore", prompt="Task 1", description="Task 1", run_in_background=true)
Task(subagent_type="explore", prompt="Task 2", description="Task 2", run_in_background=true)
Task(subagent_type="explore", prompt="Task 3", description="Task 3", run_in_background=true)
# All spawned in ONE response

❌ WRONG (Sequential):
TodoWrite([task1, task2, task3])
# End response
# Mark task1 in_progress -> work -> complete
# Mark task2 in_progress -> work -> complete  // TOO SLOW!
```

### Stravinsky Mode

When you run `/stravinsky`, the parallel_execution hook creates `~/.stravinsky_mode` marker file, which:

1. Blocks direct use of Read, Grep, Bash, Edit tools
2. Forces delegation via Task tool
3. Outputs clear error messages with delegation examples

To exit Stravinsky mode:

```bash
rm ~/.stravinsky_mode
```

### Context Injection

Automatically prepends project context from:
- `CLAUDE.md`
- `README.md`
- `AGENTS.md`

Only one file is used (first found) to keep prompts concise.

### Todo Continuation

If you have pending or in_progress todos, the hook injects a reminder:

```
[SYSTEM REMINDER - TODO CONTINUATION]

IN PROGRESS (2 items):
  - Implement authentication module
  - Add tests for API endpoints

IMPORTANT: You have incomplete work. Before starting anything new:
1. Continue working on IN_PROGRESS todos first
2. If blocked, explain why and move to next PENDING item
3. Only start NEW work if all todos are complete or explicitly abandoned
```

## Idempotency

The installer is **idempotent** - you can run it multiple times safely:

- Hook files are overwritten with latest versions
- Settings.json hooks section is replaced (other settings preserved)
- Existing user configurations outside "hooks" key are untouched

## Verification

After installation, verify hooks are active:

```bash
ls -lh ~/.claude/hooks/
cat ~/.claude/settings.json | grep -A 5 "hooks"
```

Expected output:
- 11 executable Python files in ~/.claude/hooks/
- "hooks" key in settings.json with 6 hook types registered

## Troubleshooting

### Hooks Not Firing

1. Check permissions: `chmod +x ~/.claude/hooks/*.py`
2. Verify Python 3: `which python3`
3. Check settings.json syntax: `python3 -m json.tool ~/.claude/settings.json`

### Stravinsky Mode Stuck

If stravinsky mode won't deactivate:

```bash
rm ~/.stravinsky_mode
```

### Settings.json Backup

The installer creates a backup before modifications:

```bash
cp ~/.claude/settings.json ~/.claude/settings.json.backup
```

## Uninstallation

To remove Stravinsky hooks:

```bash
# Remove hook files
rm ~/.claude/hooks/{truncator,edit_recovery,context,parallel_execution,todo_continuation,todo_delegation,stravinsky_mode,tool_messaging,notification_hook,subagent_stop,pre_compact}.py

# Remove stravinsky mode marker
rm ~/.stravinsky_mode

# Manually edit ~/.claude/settings.json to remove "hooks" key or restore backup
cp ~/.claude/settings.json.backup ~/.claude/settings.json
```

## Integration with Stravinsky MCP

These hooks work seamlessly with the Stravinsky MCP server:

1. **Install Stravinsky MCP**: `claude mcp add stravinsky -- uvx stravinsky`
2. **Install Hooks**: `stravinsky-install-hooks`
3. **Use /stravinsky skill**: Activates parallel execution mode + tool blocking
4. **Profit**: Multi-model orchestration with enforced best practices

## See Also

- [Stravinsky MCP Documentation](../README.md)
- [Agent Prompts](../mcp_bridge/prompts/)
- [Hook Source Code](../mcp_bridge/cli/install_hooks.py)
