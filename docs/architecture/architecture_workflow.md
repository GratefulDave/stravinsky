# Stravinsky Workflow Architecture: 7-Phase Orchestrator

This document outlines the high-level architecture of Stravinsky's orchestration system, focusing on the 7-phase state machine that governs task execution from query intake through verification.

## Overview

Stravinsky implements an "Enforced Parallelism" pattern with a formal state machine. The orchestrator progresses through eight distinct phases (numbered 1-8 in the codebase, commonly referred to as the "7-phase workflow" plus verification), each with strict artifact requirements and valid transitions.

## 7-Phase State Machine

```
                    +----------+
                    | CLASSIFY |  Phase 1
                    +----+-----+
                         |
                         v
                    +----------+
                    | CONTEXT  |  Phase 2
                    +----+-----+
                         |
              +----------+----------+
              |                     |
              v                     |
         +---------+                |
         | WISDOM  |  Phase 3       | (optional)
         +----+----+                |
              |                     |
              +----------+----------+
                         |
                         v
                    +-------+
        +---------->| PLAN  |  Phase 4
        |           +---+---+
        |               |
        | (critique     v
        |  loop)   +----------+
        +----------+ VALIDATE |  Phase 5
                   +----+-----+
                        |
                        v
                   +----------+
                   | DELEGATE |  Phase 6
                   +----+-----+
                        |
                        v
                   +---------+
        +--------->| EXECUTE |  Phase 7
        |          +----+----+
        | (retry)       |
        +---------------+
                        |
                        v
                   +--------+
                   | VERIFY |  Phase 8
                   +---+----+
                       |
                       v
               (new orchestration cycle)
```

### Phase Descriptions

| Phase | Name | Description | Required Artifacts |
|-------|------|-------------|-------------------|
| 1 | CLASSIFY | Query classification and scope definition | None (entry point) |
| 2 | CONTEXT | Gather codebase context using appropriate search strategy | `query_classification` |
| 3 | WISDOM | Inject project wisdom from `.stravinsky/wisdom.md` | `context_summary` |
| 4 | PLAN | Strategic planning with critique loop | None (wisdom optional) |
| 5 | VALIDATE | Validate plan against rules and constraints | `plan.md` |
| 6 | DELEGATE | Route to appropriate models/agents and create TaskGraph | `validation_result` |
| 7 | EXECUTE | Execute the plan with parallel enforcement | `delegation_targets`, `task_graph` |
| 8 | VERIFY | Verify results and synthesize output | `execution_result` |

### Valid Phase Transitions

The state machine enforces strict transitions to ensure workflow integrity:

```python
VALID_TRANSITIONS = {
    CLASSIFY: [CONTEXT],
    CONTEXT: [WISDOM, PLAN],      # Wisdom is optional
    WISDOM: [PLAN],
    PLAN: [VALIDATE, PLAN],       # Can loop for critique
    VALIDATE: [DELEGATE, PLAN],   # Can return to PLAN if validation fails
    DELEGATE: [EXECUTE],
    EXECUTE: [VERIFY, EXECUTE],   # Can loop for retries
    VERIFY: [CLASSIFY],           # Start new cycle
}
```

## Core Components

### 1. OrchestratorState (`mcp_bridge/orchestrator/state.py`)

The central state machine that tracks:

- **Current Phase**: Which phase the orchestrator is in
- **History**: Record of all phase transitions
- **Artifacts**: Named artifacts required for phase transitions
- **Transition Log**: Audit trail of all transitions with timestamps
- **Critique Count**: Tracks PLAN/VALIDATE loops (max 3 iterations)

Key methods:
- `transition_to(phase)`: Validates and executes a phase transition
- `register_artifact(name, content)`: Registers an artifact for validation
- `can_transition_to(phase)`: Checks if transition is valid without executing
- `get_missing_artifacts(phase)`: Lists what artifacts are needed

### 2. TaskGraph (`mcp_bridge/orchestrator/task_graph.py`)

A Directed Acyclic Graph (DAG) representing task dependencies:

```python
# Example TaskGraph definition
task_graph = {
    "find_auth": {
        "description": "Find authentication implementations",
        "agent_type": "explore",
        "depends_on": []
    },
    "find_tests": {
        "description": "Find related test files",
        "agent_type": "explore",
        "depends_on": []
    },
    "analyze_coverage": {
        "description": "Analyze test coverage",
        "agent_type": "dewey",
        "depends_on": ["find_auth", "find_tests"]
    }
}
```

