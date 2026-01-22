# Stravinsky Architecture Map - Baseline Inventory

**Current Version**: 0.5.x
**Python Constraint**: >=3.11,<3.14 (due to chromadb/onnxruntime)
**Document Date**: 2026-01-22

---

## Executive Summary

Stravinsky is a sophisticated MCP bridge for Claude Code with:
- **7-Phase Orchestration**: CLASSIFY -> CONTEXT -> WISDOM -> PLAN -> VALIDATE -> DELEGATE -> EXECUTE -> VERIFY
- **Hard Parallel Enforcement**: TaskGraph and DelegationEnforcer ensure independent tasks run simultaneously
- **40+ MCP tools** for model invocation, code search, LSP refactoring, semantic search, and agent management
- **10+ native specialist agents** with role-based delegation and injected delegation prompts
- **30+ hook implementations** for automatic delegation and context management

This document establishes the **baseline architecture** with focus on the new orchestration system.

---

## Part 1: 7-Phase Orchestration System

### Phase State Machine

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     7-PHASE ORCHESTRATION WORKFLOW                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [1] CLASSIFY ──> [2] CONTEXT ──> [3] WISDOM ──> [4] PLAN               │
│        │               │                              │                  │
│        │               └──── (optional) ─────────────>│                  │
│        │                                              │                  │
│        │                                   ┌──────────┘                  │
│        │                                   │                             │
│        │                                   v                             │
│        │                             [4] PLAN <────┐                     │
│        │                                   │       │ (critique loop,    │
│        │                                   │       │  max 3 iterations) │
│        │                                   v       │                     │
│        │                            [5] VALIDATE ──┘                     │
│        │                                   │                             │
│        │                                   v                             │
│        │                            [6] DELEGATE                         │
│        │                                   │                             │
│        │                                   │ (build TaskGraph)           │
│        │                                   v                             │
│        │                             [7] EXECUTE <────┐                  │
│        │                                   │          │ (retry loop)     │
│        │                                   v          │                  │
│        │                             [8] VERIFY ──────┘                  │
│        │                                   │                             │
│        └───────────────────────────────────┘ (start new cycle)           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Phase Requirements

| Phase | Required Artifacts | Produces |
|-------|-------------------|----------|
| CLASSIFY | None | `query_classification` |
| CONTEXT | `query_classification` | `context_summary` |
| WISDOM | `context_summary` | Wisdom injected into context |
| PLAN | None | `plan.md` |
| VALIDATE | `plan.md` | `validation_result` |
| DELEGATE | `validation_result` | `delegation_targets`, `task_graph` |
| EXECUTE | `delegation_targets`, `task_graph` | `execution_result` |
| VERIFY | `execution_result` | Final synthesis |

### Implementation Files

| File | Purpose |
|------|---------|
| `mcp_bridge/orchestrator/enums.py` | OrchestrationPhase enum |
| `mcp_bridge/orchestrator/state.py` | OrchestratorState machine, PHASE_REQUIREMENTS, VALID_TRANSITIONS |
| `mcp_bridge/orchestrator/task_graph.py` | TaskGraph, Task, TaskStatus, DelegationEnforcer |
| `mcp_bridge/orchestrator/router.py` | Router with multi-provider fallback |
| `mcp_bridge/orchestrator/wisdom.py` | WisdomLoader, CritiqueGenerator |
| `mcp_bridge/orchestrator/visualization.py` | Phase progress formatting |

---

## Part 2: TaskGraph and Parallel Enforcement

### TaskGraph Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TASKGRAPH STRUCTURE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TaskGraph                                                               │
│  ├── tasks: dict[str, Task]                                             │
│  │   ├── "search_auth" -> Task(id, description, agent_type, deps=[])    │
│  │   ├── "research_patterns" -> Task(id, description, agent_type, deps=[])
│  │   └── "implement_feature" -> Task(id, description, agent_type,       │
│  │                                   deps=["search_auth", "research..."])│
│  │                                                                       │
│  ├── add_task(task_id, description, agent_type, dependencies)           │
│  ├── get_ready_tasks() -> list[Task]  # Tasks with deps complete        │
│  ├── get_independent_groups() -> list[list[Task]]  # Execution waves    │
│  ├── mark_spawned(task_id, agent_task_id)                               │
│  ├── mark_completed(task_id)                                            │
│  └── mark_failed(task_id)                                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Execution Waves

