# Track Specification: Stravinsky Orchestration & Semantic Search Improvements

## Overview
This track implements critical improvements to the Stravinsky MCP bridge focusing on:
1. **Intelligent Semantic Search** - Auto-detection of indexes, automatic file watcher management
2. **Stronger TODO Enforcement** - Prevent premature completion when todos remain pending
3. **Clean Agent Output** - Concise status updates instead of verbose logging
4. **Delegation Enforcement** - Prevent Claude from bypassing agent spawning
5. **New Quality Agents** - Momus (quality gate) and Comment-Checker

## Core Components

### 1. Smart Semantic Search System
**Current State:**
- ✅ Semantic search implemented with ChromaDB
- ✅ File watcher available but requires manual start
- ✅ Index stats and deletion tools exist
- ❌ No automatic index checking before search
- ❌ File watcher not auto-started when index exists
- ❌ No file watcher cleanup on Claude Code exit

**Improvements:**
- Auto-check if index exists before search
- Prompt user Y/N to create index if missing
- Auto-start file watcher when index exists
- Auto-stop file watcher on Claude Code process exit
- Make it fully automatic and zero-config for users

### 2. Reinforced TODO Enforcement
**Current State:**
- ✅ `todo_enforcer.py` hook exists
- ✅ Detects pending todos in prompt
- ❌ Enforcement is too weak - agents still skip todos
- ❌ No verification that todos were actually completed

**Improvements:**
- Strengthen enforcement with blocking mechanisms
- Verify completion (use Read/Grep to validate claims)
- Add "Subagents LIE" protocol - never trust without verification
- Inject stricter continuation reminders
- Fail fast when agents claim completion without evidence

### 3. Clean Output Formatting
**Current State:**
- ❌ Agent spawn outputs 500+ char verbose prompts
- ❌ Walls of debug text obscure actual progress

**Desired:**
```bash
✓ explore:gemini-3-flash → agent_a7246077
✓ delphi:gpt-5.2 → agent_2b8d5c07
⏳ agent_a7246077 running (15s)...
✅ agent_a7246077 completed (42s) - Found 3 auth files
```

### 4. Delegation Protocol Enforcement
**Current State:**
- ❌ Claude often uses Write/Edit directly instead of spawning agents
- ❌ No mandatory parameters for agent_spawn
- ❌ Workers can spawn orchestrators (recursion risk)

**Improvements:**
- Add required params: `delegation_reason`, `expected_outcome`, `required_tools`
- Implement agent type blocking (workers cannot spawn orchestrators)
- Add 7-section delegation structure from OMO

### 5. New Quality Agents
**Missing Agents:**
- **Momus** - Quality gate/validation agent (validates work before marking complete)
- **Comment-Checker** - Code documentation validator (user requested, HIGH priority)

**Note:** Project already has `delphi` (strategic advisor) and `dewey` (research librarian).

## Technical Requirements

### Runtime & Dependencies
- **Python:** 3.11-3.13 (ChromaDB compatible)
- **Dependencies:** Already installed (chromadb, watchdog, rich)
- **MCP Tools:** Extend existing tool registration in `mcp_bridge/server.py`

### File Structure
```
mcp_bridge/
├── tools/
│   ├── semantic_search.py         # MODIFY: Add auto-index check
│   └── agent_manager.py           # MODIFY: Add delegation enforcement
├── hooks/
│   └── todo_enforcer.py           # MODIFY: Strengthen verification
├── .claude/
│   └── agents/
│       ├── momus.md               # CREATE: Quality gate agent
│       └── comment_checker.md     # CREATE: Documentation validator
└── server.py                      # MODIFY: Register new tools
```

## Success Criteria

### Phase 1: Smart Semantic Search
- [ ] `semantic_search()` auto-checks if index exists
- [ ] If no index: prompts user Y/N to create via interactive CLI
- [ ] If index exists: auto-starts file watcher
- [ ] File watcher auto-stops when Claude Code exits (atexit hook)
- [ ] Zero-config experience for users

