# Stravinsky Architecture Map - Baseline Inventory

**Current Version**: 0.4.16
**Python Constraint**: >=3.11,<3.14 (due to chromadb/onnxruntime)
**Document Date**: 2025-01-09

---

## Executive Summary

Stravinsky is a sophisticated MCP bridge for Claude Code with:
- **40+ MCP tools** for model invocation, code search, LSP refactoring, semantic search, and agent management
- **8 native specialist agents** (orchestrator + 7 specialists) with role-based delegation
- **30+ hook implementations** for automatic delegation and context management
- **14 slash commands** for common workflows

This document establishes the **baseline architecture** for gap analysis.

---

## Part 1: Tool Inventory (40+ Tools)

### Category 1: Model Invocation (3 tools)

| Tool | Purpose | Input | Use Case |
|------|---------|-------|----------|
| `invoke_gemini` | Invoke Gemini models | prompt, model, temperature, max_tokens | UI generation, analysis, creative tasks |
| `invoke_openai` | Invoke OpenAI/GPT models | prompt, model, temperature, thinking_budget | Complex reasoning, strategic advice |
| `stravinsky_version` | Get MCP version & diagnostics | None | Health checks, debugging |

**File**: `mcp_bridge/tools/model_invoke.py`

---

### Category 2: Code Search (4 tools)

| Tool | Pattern Type | Strength | Use Case |
|------|-------------|----------|----------|
| `grep_search` | Exact text regex | Fast for keywords | Find specific strings, imports, function names |
| `ast_grep_search` | AST structural patterns | Ignores formatting | Find code structure (classes, decorators, nesting) |
| `glob_files` | Filesystem patterns | Fast directory scan | List files by extension, directory traversal |
| `semantic_search` | Natural language embeddings | Conceptual matching | "Find auth logic", "error handling patterns" |

**Query Routing**:
- Exact syntax (function name, class name) → `grep_search` or `lsp_workspace_symbols`
- Code structure (inheritance, AST patterns) → `ast_grep_search`
- Behavioral/conceptual ("how", "where is logic") → `semantic_search`
- Hybrid (pattern + conceptual) → `hybrid_search`

**File**: `mcp_bridge/tools/code_search.py`

---

### Category 3: LSP Tools (12 tools) - Language Server Protocol

| Tool | Operation | Use Case | Returns |
|------|-----------|----------|---------|
| `lsp_hover` | Type info at position | Get function signature, docs | Type, docs, signature |
| `lsp_goto_definition` | Jump to symbol definition | Find where symbol is defined | File path, line number |
| `lsp_find_references` | All symbol usages | Find all callers/users | File paths, line numbers |
| `lsp_document_symbols` | File outline | Browse module structure | All symbols (functions, classes, methods) |
| `lsp_workspace_symbols` | Search symbols by name | Find class/function across workspace | Matching symbols with paths |
| `lsp_prepare_rename` | Validate rename | Check if symbol can be renamed | Validation result |
| `lsp_rename` | Rename symbol globally | Rename across workspace (dry-run safe) | Preview or apply changes |
| `lsp_code_actions` | Quick fixes at position | Available refactorings | List of code actions (fixes, refactorings) |
| `lsp_code_action_resolve` | Apply specific action | Fix unused imports, format code | Applied fix |
| `lsp_extract_refactor` | Extract to function/variable | Refactor code blocks | New function/variable created |
| `lsp_diagnostics` | Syntax/semantic errors | Find errors in file | Errors and warnings with positions |
| `lsp_servers` | List LSP servers | Check available language servers | Installed servers and status |

**Performance**: 35x speedup via persistent LSP instances (LSPManager)

**File**: `mcp_bridge/tools/lsp/tools.py`, `mcp_bridge/tools/lsp/manager.py`

---

