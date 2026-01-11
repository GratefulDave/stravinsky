# Agent Orchestration Architecture

This document details Stravinsky's agent spawning and orchestration patterns for parallel execution.

## Overview

Stravinsky implements an **Enforced Parallelism** pattern inspired by oh-my-opencode. It uses native Claude Code subagents with automatic delegation to external models via MCP tools.

```mermaid
flowchart TB
    subgraph "Orchestration Layer"
        STRAV[Stravinsky Orchestrator<br/>Claude Sonnet 4.5]
        TODO[TodoWrite<br/>Task Tracking]
    end

    subgraph "Agent Layer"
        subgraph "Async Agents (Cheap)"
            E1[explore<br/>gemini-3-flash]
            E2[dewey<br/>gemini-3-flash]
            CR[code-reviewer<br/>Claude Sonnet]
        end

        subgraph "Blocking Agents (When Needed)"
            FE[frontend<br/>gemini-3-pro-high]
            DEB[debugger<br/>Claude Sonnet]
            DEL[delphi<br/>gpt-5.2-medium]
        end
    end

    STRAV --> TODO
    TODO -->|parallel| E1
    TODO -->|parallel| E2
    TODO -->|parallel| CR
    TODO -->|blocking| FE
    TODO -->|blocking| DEB
    TODO -->|blocking| DEL
```

## Agent Types

### Agent Characteristics

| Agent | Model | Cost | Mode | Trigger |
|-------|-------|------|------|---------|
| **stravinsky** | Sonnet 4.5 (32k thinking) | Moderate | Primary | `/strav` command |
| **explore** | gemini-3-flash | Free | Async | Code search queries |
| **dewey** | gemini-3-flash | Cheap | Async | Documentation research |
| **code-reviewer** | Claude Sonnet | Cheap | Async | Quality analysis |
| **frontend** | gemini-3-pro-high | Medium | Blocking | ALL visual changes |
| **debugger** | Claude Sonnet | Medium | Blocking | After 2+ failures |
| **delphi** | gpt-5.2-medium | Expensive | Blocking | Architecture, 3+ failures |

### Cost Optimization Strategy

```mermaid
pie title Agent Cost Distribution
    "Free (explore)" : 40
    "Cheap (dewey, code-reviewer)" : 30
    "Medium (frontend, debugger)" : 20
    "Expensive (delphi)" : 10
```

**Principle**: Use the cheapest agent that can complete the task.

## Parallel Execution Pattern

### Correct Pattern

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant T as TodoWrite
    participant E1 as explore:gemini
    participant E2 as explore:gemini
    participant D as dewey:gemini

    Note over O: User requests complex task

    O->>T: TodoWrite([task1, task2, task3])

    rect rgb(200, 255, 200)
        Note over O,D: SAME RESPONSE - Parallel Launch
        O->>E1: agent_spawn(task1)
        O->>E2: agent_spawn(task2)
        O->>D: agent_spawn(task3)
    end

    E1-->>O: Results (async)
    E2-->>O: Results (async)
    D-->>O: Results (async)

    O->>O: Synthesize results
    O->>T: Mark todos complete
```

### Anti-Pattern (Sequential)

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant T as TodoWrite

    Note over O: WRONG - Sequential execution

    O->>T: TodoWrite([task1])
    Note over O: Response ends

    O->>T: Mark task1 in_progress
    O->>O: Do work manually
    Note over O: Response ends

    O->>T: TodoWrite([task2])
    Note over O: Defeats parallelism!
```

## Agent Spawn Flow

### spawn_agent() Implementation

```mermaid
flowchart TD
    SPAWN[agent_spawn] --> SETUP[Setup Task]
    SETUP --> PROC[Create Subprocess<br/>claude --agent-type]
    PROC --> BG{Background?}

    BG -->|Yes| ASYNC[Return task_id immediately]
    BG -->|No| BLOCK[Wait for completion]

    ASYNC --> MON[Monitor in background]
    BLOCK --> WAIT[Collect result]

    MON --> OUT[Write to .out file]
    WAIT --> RETURN[Return result]

    subgraph "Background Monitoring"
        OUT --> PROG[agent_progress<br/>tail -f output]
        OUT --> COLL[agent_output<br/>collect when done]
    end
```

### Agent Execution Environment

```python
# Agent subprocess command
claude \
    --agent-type {agent_type} \
    --model haiku \  # Thin wrapper
    --prompt "..." \
    --mcp-tools invoke_gemini,grep_search,...

# Output captured to:
# ~/.stravinsky/agents/{task_id}.out
```

## Thin Wrapper Pattern

### Why Thin Wrappers?

Claude Code's `Task` system only supports Claude models. To access Gemini/GPT:

```mermaid
flowchart LR
    subgraph "OLD (Expensive)"
        O1[Task] --> S1[Sonnet Agent]
        S1 --> G1[invoke_gemini]
        G1 --> GM1[Gemini]
    end

    subgraph "NEW (Cheap)"
        O2[Task] --> H2[Haiku Wrapper]
        H2 --> G2[invoke_gemini]
        G2 --> GM2[Gemini]
    end

    style S1 fill:#ff9999
    style H2 fill:#99ff99
```

**Cost Savings**: ~10x cheaper on the Claude side.

### Wrapper Implementation

Each specialized agent's prompt instructs it to:

1. Parse the incoming task
2. Immediately call `invoke_gemini` or `invoke_openai`
3. Pass through the full context
4. Return the external model's response

