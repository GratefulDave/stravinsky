# Claude Code Hooks Architecture

## Overview

This directory contains Claude Code hooks that enforce parallel delegation, provide rich console notifications, and track execution state across conversation turns.

## Hook Execution Order

### UserPromptSubmit (6 hooks)
1. `context_monitor.py` - Track session context
2. `parallel_execution.py` - Initial ULTRAWORK mode activation
3. `parallel_reinforcement.py` - Legacy parallel reminders (deprecated)
4. `parallel_reinforcement_v2.py` - **NEW** Smart adaptive reminders based on state
5. `context.py` - Inject project context
6. `todo_continuation.py` - Resume incomplete todos

### PostToolUse
1. `truncator.py` - Truncate large outputs
2. `session_recovery.py` - Session state backup
3. `execution_state_tracker.py` - **NEW** Track tool usage patterns across turns
4. `tool_messaging.py` - User-friendly tool notifications (with colors)
5. `edit_recovery.py` - Backup edited files
6. `todo_delegation.py` - Enforce parallel after TodoWrite
7. `dependency_tracker.py` - **NEW** Parse TODO dependencies and build graph

## State Files

Located in `.claude/` directory:

- `execution_state.json` - Tool usage tracking (last 10 tools, Task spawn history)
- `task_dependencies.json` - TODO dependency graph (independent vs dependent tasks)
- `hooks/state/agent_batch.json` - Agent spawn batching for grouped notifications
- `~/.stravinsky_mode` - Hard blocking mode marker (enables stravinsky mode)

## Utilities

### `utils/colors.py`
- ANSI color codes for terminal output
- Agent-specific color mappings (blue=explore, purple=dewey, etc.)
- Terminal capability detection (`supports_color()`)

### `utils/debug.py`
- Debug mode control via `STRAVINSKY_DEBUG` environment variable
- Silent by default, verbose when `STRAVINSKY_DEBUG=1`

### `utils/console_format.py`
- Standardized message formatting with `MessageType` enum
- Multi-line agent spawn formatting
- Tool usage formatting with colors

## Environment Variables

- `STRAVINSKY_DEBUG=1` - Enable debug output from hooks
- `STRAVINSKY_NO_COLOR=1` - Disable ANSI colors (for unsupported terminals)
- `NO_COLOR=1` - Standard no-color environment variable (also supported)

## Key Features

### 1. Parallel Delegation Enforcement

**Problem**: After turn 3+, Claude degrades to sequential execution despite having independent tasks.

**Solution**: State-based reinforcement via `parallel_reinforcement_v2.py`
- Tracks last 10 tool calls
- Detects when Task() hasn't been used recently (2+ turns)
- Parses TODOs for dependency keywords
- Injects aggressive reminders when degradation detected

**Files**:
- `dependency_tracker.py` - Parses TODOs for "after", "depends on", etc.
- `execution_state_tracker.py` - Tracks tool usage history
- `parallel_reinforcement_v2.py` - Smart context-aware reminders

### 2. Rich Agent Notifications

**Before**:
```
spawned explore:gemini-3-flash('task delegated')
```

**After**:
```
🔵 EXPLORE → gemini-3-flash
   Task: Find all authentication implementations in codebase
```

**Features**:
- Color-coded by agent type (blue, purple, green, orange, red)
- Multi-line format with clear task descriptions
- Model name explicitly shown
- Graceful degradation if terminal doesn't support colors

### 3. Silent Debug Mode

**Problem**: Hook debug output pollutes console (`Failed to send event: ...`)

**Solution**: File-based logging with `STRAVINSKY_DEBUG` control
- `send_event.py` logs to `~/.claude/hooks/logs/event_sender.log`
- All debug output hidden unless `STRAVINSKY_DEBUG=1`
- Clean console by default

## Agent Color Mapping

| Agent | Color | Emoji | Model |
|-------|-------|-------|-------|
| explore | Blue | 🔵 | gemini-3-flash |
| dewey | Purple | 🟣 | gemini-3-flash |
| frontend | Green | 🟢 | gemini-3-pro-high |
| delphi | Orange | 🟠 | gpt-5.2-medium |
| debugger | Red | 🔴 | sonnet-4.5 |
| code-reviewer | Purple | 🟣 | sonnet-4.5 |

## Dependency Detection

The `dependency_tracker.py` hook parses TODO content for dependency signals:

**Dependency Keywords** (marks as dependent):
- "after", "depends on", "requires", "once", "when", "then"