### Category 4: Semantic Search (5+ tools)

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `semantic_search` | Natural language code search | query, n_results, language, node_type | Ranked results with scores |
| `hybrid_search` | Pattern + semantic | query, pattern, n_results | Combined results |
| `semantic_index` | Build embeddings | project_path, provider, force | Indexed codebase |
| `semantic_stats` | Index statistics | project_path, provider | File count, chunk count, index size |
| `cancel_indexing` | Stop indexing | project_path, provider | Cancellation status |
| `delete_index` | Remove index | project_path, provider, delete_all | Cleanup status |
| `start_file_watcher` | Auto-reindex on file change | project_path, provider, debounce_seconds | Watcher PID |
| `stop_file_watcher` | Stop auto-reindex | project_path | Watcher status |

**Providers**: ollama (local), gemini (cloud), openai (cloud), huggingface (cloud)

**File**: `mcp_bridge/tools/semantic_search.py`

---

### Category 5: Agent Management (6 tools)

| Tool | Purpose | Execution | Returns |
|------|---------|-----------|---------|
| `agent_spawn` | Launch background agent | Async (non-blocking) | task_id immediately |
| `agent_output` | Get agent results | Blocking (wait_for=True) or polling | Agent output |
| `agent_progress` | Real-time agent progress | Non-blocking peek | Recent output lines |
| `agent_cancel` | Stop running agent | Immediate | Cancellation status |
| `agent_list` | List all agents | Non-blocking query | All active agents + status |
| `agent_retry` | Retry failed agent | Async | task_id for new attempt |

**Agent Types** (via `agent_spawn`):
- `explore` - Code search specialist (Gemini Flash, free)
- `dewey` - Documentation research (Gemini Flash, cheap)
- `frontend` - UI/UX specialist (Gemini 3 Pro High, medium cost)
- `delphi` - Strategic advisor (GPT-5.2, expensive)
- `code-reviewer` - Quality analysis (Gemini Flash, cheap)
- `debugger` - Root cause (Claude Sonnet, medium)
- `document_writer` - Doc generation (Gemini Flash)
- `multimodal` - Visual analysis (Gemini Flash)

**File**: `mcp_bridge/tools/agent_manager.py`

---

### Category 6: Task Management (3 tools)

| Tool | Purpose | Use Case | Execution |
|------|---------|----------|-----------|
| `task_spawn` | Background task execution | Deep research, long-running | Async, returns task_id |
| `task_status` | Check task progress | Poll task status | Non-blocking |
| `task_list` | List all tasks | See all background work | Non-blocking query |

**File**: `mcp_bridge/tools/background_tasks.py`

---

### Category 7: Session & Context (5 tools)

| Tool | Purpose | Use Case |
|------|---------|----------|
| `session_list` | List Claude Code sessions | Find specific projects, auditing |
| `session_read` | Read session messages | Analyze conversation history |
| `session_search` | Search across sessions | Find related discussions |
| `get_project_context` | Git status + rules + todos | Refresh baseline context |
| `get_system_health` | Check dependencies & auth | Verify setup (rg, fd, sg, OAuth tokens) |

**File**: `mcp_bridge/tools/session_manager.py`, `mcp_bridge/tools/project_context.py`

---

### Category 8: Skills/Commands (2 tools)

| Tool | Purpose | Use Case |
|------|---------|----------|
| `skill_list` | List available slash commands | Discover available skills |
| `skill_get` | Get skill content | Read skill implementation |

**File**: `mcp_bridge/tools/skill_loader.py`

---

### Category 9: Advanced Search (1 tool)

| Tool | Purpose | Enhancement |
|------|---------|-------------|
| `ast_grep_replace` | AST-aware code replacement | More reliable than text-based replace |

---

## Part 2: Native Agent Architecture

### Agent Manifest

```
┌─────────────────────────────────────────────────────────┐
│ User Request                                            │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│ Claude Code (Main)                                      │
│ - Auto-delegates to Stravinsky orchestrator             │
│ - Based on description/trigger matching                 │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│ STRAVINSKY (Orchestrator)  [.claude/agents/stravinsky.md]
│ - Model: Claude Sonnet 4.5 (32k thinking)               │
│ - Cost: Moderate                                        │
│ - Execution: Primary (never blocks, delegates only)     │
│ - Role: Task planning, delegation, parallel execution   │
└────────────────┬────────────────────────────────────────┘
                 │
      ┌──────────┼──────────────────────────────────────┐
      ↓          ↓          ↓         ↓        ↓         ↓
   ┌──────┐ ┌──────┐ ┌──────────┐ ┌────┐ ┌─────────┐ ┌──────┐
   │EXPLORE│ │DEWEY │ │CODE-     │ │DEBUG│ │FRONTEND │ │DELPHI│
   │       │ │      │ │REVIEWER  │ │GER  │ │         │ │      │
   └──────┘ └──────┘ └──────────┘ └────┘ └─────────┘ └──────┘
   Free    Cheap    Cheap        Medium   Medium     Expensive
   Async   Async    Async        Blocking Blocking   Blocking
```

