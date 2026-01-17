"""
Stravinsky Hooks - Claude Code Integration

This package contains all hook files for deep integration with Claude Code.
Hooks are Python scripts that intercept Claude Code events to enforce
parallel execution, stravinsky mode, and other workflow patterns.

## Available Hooks

### Core Execution Hooks
- `parallel_execution.py` - UserPromptSubmit: Pre-emptive parallel execution enforcement
- `stravinsky_mode.py` - PreToolUse: Hard blocking of direct tools (Read, Grep, Bash)
- `todo_delegation.py` - PostToolUse: Parallel execution enforcer after TodoWrite

### Context & State Hooks
- `context.py` - UserPromptSubmit: Auto-inject project context (CLAUDE.md, README.md)
- `todo_continuation.py` - UserPromptSubmit: Remind about incomplete todos
- `pre_compact.py` - PreCompact: Context preservation before compaction

### Tool Enhancement Hooks
- `tool_messaging.py` - PostToolUse: User-friendly tool/agent messaging
- `edit_recovery.py` - PostToolUse: Recovery guidance for failed Edit operations
- `truncator.py` - PostToolUse: Truncate long tool responses to prevent token overflow

### Agent Lifecycle Hooks
- `notification_hook.py` - Notification: Agent spawn messages
- `subagent_stop.py` - SubagentStop: Agent completion handling

## Installation for Claude Code

Copy the HOOKS_SETTINGS.json configuration to your project's .claude/settings.json:

```bash
# From PyPI package location
cp $(python -c "import mcp_bridge; print(mcp_bridge.__path__[0])")/hooks/HOOKS_SETTINGS.json .claude/settings.json
```

Or manually configure in .claude/settings.json (see HOOKS_SETTINGS.json for template).

## Hook Types

Claude Code supports these hook types:
- **UserPromptSubmit**: Fires before response generation
- **PreToolUse**: Fires before tool execution (can block with exit 2)
- **PostToolUse**: Fires after tool execution
- **Notification**: Fires on notification events
- **SubagentStop**: Fires when subagent completes
- **PreCompact**: Fires before context compaction

## Exit Codes

- `0` - Success (allow continuation)
- `1` - Warning (show but continue)
- `2` - Block (hard failure in stravinsky mode)

## Environment Variables

Hooks receive these environment variables from Claude Code:
- `CLAUDE_CWD` - Current working directory
- `CLAUDE_TOOL_NAME` - Tool being invoked (PreToolUse/PostToolUse)
- `CLAUDE_SESSION_ID` - Active session ID

## State Management

Stravinsky mode uses a marker file for state:
- `~/.stravinsky_mode` - Active when file exists
- Created by `/stravinsky` skill invocation
- Enables hard blocking of direct tools

## Usage

These hooks are automatically installed with the Stravinsky MCP package.
To enable them in a Claude Code project:

1. Copy HOOKS_SETTINGS.json to .claude/settings.json
2. Adjust hook paths if needed (default assumes installed via PyPI)
3. Restart Claude Code or reload configuration

## Development

To test hooks locally:

```bash
# Test parallel_execution hook
echo '{"prompt": "implement feature X"}' | python parallel_execution.py

# Test stravinsky_mode hook (requires marker file)
touch ~/.stravinsky_mode
echo '{"toolName": "Read", "params": {}}' | python stravinsky_mode.py
echo $?  # Should be 2 (blocked)
rm ~/.stravinsky_mode
```

## Package Contents
"""

__all__ = [
    # Core execution
    "parallel_execution",
    "stravinsky_mode",
    "todo_delegation",
    # Context & state
    "context",
    "todo_continuation",
    "pre_compact",
    # Tool enhancement
    "tool_messaging",
    "edit_recovery",
    "truncator",
    # Agent lifecycle
    "notification_hook",
    "subagent_stop",
]


def initialize_hooks():
    """Initialize and register all hooks with the HookManager."""
    from .delegation_policy import DelegationReminderPolicy
    from .edit_recovery_policy import EditRecoveryPolicy
    from .manager import get_hook_manager
    from .parallel_enforcement_policy import ParallelEnforcementPolicy
    from .truncation_policy import TruncationPolicy

    manager = get_hook_manager()

    # Register unified policies
    manager.register_policy(TruncationPolicy())
    manager.register_policy(DelegationReminderPolicy())
    manager.register_policy(EditRecoveryPolicy())
    manager.register_policy(ParallelEnforcementPolicy())


__version__ = "0.4.59"
__author__ = "David Andrews"
__description__ = "Claude Code hooks for Stravinsky MCP parallel execution"
