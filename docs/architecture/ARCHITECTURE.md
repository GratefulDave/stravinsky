# Stravinsky Architecture Guide

**Version:** v0.5.x (Updated 2026-01-22)
**Purpose:** Comprehensive architectural documentation for developers and contributors

---

## Executive Summary

Stravinsky is a **Model Context Protocol (MCP) bridge** that enables Claude Code to:
- Orchestrate multi-model AI workflows (Gemini, OpenAI, Claude) via 7-phase orchestration
- Spawn background agents with full tool access and parallel execution enforcement
- Perform semantic code understanding via vector embeddings
- Leverage Language Server Protocol for code refactoring

### Core Design Principles

1. **7-Phase Orchestration**: CLASSIFY -> CONTEXT -> WISDOM -> PLAN -> VALIDATE -> DELEGATE -> EXECUTE -> VERIFY
2. **Hard Parallel Enforcement**: Independent tasks MUST be spawned simultaneously via TaskGraph and DelegationEnforcer
3. **Zero-Import-Weight Startup**: Sub-second initialization via aggressive lazy loading
4. **OAuth-First with API Fallback**: Automatic degradation to API keys on rate limits
5. **Agent Delegation Prompts**: Injected at spawn time for cross-repo MCP installations

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [7-Phase Orchestration](#7-phase-orchestration)
3. [TaskGraph and Parallel Enforcement](#taskgraph-and-parallel-enforcement)
4. [Agent Delegation System](#agent-delegation-system)
5. [Project Structure](#project-structure)
6. [Core Components](#core-components)
7. [Tool Categories](#tool-categories)
8. [Authentication Flows](#authentication-flows)
9. [Hook System](#hook-system)
10. [Design Patterns](#design-patterns)
11. [Performance Optimizations](#performance-optimizations)
12. [Troubleshooting](#troubleshooting)

---

## Quick Reference

| Component | File | Purpose |
|-----------|------|---------|
| **MCP Server** | `mcp_bridge/server.py` | Protocol entry point (zero-import-weight) |
| **Agent Manager** | `tools/agent_manager.py` | Background agent orchestration with parallel enforcement |
| **Orchestrator State** | `orchestrator/state.py` | 7-phase workflow state machine |
| **TaskGraph** | `orchestrator/task_graph.py` | DAG for parallel task execution |
| **Model Routing** | `routing/config.py` | Tier-aware multi-provider routing and OAuth fallback |
| **Model Invoke** | `tools/model_invoke.py` | Multi-model API calls via proxy/direct |
| **Semantic Search** | `tools/semantic_search.py` | Vector-based code search (ChromaDB) |
| **OAuth** | `auth/google_auth.py`, `auth/openai_auth.py` | Authentication flows |

---

## 7-Phase Orchestration

Stravinsky implements a strict 7-phase workflow for task orchestration. Each phase has specific requirements and valid transitions.

### Phase Overview

```
CLASSIFY -> CONTEXT -> WISDOM -> PLAN -> VALIDATE -> DELEGATE -> EXECUTE -> VERIFY
   [1]       [2]        [3]      [4]       [5]        [6]        [7]       [8]
```

### Phase Descriptions

| Phase | Number | Purpose | Required Artifacts |
|-------|--------|---------|-------------------|
| **CLASSIFY** | 1 | Query classification and scope definition | None (entry point) |
| **CONTEXT** | 2 | Gather codebase context using appropriate search strategy | `query_classification` |
| **WISDOM** | 3 | Inject project wisdom from `.stravinsky/wisdom.md` | `context_summary` |
| **PLAN** | 4 | Strategic planning with critique loop | None (wisdom optional) |
| **VALIDATE** | 5 | Validate plan against rules and constraints | `plan.md` |
| **DELEGATE** | 6 | Route to appropriate models/agents, build TaskGraph | `validation_result` |
| **EXECUTE** | 7 | Execute the plan with parallel enforcement | `delegation_targets`, `task_graph` |
| **VERIFY** | 8 | Verify results and synthesize output | `execution_result` |

### Valid Phase Transitions

```python
VALID_TRANSITIONS = {
    CLASSIFY: [CONTEXT],
    CONTEXT: [WISDOM, PLAN],  # Wisdom is optional
    WISDOM: [PLAN],
    PLAN: [VALIDATE, PLAN],   # Can loop for critique (max 3 iterations)
    VALIDATE: [DELEGATE, PLAN],  # Can return to PLAN if validation fails
    DELEGATE: [EXECUTE],
    EXECUTE: [VERIFY, EXECUTE],  # Can loop for retries
    VERIFY: [CLASSIFY],  # Can start new cycle
}
```

### Implementation Files

- **State Machine**: `mcp_bridge/orchestrator/state.py`
- **Phase Enums**: `mcp_bridge/orchestrator/enums.py`
- **Visualization**: `mcp_bridge/orchestrator/visualization.py`
- **Wisdom Loader**: `mcp_bridge/orchestrator/wisdom.py`
- **Model Router**: `mcp_bridge/orchestrator/router.py`

### Phase Artifact Requirements

```python
PHASE_REQUIREMENTS = {
    CLASSIFY: [],  # Entry point, no requirements
    CONTEXT: ["query_classification"],
    WISDOM: ["context_summary"],
    PLAN: [],  # Wisdom is optional
    VALIDATE: ["plan.md"],
    DELEGATE: ["validation_result"],
    EXECUTE: ["delegation_targets", "task_graph"],  # TaskGraph required for parallel
    VERIFY: ["execution_result"],
}
```

---

## TaskGraph and Parallel Enforcement

Stravinsky enforces **hard parallel execution** for independent tasks. This is not advisory - the system will block sequential execution of tasks that should run in parallel.

### TaskGraph Overview

The `TaskGraph` is a Directed Acyclic Graph (DAG) that tracks task dependencies and determines which tasks can execute in parallel.

```python
from mcp_bridge.orchestrator.task_graph import TaskGraph, DelegationEnforcer

# Create a task graph
graph = TaskGraph()
graph.add_task("task_a", "Find auth code", "explore", dependencies=[])
graph.add_task("task_b", "Research best practices", "dewey", dependencies=[])
graph.add_task("task_c", "Implement feature", "frontend", dependencies=["task_a", "task_b"])

# Get parallel execution waves
waves = graph.get_independent_groups()
# Result: [[task_a, task_b], [task_c]]
# Wave 1: task_a and task_b run in parallel
# Wave 2: task_c runs after both complete
```

### DelegationEnforcer

The `DelegationEnforcer` validates that independent tasks are spawned within a time window (500ms default), indicating true parallel execution.

```python
from mcp_bridge.orchestrator.task_graph import DelegationEnforcer, ParallelExecutionError

# Create enforcer from task graph
enforcer = DelegationEnforcer(task_graph=graph, parallel_window_ms=500, strict=True)

# Before spawning, validate the spawn is allowed
is_valid, error = enforcer.validate_spawn("task_a")
if not is_valid:
    raise ParallelExecutionError(error)

# After spawning, record the spawn
enforcer.record_spawn("task_a", "agent_12345678")

# After all tasks in wave complete, check parallel compliance
is_compliant, error = enforcer.check_parallel_compliance()
# If tasks were spawned sequentially (>500ms apart), this raises ParallelExecutionError
```

### Integration with Agent Manager

The `AgentManager` integrates with the `DelegationEnforcer` to enforce parallel execution:

```python
# In agent_manager.py
from ..orchestrator.task_graph import DelegationEnforcer

# Global enforcer (set during DELEGATE phase)
_delegation_enforcer: DelegationEnforcer | None = None

def set_delegation_enforcer(enforcer: DelegationEnforcer) -> None:
    """Set the delegation enforcer for parallel execution validation."""
    global _delegation_enforcer
    _delegation_enforcer = enforcer

async def agent_spawn(
    prompt: str,
    agent_type: str,
    task_graph_id: str | None = None,  # Link to TaskGraph for enforcement
    ...
) -> str:
    enforcer = get_delegation_enforcer()
    if enforcer and task_graph_id:
        # Validate spawn is allowed
        is_valid, error = enforcer.validate_spawn(task_graph_id)
        if not is_valid:
            raise ParallelExecutionError(error)

        # Record spawn after successful validation
        task_id = await manager.spawn_async(...)
        enforcer.record_spawn(task_graph_id, task_id)
```

### Task Status Lifecycle

```python
class TaskStatus(Enum):
    PENDING = "pending"    # Task not yet spawned
    SPAWNED = "spawned"    # Task spawned, waiting to run
    RUNNING = "running"    # Task actively executing
    COMPLETED = "completed" # Task finished successfully
    FAILED = "failed"      # Task failed
```

### Parallel Execution Errors

When parallel execution rules are violated, a `ParallelExecutionError` is raised:

```python
class ParallelExecutionError(Exception):
    """Raised when parallel execution rules are violated."""
    pass

# Example error messages:
# "Task 'task_c' has unmet dependencies. Current wave tasks: ['task_a', 'task_b']"
# "Tasks in wave were not spawned in parallel. Time spread: 1200ms > 500ms limit."
```

---

## Agent Delegation System

### Agent Delegation Prompts

Stravinsky injects **delegation prompts** into agents at spawn time. This ensures agents properly delegate to their designated models (Gemini, OpenAI, etc.) even in external repositories where `.claude/agents/*.md` files are not available.

```python
# In agent_manager.py

AGENT_DELEGATION_PROMPTS = {
    "explore": """## CRITICAL: YOU ARE A THIN WRAPPER - DELEGATE TO GEMINI IMMEDIATELY

You are the Explore agent. Your ONLY job is to delegate ALL work to Gemini Flash.

**IMMEDIATELY** call `mcp__stravinsky__invoke_gemini_agentic` with:
- **model**: `gemini-3-flash`
- **prompt**: The complete task description
- **max_turns**: 10

**CRITICAL**: Use `invoke_gemini_agentic` NOT `invoke_gemini`. The agentic version
enables Gemini to call tools like `semantic_search`, `grep_search`, `ast_grep_search`.
""",
    "dewey": "...",
    "delphi": "...",  # Delegates to OpenAI/GPT
    # ... other agents
}

def get_agent_delegation_prompt(agent_type: str) -> str:
    """Get the delegation prompt for an agent type."""
    return AGENT_DELEGATION_PROMPTS.get(agent_type, DEFAULT_DELEGATION_PROMPT)
```

### Agent Model Routing

Each agent type is mapped to a specific model and cost tier:

```python
AGENT_MODEL_ROUTING = {
    "explore": None,           # Uses Gemini Flash via delegation
    "dewey": None,             # Uses Gemini Flash via delegation
    "delphi": None,            # Uses GPT-5.2 via delegation
    "frontend": None,          # Uses Gemini Pro via delegation
    "implementation-lead": "sonnet",  # Direct Claude Sonnet
    "debugger": "sonnet",      # Direct Claude Sonnet
    "planner": "opus",         # Direct Claude Opus
    "_default": "sonnet",
}

AGENT_COST_TIERS = {
    "explore": "CHEAP",
    "dewey": "CHEAP",
    "delphi": "EXPENSIVE",
    "frontend": "MEDIUM",
    "debugger": "MEDIUM",
    "planner": "EXPENSIVE",
}

AGENT_DISPLAY_MODELS = {
    "explore": "gemini-3-flash",
    "dewey": "gemini-3-flash",
    "delphi": "gpt-5.2",
    "frontend": "gemini-3-pro-high",
    "debugger": "claude-sonnet-4.5",
    "planner": "opus-4.5",
}
```

### Agent Tool Access

Each agent type has a defined set of allowed tools:

```python
AGENT_TOOLS = {
    "stravinsky": ["all"],
    "research-lead": ["agent_spawn", "agent_output", "invoke_gemini", "Read", "Grep", "Glob"],
    "implementation-lead": ["agent_spawn", "agent_output", "lsp_diagnostics", "Read", "Edit", "Write", "Grep", "Glob"],
    "explore": ["Read", "Grep", "Glob", "Bash", "semantic_search", "ast_grep_search", "lsp_workspace_symbols"],
    "dewey": ["Read", "Grep", "Glob", "Bash", "WebSearch", "WebFetch"],
    "frontend": ["Read", "Edit", "Write", "Grep", "Glob", "Bash", "invoke_gemini"],
    "delphi": ["Read", "Grep", "Glob", "Bash", "invoke_openai"],
    "debugger": ["Read", "Grep", "Glob", "Bash", "lsp_diagnostics", "lsp_hover", "ast_grep_search"],
    "code-reviewer": ["Read", "Grep", "Glob", "Bash", "lsp_diagnostics", "ast_grep_search"],
}
```

### Agent Hierarchy Enforcement

The system enforces a strict agent hierarchy:

```python
ORCHESTRATOR_AGENTS = ["stravinsky", "research-lead", "implementation-lead"]
WORKER_AGENTS = ["explore", "dewey", "delphi", "frontend", "debugger", "code-reviewer", ...]

def validate_agent_hierarchy(spawning_agent: str, target_agent: str) -> None:
    """Prevent workers from spawning orchestrators or other workers."""
    if spawning_agent in WORKER_AGENTS and target_agent in ORCHESTRATOR_AGENTS:
        raise ValueError("Worker cannot spawn orchestrator")
    if spawning_agent in WORKER_AGENTS and target_agent in WORKER_AGENTS:
        raise ValueError("Worker cannot spawn another worker")
```

---

## Project Structure

```
stravinsky/
├── mcp_bridge/                    # Python MCP server
│   ├── server.py                  # Entry point
│   ├── orchestrator/              # 7-Phase Orchestration (NEW)
│   │   ├── enums.py               # OrchestrationPhase enum
│   │   ├── state.py               # OrchestratorState machine
│   │   ├── task_graph.py          # TaskGraph and DelegationEnforcer
│   │   ├── router.py              # Intelligent model router
│   │   ├── wisdom.py              # WisdomLoader and CritiqueGenerator
│   │   └── visualization.py       # Phase progress visualization
│   ├── tools/                     # MCP Tools
│   │   ├── agent_manager.py       # Agent spawning with parallel enforcement
│   │   ├── model_invoke.py        # Multi-model invocation
│   │   ├── code_search.py         # grep, ast-grep, glob
│   │   ├── semantic_search.py     # Vector search with embeddings
│   │   └── lsp/                   # Language Server Protocol tools
│   ├── auth/                      # OAuth (Google and OpenAI)
│   ├── hooks/                     # MCP internal hooks
│   ├── routing/                   # Model routing configuration
│   └── prompts/                   # Agent system prompts
├── .claude/                       # Claude Code configuration
│   ├── agents/                    # Native subagent definitions
│   ├── commands/                  # Slash commands (skills)
│   ├── hooks/                     # Native Claude Code hooks
│   └── settings.json              # Hook registration
├── .stravinsky/                   # Runtime state
│   ├── agents/                    # Agent task state
│   └── wisdom.md                  # Project learnings
├── pyproject.toml                 # Build system
└── CLAUDE.md                      # Claude Code guide
```

---

## Core Components

### OrchestratorState (state.py)

The central state machine for the 7-phase workflow:

```python
@dataclass
class OrchestratorState:
    current_phase: OrchestrationPhase = OrchestrationPhase.CLASSIFY
    history: list[OrchestrationPhase] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    transition_log: list[PhaseTransitionEvent] = field(default_factory=list)
    enable_phase_gates: bool = False  # Require user approval
    strict_mode: bool = True  # Enforce artifact requirements
    critique_count: int = 0   # Track PLAN iterations
    max_critiques: int = 3    # Max before forcing forward

    def transition_to(self, next_phase: OrchestrationPhase) -> bool:
        """Transition to next phase if requirements met."""

    def register_artifact(self, name: str, content: str) -> None:
        """Register an artifact for phase validation."""

    def get_phase_display(self) -> str:
        """Get formatted phase display: [Phase 3/8] Injecting project wisdom"""
```

### Router (router.py)

Intelligent model routing with multi-provider fallback:

```python
class Router:
    def select_model(
        self,
        phase: OrchestrationPhase,
        task_type: TaskType | None = None,
        prompt: str | None = None,
    ) -> str:
        """Select best model for phase and task type."""
        # Task-based routing takes precedence
        # Falls back to phase-based routing
        # Checks provider availability
        # Applies OAuth fallback chain
```

### WisdomLoader (wisdom.py)

Loads project-specific learnings from `.stravinsky/wisdom.md`:

```python
class WisdomLoader:
    def load_wisdom(self) -> str:
        """Load project wisdom for injection into WISDOM phase."""

class CritiqueGenerator:
    def generate_critique_prompt(self, plan_content: str) -> str:
        """Generate self-critique prompt for PLAN phase iteration."""
```

---

## Tool Categories

### Category 1: Model Invocation (3 tools)

| Tool | Purpose | Model Access |
|------|---------|--------------|
| `invoke_gemini` | Invoke Gemini models | Direct API call |
| `invoke_gemini_agentic` | Gemini with tool access | Multi-turn with tools |
| `invoke_openai` | Invoke OpenAI/GPT models | Direct API call |

### Category 2: Agent Management (6 tools)

| Tool | Purpose | Execution |
|------|---------|-----------|
| `agent_spawn` | Launch background agent with parallel enforcement | Async |
| `agent_output` | Get agent results | Blocking or polling |
| `agent_progress` | Real-time agent progress | Non-blocking |
| `agent_cancel` | Stop running agent | Immediate |
| `agent_list` | List all agents | Non-blocking |
| `agent_retry` | Retry failed agent | Async |

### Category 3: Code Search (4 tools)

| Tool | Pattern Type | Best For |
|------|-------------|----------|
| `grep_search` | Exact text/regex | Keywords, function names |
| `ast_grep_search` | AST patterns | Code structure, decorators |
| `glob_files` | Filesystem patterns | File discovery |
| `semantic_search` | Natural language | Conceptual queries |

### Category 4: LSP Tools (12 tools)

Full Language Server Protocol support: hover, goto_definition, find_references, document_symbols, workspace_symbols, rename, code_actions, diagnostics, and more.

---

## Authentication Flows

### OAuth-First Architecture

1. **OAuth is tried first** (if configured)
2. On OAuth 429 rate limit -> **Automatically switch to API key** for 5 minutes
3. After 5-minute cooldown -> Retry OAuth

### Supported Providers

- **Google (Gemini)**: Browser-based OAuth 2.0 with PKCE
- **OpenAI (ChatGPT)**: Browser-based OAuth on port 1455

---

## Hook System

### Hybrid Architecture

Stravinsky uses a **hybrid hook architecture** with two layers:

**Native Claude Code Hooks** (in `.claude/settings.json`):
- `PreToolUse`: Block/allow tool execution
- `PostToolUse`: Result processing
- `UserPromptSubmit`: Context injection

**MCP Internal Hooks** (in `mcp_bridge/hooks/`):
- Model routing
- Token tracking
- Session state

### Why Two Layers?

| Capability | Native Hooks | MCP Hooks |
|------------|--------------|-----------|
| Block tool execution | Yes (exit 2) | No |
| Inject prompt context | Yes | No |
| Route model invocations | No | Yes |
| Track token usage | No | Yes |

---

## Design Patterns

### Parallel Execution Pattern

```python
# CORRECT: Spawn all independent tasks simultaneously
task_a = agent_spawn("Find auth code", "explore", task_graph_id="task_a")
task_b = agent_spawn("Research patterns", "dewey", task_graph_id="task_b")
task_c = agent_spawn("Review security", "code-reviewer", task_graph_id="task_c")
# All spawn within 500ms window

# Wait for results
result_a = agent_output(task_a, block=True)
result_b = agent_output(task_b, block=True)
result_c = agent_output(task_c, block=True)

# WRONG: Sequential spawning (will raise ParallelExecutionError)
# task_a = agent_spawn(...)
# result_a = agent_output(task_a, block=True)  # Wait before next spawn
# task_b = agent_spawn(...)  # ERROR: Should have been spawned with task_a
```

### Delegation Pattern

```python
# Agents are thin wrappers that delegate to specialized models
# Example: explore agent delegates to Gemini Flash

# System prompt injected at spawn time:
"""
You are the Explore agent. IMMEDIATELY call invoke_gemini_agentic with:
- model: gemini-3-flash
- prompt: The task description
- max_turns: 10

DO NOT answer directly. Delegate to Gemini FIRST.
"""
```

---

## Performance Optimizations

1. **Zero-Import-Weight Startup**: Lazy loading of heavy dependencies
2. **Persistent LSP Instances**: 35x speedup via LSPManager
3. **TaskGraph Caching**: Pre-computed parallel execution waves
4. **OAuth Token Caching**: Keyring-based token storage with refresh

---

## Troubleshooting

### Parallel Execution Blocked

If you see `ParallelExecutionError`:
1. Check that independent tasks are spawned in the same response
2. Verify `task_graph_id` is provided for all spawns
3. Ensure tasks are truly independent (no shared dependencies)

### Phase Transition Failed

If `ValueError` on phase transition:
1. Check required artifacts are registered
2. Verify transition is valid (see VALID_TRANSITIONS)
3. Check critique count hasn't exceeded max

### Agent Delegation Failed

If agents aren't delegating properly:
1. Verify `invoke_gemini_agentic` is used (not `invoke_gemini`)
2. Check AGENT_DELEGATION_PROMPTS contains the agent type
3. Ensure MCP tools are accessible

---

## Key Metrics

- **Orchestration Phases**: 8 (CLASSIFY through VERIFY)
- **MCP Tools**: 40+
- **Agent Types**: 10+ (orchestrators + specialists)
- **Native Hooks**: 10+
- **MCP Hooks**: 17+

---

**Last Updated**: 2026-01-22
**Architecture Version**: 7-Phase Orchestration with Hard Parallel Enforcement