Task statuses: `PENDING` -> `SPAWNED` -> `RUNNING` -> `COMPLETED` (or `FAILED`)

### 3. DelegationEnforcer (`mcp_bridge/orchestrator/task_graph.py`)

Enforces parallel execution of independent tasks:

- **Parallel Window**: Tasks in the same wave must spawn within 500ms
- **Wave Detection**: Groups tasks by dependency level
- **Compliance Checking**: Raises `ParallelExecutionError` if parallel rules violated

```python
# Wave-based execution
Wave 1: [find_auth, find_tests]      # No dependencies - MUST run parallel
Wave 2: [analyze_coverage]            # Depends on Wave 1 completion
```

### 4. Specialized Agents (The Workers)

Agents configured in `.claude/agents/` use specialized models via MCP tools:

| Agent | Wrapper Model | External Model | Use Case |
|-------|---------------|----------------|----------|
| `explore` | Haiku | gemini-3-flash | Code search, pattern finding |
| `dewey` | Haiku | gemini-3-flash | Documentation research |
| `frontend` | Haiku | gemini-3-pro | UI/UX implementation |
| `delphi` | Haiku | gpt-5.2-medium | Strategic architecture advice |
| `stravinsky` | N/A (direct) | Sonnet 4.5 | Primary orchestration |

### 5. Phase Gates (Optional)

When `enable_phase_gates=True`, the orchestrator can require user approval before transitions:

```python
state = OrchestratorState(
    enable_phase_gates=True,
    approver=lambda: input("Approve transition? (y/n): ").lower() == "y"
)
```

---

## Workflow Lifecycle (Detailed)

### Phase 1: CLASSIFY (Intent Detection)

1. User provides a complex prompt
2. Orchestrator classifies the query type (research, implementation, debugging, etc.)
3. Registers `query_classification` artifact

**Output artifact**: `query_classification`

### Phase 2: CONTEXT (Codebase Understanding)

1. Based on classification, gathers relevant context
2. Uses appropriate search strategy (semantic, grep, AST)
3. Registers `context_summary` artifact

**Required artifact**: `query_classification`
**Output artifact**: `context_summary`

### Phase 3: WISDOM (Project Knowledge Injection)

1. Loads project-specific wisdom from `.stravinsky/wisdom.md`
2. Injects patterns, conventions, and lessons learned
3. Optional phase - can skip directly to PLAN

**Required artifact**: `context_summary`
**Output**: Wisdom context injected into orchestrator state

### Phase 4: PLAN (Strategic Planning)

1. Creates detailed execution plan
2. May iterate with VALIDATE phase (critique loop)
3. Maximum 3 critique iterations before forced forward

**Output artifact**: `plan.md`

### Phase 5: VALIDATE (Plan Validation)

1. Validates plan against project rules and constraints
2. Can return to PLAN phase if validation fails
3. Registers `validation_result` artifact on success

**Required artifact**: `plan.md`
**Output artifact**: `validation_result`

### Phase 6: DELEGATE (Agent Routing)

1. Creates TaskGraph from validated plan
2. Identifies independent task groups (waves)
3. Registers `delegation_targets` and `task_graph` artifacts

**Required artifact**: `validation_result`
**Output artifacts**: `delegation_targets`, `task_graph`

### Phase 7: EXECUTE (Parallel Execution)

1. DelegationEnforcer monitors task spawns
2. Independent tasks MUST spawn within 500ms window
3. Violation raises `ParallelExecutionError`
4. Can retry on failures

**Required artifacts**: `delegation_targets`, `task_graph`
**Output artifact**: `execution_result`

### Phase 8: VERIFY (Results Verification)

1. Collects results from all spawned agents
2. Verifies completion and quality
3. Synthesizes final output
4. Can start new orchestration cycle

**Required artifact**: `execution_result`

---

## Technical Constraints & Design Choices

### Artifact-Based Transitions

Each phase transition validates required artifacts exist:

```python
PHASE_REQUIREMENTS = {
    CLASSIFY: [],                              # Entry point
    CONTEXT: ["query_classification"],
    WISDOM: ["context_summary"],
    PLAN: [],                                  # Wisdom optional
    VALIDATE: ["plan.md"],
    DELEGATE: ["validation_result"],
    EXECUTE: ["delegation_targets", "task_graph"],
    VERIFY: ["execution_result"],
}
```

