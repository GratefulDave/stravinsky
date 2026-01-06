# Native Hooks in Stravinsky Orchestrator

The Stravinsky orchestrator native subagent uses **native Claude Code hooks** to control delegation behavior.

## Hook Architecture

```
User Request
    ↓
Claude Code (main)
    ↓
Auto-delegates to stravinsky native subagent
    ↓
PreToolUse Hook (in orchestrator)
    ├→ Intercepts: Read, Grep, Bash, Glob
    ├→ Blocks: Return exit code 2 or {"decision": "block"}
    └→ Delegates: Task tool → specialist native subagents
        ├→ explore.md (code search)
        ├→ dewey.md (documentation)
        ├→ code-reviewer.md (quality analysis)
        ├→ debugger.md (root cause)
        └→ frontend.md (UI implementation)
```

## Hook Types Available

| Hook | When It Fires | Can Block? | Use In Orchestrator |
|------|---------------|------------|---------------------|
| **PreToolUse** | Before any tool executes | ✅ Yes | Control delegation (block direct tools, use Task instead) |
| **PostToolUse** | After tool completes | ❌ No | Result aggregation, metrics |
| **UserPromptSubmit** | Before prompt sent to LLM | ✅ Yes | Context injection, preprocessing |
| **PreCompact** | Before context compression | ❌ No | Save state before compaction |
| **SessionEnd** | When session terminates | ❌ No | Cleanup, final reporting |

## PreToolUse Hook for Delegation

The orchestrator uses `PreToolUse` to intercept direct tool calls and delegate to specialists instead.

### Example: Delegating Read/Grep to Explore Agent

```bash
#!/usr/bin/env bash
# .claude/agents/hooks/pre_tool_use.sh

# Read stdin JSON
input=$(cat)

# Parse tool name and args
tool=$(echo "$input" | jq -r '.tool')
args=$(echo "$input" | jq -r '.args')

# Delegation logic
case "$tool" in
  "Read"|"Grep"|"Glob")
    # Complex search → Delegate to explore agent
    if should_delegate_search "$args"; then
      # Block the native tool
      echo '{"decision": "block", "reason": "Delegating to explore specialist"}' | jq -c

      # Trigger Task tool delegation
      # (This would be handled by the orchestrator's system prompt)
      exit 2  # Block native tool execution
    fi
    ;;

  "Edit"|"Write")
    # Let these through - orchestrator can edit directly
    echo '{"decision": "allow"}' | jq -c
    exit 0
    ;;

  "Bash")
    # Only allow safe commands
    command=$(echo "$args" | jq -r '.command')
    if is_safe_command "$command"; then
      echo '{"decision": "allow"}' | jq -c
      exit 0
    else
      echo '{"decision": "block", "reason": "Unsafe command - requires review"}' | jq -c
      exit 2
    fi
    ;;

  *)
    # Allow all other tools
    echo '{"decision": "allow"}' | jq -c
    exit 0
    ;;
esac

# Helper functions
should_delegate_search() {
  local args="$1"

  # Delegate if:
  # - Complex pattern matching (AST search)
  # - Multi-file search (grep across codebase)
  # - Structural analysis

  # Simple heuristic: delegate if searching more than 3 files
  file_count=$(echo "$args" | jq -r '.pattern' | wc -w)
  [[ $file_count -gt 3 ]]
}

is_safe_command() {
  local cmd="$1"

  # Allow: git, ls, pwd, echo
  # Block: rm, dd, mkfs, sudo

  if echo "$cmd" | grep -qE "^(git|ls|pwd|echo|cat|head|tail)"; then
    return 0  # Safe
  else
    return 1  # Unsafe
  fi
}
```

## PostToolUse Hook for Result Aggregation

After Task tool completes, aggregate results from specialist agents.

```bash
#!/usr/bin/env bash
# .claude/agents/hooks/post_tool_use.sh

input=$(cat)
tool=$(echo "$input" | jq -r '.tool')
result=$(echo "$input" | jq -r '.result')

case "$tool" in
  "Task")
    # Specialist agent completed
    agent_type=$(echo "$input" | jq -r '.args.subagent_type')

    # Log completion
    log_agent_completion "$agent_type" "$result"

    # Update orchestrator state
    update_task_graph "$agent_type" "completed"

    # Check if all parallel tasks complete
    if all_tasks_complete; then
      trigger_synthesis_phase
    fi
    ;;
esac

# Pass through result unmodified
echo "$result"
exit 0
```

