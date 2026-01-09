# Stravinsky Architecture Baseline - Complete Index

**Purpose**: Quick navigation guide to all baseline documentation and source code.

**Generated**: 2025-01-09
**Version**: 0.4.16

---

## 📋 Baseline Documentation (Start Here)

### 1. **BASELINE_SUMMARY.md** ← START HERE
**What**: Executive summary in 3 pages
**Best For**: Quick overview, 5-minute read
**Contains**:
- Key findings (80% complete)
- Critical gap (hook integration missing)
- Completeness score
- Recommendations (phased approach)

### 2. **ARCHITECTURE_MAP.md**
**What**: Comprehensive 12-section reference
**Best For**: Deep dive, detailed inventory
**Contains**:
- Complete tool inventory (40+)
- Agent specifications with cost tiers
- Hook architecture with implementation status
- Delegation patterns
- Gap analysis with recommendations
- Quick reference tables
- File organization

### 3. **ARCHITECTURE_FLOWS.md**
**What**: Visual ASCII diagrams and flows
**Best For**: Understanding interactions
**Contains**:
- Complete request lifecycle (with hooks)
- Tool selection decision tree
- Delegation decision matrix
- Parallel execution pattern
- Hook integration points
- Cost tier routing
- Agent capability matrix
- Token cost comparison

### 4. **THIS FILE: BASELINE_INDEX.md**
**What**: Navigation guide
**Best For**: Finding what you need

---

## 🛠️ Key Source Files

### Agents (.claude/agents/)

| File | Agent | Purpose |
|------|-------|---------|
| stravinsky.md | Stravinsky | Orchestrator (most important) |
| explore.md | Explore | Code search specialist |
| dewey.md | Dewey | Documentation research |
| code-reviewer.md | Code Reviewer | Quality analysis |
| debugger.md | Debugger | Root cause investigation |
| frontend.md | Frontend | UI/UX implementation |
| delphi.md | Delphi | Architecture advisor |
| HOOKS.md | Hooks | Hook system architecture |
| research-lead.md | Research Lead | Research coordinator |
| implementation-lead.md | Implementation Lead | Implementation coordinator |

**Key Insight**: `.claude/agents/stravinsky.md` is the most critical file - contains orchestrator system prompt with complete delegation patterns.

---

### MCP Tools (mcp_bridge/)

| Module | Tools | Count | Purpose |
|--------|-------|-------|---------|
| tools/model_invoke.py | invoke_gemini, invoke_openai | 2 | Multi-model access |
| tools/code_search.py | grep_search, ast_grep_search, glob_files | 3 | Code search strategies |
| tools/lsp/tools.py | lsp_* (12 tools) | 12 | Language server integration |
| tools/semantic_search.py | semantic_search, hybrid_search, semantic_index | 5+ | Natural language search |
| tools/agent_manager.py | agent_spawn, agent_output, agent_progress, etc | 6 | Agent orchestration |
| tools/background_tasks.py | task_spawn, task_status, task_list | 3 | Background execution |
| tools/session_manager.py | session_list, session_read, session_search | 3 | Session management |
| tools/project_context.py | get_project_context | 1 | Context retrieval |
| tools/skill_loader.py | skill_list, skill_get | 2 | Slash command discovery |
| server_tools.py | All 40+ tools defined | 40+ | Tool definitions (JSON schema) |

**Key Insight**: `server_tools.py` defines all 40+ MCP tools as JSON schemas. This is the source of truth for what Stravinsky exposes to Claude Code.

---

### Hooks (mcp_bridge/hooks/)

| Module | Purpose |
|--------|---------|
| manager.py | Hook orchestration |
| agent_reminder.py | Remind about agents |
| parallel_enforcer.py | Enforce parallel execution |
| parallel_execution.py | Coordinate parallel tasks |
| rules_injector.py | Inject project rules |
| context.py / context_monitor.py | Context management |
| todo_delegation.py / todo_enforcer.py | Todo patterns |
| preemptive_compaction.py | Proactive compression |
| [26 more] | Various specific hooks |

**Key Insight**: Python hooks are implemented but NOT wired to Claude Code's native hook system. Need `.claude/settings.json` to register them.

---

### Configuration