```
PARALLEL EXECUTION WAVES
═══════════════════════════════════════════════════════════════════════════

Example TaskGraph:
  search_auth:        deps=[]        ─┐
  research_patterns:  deps=[]        ─┼─> Wave 1 (parallel)
  review_security:    deps=[]        ─┘
  implement_feature:  deps=[search_auth, research_patterns] ─> Wave 2
  write_tests:        deps=[implement_feature] ─> Wave 3

Execution:
  Wave 1: [search_auth, research_patterns, review_security]
          All spawned within 500ms window (parallel enforcement)

  Wave 2: [implement_feature]
          Only starts after Wave 1 completes

  Wave 3: [write_tests]
          Only starts after Wave 2 completes
```

### DelegationEnforcer

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DELEGATIONENFORCER                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DelegationEnforcer                                                      │
│  ├── task_graph: TaskGraph                                              │
│  ├── parallel_window_ms: float = 500  # Max time between spawns         │
│  ├── strict: bool = True  # Raise errors on violations                  │
│  │                                                                       │
│  ├── validate_spawn(task_id) -> (bool, str | None)                      │
│  │   # Returns (is_valid, error_message)                                │
│  │   # Checks if task is in current wave                                │
│  │   # Blocks tasks with unmet dependencies                             │
│  │                                                                       │
│  ├── record_spawn(task_id, agent_task_id)                               │
│  │   # Records spawn time for parallel checking                         │
│  │                                                                       │
│  ├── check_parallel_compliance() -> (bool, str | None)                  │
│  │   # Verifies all wave tasks spawned within window                    │
│  │   # Raises ParallelExecutionError if > 500ms spread                  │
│  │                                                                       │
│  ├── advance_wave() -> bool                                             │
│  │   # Move to next wave after current completes                        │
│  │   # Returns False if all waves done                                  │
│  │                                                                       │
│  └── get_enforcement_status() -> dict                                   │
│      # Debug info: current_wave, task_statuses, spawn_batch            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Task Status Flow

```
TASK STATUS LIFECYCLE
═══════════════════════════════════════════════════════════════════════════

  PENDING ──spawn──> SPAWNED ──start──> RUNNING ──finish──> COMPLETED
     │                                      │                    │
     │                                      └──error──> FAILED   │
     │                                                           │
     └───────────────────────────────────────────────────────────┘
                           (next wave starts)
```

---

## Part 3: Agent Delegation System

### Agent Delegation Prompts

Stravinsky injects delegation prompts at spawn time to ensure proper model routing.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AGENT DELEGATION PROMPTS                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Location: mcp_bridge/tools/agent_manager.py                            │
│                                                                          │
│  AGENT_DELEGATION_PROMPTS = {                                           │
│      "explore": """                                                      │
│          ## CRITICAL: DELEGATE TO GEMINI IMMEDIATELY                    │
│          IMMEDIATELY call mcp__stravinsky__invoke_gemini_agentic with:  │
│          - model: gemini-3-flash                                        │
│          - max_turns: 10                                                │
│          Use invoke_gemini_agentic NOT invoke_gemini for tool access.   │
│      """,                                                                │
│                                                                          │
│      "delphi": """                                                       │
│          ## CRITICAL: DELEGATE TO OPENAI/GPT IMMEDIATELY                │
│          IMMEDIATELY call mcp__stravinsky__invoke_openai with:          │
│          - model: gpt-5.2-codex                                         │
│          - reasoning_effort: high                                       │
│      """,                                                                │
│                                                                          │
│      # ... other agents                                                  │
│  }                                                                       │
│                                                                          │
│  get_agent_delegation_prompt(agent_type) -> str                         │
│  # Returns prompt for agent, falls back to DEFAULT_DELEGATION_PROMPT   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Agent Manifest

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AGENT MANIFEST                                   │
├─────────────────────────────────────────────────────────────────────────┤
│ User Request                                                             │
└────────────────┬────────────────────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ STRAVINSKY ORCHESTRATOR                                                  │
│ ├─ Model: Claude Sonnet 4.5 / Opus                                      │
│ ├─ Role: 7-phase workflow execution, parallel enforcement               │
│ └─ Builds TaskGraph, enforces delegation                                │
└────────────────┬────────────────────────────────────────────────────────┘
                 │
      ┌──────────┼──────────┬──────────┬──────────┬──────────┬──────────┐
      ↓          ↓          ↓          ↓          ↓          ↓          ↓
   EXPLORE    DEWEY    CODE-REV    DEBUGGER  FRONTEND   DELPHI    MOMUS
   ────────   ─────    ────────    ────────  ────────   ──────    ─────
   Gemini     Gemini   Gemini      Sonnet    Gemini     GPT-5.2   Gemini
   Flash      Flash    Flash       4.5       Pro High   Codex     Flash
   CHEAP      CHEAP    CHEAP       MEDIUM    MEDIUM     EXPENSIVE CHEAP
   Async      Async    Async       Blocking  Blocking   Blocking  Async

   Code       Docs     Quality     Debug     UI/UX      Strategy  Quality
   Search     Research Review      Analysis  Design     Advice    Gate