## Hook Configuration

Hooks are configured in the orchestrator's `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "command": "/absolute/path/to/.claude/agents/hooks/pre_tool_use.sh",
        "description": "Delegation control for orchestrator"
      }
    ],
    "PostToolUse": [
      {
        "command": "/absolute/path/to/.claude/agents/hooks/post_tool_use.sh",
        "description": "Result aggregation for orchestrator"
      }
    ],
    "UserPromptSubmit": [
      {
        "command": "/absolute/path/to/.claude/agents/hooks/user_prompt_submit.sh",
        "description": "Context injection for orchestrator"
      }
    ]
  }
}
```

## Delegation Patterns

### Pattern 1: Automatic Delegation on Tool Use

```
User: "Find all authentication implementations"
    ↓
Stravinsky orchestrator (native subagent)
    ↓
PreToolUse hook detects complex search
    ├→ Blocks: Read/Grep tools
    └→ Orchestrator prompt triggers: Task(subagent_type="explore", ...)
        ↓
    Explore specialist executes search
        ↓
    PostToolUse hook aggregates results
        ↓
    Orchestrator synthesizes and responds
```

### Pattern 2: Conditional Delegation

```
User: "Review this code for security issues"
    ↓
Stravinsky orchestrator
    ↓
System prompt recognizes: "review" + "security" → delegate to code-reviewer
    ↓
Task(subagent_type="code-reviewer", prompt="Review for security...")
    ↓
Code-reviewer specialist analyzes code
    ↓
Returns structured review
    ↓
Orchestrator presents to user
```

### Pattern 3: Multi-Agent Parallel Execution

```
User: "Implement JWT authentication"
    ↓
Stravinsky orchestrator
    ↓
TodoWrite: [Research JWT, Find examples, Implement, Review, Test]
    ↓
SAME RESPONSE: Multiple Task() calls
    ├→ Task(subagent_type="dewey", prompt="Research JWT best practices")
    ├→ Task(subagent_type="explore", prompt="Find existing auth patterns")
    └→ Task(subagent_type="code-reviewer", prompt="Review security")
        ↓
    All specialists execute in parallel
        ↓
    PostToolUse hooks aggregate results
        ↓
    Orchestrator synthesizes and implements
```

## Hook Execution Flow

```
┌─────────────────────────────────────────┐
│ User submits prompt                      │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ UserPromptSubmit Hook                    │
│ - Inject context (CLAUDE.md, README)    │
│ - Preprocess prompt                      │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ Claude Code auto-delegates to stravinsky │
│ (based on description matching)          │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ Stravinsky orchestrator processes        │
│ - TodoWrite (plan tasks)                 │
│ - Decides on delegation strategy         │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ PreToolUse Hook fires                    │
│ - Intercepts: Read, Grep, Glob, Bash    │
│ - Decision: Allow or Block               │
└───────────────┬─────────────────────────┘
                ↓
        ┌───────┴───────┐
        ↓               ↓
┌──────────────┐ ┌──────────────────────┐
│ ALLOW        │ │ BLOCK                │
│ Native tool  │ │ Delegate via Task    │
│ executes     │ │ to specialist agent  │
└──────┬───────┘ └──────┬───────────────┘
       │                │
       └────────┬───────┘
                ↓