### Strict Mode vs. Permissive Mode

- **Strict Mode** (`strict_mode=True`): Enforces all artifact requirements
- **Permissive Mode** (`strict_mode=False`): Allows transitions without artifact checks

### Critique Loop Limits

The PLAN/VALIDATE loop is limited to 3 iterations:

```python
if critique_count >= max_critiques:
    raise ValueError("Max critique iterations reached. Must proceed to DELEGATE.")
```

### The "Exit Code 2" Strategy

Exit code 2 signals a **Hard Block**, forcing Claude to reconsider:
- Direct file operations blocked in stravinsky mode
- Sequential execution when parallel required

### Parallel Execution Enforcement

The DelegationEnforcer uses time-based validation:

```python
parallel_window_ms = 500  # Tasks must spawn within 500ms

# If time spread exceeds window:
raise ParallelExecutionError(
    "Tasks in wave were not spawned in parallel. "
    f"Time spread: {time_spread_ms}ms > {parallel_window_ms}ms limit."
)
```

---

## Model Routing Architecture

### Why Thin Wrappers?

Claude Code's native `Task` system only supports Claude models. To route work to external models like Gemini or GPT:

1. **Task spawns a cheap Claude Haiku wrapper** - Minimal orchestration overhead
2. **Wrapper immediately calls `invoke_gemini` or `invoke_openai`** - External model does all work

### Cost Comparison

| Pattern | Model Chain | Relative Cost |
|---------|-------------|---------------|
| **OLD** | Task -> Sonnet agent -> invoke_gemini -> Gemini | Sonnet + Gemini |
| **NEW** | Task -> Haiku wrapper -> invoke_gemini -> Gemini | Haiku + Gemini |

**Savings**: ~10x cheaper on the Claude side.

### Flow Diagram

```
User Request
     |
     v
Stravinsky Orchestrator (Sonnet)
     |
     v
[DELEGATE Phase] -> Creates TaskGraph
     |
     v
[EXECUTE Phase] -> DelegationEnforcer validates parallel spawns
     |
     +---> Task(subagent_type="explore") -> Haiku -> invoke_gemini
     |
     +---> Task(subagent_type="dewey") -> Haiku -> invoke_gemini
     |
     v
[VERIFY Phase] -> Collect and synthesize results
```

---

## State Management

### Files and Artifacts

| Location | Purpose |
|----------|---------|
| `~/.stravinsky_mode` | Marker file indicating orchestrator control |
| `.claude/execution_state.json` | Tool usage tracking |
| `.claude/task_dependencies.json` | TODO dependency graph |
| `.stravinsky/wisdom.md` | Project-specific wisdom |

### OrchestratorState Summary

Call `state.get_summary()` to get:

```python
{
    "current_phase": "execute",
    "phase_display": "[Phase 7/8] Executing the plan",
    "phase_number": 7,
    "total_phases": 8,
    "history": ["classify", "context", "wisdom", "plan", "validate", "delegate"],
    "artifacts": ["query_classification", "context_summary", "plan.md", "validation_result", "delegation_targets", "task_graph"],
    "critique_count": 1,
    "strict_mode": True,
    "phase_gates_enabled": False,
    "transitions_count": 6,
}
```

---

## Error Handling

### ParallelExecutionError

Raised when independent tasks are not spawned in parallel:

```python
class ParallelExecutionError(Exception):
    """Raised when parallel execution rules are violated."""
    pass
```

### Invalid Transitions

```python
# Attempting CLASSIFY -> EXECUTE directly raises:
ValueError: Invalid transition: classify -> execute. Valid transitions: ['context']
```

### Missing Artifacts

```python
# Attempting CONTEXT without query_classification raises:
ValueError: Missing artifacts for context phase: ['query_classification']. Available: []
```

---

## Integration with Hooks

The state machine integrates with Claude Code hooks:

| Hook Type | Integration Point |
|-----------|------------------|
| `UserPromptSubmit` | CLASSIFY phase (intent detection) |
| `PreToolUse` | EXECUTE phase (block direct operations) |
| `PostToolUse` | VERIFY phase (result collection) |

See [IMPLEMENTATION_GUIDE.md](../plans/IMPLEMENTATION_GUIDE.md) for hook implementation details.
