# Stravinsky Architecture Guide

## Overview

Stravinsky is an MCP bridge for Claude Code that enables multi-model AI orchestration with parallel agent execution. This document provides comprehensive architectural guidance based on extensive analysis of the hooks system, agent orchestration patterns, and native subagent integration.

## Table of Contents

1. [Hooks Architecture](#hooks-architecture)
2. [Native Subagent Migration](#native-subagent-migration)
3. [Hybrid Architecture Recommendations](#hybrid-architecture-recommendations)
4. [Implementation Roadmap](#implementation-roadmap)

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

#### Native Hooks (5)

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

#### Phase 1: Unified Interface Layer

Create a canonical event model that both hook types can use:

```python
# mcp_bridge/hooks/events.py

from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class ToolCallEvent:
    """Canonical event for tool invocation"""
    tool_name: str
    args: dict[str, Any]
    result: Optional[Any] = None
    timestamp: float
    session_id: str

    @classmethod
    def from_native_hook(cls, stdin_json: dict):
        """Adapter for native hook JSON"""
        return cls(
            tool_name=stdin_json["tool"],
            args=stdin_json["args"],
            result=stdin_json.get("result"),
            timestamp=time.time(),
            session_id=stdin_json.get("session_id", "unknown")
        )

    @classmethod
    def from_mcp_hook(cls, name: str, args: dict, result: Any):
        """Adapter for MCP hook calls"""
        return cls(
            tool_name=name,
            args=args,
            result=result,
            timestamp=time.time(),
            session_id=get_current_session_id()
        )

@dataclass
class HookPolicy:
    """Shared policy that both hook types can enforce"""
    name: str
    should_block: Callable[[ToolCallEvent], bool]
    transform_result: Callable[[Any], Any]
    priority: int
```

**Benefits**:
- Shared policy definitions (DRY principle)
- Easier testing (policies are pure functions)
- Clear separation: native hooks enforce hard boundaries, MCP hooks orchestrate behavior

#### Phase 2: Model Proxy (Critical Optimization)

Current architecture has **head-of-line blocking**:

```
Native Subagent → agent_spawn → Claude CLI spawn → invoke_gemini
                                                   ↓
                                    MCP stdio transport (BLOCKS)
                                                   ↓
                        Stravinsky MCP Server → Gemini API
```

**Problem**: When agent uses invoke_gemini, the ENTIRE MCP stdio transport blocks until Gemini responds (2-30 seconds). This prevents other agents from using ANY MCP tool.

**Solution**: Local model proxy

```python
# mcp_bridge/proxy/model_server.py

import asyncio
from fastapi import FastAPI

app = FastAPI()

@app.post("/v1/gemini/generate")
async def gemini_proxy(request: dict):
    """Proxy Gemini calls locally - no MCP blocking"""
    token = await get_gemini_token()
    # Direct API call, no MCP protocol overhead
    response = await gemini_client.generate(...)
    return response
```

**Benefits**:
- Eliminates head-of-line blocking
- Enables true parallelism (20+ concurrent model calls)
- Adds observability (trace IDs, circuit breakers, rate limiting)

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
| **delphi** | Expensive | Blocking | After 3+ failures, architecture |
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

### Phase 1: Native Subagent Prototype (1 week)

**Tasks**:
1. Create `.claude/agents/stravinsky.md` with full orchestrator prompt
2. Test auto-delegation with complex tasks
3. Verify agent_spawn MCP tool calls work from native subagent
4. Measure: delegation accuracy, context size, execution time

**Success Criteria**:
- [ ] Stravinsky auto-delegates for 90%+ of complex tasks
- [ ] agent_spawn works from native subagent context
- [ ] No increase in token usage vs slash command

### Phase 2: Specialist Agent Migration (1 week)

**Tasks**:
1. Create `.claude/agents/code-reviewer.md`
2. Create `.claude/agents/debugger.md`
3. Update Stravinsky orchestrator to delegate to new agents
4. Test: code review workflow, debugging workflow

**Success Criteria**:
- [ ] Code reviews auto-delegated without manual `/review`
- [ ] Debugger auto-delegated for error analysis
- [ ] Context isolation verified

### Phase 3: Hook Unification Layer (2 weeks)

**Tasks**:
1. Implement `mcp_bridge/hooks/events.py` with canonical event model
2. Create adapters for native and MCP hooks
3. Migrate 3 policies to unified interface
4. Add policy testing framework

**Success Criteria**:
- [ ] 3+ policies using unified HookPolicy class
- [ ] Native and MCP hooks share policy definitions
- [ ] Test coverage >80% for policies

### Phase 4: Model Proxy (2 weeks)

**Tasks**:
1. Implement `mcp_bridge/proxy/model_server.py` with FastAPI
2. Add Gemini and OpenAI proxy endpoints
3. Migrate invoke_gemini to use proxy (optional fallback to MCP)
4. Add observability: trace IDs, circuit breaker, rate limiting

**Success Criteria**:
- [ ] 20+ concurrent model calls without blocking
- [ ] <100ms overhead vs direct API calls
- [ ] Circuit breaker triggers on API failures
- [ ] Trace IDs in all logs

### Phase 5: Documentation & Cleanup (1 week)

**Tasks**:
1. Update CLAUDE.md with native subagent architecture
2. Remove "DO NOT USE" warning from templates.py
3. Update README.md with new orchestration pattern
4. Create migration guide for existing users

**Success Criteria**:
- [ ] All docs reference native subagent pattern
- [ ] Migration guide tested with 3+ users
- [ ] Slash commands marked as deprecated

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
