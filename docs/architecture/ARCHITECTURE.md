# Stravinsky Architecture Guide

**Version:** v0.5.x (Updated 2026-01-11)
**Purpose:** Comprehensive architectural documentation for developers and contributors

---

## Executive Summary

Stravinsky is a **Model Context Protocol (MCP) bridge** that enables Claude Code to:
- Orchestrate multi-model AI workflows (Gemini, OpenAI, Claude)
- Spawn background agents with full tool access
- Perform semantic code understanding via vector embeddings
- Leverage Language Server Protocol for code refactoring

### Core Design Principles

1. **Zero-Import-Weight Startup**: Sub-second initialization via aggressive lazy loading
2. **OAuth-First with API Fallback**: Automatic degradation to API keys on rate limits
3. **Parallel Agent Execution**: Background agents run as independent Claude CLI processes
4. **Semantic-First Search**: Vector embeddings + AST patterns for code discovery
5. **Defense in Depth**: Multi-layer hook architecture for safety and flexibility

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Tool Categories](#tool-categories)
5. [Authentication Flows](#authentication-flows)
6. [Hook System](#hook-system)
7. [Design Patterns](#design-patterns)
8. [Deployment Architecture](#deployment-architecture)
9. [Performance Optimizations](#performance-optimizations)
10. [Native Subagent Migration](#native-subagent-migration)
11. [Contributing Guidelines](#contributing-guidelines)
12. [Troubleshooting](#troubleshooting)

---

## Quick Reference

| Component | File | Purpose |
|-----------|------|---------|
| **MCP Server** | `mcp_bridge/server.py` | Protocol entry point (zero-import-weight) |
| **Agent Manager** | `tools/agent_manager.py` | Background agent orchestration |
| **Model Routing** | `tools/model_invoke.py` | Multi-model API calls with OAuth fallback |
| **Semantic Search** | `tools/semantic_search.py` | Vector-based code search (ChromaDB) |
| **OAuth** | `auth/google_auth.py`, `auth/openai_auth.py` | Authentication flows |
| **Hook Manager** | `hooks/manager.py` | Tool execution middleware |
| **Native Hooks** | `.claude/hooks/` | PreToolUse/PostToolUse delegation |

---

## Hooks Architecture

### The Hook Split: Native vs MCP

Stravinsky uses a **hybrid hook architecture** with two layers:

**Native Claude Code Hooks** (5 hooks in `.claude/settings.json`):
- `PreToolUse`: stravinsky_mode.py (blocks Read/Grep/Bash in orchestrator mode)
- `UserPromptSubmit`: context.py (prepends CLAUDE.md/README.md/AGENTS.md)
- `PostToolUse`: truncator.py, edit_recovery.py, todo_delegation.py

**MCP Internal Hooks** (17+ hooks in `mcp_bridge/hooks/`):
- 5 tiers: post_tool_call, context management, optimization, behavior, lifecycle
- Examples: model routing, token tracking, session state, auto-save

### Why the Split is Necessary

This is **NOT a design flaw** - it's an intentional architectural pattern called "defense in depth":

#### 1. Process Isolation Boundary

```
Claude Code Process
├── Native Hook (subprocess shell)  ← Intercepts BEFORE MCP call
└── MCP Server Process
    └── MCP Hook (async Python)     ← Intercepts INSIDE MCP tool dispatch
```

- **Native hooks** run as separate subprocesses spawned by Claude Code
- **MCP hooks** run in-process within the Stravinsky MCP server
- These execute at **different lifecycle points** in fundamentally **different processes**

#### 2. Protocol Incompatibility

- Native hooks communicate via **stdin/stdout JSON** with Claude Code
- MCP hooks communicate via **MCP protocol (stdio transport)** between Claude Code and Stravinsky
- Native hooks can't access MCP server internals (tokens, model state)
- MCP hooks can't intercept Claude Code lifecycle events (tool approval, user prompts)

#### 3. Capability Separation

| Capability | Native Hooks | MCP Hooks |
|------------|--------------|-----------|
| Block tool execution | ✅ (hard boundary) | ❌ (tool already dispatched) |
| Inject context to user prompts | ✅ (UserPromptSubmit) | ❌ (no access to prompts) |
| Route model invocations | ❌ (no model access) | ✅ (invoke_gemini/openai) |
| Track token usage | ❌ (no token access) | ✅ (post_model_invoke) |
| Modify tool results | ✅ (PostToolUse) | ✅ (post_tool_call) |
| Session persistence | ❌ (stateless subprocess) | ✅ (session_idle, compact) |

#### 4. Defense in Depth Pattern

From Delphi (GPT-5.2 strategic analysis):

> "This is textbook 'defense in depth' - you want hard security boundaries (native hooks block unsafe tools) enforced OUTSIDE the MCP process, while allowing flexible orchestration (MCP hooks route models) INSIDE. If you move everything to MCP hooks, a bug in your MCP server could bypass all safety checks."

**Validated Pattern**: Used in production systems (Kubernetes admission webhooks, WAF + app-layer validation)

### Current Hook Inventory

#### Native Hooks (10+)

1. **stravinsky_mode.py** (PreToolUse)
   - Blocks Read/Grep/Bash when orchestrator mode active
   - Hard enforcement boundary

2. **context.py** (UserPromptSubmit)
   - Prepends project context (CLAUDE.md, README.md, AGENTS.md)
   - Context injection at prompt boundary

3. **truncator.py** (PostToolUse)
   - Truncates large tool outputs
   - Output size management

4. **edit_recovery.py** (PostToolUse)
   - Recovers from Edit tool failures
   - Error resilience

5. **todo_delegation.py** (PostToolUse)
   - Reminds to use parallel agent spawning after TodoWrite
   - Orchestration guidance

6. **dependency_tracker.py** (UserPromptSubmit)
   - Tracks task dependencies to enable smart parallelization suggestions

7. **execution_state_tracker.py** (UserPromptSubmit)
   - Monitors execution patterns to detect sequential fallback

8. **parallel_reinforcement_v2.py** (UserPromptSubmit)
   - Injects smart reminders when parallel execution degrades

9. **ralph_loop.py** (PostAssistantMessage)
   - Automatically continues work if TODOs are incomplete (RALPH Loop)

10. **notification_hook_v2.py** (Notification)
    - Enhanced agent spawn notifications with colors and formatting

#### MCP Hooks (17+, 5 tiers)

**Tier 1: Post-Tool-Call**
- model_routing (route Gemini vs GPT based on task)
- token_tracking (track usage per model)
- task_persistence (save agent state to `.stravinsky/agents.json`)

**Tier 2: Context Management**
- context_injection (add session history to prompts)
- session_state (maintain conversation state)

**Tier 3: Optimization**
- cache_warming (preload frequently used data)
- rate_limiting (prevent API quota exhaustion)

**Tier 4: Behavior**
- auto_delegation (suggest agent spawning for complex tasks)
- parallel_reminder (enforce parallel execution patterns)

**Tier 5: Lifecycle**
- session_idle (cleanup after inactivity)
- pre_compact (prepare for context compression)

### Recommended Hook Strategy

**Keep the Hybrid Architecture** with these enhancements:

### The Unified Hook Interface (NEW in v0.4.58)

To reduce duplication and enable shared logic, Stravinsky now uses a **Unified Hook Interface** via `mcp_bridge/hooks/events.py`.

#### Canonical Event Model:
- `ToolCallEvent`: A unified data structure for all hook types (Native and MCP).
- `HookPolicy`: An abstract base class for implementing cross-environment policies.
- Adapters: Built-in support for running policies as standalone native scripts (`run_as_native`) or internal MCP callables.

#### Benefits:
- **Shared Logic**: Policies like Truncation and Edit Recovery run the same code in both environments.
- **Improved Testing**: Policies can be unit-tested in isolation without mocking the entire Claude Code lifecycle.

---

### Model Proxy Architecture (NEW in v0.4.58)

To solve the "Head-of-Line Blocking" problem in MCP stdio, Stravinsky implements a local **Model Proxy**.

#### Data Flow (NEW):
```
Claude Code
└── Native Subagent
    └── Calls invoke_gemini (MCP)
        └── Stravinsky Bridge
            └── Proxy Client (httpx)
                └── Model Proxy (FastAPI @ localhost:8765)
                    └── External API (Gemini/GPT)
```

#### Why This Matters:
MCP stdio transport is inherently single-threaded and blocking. By offloading model generation to a separate FastAPI process, the bridge can handle other tool calls (like search or read) immediately, even while multiple models are generating responses in parallel.

---

## Native Subagent Migration

### The Key Insight

**Native subagents use the Task tool to delegate to OTHER native subagents**, with PreToolUse hooks controlling delegation behavior.

This enables the orchestration pattern:

```
Claude Code
└── Native Subagent "stravinsky" (auto-delegated orchestrator)
    ├── PreToolUse Hook: Intercepts Read/Grep/Bash → Blocks and delegates
    ├── Calls: TodoWrite (native Claude tool for planning)
    ├── Calls: Task(subagent_type="explore", prompt="search Y")
    ├── Calls: Task(subagent_type="dewey", prompt="research X")
    ├── Calls: Task(subagent_type="code-reviewer", prompt="review Z")
    └── PostToolUse Hook: Aggregates results from specialist agents
```

**Why This is the CORRECT Architecture**:
- **Native Task tool** for delegation (not agent_spawn CLI spawning)
- **PreToolUse hooks** can block native tools (exit code 2 or {"decision": "block"})
- **Specialists are native subagents** (.claude/agents/explore.md, dewey.md, etc.)
- **Specialists use MCP tools** (invoke_gemini, invoke_openai) for multi-model routing
- **No CLI overhead** - all native delegation via Task tool
- **Hard boundaries** - PreToolUse hooks enforce delegation policy

### Current Slash Command Pattern (To Be Deprecated)

```bash
# User manually invokes:
/stravinsky "implement feature X"

# Claude Code expands to full prompt from slash command
# Then executes inline (no delegation)
```

**Problems**:
- ❌ Manual invocation required (no auto-delegation)
- ❌ Executes in main conversation (context pollution)
- ❌ Can't differentiate orchestrator from execution

### Proposed Native Subagent Pattern

#### Step 1: Create Stravinsky Orchestrator Agent

Create `.claude/agents/stravinsky.md`:

```yaml
---
name: stravinsky
description: |
  Task orchestrator and planner. Use PROACTIVELY for:
  - Complex multi-step tasks (3+ steps)
  - Research + implementation workflows
  - Tasks requiring multiple file changes
  - Parallel exploration of multiple solutions
model: sonnet
---

You are Stravinsky, the task orchestrator and parallel execution specialist.

Core Responsibilities:
1. Task Planning: Use TodoWrite to break down complex tasks
2. Parallel Delegation: Spawn specialized agents concurrently
3. Result Synthesis: Collect and integrate agent outputs
4. Execution Coordination: Ensure all subtasks complete successfully

Available Specialist Agents (use agent_spawn):
- explore: Codebase search, structural analysis
- dewey: Documentation research, library usage examples
- frontend: UI/UX implementation (uses Gemini 3 Pro)
- delphi: Strategic advice, architecture decisions (uses GPT-5.2)

Execution Rules:
- For 2+ independent tasks, spawn ALL agents in a SINGLE response
- Monitor progress with agent_progress(task_id)
- Collect results with agent_output(task_id, block=true)
- Always synthesize findings before presenting to user
```

**Benefits**:
- ✅ Auto-delegation (Claude detects complex tasks automatically)
- ✅ Isolated execution (runs as subagent, not inline)
- ✅ Full parallelism (via agent_spawn MCP tool)
- ✅ Better UX (no manual `/stravinsky` needed)

#### Step 2: Migrate Specialist Agents

Create native subagents for Claude-native specialists:

**`.claude/agents/code-reviewer.md`**:
```yaml
---
name: code-reviewer
description: |
  Code review specialist. Use for:
  - Reviewing pull requests
  - Analyzing code quality
  - Suggesting improvements
model: sonnet
---

You are a code review specialist focused on identifying bugs, security issues, and code quality improvements.
```

**`.claude/agents/debugger.md`**:
```yaml
---
name: debugger
description: |
  Debugging specialist. Use for:
  - Analyzing errors and stack traces
  - Root cause analysis
  - Fixing complex bugs
model: sonnet
---

You are a debugging specialist focused on systematic root cause analysis.
```

**Keep as CLI Spawns** (via agent_spawn):
- delphi (uses GPT-5.2 via invoke_openai)
- frontend (uses Gemini 3 Pro via invoke_gemini)
- dewey (uses Gemini + web search)
- multimodal (uses Gemini vision)

---

## Hybrid Architecture Recommendations

### Final Recommended Structure

```
Stravinsky Architecture (CORRECT - Native Subagents + Hooks)
├── Native Claude Code Hooks (Global - .claude/settings.json)
│   ├── PreToolUse: stravinsky_mode.py (hard enforcement - DEPRECATED)
│   ├── UserPromptSubmit: context.py (context injection)
│   └── PostToolUse: truncator.py, edit_recovery.py, todo_delegation.py
│
├── Native Subagent Hooks (Orchestrator-specific)
│   ├── PreToolUse: Delegation control (blocks Read/Grep → delegates to Task)
│   ├── PostToolUse: Result aggregation from specialist agents
│   └── UserPromptSubmit: Context injection for orchestrator
│
├── MCP Internal Hooks (17+ - mcp_bridge/hooks/)
│   ├── Tier 1: post_tool_call (model routing, token tracking, task persistence)
│   ├── Tier 2: context management (session state, context injection)
│   ├── Tier 3: optimization (cache warming, rate limiting)
│   ├── Tier 4: behavior (auto delegation, parallel reminder)
│   └── Tier 5: lifecycle (session idle, pre compact)
│
├── Native Subagents (.claude/agents/)
│   ├── stravinsky.md (orchestrator - uses Task tool + PreToolUse hooks)
│   ├── explore.md (code search - uses invoke_gemini MCP tool)
│   ├── dewey.md (documentation - uses invoke_gemini + WebSearch)
│   ├── code-reviewer.md (quality analysis - Claude Sonnet)
│   ├── debugger.md (root cause - Claude Sonnet)
│   └── frontend.md (UI/UX - uses invoke_gemini with Gemini 3 Pro High)
│
└── MCP Tools (31 - used BY native subagents)
    ├── Model Invocation: invoke_gemini, invoke_openai
    ├── Code Search: ast_grep_search, grep_search, glob_files
    ├── LSP: lsp_hover, lsp_goto_definition, lsp_find_references, etc.
    └── Legacy (deprecated): agent_spawn, agent_output, agent_progress, agent_list
```

### Decision Matrix

| Agent Type | Implementation | Reasoning |
|------------|---------------|-----------|
| **Stravinsky Orchestrator** | Native subagent + Task tool + PreToolUse hooks | Auto-delegation, hook-based control |
| **Explore** | Native subagent + invoke_gemini | Uses Gemini 3 Flash via MCP tool |
| **Dewey** | Native subagent + invoke_gemini | Uses Gemini 3 Flash + WebSearch |
| **Code Reviewer** | Native subagent | Claude Sonnet (native, no MCP needed) |
| **Debugger** | Native subagent | Claude Sonnet (native, no MCP needed) |
| **Frontend** | Native subagent + invoke_gemini | Uses Gemini 3 Pro High via MCP tool |
| **Delphi (future)** | Native subagent + invoke_openai | Uses GPT-5.2 via MCP tool |

### Migration Benefits

**Before (Current - agent_spawn CLI spawning)**:
- User types: `/stravinsky "implement feature"`
- Executes inline with full system prompt
- Manual slash command invocation
- CLI subprocess overhead (agent_spawn)
- No automatic delegation

**After (CORRECT - Native Task tool + Hooks)**:
- User types: "implement a complex feature with X, Y, Z"
- Claude auto-delegates to stravinsky native subagent
- Stravinsky PreToolUse hooks intercept and delegate via Task tool
- Specialists execute as native subagents (no CLI spawning)
- PostToolUse hooks aggregate results
- Clean separation of orchestration vs execution

**Measured Improvements**:
- ✅ **Zero user friction**: Auto-delegation (no slash commands)
- ✅ **Hook-based control**: PreToolUse enforces delegation policy
- ✅ **Context isolation**: Each specialist runs as separate native subagent
- ✅ **True parallelism**: Multiple Task() calls execute concurrently
- ✅ **Multi-model routing**: Specialists use invoke_gemini/openai MCP tools
- ✅ **No CLI overhead**: All delegation via native Task tool
- ✅ **Hard boundaries**: PreToolUse can block unsafe operations

---

## Implementation Roadmap

## Comparison: Stravinsky vs oh-my-opencode

### Architecture Alignment

Stravinsky's architecture **matches and exceeds** oh-my-opencode's design patterns:

| Feature | oh-my-opencode (Sisyphus) | Stravinsky | Status |
|---------|---------------------------|------------|--------|
| **Orchestrator** | Sisyphus (Opus 4.5, 32k thinking) | Stravinsky (Sonnet 4.5) | ✅ MATCH |
| **Delegation** | Task tool + background_task (CLI spawns) | Task tool (native subagents, zero overhead) | ✅ **BETTER** |
| **Parallel Execution** | Async background agents | Native Task tool (parallel by default) | ✅ **BETTER** |
| **Strategic Advisor** | Oracle (GPT-5.2, after 3 failures) | Delphi (GPT-5.2 Medium, systematic) | ✅ MATCH |
| **Frontend Specialist** | Gemini 3 Pro (ALL visual changes) | Gemini 3 Pro High (UI/UX specialist) | ✅ **BETTER** |
| **Code Search** | Explore (Grok/Gemini/Haiku, always async) | Explore (Gemini 3 Flash, native subagent) | ✅ MATCH |
| **Documentation** | Librarian (Sonnet/Gemini, always async) | Dewey (Gemini 3 Flash + WebSearch) | ✅ MATCH |
| **Code Review** | Not mentioned | Code Reviewer (Claude Sonnet, native) | ✅ **BETTER** |
| **Debugging** | Not mentioned | Debugger (Claude Sonnet, systematic) | ✅ **BETTER** |
| **Tool Access** | Explicit include lists | MCP tools + native inheritance | ✅ **BETTER** |
| **Hook System** | PostToolUse hooks | Pre/PostToolUse + UserPromptSubmit | ✅ **BETTER** |
| **Todo Continuation** | Enforcer hook (prevents abandonment) | Native hook (already implemented) | ✅ MATCH |
| **Context Management** | AnthropicAutoCompact | Claude Code native compaction | ✅ MATCH |
| **Model Fallbacks** | 3-tier (user/installer/default) | OAuth + token refresh | ✅ MATCH |
| **PreToolUse Blocking** | Not mentioned | Hard boundaries (exit code 2) | ✅ **BETTER** |
| **Multi-Model Routing** | Background vs blocking agents | invoke_gemini/openai MCP tools | ✅ MATCH |

### Key Innovations from oh-my-opencode

#### 1. Agent Classification (Cost-Based Routing)

**oh-my-opencode Pattern**:
- **Async (Always Background)**: explore (free), librarian (cheap)
- **Blocking (Synchronous)**: oracle (expensive, only after 3 failures), frontend (medium, ALL visual)

**Stravinsky Enhancement**:
```markdown
# Agent Cost Classification

| Agent | Cost | Execution | When to Use |
|-------|------|-----------|-------------|
| **explore** | Free | Async (Task tool parallel) | Always for code search |
| **dewey** | Cheap | Async (Task tool parallel) | Always for docs research |
| **code-reviewer** | Cheap | Async (Task tool parallel) | Always for quality checks |
| **debugger** | Medium | Blocking | After 2+ failed fixes |
| **frontend** | Medium | Blocking | ALL visual changes |
| delphi | GPT-5.2 | N/A (reasoning_effort) | Strategic architectural decisions |
```

#### 2. Todo Continuation Enforcer

**Status**: ✅ Already implemented in `mcp_bridge/native_hooks/todo_continuation.py`

**Pattern**:
- Injects `[SYSTEM REMINDER - TODO CONTINUATION]` via UserPromptSubmit hook
- Lists IN_PROGRESS and PENDING todos
- Forces continuation before new work
- Prevents chronic LLM task abandonment

#### 3. Delegation Discipline

**oh-my-opencode Rule**: "Sisyphus never works alone when specialists are available"

**Stravinsky Implementation**:
- Orchestrator has PreToolUse hooks that **block** Read/Grep/Bash
- Forces delegation via Task tool to specialists
- Hard enforcement (exit code 2) prevents bypass

#### 4. Search Stop Conditions

**oh-my-opencode Pattern**:
- Sufficient context exists
- Same info across sources
- 2 iterations yield nothing new
- Direct answer found

**Stravinsky Integration**: Already documented in explore.md and dewey.md

### Stravinsky Advantages Over oh-my-opencode

1. **Zero CLI Overhead**: Native Task tool delegation vs CLI subprocess spawning (500ms+ per agent)
2. **Hard Boundaries**: PreToolUse hooks can block tools with exit code 2
3. **Additional Specialists**: code-reviewer.md, debugger.md (not in oh-my-opencode)
4. **Higher Quality Frontend**: Gemini 3 Pro High vs Gemini 3 Pro
5. **MCP Tool Isolation**: Specialists use MCP tools without direct CLI access
6. **Hook Architecture**: 3-layer (native global, native subagent, MCP internal)

### Features to Add (oh-my-opencode Parity)

1. **Agent Classification in Configs**: Add cost/execution metadata to agent YAML frontmatter
2. **Background Result Collection**: Implement non-blocking result aggregation
3. **Extended Thinking Budget**: Add to Stravinsky orchestrator (32k token thinking)

---

### Phase 1: Native Subagent Prototype (COMPLETED)
### Phase 2: Specialist Agent Migration (COMPLETED)
### Phase 3: Hook Unification Layer (COMPLETED)
### Phase 4: Model Proxy (COMPLETED)

---

## User Messaging Integration

### Hook-Based Transparency

Stravinsky now provides real-time transparency about which tools and agents are being used through PostToolUse messaging hooks.

**Implementation**: `mcp_bridge/native_hooks/tool_messaging.py`

**Configuration**:
```json
{
  "PostToolUse": [{
    "matcher": "mcp__stravinsky__*,mcp__grep-app__*,Task",
    "hooks": [{
      "type": "command",
      "command": "python3 .../tool_messaging.py"
    }]
  }]
}
```

### Message Format

**MCP Tools**:
```
🔧 tool-name('description')
```

**Examples**:
- `🔧 ast-grep('Searching AST in src/ for class definitions')`
- `🔧 grep('Searching for authentication patterns')`
- `🔧 lsp-diagnostics('Checking server.py for errors')`

**Agent Delegations**:
```
🎯 agent:model('description')
```

**Examples**:
- `🎯 explore:gemini-3-flash('Finding all API endpoints')`
- `🎯 delphi:gpt-5.2-medium('Analyzing architecture trade-offs')`
- `🎯 frontend:gemini-3-pro-high('Designing login component')`

### Benefits

1. **Cost Awareness**: Model names (gemini-3-flash, gpt-5.2-medium) indicate cost tier
2. **Transparency**: Users see exactly which specialist is handling their task
3. **Debugging**: Easy to trace which tools/agents were used for a result
4. **Workflow Clarity**: Parallel agent execution is visible in real-time

### Integration with Delegation Enforcement

The messaging hooks work in tandem with PreToolUse delegation enforcement:

```
User: "Find all authentication code"
  ↓
PreToolUse (stravinsky_mode.py)
  ↓ Output: 🎭 explore('Delegating Grep (searching for 'auth')')
  ↓ BLOCK Grep tool
  ↓
Claude uses Task tool instead
  ↓
PostToolUse (tool_messaging.py)
  ↓ Output: 🎯 explore:gemini-3-flash('Find auth code')
  ↓
User sees both:
  🎭 explore('Delegating Grep (searching for 'auth')')
  🎯 explore:gemini-3-flash('Find auth code')
```

This provides complete visibility: **why** delegation happened (PreToolUse) and **which agent** is executing (PostToolUse).

---

## Parallel Delegation Enforcement Gap

### Overview

Stravinsky's core value proposition is **parallel execution** for multi-step tasks. However, there is a critical gap between the *advisory* hooks that **remind** about parallel delegation and the actual **enforcement** of parallel patterns. This section documents the current state, why the problem exists, and proposes solutions for future implementation.

### The Problem

**Observed Behavior**: Despite parallel delegation reminders from hooks, Claude (Sonnet 4.5) frequently executes tasks sequentially:

```
User: "Implement feature X with Y and Z"
  ↓
Claude: TodoWrite([todo1, todo2, todo3])
  ↓
Hook outputs: [PARALLEL DELEGATION REQUIRED]
  ↓
Claude response ENDS without agent_spawn calls  ← PROBLEM
  ↓
Next response: Mark todo1 as in_progress, work on it directly
  ↓
Next response: Mark todo2 as in_progress, work on it directly
  ↓
Result: Sequential execution, no parallelism
```

**Impact**:
- Defeats Stravinsky's core value (multi-model parallel orchestration)
- Wastes time (sequential vs parallel execution)
- Underutilizes cheap models (gemini-3-flash unused)
- Users get Claude Sonnet behavior instead of orchestrated multi-model execution

### Current Advisory System

#### Hook Implementation: `todo_delegation.py`

**Location**: `/Users/davidandrews/PycharmProjects/stravinsky/.claude/hooks/todo_delegation.py`

**Hook Type**: `PostToolUse` (triggers after TodoWrite)

**Current Behavior**:
```python
def main():
    # ... read hook input ...

    if tool_name != "TodoWrite":
        return 0

    # Count pending todos
    pending_count = sum(1 for t in todos if t.get("status") == "pending")

    if pending_count < 2:
        return 0

    # Output reminder message
    reminder = f"""
[PARALLEL DELEGATION REQUIRED]

You just created {pending_count} pending TODOs. Before your NEXT response:

1. Identify which TODOs are INDEPENDENT (can run simultaneously)
2. For EACH independent TODO, spawn a Task agent:
   Task(subagent_type="Explore", prompt="[TODO details]", run_in_background=true)
3. Fire ALL Task calls in ONE response - do NOT wait between them
4. Do NOT mark any TODO as in_progress until agents return

WRONG: Create TODO list -> Mark TODO 1 in_progress -> Work -> Complete -> Repeat
CORRECT: Create TODO list -> Spawn Task for each -> Collect results -> Mark complete
"""
    print(reminder)
    return 0  # ← EXIT CODE 0: Advisory only, does NOT block
```

**Key Limitation**: `return 0` means the hook is **advisory only**. Claude sees the reminder but can ignore it.

#### Configuration Conflict: Task vs agent_spawn

**Two contradictory instructions exist**:

**File 1**: `.claude/commands/stravinsky.md` (slash command, line 132-134)
```markdown
## Hard Blocks (NEVER violate)

- ❌ **NEVER use Claude Code's Task tool** - It runs Claude, not Gemini/GPT
- ❌ WRONG: `Task(subagent_type="Explore", ...)` - Uses Claude Sonnet, wastes money
- ✅ CORRECT: `agent_spawn(agent_type="explore", ...)` - Uses gemini-3-flash, cheap
```

**File 2**: `.claude/agents/stravinsky.md` (native subagent, lines 48-71)
```markdown
### Delegation Pattern

Use the **Task tool** to delegate to native subagents:

```python
# Example: Delegate to specialist agents in parallel
# All in ONE response:
Task(
    subagent_type="explore",
    prompt="Find all authentication implementations...",
    description="Find auth implementations"
)
```
```

**File 3**: `.claude/hooks/todo_delegation.py` (PostToolUse hook, line 42)
```python
reminder = f"""
2. For EACH independent TODO, spawn a Task agent:
   Task(subagent_type="Explore", prompt="[TODO details]", run_in_background=true)
"""
```

**Analysis**:
- The slash command (`/stravinsky`) says "NEVER use Task tool, use agent_spawn"
- The native subagent (`.claude/agents/stravinsky.md`) says "Use Task tool for delegation"
- The hook (`todo_delegation.py`) says "Spawn a Task agent"
- This confusion contributes to inconsistent behavior

### Why Advisory Hooks Don't Work

#### 1. Exit Code 0 = No Enforcement

Hook return codes in Claude Code:
- `0` = Success, advisory message only
- `1` = Error/warning, but execution continues
- `2` = BLOCK tool execution (hard enforcement)

Current hook returns `0`, meaning:
- Reminder is printed to conversation
- TodoWrite executes successfully
- Claude is FREE to ignore the reminder
- No mechanism forces parallel delegation

#### 2. PostToolUse Timing Issue

`PostToolUse` hooks trigger **AFTER** the tool has already executed:

```
Claude decides to use TodoWrite
  ↓
TodoWrite executes (creates todos)
  ↓
PostToolUse hook runs (prints reminder)  ← Too late to block
  ↓
Claude's response ends (no agent_spawn calls)
```

**Problem**: By the time the hook runs, TodoWrite has already completed. The hook can only *suggest* what to do next, not *enforce* behavior in the current response.

#### 3. LLM Behavioral Patterns

Large language models (including Claude Sonnet 4.5) exhibit **task continuation bias**:
- After planning (TodoWrite), the model defaults to immediate execution
- "Mark first todo as in_progress" is the natural next action
- Delegation requires breaking this pattern (context switch)
- Advisory reminders compete with strong sequential instincts

From testing:
- Reminders work ~30-40% of the time
- Longer prompts/reminders are more easily ignored
- Model prioritizes "making progress" over "orchestration"

#### 4. Logging Evidence

**Observation from logs**: Zero agent spawning activity despite reminders

From `logs/application-2026-01-05.log`:
```
# Many TodoWrite calls observed
# Many tool invocations (Read, Grep, Edit)
# Zero agent_spawn MCP tool calls
# Zero background task creation
```

**Conclusion**: Hook reminders are being ignored consistently.

### Proposed Enforcement Solutions

#### Solution 1: Exit Code 1 Hard Block (PreToolUse)

**Strategy**: Block TodoWrite if parallel delegation didn't happen

**Implementation**:
```python
# .claude/hooks/parallel_enforcement.py (PreToolUse hook)

def main():
    hook_input = json.load(sys.stdin)
    tool_name = hook_input.get("tool_name", "")

    # Check session state for "todos created but no agents spawned"
    if tool_name == "TodoWrite":
        # Load session state
        state = load_session_state()

        # Check if previous TodoWrite had pending todos
        if state.get("pending_todos_count", 0) >= 2:
            # Check if agents were spawned since then
            if state.get("agents_spawned_since_todowrite", 0) == 0:
                # BLOCK: Parallel delegation was not done
                print(json.dumps({
                    "decision": "block",
                    "reason": "Previous TodoWrite created 2+ pending todos but ZERO agents were spawned. You MUST spawn Task agents for independent todos before creating more."
                }))
                return 2  # BLOCK

        # Allow this TodoWrite but track it
        return 0
```

**Benefits**:
- Hard enforcement (exit code 2 blocks execution)
- Provides clear error message explaining violation
- Forces Claude to spawn agents before creating more todos

**Drawbacks**:
- Requires session state tracking (complex)
- May block legitimate use cases (user wants sequential execution)
- Can't detect agents spawned in same response (timing issue)

#### Solution 2: Runtime Validation (MCP Hook)

**Strategy**: Validate delegation immediately after TodoWrite via MCP hook

**Implementation**:
```python
# mcp_bridge/hooks/post_tool/parallel_validation.py

async def validate_parallel_delegation(
    tool_name: str,
    tool_input: dict,
    result: Any,
    context: HookContext
) -> HookResult:
    """Validate parallel delegation after TodoWrite"""

    if tool_name != "TodoWrite":
        return HookResult.CONTINUE

    todos = tool_input.get("todos", [])
    pending_count = sum(1 for t in todos if t.get("status") == "pending")

    if pending_count < 2:
        return HookResult.CONTINUE

    # Track this TodoWrite in session
    context.session_state["last_todowrite"] = {
        "timestamp": time.time(),
        "pending_count": pending_count,
        "agent_spawn_required": True
    }

    # Set a flag that next response MUST include agent_spawn
    context.session_state["require_agent_spawn"] = True

    return HookResult.CONTINUE

# mcp_bridge/hooks/pre_tool/agent_spawn_validator.py

async def validate_agent_spawn_happened(
    tool_name: str,
    tool_input: dict,
    context: HookContext
) -> HookResult:
    """Block tools if agent_spawn was required but didn't happen"""

    # If agent_spawn is required
    if context.session_state.get("require_agent_spawn", False):
        # Check if we're calling agent_spawn now
        if tool_name == "agent_spawn":
            # Good! Clear the requirement
            context.session_state["require_agent_spawn"] = False
            return HookResult.CONTINUE

        # Otherwise, block any other tool
        return HookResult.BLOCK(
            reason="TodoWrite created 2+ pending todos. You MUST call agent_spawn for each independent todo before using other tools."
        )

    return HookResult.CONTINUE
```

**Benefits**:
- Runtime validation within MCP server (no subprocess overhead)
- Can track state across tool calls in same response
- Provides immediate feedback

**Drawbacks**:
- Only works for MCP tools (can't block native tools like Read/Grep)
- Requires session state management
- Complex hook orchestration

#### Solution 3: Tool Response Interception (Response Modification)

**Strategy**: Modify TodoWrite response to FORCE agent_spawn calls

**Implementation**:
```python
# mcp_bridge/hooks/post_tool/inject_agent_spawn.py

async def inject_agent_spawn_calls(
    tool_name: str,
    tool_input: dict,
    result: Any,
    context: HookContext
) -> HookResult:
    """Automatically inject agent_spawn calls into response"""

    if tool_name != "TodoWrite":
        return HookResult.CONTINUE

    todos = tool_input.get("todos", [])
    pending_todos = [t for t in todos if t.get("status") == "pending"]

    if len(pending_todos) < 2:
        return HookResult.CONTINUE

    # Generate agent_spawn calls for each pending todo
    spawn_calls = []
    for todo in pending_todos:
        spawn_call = {
            "tool": "agent_spawn",
            "input": {
                "agent_type": "explore",  # Default to explore
                "prompt": generate_delegation_prompt(todo),
                "description": todo.get("content", "")[:50]
            }
        }
        spawn_calls.append(spawn_call)

    # Modify result to include spawn calls
    modified_result = {
        "original": result,
        "injected_calls": spawn_calls,
        "message": f"Auto-spawned {len(spawn_calls)} agents for parallel execution"
    }

    return HookResult.MODIFY(modified_result)
```

**Benefits**:
- Automatic parallel delegation (no user intervention)
- Guarantees parallel execution pattern
- Transparent to Claude (happens at hook level)

**Drawbacks**:
- Removes Claude's agency (may spawn wrong agents)
- Hard to determine correct agent_type per todo
- May spawn agents for todos that shouldn't be delegated
- Experimental (MCP hook response modification is complex)

### Recommended Approach

**Phase 1: Configuration Clarity (Immediate)**

1. **Resolve Task vs agent_spawn conflict**:
   - Decision: Use **Task tool** for native subagent delegation (matches `.claude/agents/stravinsky.md`)
   - Update `.claude/commands/stravinsky.md` to remove "NEVER use Task" warning
   - Update `todo_delegation.py` hook to use consistent terminology

2. **Strengthen hook messaging**:
   - Make reminder more prominent (ASCII art border, ALL CAPS)
   - Add examples of CORRECT vs WRONG patterns
   - Reference specific line numbers in agent configs

**Phase 2: Soft Enforcement (Short Term)**

1. **Add progress tracking**:
   - Hook tracks if agents were spawned after TodoWrite
   - Next TodoWrite shows warning if no agents were used
   - Non-blocking but creates visible accountability

2. **Session state persistence**:
   - Store last TodoWrite timestamp and pending count
   - Track agent_spawn calls in session
   - Display statistics at end of session

**Phase 3: Hard Enforcement (Long Term)**

1. **Implement Solution 2 (Runtime Validation)**:
   - MCP hook blocks non-agent-spawn tools after TodoWrite
   - Provides clear error messages
   - Allows override flag for legitimate sequential work

2. **Add configuration option**:
   - `.stravinsky/config.json` → `"enforce_parallel_delegation": true/false`
   - Default: `false` (advisory only, backward compatible)
   - Users can opt-in to strict enforcement

### Testing & Validation

**Success Metrics**:
- Parallel delegation rate increases from ~30% to >80%
- Agent spawn count correlates with TodoWrite pending count
- Logs show agent_spawn calls after TodoWrite
- User feedback: "Stravinsky feels more automated"

**Test Cases**:
1. **Basic**: TodoWrite with 3 pending todos → Should spawn 3 agents
2. **Sequential**: TodoWrite with 1 pending todo → Should NOT require agents
3. **Mixed**: TodoWrite with 2 dependent + 1 independent → Should spawn 1 agent
4. **Override**: User explicitly wants sequential work → Should allow bypass

### Open Questions

1. **Should enforcement apply to native subagents only or all contexts?**
   - Native subagents (`.claude/agents/stravinsky.md`) are orchestrators
   - Main conversation may want flexibility
   - Proposal: Enforce for native subagents, advisory for main

2. **How to detect dependent vs independent todos?**
   - Natural language analysis? (complex, error-prone)
   - User annotation? (`todo: {..., "independent": true}`)
   - Conservative default: Assume all pending todos are independent

3. **Should Task tool support run_in_background parameter?**
   - Current Task tool is synchronous (blocks until complete)
   - Native subagents can't do "fire and forget" delegation
   - May need async Task support in Claude Code

4. **What about non-delegation workflows?**
   - Some tasks genuinely need sequential execution
   - Example: "Read file X, then based on content, modify file Y"
   - Need escape hatch: `TodoWrite([..., {"parallel": false}])`

### Conclusion

The parallel delegation enforcement gap exists because:
1. Hooks are advisory (exit code 0), not enforcement (exit code 2)
2. PostToolUse timing is too late to block behavior
3. LLM task continuation bias defaults to sequential execution
4. Configuration conflicts create inconsistent guidance

**Immediate Action**: Resolve Task vs agent_spawn documentation conflict

**Future Work**: Implement runtime validation with opt-in enforcement flag

**Goal**: Make parallel delegation the **default, enforced pattern** rather than an optional suggestion.

---

## Appendix

### Delphi Strategic Recommendations (GPT-5.2)

From comprehensive architecture analysis:

1. **Keep the Hook Split** - It's defense in depth, not duplication
2. **Add Model Proxy** - Critical for true parallelism
3. **Unified Interface** - Share policies between hook types
4. **Native Subagents** - Enable auto-delegation without friction
5. **Hybrid Pattern** - Native for Claude tasks, CLI spawn for multi-model

### Key Metrics

- **Native Hooks**: 5 (hard enforcement boundaries)
- **MCP Hooks**: 17+ (orchestration, optimization, lifecycle)
- **MCP Tools**: 31 (agent, model, search, LSP, session, skill)
- **Agent Types**: 7 (stravinsky, delphi, dewey, explore, frontend, document_writer, multimodal)
- **Current Architecture**: Slash commands + CLI spawns
- **Target Architecture**: Native subagents + MCP tools + CLI spawns

### Questions & Discussion

For questions about this architecture or to discuss migration strategy:
- Review Delphi analysis in `.stravinsky/agents.json` (task_id: a37cb8e)
- Check hook research outputs (task_ids: ad11edb, a1f808d, a0ea7cf, etc.)
- Consult native subagent research (task_ids: adeec70, a3a3825)