**Parallel Keywords** (marks as independent):
- "also", "meanwhile", "simultaneously", "and", "plus"

**Example**:
```json
{
  "dependencies": {
    "todo_1": {"deps": [], "independent": true, "parallel_safe": true},
    "todo_2": {"deps": [], "independent": true, "parallel_safe": true},
    "todo_3": {"deps": ["todo_1"], "independent": false, "parallel_safe": false}
  }
}
```

## Parallel Reinforcement Algorithm

1. **Check Mode**: Is `~/.stravinsky_mode` active? If not, skip.
2. **Check State**: Are there 2+ pending TODOs? If not, skip.
3. **Check History**: How many turns since last `Task()` spawn?
   - If < 2 turns → skip (still fresh)
   - If >= 2 turns → degradation detected
4. **Check Dependencies**: How many independent tasks exist?
   - If < 2 → skip (no parallelization needed)
   - If >= 2 → inject aggressive reminder
5. **Inject Reminder**: Add context-aware instructions to prompt

## Testing

### Test Parallel Delegation Persistence

```bash
# Create a multi-step task and track behavior over 10+ turns
# Expected: Task() spawns for independent tasks even at turn 10
```

### Test Console Output

```bash
# Run hooks and verify no debug clutter
export STRAVINSKY_DEBUG=0
# Should see ONLY user-relevant messages (colored agent notifications)

# Enable debug mode
export STRAVINSKY_DEBUG=1
# Should see debug output in ~/.claude/hooks/logs/event_sender.log
```

### Test Color Support

```bash
# Disable colors
export STRAVINSKY_NO_COLOR=1
# Should see emojis but no ANSI codes

# Enable colors (default)
unset STRAVINSKY_NO_COLOR
# Should see colored output
```

## Architecture Comparison: Stravinsky vs oh-my-opencode

| Aspect | oh-my-opencode (TS) | Stravinsky (Python) |
|--------|---------------------|---------------------|
| Parallel Enforcement | Structural (orchestrator pattern) | Prompt-based with state tracking |
| State Management | Built-in TypeScript state | External JSON files |
| Dependency Tracking | Explicit graph | Keyword-based parsing |
| Agent Notifications | Rich formatting (assumed) | Rich formatting with ANSI colors |
| Console Output | Clean separation | File-based logging + formatting |

## Future Enhancements

1. **Agent Batching** - Group parallel agent spawns visually
2. **Dependency Graph Visualization** - CLI tool to view task dependencies
3. **Performance Metrics** - Track agent completion times
4. **ML-Based Agent Selection** - Predict best agent for task type

## Troubleshooting

### Import Errors in LSP

**Symptom**: Pyright shows "Import could not be resolved" for `utils/*` modules

**Cause**: LSP can't resolve relative imports in hook scripts

**Solution**: These are false positives. Python resolves imports at runtime via `sys.path.insert(0, ...)` in each hook. Safe to ignore.

### Parallel Delegation Still Fails

**Check**:
1. Is `~/.stravinsky_mode` file present?
2. Run: `cat .claude/execution_state.json` - verify state is updating
3. Run: `cat .claude/task_dependencies.json` - verify dependencies detected
4. Enable debug: `STRAVINSKY_DEBUG=1` and check logs

### Colors Not Showing

**Check**:
1. Terminal supports ANSI colors? (`echo $TERM`)
2. `STRAVINSKY_NO_COLOR` or `NO_COLOR` set?
3. Is stderr a TTY? (Colors disabled for piped output)

## Maintenance

### Adding New Hooks

1. Create hook file in `.claude/hooks/`
2. Add to appropriate section in `.claude/settings.json`
3. Test in isolation with mock input
4. Update this README

### Modifying State Schema

If changing `execution_state.json` or `task_dependencies.json` format:
1. Update tracker scripts (`execution_state_tracker.py`, `dependency_tracker.py`)
2. Update consumer scripts (`parallel_reinforcement_v2.py`)
3. Add migration logic or document breaking change
4. Consider versioning state files

### Deprecating Old Hooks

1. Mark as deprecated in comments
2. Add to "Deprecated" section below
3. After 1 month, remove from `settings.json`
4. After 2 months, delete file

## Deprecated Hooks

- `parallel_reinforcement.py` - Replaced by `parallel_reinforcement_v2.py` (state-based)
  - Removal target: TBD (keep for backward compatibility for now)