```python
# explore agent prompt (simplified)
"""
You are an explore agent. For ALL tasks:
1. Call invoke_gemini with the search query
2. Return Gemini's response unchanged
Do NOT do any work yourself.
"""
```

## Delegation Rules

### When to Use Each Agent

```mermaid
flowchart TD
    TASK[User Task] --> TYPE{Task Type?}

    TYPE -->|"Where is X?"| EXP[explore<br/>async]
    TYPE -->|"How does library Y work?"| DEW[dewey<br/>async]
    TYPE -->|"Review this code"| CR[code-reviewer<br/>async]
    TYPE -->|"Change this UI"| FE[frontend<br/>blocking]
    TYPE -->|"Fix this bug"| DEBUG{Attempts?}
    TYPE -->|"Design this system"| ARCH{Complexity?}

    DEBUG -->|< 2| TRY[Try directly]
    DEBUG -->|>= 2| DEB[debugger<br/>blocking]

    ARCH -->|Low| TRY
    ARCH -->|High| DEL[delphi<br/>blocking]

    TRY -->|Fails| DEBUG
```

### Blocking vs Async

| Mode | Agents | When to Use |
|------|--------|-------------|
| **Async** | explore, dewey, code-reviewer | Research, search, review |
| **Blocking** | frontend, debugger, delphi | Must complete before next step |

## Hook-Based Enforcement

### PreToolUse Hooks

```mermaid
flowchart TD
    TOOL[Tool Call] --> HOOK{Stravinsky Mode?}

    HOOK -->|No| EXEC[Execute normally]
    HOOK -->|Yes| CHECK{Tool Type?}

    CHECK -->|Read/Grep/Bash| BLOCK[Exit Code 2<br/>Must delegate!]
    CHECK -->|Task/agent_spawn| ALLOW[Allow execution]
    CHECK -->|TodoWrite| ALLOW

    BLOCK --> RETRY[Force delegation]
    RETRY --> ALLOW
```

### Stravinsky Mode Marker

```bash
# Mode activated by orchestrator
touch ~/.stravinsky_mode

# Mode deactivated on completion
rm ~/.stravinsky_mode
```

When active, hooks block direct file operations, forcing delegation.

## Agent Output Collection

### Output Storage

```
~/.stravinsky/agents/
├── agent_abc123.out     # stdout/stderr
├── agent_abc123.status  # running/complete/failed
├── agent_def456.out
└── agent_def456.status
```

### Collection Flow

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant AM as Agent Manager
    participant FS as File System

    O->>AM: agent_output(task_id, block=false)
    AM->>FS: Read {task_id}.status

    alt Status: running
        AM-->>O: Running (partial output)
    else Status: complete
        AM->>FS: Read {task_id}.out
        AM-->>O: Full result
    else Status: failed
        AM->>FS: Read {task_id}.out
        AM-->>O: Error + stderr
    end
```

### Progress Monitoring

```python
# Real-time progress (like tail -f)
result = await agent_progress(task_id, lines=20)

# Block until complete
result = await agent_output(task_id, block=True)
```

## ULTRATHINK / IRONSTAR Modes

### ULTRATHINK

Extended thinking budget for complex reasoning:

```mermaid
flowchart LR
    REQ[Complex Request] --> UT[ULTRATHINK Mode]
    UT --> TB[32k thinking tokens]
    TB --> DEEP[Deep Analysis]
    DEEP --> RESULT[Thorough Result]
```

### IRONSTAR

Maximum parallel execution:

```mermaid
flowchart TB
    REQ[Multi-Part Request] --> IS[IRONSTAR Mode]

    IS --> SPAWN1[agent_spawn #1]
    IS --> SPAWN2[agent_spawn #2]
    IS --> SPAWN3[agent_spawn #3]
    IS --> SPAWN4[agent_spawn #4]
    IS --> SPAWN5[agent_spawn #5]

    SPAWN1 & SPAWN2 & SPAWN3 & SPAWN4 & SPAWN5 --> SYNC[Synchronize]
    SYNC --> RESULT[Combined Result]
```

**Rule**: Launch ALL agents in ONE response. Don't wait.

## Error Handling

### Failed Agent Recovery

```mermaid
stateDiagram-v2
    [*] --> Running: agent_spawn

    Running --> Complete: Success
    Running --> Failed: Error

    Failed --> Retry: agent_retry()
    Retry --> Running: New attempt

    Failed --> Escalate: Max retries
    Escalate --> Delphi: Consult advisor

    Complete --> [*]
    Delphi --> [*]
```

### Timeout Handling

```python
# Default timeout: 300 seconds (5 min)
# Can be customized per agent
result = await agent_spawn(
    prompt="...",
    timeout=600,  # 10 min for long tasks
    agent_type="explore"
)
```

## Best Practices

### Do's

- Fire all independent agents in ONE response
- Use cheapest agent that can do the job
- Mark todos complete immediately when done
- Use `agent_progress` for long-running tasks

### Don'ts

- Don't use `delphi` for simple searches (use `explore`)
- Don't block on async agents unnecessarily
- Don't forget to mark todos complete
- Don't spawn sequential agents across responses

## Related Documentation

- [Architecture Overview](ARCHITECTURE.md)
- [MCP Tool Flow](MCP_TOOL_FLOW.md)
- [Hooks System](HOOKS.md)
- [Agent Workflow](AGENT_WORKFLOW.md)
