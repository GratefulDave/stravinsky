# Stravinsky Hooks Integration

## Overview

Stravinsky uses native Claude Code hooks for delegation enforcement and user messaging. All hooks are configured in `.claude/settings.json` and execute as Python scripts.

## Hook Types

### PreToolUse Hooks

**Purpose**: Intercept tool calls before execution to enforce delegation patterns.

#### 1. Stravinsky Mode Enforcer (`stravinsky_mode.py`)

**Location**: `mcp_bridge/native_hooks/stravinsky_mode.py`

**Matcher**: `Read,Search,Grep,Bash,Edit,MultiEdit`

**Behavior**:
- Checks for `~/.stravinsky_mode` marker file
- When active, blocks native file tools (Read, Grep, Bash, etc.)
- Forces use of Task tool for native subagent delegation
- Outputs user-friendly messages like: `🎭 explore('Delegating Grep (searching for 'auth')')`

**Example**:
```
User prompt: "Find all authentication code"
Without hook: Uses Grep directly
With hook: Blocks Grep, shows "🎭 explore('Delegating Grep (searching for 'auth')')", forces Task delegation
```

**Delegation Pattern**:
```python
# WRONG (blocked by hook)
Grep(pattern="auth", path="src/")

# CORRECT (enforced by hook)
Task(
  subagent_type="explore",
  prompt="Find all authentication implementations in src/",
  description="Find auth code"
)
```

### PostToolUse Hooks

**Purpose**: Execute after tool completion for messaging and result processing.

#### 1. Truncator (`truncator.py`)

**Location**: `mcp_bridge/native_hooks/truncator.py`

**Matcher**: `*` (all tools)

**Behavior**: Truncates large tool outputs to prevent context overflow.

#### 2. Tool Messaging (`tool_messaging.py`)

**Location**: `mcp_bridge/native_hooks/tool_messaging.py`

**Matcher**: `mcp__stravinsky__*,mcp__grep-app__*,Task`

**Behavior**:
- Outputs concise messages about which tool/agent was used
- Format: `🔧 tool-name('description')` or `🎯 agent:model('description')`

**Examples**:
```
🔧 ast-grep('Searching AST in src/ for class definitions')
🔧 grep('Searching for authentication patterns')
🔧 lsp-diagnostics('Checking server.py for errors')
🎯 explore:gemini-3-flash('Finding all API endpoints')
🎯 delphi:gpt-5.2-medium('Analyzing architecture trade-offs')
🎯 frontend:gemini-3-pro-high('Designing login component')
```

#### 3. Edit Recovery (`edit_recovery.py`)

**Location**: `mcp_bridge/native_hooks/edit_recovery.py`

**Matcher**: `Edit,MultiEdit`

**Behavior**: Backs up file state before edits for recovery.

#### 4. Todo Delegation (`todo_delegation.py`)

**Location**: `mcp_bridge/native_hooks/todo_delegation.py`

**Matcher**: `TodoWrite`

**Behavior**: After TodoWrite, enforces parallel Task delegation for independent todos.

**Example Output**:
```
[PARALLEL DELEGATION REQUIRED]

You just created 3 pending TODOs. Before your NEXT response:

1. Identify which TODOs are INDEPENDENT (can run simultaneously)
2. For EACH independent TODO, spawn a Task agent:
   Task(subagent_type="explore", prompt="[TODO details]", run_in_background=true)
3. Fire ALL Task calls in ONE response - do NOT wait between them
```

### UserPromptSubmit Hooks

**Purpose**: Execute before prompt processing to inject context.

#### 1. Context Injector (`context.py`)

**Location**: `mcp_bridge/native_hooks/context.py`

**Matcher**: `*` (all prompts)

**Behavior**: Injects project context (git status, rules, todos) into prompts.

## Configuration

**File**: `.claude/settings.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read,Search,Grep,Bash,Edit,MultiEdit",
        "hooks": [{
          "type": "command",
          "command": "python3 /path/to/stravinsky_mode.py"
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [{
          "type": "command",
          "command": "python3 /path/to/truncator.py"
        }]
      },
      {
        "matcher": "mcp__stravinsky__*,mcp__grep-app__*,Task",
        "hooks": [{
          "type": "command",
          "command": "python3 /path/to/tool_messaging.py"
        }]
      },
      {
        "matcher": "Edit,MultiEdit",
        "hooks": [{
          "type": "command",
          "command": "python3 /path/to/edit_recovery.py"
        }]
      },
      {
        "matcher": "TodoWrite",
        "hooks": [{
          "type": "command",
          "command": "python3 /path/to/todo_delegation.py"
        }]
      }
    ],
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "hooks": [{
          "type": "command",
          "command": "python3 /path/to/context.py"
        }]
      }
    ]
  }
}
```