```

### Agent Specifications

| Agent | Model | Cost Tier | Execution | Delegation Target |
|-------|-------|-----------|-----------|-------------------|
| **stravinsky** | Sonnet/Opus | Expensive | Primary | N/A (orchestrator) |
| **research-lead** | Gemini Flash | Cheap | Coordinator | invoke_gemini |
| **implementation-lead** | Sonnet | Medium | Coordinator | Direct |
| **explore** | Gemini Flash | Cheap | Async | invoke_gemini_agentic |
| **dewey** | Gemini Flash | Cheap | Async | invoke_gemini_agentic |
| **code-reviewer** | Gemini Flash | Cheap | Async | invoke_gemini_agentic |
| **debugger** | Sonnet | Medium | Blocking | Direct |
| **frontend** | Gemini Pro High | Medium | Blocking | invoke_gemini_agentic |
| **delphi** | GPT-5.2 | Expensive | Blocking | invoke_openai |
| **momus** | Gemini Flash | Cheap | Async | invoke_gemini_agentic |

### Agent Hierarchy

```
AGENT HIERARCHY ENFORCEMENT
═══════════════════════════════════════════════════════════════════════════

ORCHESTRATOR_AGENTS = ["stravinsky", "research-lead", "implementation-lead"]
WORKER_AGENTS = ["explore", "dewey", "delphi", "frontend", "debugger", ...]

ALLOWED SPAWNS:
  Orchestrator -> Orchestrator  ✓
  Orchestrator -> Worker        ✓
  Worker       -> Orchestrator  ✗ (raises ValueError)
  Worker       -> Worker        ✗ (raises ValueError)