### Phase 2: TODO Enforcement
- [ ] Todo enforcer rejects completion claims without evidence
- [ ] Verification protocol: Read files to confirm claims
- [ ] Stricter continuation reminders (no escape until todos done)
- [ ] Agent output includes evidence references (file:line format)

### Phase 3: Clean Output
- [ ] Agent spawn returns: `✓ agent_type:model → task_id` (under 100 chars)
- [ ] Progress notifications every 10s: `⏳ agent_id running (Xs)...`
- [ ] Completion summary: `✅ agent_id (Xs) - One sentence result`
- [ ] Configurable output mode (clean, verbose, silent)

### Phase 4: Delegation Enforcement
- [ ] `agent_spawn()` requires: delegation_reason, expected_outcome, required_tools
- [ ] Worker agents blocked from spawning orchestrators
- [ ] Stravinsky system prompt enforces 7-section delegation structure
- [ ] Validation errors fail fast with clear messages

### Phase 5: New Agents
- [ ] Momus agent created with validation checklist
- [ ] Comment-Checker agent created with documentation criteria
- [ ] Both agents registered in MCP server
- [ ] Integration tests pass for new agents

## Architecture Decisions

### Semantic Search Auto-Index Flow
```
User calls semantic_search("find auth logic")
     ↓
Check if index exists (collection.count() > 0)
     ↓
  No index found
     ↓
Print: "⚠️ No semantic index found. Create one? (Y/n)"
     ↓
User input via stdin (blocking)
     ↓
If Y: Run semantic_index() → Start file_watcher → Continue search
If n: Return "Index required. Run semantic_index() manually."
```

### File Watcher Lifecycle
```
semantic_index() completes
     ↓
Auto-start file_watcher (debounce=2s)
     ↓
Register atexit cleanup handler
     ↓
Claude Code process exits
     ↓
atexit calls stop_file_watcher()
     ↓
Watcher thread gracefully stops
```

### TODO Verification Protocol
```
Agent claims: "Created file src/auth.ts"
     ↓
Todo enforcer intercepts completion
     ↓
Verification: Read("src/auth.ts")
     ↓
File exists + contains expected code?
  YES → Mark todo completed
  NO  → Reject with: "Evidence missing - file not found or empty"
```

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Blocking user input breaks automation | Add timeout (30s), default to "n" if no response |
| File watcher crashes on startup | Wrap in try/except, log error, continue without watcher |
| Todo verification too strict | Allow "skip_verification: true" flag for edge cases |
| Output mode breaks existing workflows | Default to current verbose mode, opt-in to clean mode |
| New agents conflict with existing | Use unique agent type names, test integration thoroughly |

## Dependencies on Existing Features

**Relies on:**
- ✅ `semantic_index()` - Already implemented
- ✅ `start_file_watcher()` - Already implemented
- ✅ `semantic_stats()` - Already implemented
- ✅ `agent_spawn()` - Already implemented
- ✅ `todo_enforcer` hook - Already implemented

**Extends:**
- `semantic_search()` - Add index check + user prompt
- `agent_spawn()` - Add required parameters
- `todo_enforcer` - Add verification logic
- MCP server - Register new tools and agents

## Timeline Estimate
- **Phase 1 (Semantic Search):** 4-6 hours
- **Phase 2 (TODO Enforcement):** 3-4 hours
- **Phase 3 (Clean Output):** 2-3 hours
- **Phase 4 (Delegation):** 4-5 hours
- **Phase 5 (New Agents):** 3-4 hours
- **Total:** 16-22 hours

## Out of Scope
- ❌ OpenCode MCP bridge (separate project: claude-cli-conduit)
- ❌ Sisyphus-Junior implementation worker pattern (future enhancement)
- ❌ Multi-model routing changes (already implemented)
- ❌ Git diff rendering improvements (deferred to claude-cli-conduit)