## Hook Execution Flow

### Stravinsky Mode Active

```
User: "Find all auth code"
  ↓
PreToolUse (stravinsky_mode.py)
  ↓ Detects ~/.stravinsky_mode exists
  ↓ Tool: Grep
  ↓ BLOCK (exit code 2)
  ↓ Output: 🎭 explore('Delegating Grep (searching for 'auth')')
  ↓
Claude receives block + message
  ↓ Uses Task tool instead:
  ↓ Task(subagent_type="explore", prompt="Find all auth...", description="Find auth")
  ↓
PostToolUse (tool_messaging.py)
  ↓ Tool: Task
  ↓ Output: 🎯 explore:gemini-3-flash('Find auth')
  ↓
User sees both messages:
  🎭 explore('Delegating Grep (searching for 'auth')')
  🎯 explore:gemini-3-flash('Find auth')
```

### Normal Mode (No Stravinsky Mode)

```
User: "Read server.py"
  ↓
PreToolUse (stravinsky_mode.py)
  ↓ ~/.stravinsky_mode does NOT exist
  ↓ ALLOW (exit code 0)
  ↓
Read tool executes normally
  ↓
PostToolUse (truncator.py)
  ↓ Truncates output if too large
  ↓
User sees normal Read output
```

### MCP Tool Usage

```
Claude: Uses lsp_diagnostics(file_path="server.py")
  ↓
PostToolUse (tool_messaging.py)
  ↓ Tool: mcp__stravinsky__lsp_diagnostics
  ↓ Output: 🔧 lsp-diagnostics('Checking server.py for errors')
  ↓
User sees: 🔧 lsp-diagnostics('Checking server.py for errors')
[followed by actual diagnostic results]
```

## Activating Stravinsky Mode

```bash
# Activate (blocks native tools, forces Task delegation)
touch ~/.stravinsky_mode

# Or with configuration
echo '{"active": true, "agent_type": "explore"}' > ~/.stravinsky_mode

# Deactivate (allows normal tool usage)
rm ~/.stravinsky_mode
```

## Agent Model Mapping

When user sees messages like `agent:model('description')`, the model shows which backend is being used:

| Agent | Model | Cost | Use Case |
|-------|-------|------|----------|
| explore | gemini-3-flash | Free | Code search, file reading |
| dewey | gemini-3-flash | Cheap | Documentation research |
| code-reviewer | sonnet | Cheap | Code quality analysis |
| debugger | sonnet | Medium | Root cause investigation |
| frontend | gemini-3-pro-high | Medium | UI/UX design |
| delphi | gpt-5.2-medium | Expensive | Strategic architecture |

## User Messaging Examples

### Successful Delegation

```
🎭 explore('Delegating Grep (searching for 'authentication')')
🎯 explore:gemini-3-flash('Find all auth implementations')
[Agent output: Found 15 authentication files...]
```

### Multi-Agent Parallel Execution

```
🎯 explore:gemini-3-flash('Find API endpoints')
🎯 dewey:gemini-3-flash('Research JWT best practices')
🎯 code-reviewer:sonnet('Review auth implementation')
[All agents execute in parallel, results aggregated]
```

### Strategic Consultation

```
🎯 delphi:gpt-5.2-medium('Architecture decision: WebSocket vs SSE')
[Delphi provides deep strategic analysis with trade-offs]
```

## Hook Benefits

1. **Enforcement**: PreToolUse hooks ensure delegation patterns are followed
2. **Transparency**: PostToolUse messaging shows which tools/agents are being used
3. **Cost Awareness**: Model names in messages (gemini-3-flash, gpt-5.2-medium) indicate cost
4. **Zero Overhead**: Hooks run in-process, no CLI spawning latency
5. **Hard Boundaries**: Native subagents inherit explicit tool lists, enforced at Claude Code level
6. **Fail-Safe**: Hooks fail open (allow on error) to prevent blocking workflow

## Debugging Hooks

```bash
# Test hook directly
echo '{"toolName": "Grep", "params": {"pattern": "auth"}}' | python3 stravinsky_mode.py
# Should output delegation message if ~/.stravinsky_mode exists

# View hook output in Claude Code logs
tail -f ~/.claude/logs/hooks.log

# Disable hook temporarily
# Edit .claude/settings.json, remove hook from matcher
```

## Next Steps

1. **Test hooks**: Run `/stravinsky` command to activate mode, verify delegation enforcement
2. **Monitor messaging**: Check that tool messages appear in stderr
3. **Verify parallel execution**: TodoWrite → Task delegation should fire simultaneously
4. **Cost optimization**: Track which agents are used most, optimize routing

---

**Summary**: Stravinsky hooks provide transparent, enforced delegation with user-friendly messaging showing which specialist agent/tool is handling each task, with clear cost indicators via model names.