### Agent Specifications

| Agent | File | Model | Cost | Execution | When to Delegate |
|-------|------|-------|------|-----------|------------------|
| **stravinsky** | stravinsky.md | Sonnet 4.5 | Moderate | Primary | Auto (orchestrator) |
| **explore** | explore.md | Gemini Flash | Free | Async | Code search, "where is X?" |
| **dewey** | dewey.md | Gemini Flash + WebSearch | Cheap | Async | Doc research, examples |
| **code-reviewer** | code-reviewer.md | Gemini Flash | Cheap | Async | Code review, security |
| **debugger** | debugger.md | Claude Sonnet | Medium | Blocking | After 2+ failures |
| **frontend** | frontend.md | Gemini 3 Pro High | Medium | Blocking | ALL visual changes |
| **delphi** | delphi.md | GPT-5.2 | Expensive | Blocking | After 3+ failures, architecture |
| **research-lead** | research-lead.md | Gemini Flash | Cheap | Coordinator | Research workflows |
| **implementation-lead** | implementation-lead.md | Claude Sonnet | Medium | Coordinator | Implementation workflows |

**Location**: `/Users/davidandrews/PycharmProjects/stravinsky/.claude/agents/`

---

### Agent Features (Stravinsky Orchestrator Capabilities)

#### 1. Parallel Execution Pattern
```
TodoWrite([task1, task2, task3])  # Create all todos
  ↓ (SAME RESPONSE)
Task(subagent_type="explore", prompt="...", description="task1")
Task(subagent_type="dewey", prompt="...", description="task2")
Task(subagent_type="frontend", prompt="...", description="task3")
  ↓ (All execute in parallel)
Synthesize results from Task tool responses
Mark todos complete
```

#### 2. Search Strategy Classification
- **Pattern-Based**: grep_search, ast_grep_search, glob_files
- **Conceptual**: semantic_search, hybrid_search
- **Symbol Navigation**: lsp_* tools
- **Advanced**: agent_spawn for multi-layer analysis

#### 3. Cost Optimization (oh-my-opencode pattern)
- **Always Async**: explore, dewey, code-reviewer (free/cheap)
- **Blocking Only When Necessary**: debugger (2+ failures), frontend (ALL visual), delphi (3+ failures)
- **Never Work Alone**: PreToolUse hooks block Read/Grep/Bash, forcing delegation

---

## Part 3: Hook Architecture

### Hook System Overview

Stravinsky uses native Claude Code hooks to control delegation behavior.

```
User Request
    ↓
UserPromptSubmit Hook
├→ Inject context (CLAUDE.md, README)
├→ Add system rules
└→ Preprocess prompt
    ↓
Claude Code Auto-Delegates
├→ Matches agent description
└→ Launches stravinsky native subagent
    ↓
Stravinsky Processes
├→ TodoWrite (plan)
├→ Classify request type
└→ Prepare delegation strategy
    ↓
PreToolUse Hook (CRITICAL)
├→ Intercepts: Read, Grep, Bash, Glob
├→ Decision: Allow or Block
│   └→ ALLOW: Native tool executes
│   └→ BLOCK: Delegate via Task() to specialist
└→ Exit code 2 = block signal
    ↓
Specialist Agent Executes
├→ explore, dewey, code-reviewer, etc.
└→ Full tool access
    ↓
PostToolUse Hook
├→ Log completion
├→ Aggregate results
├→ Update task graph
└→ Signal synthesis phase
    ↓
Orchestrator Synthesizes
├→ Combine specialist outputs
├→ Update todos
└→ Respond to user
```

