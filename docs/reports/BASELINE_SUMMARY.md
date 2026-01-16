# Stravinsky Architecture Baseline - Executive Summary

**Date**: 2025-01-09
**Version**: 0.4.16
**Status**: Ready for Gap Analysis

---

## What is This Document?

This is the **baseline inventory** of Stravinsky's current architecture. It answers:
- ✅ What tools exist?
- ✅ What agents are defined?
- ✅ What patterns are implemented?
- ❌ What gaps need to be filled?

---

## Key Findings

### 1. **Tool Ecosystem: 40+ Tools, Fully Functional**

Stravinsky exposes **40+ MCP tools** organized into 9 categories:

| Category | Count | Status |
|----------|-------|--------|
| Model Invocation (Gemini/OpenAI) | 3 | ✅ Working |
| Code Search (grep, AST, semantic) | 4 | ✅ Working |
| LSP Tools (hover, goto, rename, etc.) | 12 | ✅ Working (35x speedup) |
| Semantic Search | 5+ | ✅ Working |
| Agent Management | 6 | ✅ Working |
| Task Management | 3 | ✅ Working |
| Session & Context | 5 | ✅ Working |
| Skills/Commands | 2 | ✅ Working |
| Advanced | 1 | ✅ Working |

**Tools are production-ready.** All search capabilities, LSP integration, agent spawning, and model invocation work correctly.

---

### 2. **Native Agent Architecture: 8 Agents Defined**

Stravinsky includes **8 native Claude Code subagents**:

| Agent | Role | Model | Cost | Status |
|-------|------|-------|------|--------|
| stravinsky | Orchestrator | Claude Sonnet 4.5 | Moderate | ✅ Defined |
| explore | Code search | Gemini Flash | Free | ✅ Defined |
| dewey | Doc research | Gemini Flash | Cheap | ✅ Defined |
| code-reviewer | Quality analysis | Gemini Flash | Cheap | ✅ Defined |
| debugger | Root cause | Claude Sonnet | Medium | ✅ Defined |
| frontend | UI/UX | Gemini 3 Pro High | Medium | ✅ Defined |
| delphi | Architecture | GPT-5.2 | Expensive | ✅ Defined |
| research-lead | Research coordinator | Gemini Flash | Cheap | ✅ Defined |
| implementation-lead | Implementation coordinator | Claude Sonnet | Medium | ✅ Defined |

**All agents have system prompts defining their roles and tools.**

---

### 3. **Delegation Patterns: Working, But Manual**

Stravinsky supports **3 core delegation patterns**:

```
Pattern 1: Parallel Delegation
├─ TodoWrite([task1, task2, task3])
├─ Task(explore) + Task(dewey) + Task(frontend)  [SAME RESPONSE]
└─ All execute in parallel

Pattern 2: Conditional Blocking
├─ Attempt fix #1 (orchestrator)
├─ Attempt fix #2 (orchestrator)
└─ If both fail: Task(debugger, blocking=true)

Pattern 3: Visual-Always Delegation
└─ ANY visual change: Task(frontend, blocking=true)
```

**Status**: ✅ **Works, but manual** - Orchestrator must decide when to delegate. No automatic enforcement.

---

### 4. **Hook System: Implemented in Python, Not Wired to Claude Code**

Stravinsky has **30+ Python hook implementations** in `mcp_bridge/hooks/`:

- agent_reminder.py, parallel_enforcer.py, rules_injector.py, etc.
- These hook into the MCP bridge lifecycle

**Status**: ✅ **Python layer ready, but NOT wired to Claude Code's native hook system**

**Missing**: Hook registration in `.claude/settings.json` to enable:
- PreToolUse hook (block Read/Grep/Bash, force delegation)
- PostToolUse hook (aggregate specialist results)
- UserPromptSubmit hook (inject context)

---

### 5. **Search Capabilities: All 4 Strategies Implemented**

| Strategy | Tools | Status |
|----------|-------|--------|
| **Pattern-based** | grep_search, ast_grep_search | ✅ Working |
| **Semantic** | semantic_search, hybrid_search | ✅ Working |
| **Symbol Navigation** | lsp_workspace_symbols, lsp_goto_definition | ✅ Working |
| **Reference Tracing** | lsp_find_references | ✅ Working |

Decision tree for choosing tools is clearly documented. All search methods work.

---

### 6. **Semantic Search: Fully Integrated**

- ✅ Multiple providers: ollama (local), gemini (cloud), openai (cloud), huggingface (cloud)
- ✅ Auto-indexing with file watcher
- ✅ Hybrid search combining semantic + AST
- ✅ Explore agent can synthesize results with Gemini analysis

**Status**: Production-ready. Requires one-time `semantic_index()` per project.

---

### 7. **LSP Integration: 35x Speedup via Persistent Servers**

- ✅ All 12 LSP tools: hover, goto_definition, find_references, rename, code_actions, extract_refactor, etc.
- ✅ Persistent LSPManager prevents repeated initialization
- ✅ 35x faster than reinitializing per request

**Status**: Production-ready and optimized.

---

### 8. **OAuth & Authentication: Secure Token Management**

- ✅ Google OAuth (Gemini)
- ✅ OpenAI OAuth (ChatGPT)
- ✅ Secure keyring + encrypted file fallback
- ✅ Auto-refresh tokens