| File | Purpose |
|------|---------|
| pyproject.toml | Package metadata, version (0.4.16), Python constraint (<3.14) |
| mcp_bridge/__init__.py | Version constant |
| .claude/commands/*.md | 14 slash commands |
| .mcp.json | Claude Code MCP bridge registration (not in repo) |
| .claude/settings.json | ❌ **MISSING** - Needs to register hooks |

---

## 📊 Architecture at a Glance

```
STRAVINSKY MCP BRIDGE (v0.4.16)
═════════════════════════════════════════════════════════════

LAYER 1: CLAUDE CODE INTERFACE
├─ Native Agents (8): stravinsky, explore, dewey, etc.
├─ Slash Commands (14): /strav, /delphi, /review, etc.
└─ Auto-delegation: Based on agent description matching

LAYER 2: MCP TOOLS (40+)
├─ Model Invocation (3): invoke_gemini, invoke_openai
├─ Code Search (4): grep, AST, semantic, glob
├─ LSP Integration (12): hover, goto, rename, etc. (35x speedup)
├─ Agent Management (6): spawn, output, progress, etc.
├─ Task Management (3): task_spawn, task_status, etc.
├─ Session & Context (5): session_list, get_project_context
└─ Skills (2): skill_list, skill_get

LAYER 3: EXECUTION
├─ Parallel Execution: Via Task() tool (all agents in parallel)
├─ Delegation: Stravinsky orchestrator → specialists
├─ Cost Optimization: Free agents async, expensive blocking
└─ Search Strategies: Pattern-based, semantic, hybrid, LSP

LAYER 4: HOOK SYSTEM (30+ implemented, 0 wired)
├─ Python hooks: mcp_bridge/hooks/ (implemented)
├─ Native hooks: .claude/agents/hooks/ (MISSING SCRIPTS)
├─ Hook registration: .claude/settings.json (MISSING FILE)
└─ Status: 80% complete, needs hook integration

LAYER 5: AUTHENTICATION
├─ OAuth: Google (Gemini), OpenAI (ChatGPT)
├─ Token Storage: Keyring + encrypted files
└─ Status: Complete, working
```

---

## 🎯 Quick Answer Guide

### "How do I...?"

| Question | Answer | File |
|----------|--------|------|
| Understand complete architecture? | Read ARCHITECTURE_MAP.md | ARCHITECTURE_MAP.md |
| See how agents interact? | View flow diagrams | ARCHITECTURE_FLOWS.md |
| Get quick overview? | Read executive summary | BASELINE_SUMMARY.md |
| Find which tool to use? | Use decision tree in Flow 2 | ARCHITECTURE_FLOWS.md |
| Understand delegation? | Read Stravinsky prompt | .claude/agents/stravinsky.md |
| Learn hook system? | Read HOOKS.md | .claude/agents/HOOKS.md |
| Implement Phase 1 (hooks)? | Follow recommendations | ARCHITECTURE_MAP.md Part 10 |
| Cost optimize? | See cost tier routing | ARCHITECTURE_FLOWS.md Flow 6 |

---

## 🔍 Gap Analysis Summary

### Implemented ✅ (80%)

- ✅ 40+ MCP tools fully functional
- ✅ 8 native agents defined with prompts
- ✅ Code search (grep, AST, semantic, LSP)
- ✅ Parallel execution via Task() tool
- ✅ OAuth authentication
- ✅ 30+ Python hook implementations
- ✅ 14 slash commands

### Missing ❌ (20%)

- ❌ Native Claude Code hook scripts (.claude/agents/hooks/*.sh)
- ❌ Hook registration (.claude/settings.json)
- ❌ PreToolUse enforcement (block Read/Grep/Bash)
- ❌ PostToolUse aggregation
- ❌ Automatic delegation enforcement

### Impact of Missing Pieces

**Without hooks**:
- Orchestrator CAN delegate but doesn't have to
- No automatic enforcement
- More expensive (Sonnet does cheap work)
- Less cost-optimized

**With hooks**:
- Orchestrator MUST delegate (hard boundary)
- Automatic enforcement
- Better cost optimization (70% cheaper)
- Guaranteed parallel execution

---

## 📈 Implementation Roadmap

### Phase 1: Hook Integration (2-4 hours) ← CRITICAL
**Status**: Planned
**Files to create**:
1. `.claude/agents/hooks/pre_tool_use.sh`
2. `.claude/agents/hooks/post_tool_use.sh`
3. `.claude/settings.json` (register hooks)

**Impact**: Enables automatic delegation, cost savings, parallel execution

### Phase 2: Validation & Testing (4-6 hours)
**Status**: Pending Phase 1
**What**: Test all delegation patterns, measure savings

### Phase 3: Documentation (2-3 hours)
**Status**: Pending Phase 2
**What**: User guide, troubleshooting, examples

---

## 📍 Navigation by Use Case

### "I want to understand the architecture"
1. Start: BASELINE_SUMMARY.md (5 min)
2. Deep dive: ARCHITECTURE_MAP.md (20 min)
3. Visualize: ARCHITECTURE_FLOWS.md (10 min)

### "I need to implement Phase 1 (hooks)"
1. Understand current state: ARCHITECTURE_MAP.md Part 9-10
2. See hook flow: ARCHITECTURE_FLOWS.md Flow 5
3. Read hook docs: .claude/agents/HOOKS.md
4. Implementation guide: ARCHITECTURE_MAP.md Part 10, Phase 1

### "I want to choose which tool to use"
1. Decision tree: ARCHITECTURE_FLOWS.md Flow 2
2. Tool inventory: ARCHITECTURE_MAP.md Part 1
3. Quick reference: ARCHITECTURE_MAP.md Part 11

### "I need to optimize costs"
1. Agent tiers: ARCHITECTURE_MAP.md Part 6
2. Delegation matrix: ARCHITECTURE_FLOWS.md Flow 3
3. Cost comparison: ARCHITECTURE_FLOWS.md Flow 8

### "I want to understand agent capabilities"
1. Agent matrix: ARCHITECTURE_FLOWS.md Flow 7
2. Agent specs: ARCHITECTURE_MAP.md Part 2
3. Individual prompts: .claude/agents/*.md

---

## 🔗 Cross-Reference Map

### Key Concepts

**Delegation**:
- How it works: ARCHITECTURE_FLOWS.md Flow 1, Flow 3
- Patterns: ARCHITECTURE_MAP.md Part 5
- Orchestrator logic: .claude/agents/stravinsky.md

**Tools**:
- Inventory: ARCHITECTURE_MAP.md Part 1
- Selection: ARCHITECTURE_FLOWS.md Flow 2
- Definitions: mcp_bridge/server_tools.py

**Agents**:
- Capabilities: ARCHITECTURE_FLOWS.md Flow 7
- Specifications: ARCHITECTURE_MAP.md Part 2
- Prompts: .claude/agents/*.md

**Hooks**:
- Architecture: ARCHITECTURE_MAP.md Part 3
- Detailed docs: .claude/agents/HOOKS.md
- Integration flow: ARCHITECTURE_FLOWS.md Flow 5
- Implementation status: ARCHITECTURE_MAP.md Part 9

**Cost Optimization**:
- Cost tiers: ARCHITECTURE_MAP.md Part 6
- Routing: ARCHITECTURE_FLOWS.md Flow 6
- Comparison: ARCHITECTURE_FLOWS.md Flow 8

---

## 📝 Document Sizes & Read Times

| Document | File Size | Read Time | Best For |
|----------|-----------|-----------|----------|
| BASELINE_SUMMARY.md | ~3 KB | 5 min | Quick overview |
| ARCHITECTURE_MAP.md | ~30 KB | 20-30 min | Deep understanding |
| ARCHITECTURE_FLOWS.md | ~20 KB | 15-20 min | Visual learners |
| BASELINE_INDEX.md | ~8 KB | 5 min | Navigation |

**Total**: ~61 KB of documentation covering complete architecture baseline

---

## ✅ Verification Checklist

Use this to verify you understand the baseline:

### Understanding
- [ ] I can explain what Stravinsky does in 1 sentence
- [ ] I know the 8 agent types and their roles
- [ ] I understand the 4 search strategies
- [ ] I can explain parallel execution
- [ ] I know what's missing (hooks)

### Implementation
- [ ] I know the critical gap (PreToolUse hook)
- [ ] I understand Phase 1 requirements
- [ ] I can identify which files need changes
- [ ] I understand cost optimization impact
- [ ] I can explain why hooks are needed

### Navigation
- [ ] I can find which tool to use for a task
- [ ] I can navigate between documents
- [ ] I know where source code lives
- [ ] I understand the delegation decision matrix
- [ ] I can estimate implementation effort

---

## 🚀 Next Steps

1. **Review** this baseline documentation (1-2 hours)
2. **Understand** the gap (hooks not wired to Claude Code)
3. **Plan** Phase 1 implementation (2-4 hours of work)
4. **Execute** Phase 1 (create hook scripts + settings.json)
5. **Test** delegation patterns
6. **Measure** cost savings and performance

---

## 📞 Reference

**For questions about**:
- Architecture → ARCHITECTURE_MAP.md
- Workflows → ARCHITECTURE_FLOWS.md
- Quick answers → BASELINE_SUMMARY.md
- Navigation → BASELINE_INDEX.md (this file)

---

**This baseline is READY for implementation.**

All tools, agents, and patterns are in place. The only missing piece is hook integration (PreToolUse/PostToolUse scripts and registration), which is Phase 1 of the implementation plan.

See ARCHITECTURE_MAP.md Part 10 for detailed Phase 1 specifications.