### Hook Implementation Status

| Hook Type | Location | Status | Purpose |
|-----------|----------|--------|---------|
| **PreToolUse** | `.claude/agents/hooks/pre_tool_use.sh` | [ ] Planned | Block direct tools, force delegation |
| **PostToolUse** | `.claude/agents/hooks/post_tool_use.sh` | [ ] Planned | Aggregate specialist results |
| **UserPromptSubmit** | `.claude/agents/hooks/user_prompt_submit.sh` | [ ] Planned | Context injection, preprocessing |
| **PreCompact** | `.claude/agents/hooks/pre_compact.sh` | [ ] Planned | Save state before compression |
| **SessionEnd** | `.claude/agents/hooks/session_end.sh` | [ ] Planned | Cleanup, final reporting |

**Configuration File**: `.claude/settings.json` (not yet implemented)

### Available Hook Types in Claude Code

| Hook | When It Fires | Can Block? | Use Case |
|------|---------------|-----------|----------|
| **PreToolUse** | Before any tool executes | ✅ Yes (exit 2) | Control delegation |
| **PostToolUse** | After tool completes | ❌ No | Result aggregation |
| **UserPromptSubmit** | Before prompt sent to LLM | ✅ Yes | Context injection |
| **PreCompact** | Before compression | ❌ No | Save state |
| **SessionEnd** | Session terminates | ❌ No | Cleanup |