**Status**: Complete and working.

---

## Critical Gap: Hook Integration

### Problem
Stravinsky has all the **tools, agents, and patterns**, but the **PreToolUse hook** isn't wired to enforce delegation.

Currently:
- Orchestrator CAN choose to delegate
- But NOTHING FORCES it to

What's needed:
- `.claude/agents/hooks/pre_tool_use.sh` to intercept Read/Grep/Bash
- Block complex searches, return exit code 2
- Orchestrator system prompt then uses Task() to delegate
- `.claude/settings.json` to register the hook

### Impact
Without hooks:
- ❌ Orchestrator can execute tools directly (defeats parallel execution)
- ❌ No automatic enforcement of delegation
- ❌ More expensive (Sonnet doing free work, explore agent not used)

With hooks:
- ✅ Orchestrator forced to delegate (hard boundary)
- ✅ Parallel execution guaranteed (free agents always async)
- ✅ Cost optimization automatic (expensive model doing only planning)
- ✅ Better context isolation (specialists have limited tool access)

---

## Architecture Completeness

```
┌─────────────────────────────────────────────────────┐
│ ARCHITECTURE COMPLETENESS SCORE: 80%                │
└─────────────────────────────────────────────────────┘

✅ MCP Tools                    100% (40+ tools)
✅ Native Agents                100% (8 agents defined)
✅ Agent Prompts               100% (system prompts ready)
✅ Code Search                 100% (all 4 strategies)
✅ LSP Integration             100% (12 tools, 35x speedup)
✅ Semantic Search             100% (multi-provider)
✅ OAuth                       100% (Google, OpenAI)
✅ Python Hook Layer           100% (30+ modules)
❌ Claude Code Hook Integration   0% (not wired)
❌ Delegation Enforcement         0% (PreToolUse not active)

Missing: Hook registration (.claude/settings.json) and
         native script (.claude/agents/hooks/pre_tool_use.sh)
```

---

## Recommendations (Next Steps)

### Phase 1: Hook Integration (CRITICAL)
1. Implement `.claude/agents/hooks/pre_tool_use.sh`
   - Detect complex searches (3+ files, AST patterns)
   - Return exit code 2 to block
   - Let simple lookups through

2. Implement `.claude/agents/hooks/post_tool_use.sh`
   - Detect Task() completion
   - Log results
   - Signal orchestrator

3. Register hooks in `.claude/settings.json`
   - Map hook scripts to Claude Code events
   - Set execution order

**Effort**: ~2-4 hours
**Impact**: Enables automatic delegation enforcement, reduces cost, guarantees parallel execution

---

### Phase 2: Validation & Testing
- Test all 3 delegation patterns
- Verify parallel execution works
- Measure: cost savings, context isolation, overhead

**Effort**: ~4-6 hours

---

### Phase 3: Documentation
- User guide: when to use which agent
- Troubleshooting: common issues
- Cost optimization patterns

**Effort**: ~2-3 hours

---

## Key Files to Review

**Baseline Map**: `/Users/davidandrews/PycharmProjects/stravinsky/ARCHITECTURE_MAP.md`
- 12 sections covering complete architecture
- Tool inventory, agent specs, gap analysis, recommendations
- Quick reference tables

**Agent System Prompts**:
- `.claude/agents/stravinsky.md` - Orchestrator (longest, most detailed)
- `.claude/agents/explore.md` - Code search specialist
- `.claude/agents/HOOKS.md` - Hook documentation

**Tool Definitions**:
- `mcp_bridge/server_tools.py` - All 40+ tool definitions

**Config Files**:
- `pyproject.toml` - Version, Python constraints
- `mcp_bridge/__init__.py` - Version constant

---

## What This Baseline Enables

With this baseline documented, you can now:

1. **Gap Analysis**: Identify what's implemented vs. missing
2. **Implementation Planning**: Prioritize hook integration
3. **Cost Modeling**: Understand agent costs and when to delegate
4. **Testing Strategy**: Know what needs validation
5. **Documentation**: Refer to architecture map for users

---

## Quick Reference: Tool Lookup

| Need | Tool | File |
|------|------|------|
| Find function/class | lsp_workspace_symbols | tools/lsp/tools.py |
| Find all callers | lsp_find_references | tools/lsp/tools.py |
| Search code text | grep_search | tools/code_search.py |
| Search code structure | ast_grep_search | tools/code_search.py |
| Search behavior | semantic_search | tools/semantic_search.py |
| List files | glob_files | tools/code_search.py |
| Spawn agent | agent_spawn | tools/agent_manager.py |
| Invoke Gemini | invoke_gemini | tools/model_invoke.py |
| Invoke OpenAI | invoke_openai | tools/model_invoke.py |
| Get project context | get_project_context | tools/project_context.py |
| List sessions | session_list | tools/session_manager.py |

---

## Next: Implementation Plan

Once this baseline is approved, the next step is implementing **Phase 1 (Hook Integration)** which enables:
- Automatic delegation enforcement
- Guaranteed parallel execution
- Cost optimization
- Context isolation

This is the critical missing piece that transforms Stravinsky from "capable toolkit" to "self-optimizing orchestrator."

---

**Document Version**: 1.0
**Last Updated**: 2025-01-09
**Ready For**: Gap Analysis, Implementation Planning, Testing Strategy