```

---

## Part 4: Tool Inventory (40+ Tools)

### Category 1: Model Invocation (3 tools)

| Tool | Purpose | Input | Use Case |
|------|---------|-------|----------|
| `invoke_gemini` | Invoke Gemini models | prompt, model, temperature | Simple completions |
| `invoke_gemini_agentic` | Gemini with tool access | prompt, model, max_turns | Multi-step with tools |
| `invoke_openai` | Invoke OpenAI/GPT models | prompt, model, reasoning_effort | Complex reasoning |

### Category 2: Agent Management (6 tools)

| Tool | Purpose | Execution | Returns |
|------|---------|-----------|---------|
| `agent_spawn` | Launch agent with parallel enforcement | Async | task_id |
| `agent_output` | Get agent results | Blocking or polling | Agent output |
| `agent_progress` | Real-time progress | Non-blocking | Recent lines |
| `agent_cancel` | Stop agent | Immediate | Status |
| `agent_list` | List all agents | Non-blocking | Agent list |
| `agent_retry` | Retry failed agent | Async | task_id |

### Category 3: Code Search (4 tools)

| Tool | Pattern Type | Strength | Use Case |
|------|-------------|----------|----------|
| `grep_search` | Exact text regex | Fast | Keywords, imports |
| `ast_grep_search` | AST patterns | Structure-aware | Classes, decorators |
| `glob_files` | Filesystem | Fast | File discovery |
| `semantic_search` | Embeddings | Conceptual | "Find auth logic" |

### Category 4: LSP Tools (12 tools)

| Tool | Operation | Returns |
|------|-----------|---------|
| `lsp_hover` | Type info at position | Type, docs |
| `lsp_goto_definition` | Jump to definition | File path, line |
| `lsp_find_references` | All usages | Paths, lines |
| `lsp_document_symbols` | File outline | All symbols |
| `lsp_workspace_symbols` | Search symbols | Matching symbols |
| `lsp_prepare_rename` | Validate rename | Validation result |
| `lsp_rename` | Rename symbol | Preview or apply |
| `lsp_code_actions` | Quick fixes | Actions list |
| `lsp_code_action_resolve` | Apply action | Applied fix |
| `lsp_extract_refactor` | Extract code | New function |
| `lsp_diagnostics` | Errors/warnings | Diagnostic list |
| `lsp_servers` | List servers | Server status |

### Category 5: Semantic Search (5+ tools)

| Tool | Purpose | Input |
|------|---------|-------|
| `semantic_search` | Natural language search | query, n_results |
| `hybrid_search` | Pattern + semantic | query, pattern |
| `semantic_index` | Build embeddings | project_path, provider |
| `semantic_stats` | Index statistics | project_path |
| `start_file_watcher` | Auto-reindex | project_path, debounce |
| `stop_file_watcher` | Stop watching | project_path |

---

## Part 5: File Organization

```
mcp_bridge/
├── orchestrator/                    # 7-PHASE ORCHESTRATION (NEW)
│   ├── __init__.py
│   ├── enums.py                     # OrchestrationPhase enum
│   ├── state.py                     # OrchestratorState, PHASE_REQUIREMENTS
│   ├── task_graph.py                # TaskGraph, DelegationEnforcer
│   ├── router.py                    # Multi-provider model router
│   ├── wisdom.py                    # WisdomLoader, CritiqueGenerator
│   └── visualization.py             # Phase progress formatting
│
├── tools/
│   ├── agent_manager.py             # AGENT_DELEGATION_PROMPTS, agent_spawn
│   ├── model_invoke.py              # invoke_gemini, invoke_openai
│   ├── code_search.py               # grep, ast_grep, glob
│   ├── semantic_search.py           # Vector search, file watcher
│   ├── project_context.py           # get_project_context
│   ├── session_manager.py           # Session tools
│   ├── skill_loader.py              # Slash commands
│   └── lsp/
│       ├── manager.py               # LSPManager
│       └── tools.py                 # 12 LSP tools
│
├── routing/                         # Model routing
│   ├── config.py                    # Routing configuration
│   ├── provider_state.py            # Provider availability
│   ├── model_tiers.py               # OAuth fallback chains
│   └── task_classifier.py           # Task type classification
│
├── hooks/                           # 30+ hook implementations
├── auth/                            # OAuth (Google, OpenAI)
├── prompts/                         # Agent system prompts
├── server.py                        # MCP entry point
└── server_tools.py                  # Tool definitions
```

---

## Part 6: Configuration Files

### Key Locations

| File | Purpose |
|------|---------|
| `pyproject.toml` | Version, Python constraints (>=3.11,<3.14) |
| `mcp_bridge/__init__.py` | `__version__` |
| `.claude/agents/*.md` | Native subagent definitions |
| `.claude/commands/*.md` | Slash commands |
| `.claude/hooks/*.py` | Native hook implementations |
| `.claude/settings.json` | Hook registration |
| `.stravinsky/wisdom.md` | Project learnings (injected in WISDOM phase) |

---

## Part 7: Architecture Completeness Score

| Component | Coverage | Status |
|-----------|----------|--------|
| **7-Phase Orchestration** | 8 phases | Complete |
| **TaskGraph** | DAG + waves | Complete |
| **DelegationEnforcer** | Parallel validation | Complete |
| **Agent Delegation Prompts** | 10+ agents | Complete |
| **MCP Tools** | 40+ | Complete |
| **Native Agents** | 10+ | Complete |
| **LSP Integration** | 12 tools | Complete |
| **Semantic Search** | 5+ tools | Complete |
| **Hook System** | 30+ hooks | Complete |

**Overall**: **95% Complete** - Full 7-phase orchestration with hard parallel enforcement.

---

## Part 8: Quick Reference Tables

### Phase Transition Cheat Sheet

| From | To | Condition |
|------|----|----|
| CLASSIFY | CONTEXT | Always |
| CONTEXT | WISDOM | If wisdom exists |
| CONTEXT | PLAN | Skip wisdom if not exists |
| WISDOM | PLAN | Always |
| PLAN | VALIDATE | Plan created |
| PLAN | PLAN | Critique needed (max 3) |
| VALIDATE | DELEGATE | Plan passes validation |
| VALIDATE | PLAN | Plan fails validation |
| DELEGATE | EXECUTE | TaskGraph built |
| EXECUTE | VERIFY | All tasks complete |
| EXECUTE | EXECUTE | Retry needed |
| VERIFY | CLASSIFY | New task cycle |

### Agent Selection Cheat Sheet

| Need | Agent | Cost |
|------|-------|------|
| Code search | explore | Cheap |
| Documentation research | dewey | Cheap |
| Code quality review | code-reviewer | Cheap |
| Debugging (after 2+ failures) | debugger | Medium |
| UI/UX implementation | frontend | Medium |
| Architecture decisions | delphi | Expensive |
| Quality gate validation | momus | Cheap |

### Tool Selection Cheat Sheet

| Need | Tool | Speed |
|------|------|-------|
| Find function by name | lsp_workspace_symbols | Fast |
| Find all callers | lsp_find_references | Fast |
| Find imports | grep_search | Very Fast |
| Find class inheritance | ast_grep_search | Fast |
| Find "auth logic" | semantic_search | Medium |
| Type signature | lsp_hover | Fast |
| Jump to definition | lsp_goto_definition | Fast |

---

**Last Updated**: 2026-01-22
**Architecture Version**: 7-Phase Orchestration with TaskGraph and DelegationEnforcer
