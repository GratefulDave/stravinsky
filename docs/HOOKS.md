# Stravinsky Hooks Documentation

Comprehensive documentation of all hooks in the Stravinsky MCP Bridge.

## Overview

Stravinsky uses a sophisticated hook system to enhance Claude Code's behavior:
- **PreToolUse**: Fire before a tool executes (can block)
- **PostToolUse**: Fire after a tool completes (observe/modify output)
- **UserPromptSubmit**: Fire before user prompt is processed
- **PreCompact**: Fire before context compaction
- **Notification**: Fire on system notifications
- **SubagentStop**: Fire when a subagent completes

## Hook Catalog

### 1. parallel_execution.py

**Type**: UserPromptSubmit  
**Purpose**: Inject parallel execution instructions for implementation tasks  
**Location**: `~/.claude/hooks/parallel_execution.py`

**Features**:
- Detects implementation tasks (create, build, refactor, etc.)
- Injects TodoWrite → Task() parallelization pattern
- **IRONSTAR MODE**: When "ironstar" or "irs" detected:
  - Aggressive parallelization instructions
  - Maximum agent concurrency
  - Zero tolerance for partial completion
  - Verification guarantee requirements

**Triggers**:
- Keywords: implement, add, create, build, refactor, fix, update, modify
- Magic words: ironstar, irs, ultrathink, /stravinsky

---

### 2. stravinsky_mode.py

**Type**: PreToolUse  
**Purpose**: Block direct tool usage when Stravinsky orchestrator is active  
**Location**: `~/.claude/hooks/stravinsky_mode.py`

**Features**:
- Blocks Read, Grep, Bash, Edit when marker file exists
- Forces delegation to specialized agents
- Exit code 2 = hard block

**Marker File**: `~/.stravinsky_mode`

---

### 3. comment_checker.py

**Type**: PreToolUse (on Bash)  
**Purpose**: Enforce comment quality before git commits  
**Location**: `~/.claude/hooks/comment_checker.py`

**Features**:
- Detects low-quality comments in staged diff
- Warns about comments that just restate code
- Allows override with `--no-verify`

**Triggers**:
- `git commit` commands
- `git push` commands

**Quality Checks**:
- Flags comments like "# increment i" or "# set value"
- Allows docstrings, URLs, type hints, pragmas
- Encourages "why" over "what" comments

---

### 4. session_recovery.py

**Type**: PostToolUse  
**Purpose**: Detect and log API failures for recovery  
**Location**: `~/.claude/hooks/session_recovery.py`

**Features**:
- Detects thinking block errors
- Detects rate limits (429)
- Detects API timeouts
- Detects context overflow
- Logs to `~/.claude/state/recovery.jsonl`
- Provides recovery suggestions

**Error Types Detected**:
| Type | Patterns | Suggestion |
|------|----------|------------|
| thinking_block | "thinking block", "extended thinking" | Retry immediately |
| rate_limit | "429", "too many requests" | Wait 30-60s |
| api_timeout | "timeout", "connection reset" | Retry immediately |
| context_overflow | "context length", "too long" | Use /compact |
| auth_error | "401", "unauthorized" | Re-authenticate |

---

### 5. context_monitor.py

**Type**: UserPromptSubmit  
**Purpose**: Monitor context usage and warn about limits  
**Location**: `~/.claude/hooks/context_monitor.py`

---

### 6. context.py

**Type**: UserPromptSubmit  
**Purpose**: Inject local context (README, git state)  
**Location**: `~/.claude/hooks/context.py`

---

### 7. todo_continuation.py

**Type**: UserPromptSubmit  
**Purpose**: Inject active todos on prompt submit  
**Location**: `~/.claude/hooks/todo_continuation.py`

---

### 8. truncator.py

**Type**: PostToolUse  
**Purpose**: Truncate long tool outputs  
**Location**: `~/.claude/hooks/truncator.py`

---

### 9. tool_messaging.py

**Type**: PostToolUse  
**Purpose**: Format MCP tool outputs for user  
**Location**: `~/.claude/hooks/tool_messaging.py`

---

### 10. edit_recovery.py

**Type**: PostToolUse (on Edit, MultiEdit)  
**Purpose**: Backup files before edit for recovery  
**Location**: `~/.claude/hooks/edit_recovery.py`

---

### 11. todo_delegation.py

**Type**: PostToolUse (on TodoWrite)  
**Purpose**: Remind to spawn parallel agents after TodoWrite  
**Location**: `~/.claude/hooks/todo_delegation.py`

---

### 12. notification_hook.py

**Type**: Notification  
**Purpose**: Display system notifications  
**Location**: `~/.claude/hooks/notification_hook.py`

---

### 13. subagent_stop.py

**Type**: SubagentStop  
**Purpose**: Handle subagent completion  
**Location**: `~/.claude/hooks/subagent_stop.py`

---

### 14. pre_compact.py

**Type**: PreCompact  
**Purpose**: Preserve critical context before compaction  
**Location**: `~/.claude/hooks/pre_compact.py`

---

## Configuration

Hooks are configured in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/comment_checker.py"
          }
        ]
      }
    ]
  }
}
```

### Matcher Patterns

- `*` - Match all tools
- `Tool1,Tool2` - Match specific tools
- `mcp__server__*` - Match MCP tools by pattern

### Exit Codes

- `0` - Allow, pass through output
- `1` - Error (logged but not blocking)
- `2` - Hard block (stops the operation)

## Disabling Hooks

Create `~/.stravinsky/disable_hooks.txt` with one hook name per line:

```
comment_checker
session_recovery
```

## Troubleshooting

### Hook not firing

1. Check `~/.claude/settings.json` has the hook registered
2. Verify the hook file is executable: `chmod +x hook.py`
3. Check hook output: run manually with test JSON

### Hook blocking unexpectedly

1. Check for `~/.stravinsky_mode` marker file
2. Review exit codes in hook source
3. Test with `echo '{"tool_name":"Bash"}' | python3 hook.py`

### Performance issues

1. Hooks run synchronously - keep them fast
2. Avoid network calls in PreToolUse hooks
3. Use PostToolUse for logging/analytics

---

## Adding New Hooks

1. Create hook file in `~/.claude/hooks/`
2. Add to `settings.json` with appropriate matcher
3. Test with sample JSON input
4. Document in this file

Template:

```python
#!/usr/bin/env python3
"""
Hook description.

Type: PreToolUse/PostToolUse/UserPromptSubmit
Purpose: What it does
"""
import json
import sys

def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    
    # Your logic here
    
    return 0  # 0=allow, 2=block

if __name__ == "__main__":
    sys.exit(main())
```