┌─────────────────────────────────────────┐
│ PostToolUse Hook fires                   │
│ - Log completion                         │
│ - Aggregate results                      │
│ - Update task graph                      │
└───────────────┬─────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│ Orchestrator synthesizes results         │
│ - Combines specialist outputs            │
│ - Updates todos                          │
│ - Responds to user                       │
└─────────────────────────────────────────┘
```

## Benefits of This Architecture

1. **Automatic Delegation**: Hooks detect when to delegate automatically
2. **Hard Boundaries**: PreToolUse can block unsafe operations
3. **Context Isolation**: Specialists run as separate subagents
4. **Parallel Execution**: Multiple Task() calls execute concurrently
5. **Result Aggregation**: PostToolUse hooks combine outputs
6. **Multi-Model Routing**: Specialists can use invoke_gemini/openai MCP tools
7. **Security**: Orchestrator controls what tools specialists can access

## Implementation Status

- [x] Stravinsky orchestrator native subagent (.claude/agents/stravinsky.md)
- [x] Specialist subagent configs (explore, dewey, code-reviewer, debugger, frontend)
- [ ] PreToolUse hook implementation (.claude/agents/hooks/pre_tool_use.sh)
- [ ] PostToolUse hook implementation (.claude/agents/hooks/post_tool_use.sh)
- [ ] Hook registration in .claude/settings.json
- [ ] Testing and validation

## Next Steps

1. Implement PreToolUse hook script
2. Implement PostToolUse hook script
3. Register hooks in .claude/settings.json
4. Test delegation patterns
5. Measure: delegation accuracy, context isolation, performance

---

## Agent Cost Classification & Thinking Budget

### Cost-Based Routing (oh-my-opencode Pattern)

Each agent has cost/execution metadata in YAML frontmatter:

```yaml
---
name: agent-name
model: sonnet
cost: free | cheap | medium | expensive  # Cost tier
execution: async | blocking | primary  # Execution pattern
temperature: 0.1  # Model temperature (0.0-2.0)
thinking_budget: 32000  # Extended thinking budget (optional, for Opus/GPT)
---
```

### Agent Classification

| Agent | Cost | Execution | When to Delegate |
|-------|------|-----------|------------------|
| **explore** | Free | Async | Always (code search is free) |
| **dewey** | Cheap | Async | Always (docs research is cheap) |
| **code-reviewer** | Cheap | Async | Always (quality checks are cheap) |
| **debugger** | Medium | Blocking | After 2+ failed fix attempts |
| **frontend** | Medium | Blocking | ALL visual changes (no exceptions) |
| **delphi** | Expensive | Blocking | After 3+ failures, architecture decisions |
| **stravinsky** | Moderate | Primary | Auto-delegated orchestrator |

### Execution Patterns

**Async (Non-Blocking)**:
- Agent runs in parallel via Task tool
- Orchestrator continues immediately
- Results collected when needed
- Use for: free/cheap agents (explore, dewey, code-reviewer)

**Blocking (Synchronous)**:
- Orchestrator waits for result
- Used when decision depends on output
- Use for: expensive agents (delphi), visual work (frontend), debugging (debugger)

**Primary**:
- The orchestrator itself (stravinsky)
- Manages all delegation
- Never blocks (delegates instead)

### Extended Thinking Budget

**What It Is**:
- Extended reasoning capability for complex tasks
- Claude Opus 4.5 and GPT-5.2 support thinking blocks
- Allows model to "think out loud" before responding
- Improves accuracy for complex analysis

**Configuration**:

```yaml
# In agent YAML frontmatter:
thinking_budget: 32000  # 32k tokens for thinking (oh-my-opencode Sisyphus pattern)
```

**Which Agents Use It**:
- **stravinsky** (orchestrator): 32k thinking for complex task planning
- **delphi** (strategic advisor): 32k thinking for architectural decisions
- **Others**: No extended thinking (focus on execution)

**How It Works**:

For Claude models with extended thinking:
```xml
<thinking>
[Model's internal reasoning - up to 32k tokens]
- Analyzing the problem
- Considering multiple approaches
- Evaluating trade-offs
- Planning implementation strategy
</thinking>

[Final response based on extended reasoning]
```

For GPT models (via invoke_openai):
```python
invoke_openai(
    prompt="...",
    model="gpt-5.2-medium",
    reasoning_effort="medium",  # Equivalent to thinking budget
    text_verbosity="high"  # Get detailed reasoning
)
```

### Cost Optimization Rules

**Always Delegate Async** (oh-my-opencode rule):
- explore: Free, always background
- dewey: Cheap, always background
- code-reviewer: Cheap, always background

**Use Blocking Sparingly**:
- debugger: Only after 2+ failed attempts
- frontend: Only for visual changes (but ALWAYS for visual)
- delphi: Only after 3+ failures OR complex architecture

**Never Work Alone** (delegation discipline):
- Orchestrator blocks Read/Grep/Bash via PreToolUse hooks
- Forces delegation to specialists
- Prevents expensive orchestrator from doing cheap work

---

**Key Insight**: Native hooks in the orchestrator subagent enable **automatic delegation** to specialist agents while maintaining **hard security boundaries** and **context isolation**. This is the CORRECT architecture the user has been advocating for.