**Implemented Python Hooks in mcp_bridge/hooks/**:
- agent_reminder.py - Remind about agent patterns
- auto_slash_command.py - Auto-trigger slash commands
- budget_optimizer.py - Token budget management
- comment_checker.py - Code comment validation
- compaction.py - Context compaction
- context.py - Context management
- context_monitor.py - Monitor context usage
- directory_context.py - Directory-based context
- edit_recovery.py - Undo/recovery
- empty_message_sanitizer.py - Clean empty messages
- git_noninteractive.py - Non-interactive git
- keyword_detector.py - Keyword detection
- manager.py - Hook manager
- notification_hook.py - User notifications
- parallel_enforcer.py - Enforce parallel execution
- parallel_execution.py - Parallel task coordination
- pre_compact.py - Pre-compaction logic
- preemptive_compaction.py - Proactive compression
- rules_injector.py - Inject project rules
- session_idle.py - Monitor idle sessions
- session_notifier.py - Session notifications
- session_recovery.py - Session recovery
- stravinsky_mode.py - Orchestrator mode control
- subagent_stop.py - Stop subagents
- task_validator.py - Validate tasks
- tmux_manager.py - Terminal management
- todo_continuation.py - Continue unfinished todos
- todo_delegation.py - Delegate todos
- todo_enforcer.py - Enforce todo patterns
- tool_messaging.py - Tool communication
- truncator.py - Truncate output

---

## Part 4: Slash Commands (Skills)

### Available Commands

| Command | File | Purpose |
|---------|------|---------|
| `/strav` | strav.md | Task Orchestrator & Planner |
| `/delphi` | delphi.md | Architecture & Debug Advisor |
| `/dewey` | dewey.md | Documentation & Research |
| `/review` | review.md | Code Review |
| `/verify` | verify.md | Post-Implementation Verification |
| `/version` | version.md | Check Stravinsky version |
| `/publish` | publish.md | PyPI deployment workflow |
| `/str:watch` | str/watch.md | Start semantic search file watching |
| `/str:unwatch` | str/unwatch.md | Stop file watching |
| `/str:cancel` | str/cancel.md | Cancel ongoing indexing |
| `/str:clean` | str/clean.md | Delete semantic search indexes |
| `/index` | index.md | Index project for semantic search |

**Location**: `/Users/davidandrews/PycharmProjects/stravinsky/.claude/commands/`

---

## Part 5: Delegation Patterns

### Pattern 1: Simple Parallel Delegation

```yaml
Request Type: Multi-step exploration
Trigger: "Find X AND research Y AND review code for Z"

Stravinsky Flow:
  1. TodoWrite([Find X, Research Y, Review code])
  2. SAME RESPONSE:
     - Task(subagent_type="explore", prompt="Find X")
     - Task(subagent_type="dewey", prompt="Research Y")
     - Task(subagent_type="code-reviewer", prompt="Review code")
  3. All execute in parallel → results returned immediately
  4. Synthesize results in single response
  5. Mark todos complete
```

### Pattern 2: Conditional Blocking Delegation

```yaml
Request Type: Debugging
Trigger: "Error occurred, fix attempt #1 failed"

Stravinsky Flow:
  1. Analyze error (orchestrator native tools allowed)
  2. Attempt first fix (orchestrator)
  3. If fails:
     - Attempt second fix (orchestrator)
     - If fails again:
       - PreToolUse hook detects second failure
       - BLOCK further native tool use
       - Task(subagent_type="debugger", blocking=true, prompt="Root cause analysis")
       - Wait for debugger (blocking)
       - Implement debugger recommendation
```

### Pattern 3: Visual-Only Delegation

```yaml
Request Type: UI implementation
Trigger: "Add dark mode toggle"

Stravinsky Flow:
  1. Plan UI structure (orchestrator)
  2. PreToolUse hook ALWAYS intercepts visual changes
  3. Task(subagent_type="frontend", blocking=true, prompt="Implement dark mode UI")
  4. Frontend uses invoke_gemini(model="gemini-3-pro-high") for UI generation
  5. Orchestrator integrates backend logic
```

### Pattern 4: Architecture Consultation

```yaml
Request Type: Complex architecture decision
Trigger: "How should we structure authentication?" + 3 failed attempts

Stravinsky Flow:
  1. Attempt first solution (orchestrator)
  2. If 3+ failures detected:
     - Task(subagent_type="delphi", blocking=true, prompt="Architecture recommendation")
     - Delphi uses invoke_openai(model="gpt-5.2") with extended thinking
     - Implement delphi recommendation
```

---

## Part 6: Cost Classification & Thinking Budget

### Agent Cost Tiers

| Tier | Agents | Execution | Budget | Use Case |
|------|--------|-----------|--------|----------|
| **Free** | explore | Async | $0 | Code search (always delegate) |
| **Cheap** | dewey, code-reviewer, momus | Async | $0.075/1M tokens | Research, reviews (always delegate) |
| **Medium** | debugger, frontend, implementation-lead | Blocking | $0.5-2.00 | Visual work, debugging (after threshold) |
| **Expensive** | delphi, stravinsky, planner | Varies | $4-8.00 | Architecture, orchestration (sparingly) |

### Extended Thinking Budget

| Agent | Model | Thinking Tokens | Use |
|-------|-------|-----------------|-----|
| stravinsky | Claude Sonnet 4.5 | 32,000 | Complex task planning |
| delphi | GPT-5.2 | N/A (reasoning_effort) | Strategic architectural decisions |

---

## Part 7: Search Strategy Decision Tree

```
Query Received:
  │
  ├─ Is it about FILE NAMES/PATHS?
  │  └─ YES → glob_files
  │
  ├─ Does it contain EXACT SYNTAX (class name, decorator, import)?
  │  └─ YES → grep_search (fastest)
  │
  ├─ Is it about CODE STRUCTURE (inheritance, nesting, AST)?
  │  └─ YES → ast_grep_search
  │
  ├─ Is it BEHAVIORAL/CONCEPTUAL ("how", "where is X logic", "patterns")?
  │  └─ YES → semantic_search
  │
  └─ Do you need COMPILER-LEVEL PRECISION (definitions, references)?
     └─ YES → lsp_* tools (goto_definition, find_references)
     └─ NO → fallback to grep_search
```

---

## Part 8: Tool File Organization

```
mcp_bridge/
├── tools/
│   ├── __init__.py
│   ├── agent_manager.py          # agent_spawn, agent_output, etc.
│   ├── background_tasks.py        # task_spawn, task_status, task_list
│   ├── code_search.py            # grep_search, ast_grep_search, glob_files
│   ├── model_invoke.py           # invoke_gemini, invoke_openai
│   ├── project_context.py        # get_project_context
│   ├── query_classifier.py       # Query type classification for routing
│   ├── semantic_search.py        # semantic_search, semantic_index, etc.
│   ├── session_manager.py        # session_list, session_read, session_search
│   ├── skill_loader.py           # skill_list, skill_get
│   ├── task_runner.py            # Background task execution
│   ├── lsp/
│   │   ├── __init__.py
│   │   ├── manager.py            # LSPManager (persistent servers)
│   │   └── tools.py              # All 12 lsp_* tools
│   └── templates.py              # Tool templates
│
├── hooks/                        # 30+ hook implementations
│   ├── manager.py
│   ├── agent_reminder.py
│   ├── parallel_enforcer.py
│   ├── preemptive_compaction.py
│   └── [26 more hooks...]
│
├── prompts/                      # System prompts for agents
│   ├── stravinsky.py
│   ├── explore.py
│   ├── dewey.py
│   ├── delphi.py
│   ├── frontend.py
│   ├── code_reviewer.py
│   ├── debugger.py
│   └── document_writer.py
│
├── auth/                         # OAuth authentication
│   ├── oauth.py                  # Google OAuth (Gemini)
│   ├── openai_oauth.py           # OpenAI OAuth (ChatGPT)
│   ├── token_store.py            # Keyring + file-based storage
│   ├── token_refresh.py          # Auto token refresh
│   └── cli.py                    # stravinsky-auth command
│
├── config/
│   └── hooks.py                  # Hook configuration
│
├── server.py                     # Main MCP server entry point
├── server_tools.py               # Tool definitions (40+ tools)
├── notifications.py              # User notifications
└── update_manager.py             # Update checking
```

---

## Part 9: Current Gap Analysis

### Implemented ✅

1. **MCP Tools**: All 40+ tools defined and working
2. **Native Agents**: All 8 agent definitions in `.claude/agents/`
3. **Model Invocation**: invoke_gemini, invoke_openai fully functional
4. **Code Search**: grep, AST, semantic, LSP all working
5. **Agent Management**: agent_spawn, agent_output, agent_progress working
6. **Hook Python Infrastructure**: 30+ hook implementations in mcp_bridge/hooks/
7. **Prompts**: System prompts for all agents ready
8. **OAuth**: Google (Gemini) and OpenAI (ChatGPT) authentication complete
9. **Native Claude Code Hooks**: 10+ hooks implemented and registered in `.claude/settings.json`
   - `stravinsky_mode.py`, `context.py`, `todo_delegation.py`, etc.
10. **Delegation Enforcement**: PreToolUse hooks blocking Read/Grep/Bash implemented

### NOT Implemented ❌

1. **Advanced Hook Patterns**:
   - SessionEnd cleanup hooks not fully implemented
   - PreCompact state preservation hooks pending refinement

2. **Research-Lead & Implementation-Lead**:
   - Definitions exist but workflow coordination needs further validation

---

## Part 10: Recommendations

### Phase 1: Hook Activation (COMPLETED)
**Goal**: Enable automatic delegation control via native Claude Code hooks

✅ **Implement PreToolUse Hook** (`stravinsky_mode.py`)
   - Intercept Read, Grep, Bash, Glob calls
   - Blocks complex searches in orchestrator mode

✅ **Implement PostToolUse Hook** (`tool_messaging.py`, `todo_delegation.py`)
   - User-friendly messages
   - Enforced parallel delegation

✅ **Implement UserPromptSubmit Hook** (`context.py`, `parallel_execution.py`)
   - Inject context and rules
   - Detect implementation intent

✅ **Register Hooks in `.claude/settings.json`**
   - Done via `stravinsky-install-hooks`

**Impact**: "Never work alone" pattern is now enforced by default.

---

### Phase 2: Hook Testing & Validation
- Unit test each hook script
- Integration tests: Multi-agent parallel execution
- Measure: delegation accuracy, context isolation, overhead

---

### Phase 3: Advanced Patterns
- SessionEnd hooks for cleanup
- Budget optimizer hooks for cost tracking
- Multi-model routing hooks (invoke_gemini vs invoke_openai selection)

---

### Phase 4: Documentation
- User guide: When to use which agent
- Hook system guide for Claude Code authors
- Cost optimization patterns
- Troubleshooting guide

---

## Part 11: Quick Reference Tables

### Tool Selection Cheat Sheet

| Need | Tool | Speed | Accuracy |
|------|------|-------|----------|
| Find function named X | lsp_workspace_symbols | Fast | Perfect |
| Find all callers of X | lsp_find_references | Fast | Perfect |
| Find import statements | grep_search | Very Fast | Good |
| Find class inheritance | ast_grep_search | Fast | Perfect |
| Find "auth logic" | semantic_search | Medium | Good |
| Find all error handlers | ast_grep_search or semantic_search | Fast | Good |
| File listing | glob_files | Very Fast | Perfect |
| Type signature | lsp_hover | Fast | Perfect |
| Jump to definition | lsp_goto_definition | Fast | Perfect |

### Delegation Decision Matrix

| Situation | Delegate? | To Whom | Execution |
|-----------|-----------|---------|-----------|
| User asks "find X" | ✅ Yes | explore | Async |
| User asks "research X" | ✅ Yes | dewey | Async |
| User asks "review code" | ✅ Yes | code-reviewer | Async |
| User asks "debug error" (1st attempt) | ❌ No | Orchestrator | Native |
| User asks "debug error" (3rd+ attempt) | ✅ Yes | debugger | Blocking |
| User asks "design UI" | ✅ Yes (always) | frontend | Blocking |
| User asks "architecture" (after 3 failures) | ✅ Yes | delphi | Blocking |
| Trivial change (typo, single line) | ❌ No | Orchestrator | Native |
| Multi-component feature | ✅ Yes (parallel) | explore+dewey+frontend | Async+Blocking |

---

## Part 12: File Paths Reference

### Key Configuration Files
- **pyproject.toml**: Version 0.4.16, Python constraints
- **mcp_bridge/__init__.py**: __version__ = "0.4.16"
- **.claude/agents/stravinsky.md**: Orchestrator system prompt
- **.claude/agents/HOOKS.md**: Hook architecture documentation
- **.claude/settings.json**: Hook registration (NOT YET IMPLEMENTED)

### Agent Definitions
- `.claude/agents/stravinsky.md` - Orchestrator
- `.claude/agents/explore.md` - Code search
- `.claude/agents/dewey.md` - Documentation
- `.claude/agents/code-reviewer.md` - Quality analysis
- `.claude/agents/debugger.md` - Debugging
- `.claude/agents/frontend.md` - UI/UX
- `.claude/agents/delphi.md` - Architecture
- `.claude/agents/research-lead.md` - Research coordinator
- `.claude/agents/implementation-lead.md` - Implementation coordinator

### Slash Commands
- `.claude/commands/*.md` - 14 commands

### Hook Implementations
- `mcp_bridge/hooks/` - 30+ Python hook modules

### MCP Tools
- `mcp_bridge/tools/` - 17 Python tool modules
- `mcp_bridge/tools/lsp/` - LSP server management

---

## Summary: Architecture Completeness Score

| Component | Coverage | Status |
|-----------|----------|--------|
| MCP Tools | 40+ defined | ✅ 100% |
| Agents | 8 defined | ✅ 100% (missing hook wiring) |
| Prompts | 8 agents | ✅ 100% |
| Code Search | 4 tools | ✅ 100% |
| LSP Integration | 12 tools | ✅ 100% |
| Semantic Search | 5+ tools | ✅ 100% |
| Agent Management | 6 tools | ✅ 100% |
| Hook Python Layer | 30+ modules | ✅ 100% |
| Hook Integration (Claude Code) | 0/5 hooks | ❌ 0% |
| Parallel Execution | Task() tool | ⚠️ Manual (not enforced) |
| Delegation Enforcement | PreToolUse | ❌ Not implemented |

**Overall**: **80% Complete** - Core tools/agents/prompts ready, needs hook integration layer to enforce delegation patterns automatically.

---

**Last Updated**: 2025-01-09
**For Gap Analysis**: See "Part 10: Recommendations" and "Part 9: Current Gap Analysis"
