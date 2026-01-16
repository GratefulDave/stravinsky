u s# Stravinsky Project Context Snapshot

**Generated:** 2026-01-16

---

## Project Overview

**Stravinsky** - The Avant-Garde MCP Bridge for Claude Code

Multi-model AI orchestration with OAuth authentication for Claude Code.

---

## Key Features

- 🔐 **OAuth Authentication** - Secure browser-based auth for Google (Gemini) and OpenAI (ChatGPT)
- 🤖 **Multi-Model Support** - Seamlessly invoke Gemini and GPT models from Claude
- 🎯 **Native Subagent Orchestration** - Auto-delegating orchestrator with parallel execution (zero CLI overhead)
- 🛠️ **40 MCP Tools** - Model invocation, code search, semantic search, LSP refactoring, session management
- 🧠 **9 Specialized Native Agents** - Stravinsky (orchestrator), Research Lead, Implementation Lead, Delphi (GPT-5.2
  advisor), Dewey (documentation), Explore (code search), Frontend (Gemini 3 Pro High UI/UX), Code Reviewer, Debugger
- 🔄 **Hook-Based Delegation** - PreToolUse hooks enforce delegation patterns with hard boundaries
- 📝 **LSP Integration** - Full Language Server Protocol support with persistent servers (35x speedup)
- 🔍 **AST-Aware Search** - Structural code search and refactoring with ast-grep
- 🧠 **Semantic Code Search** - Natural language queries with local embeddings (ChromaDB + Ollama)

---

## Installation

**CRITICAL: Always use --scope user with @latest for auto-updates and Python 3.13**

```bash
# CORRECT: User-level installation with Python 3.13 and automatic updates
claude mcp add --scope user stravinsky -- uvx --python python3.13 stravinsky@latest
```

**⚠️ Python 3.13 Required**: Python 3.14+ is not supported due to chromadb → onnxruntime dependency.

---

## Authentication

### OAuth (Recommended - Primary Method)

```bash
# Login to Google (Gemini)
stravinsky-auth login gemini

# Login to OpenAI (ChatGPT Plus/Pro required)
stravinsky-auth login openai

# Check status
stravinsky-auth status
```

### API Key (Tier 3 High Quotas - Automatic Fallback)

Add to `.env`:

```bash
GEMINI_API_KEY=your_tier_3_api_key_here
```

**Rate Limit Architecture:**

1. OAuth is tried first (if configured)
2. On OAuth 429 rate limit → Automatically switch to API key (Tier 3 quotas) for 5 minutes
3. After 5-minute cooldown → Retry OAuth

---

## Git Status

**Current branch:** release/v0.4.41
**Main branch:** main
**Status:** (clean)

**Recent commits:**

- 9aca01f - fix: fix test suite failures and prepare for v0.4.55 deployment
- f276ac5 - chore: update lockfile for version 0.4.54
- ff9913c - feat: manifest-based incremental indexing for semantic search
- e2d44cc - chore: update lockfile for 0.4.53
- 90693fc - fix: bump version to 0.4.53 due to PyPI conflict

---

## Tools (47 Total)

| Category             | Tools                                                                                                                                                                                                                                |
|----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Model Invoke**     | invoke_gemini, invoke_gemini_agentic, invoke_openai (3)                                                                                                                                                                              |
| **Environment**      | get_project_context, get_system_health, stravinsky_version, system_restart, semantic_health, lsp_health (6)                                                                                                                          |
| **Background Tasks** | task_spawn, task_status, task_list (3)                                                                                                                                                                                               |
| **Agents**           | agent_spawn, agent_output, agent_cancel, agent_list, agent_progress, agent_retry (6)                                                                                                                                                 |
| **Code Search**      | ast_grep_search, ast_grep_replace, grep_search, glob_files (4)                                                                                                                                                                       |
| **Semantic**         | semantic_search, hybrid_search, semantic_index, semantic_stats, start_file_watcher, stop_file_watcher, cancel_indexing, delete_index, list_file_watchers, multi_query_search, decomposed_search, enhanced_search (12)                |
| **LSP**              | lsp_diagnostics, lsp_hover, lsp_goto_definition, lsp_find_references, lsp_document_symbols, lsp_workspace_symbols, lsp_prepare_rename, lsp_rename, lsp_code_actions, lsp_code_action_resolve, lsp_extract_refactor, lsp_servers (12) |
| **Sessions**         | session_list, session_read, session_search (3)                                                                                                                                                                                       |
| **Skills**           | skill_list, skill_get (2)                                                                                                                                                                                                            |

---

## Native Subagent Architecture

| Agent             | Model                            | Cost      | Use For                                |
|-------------------|----------------------------------|-----------|----------------------------------------|
| **stravinsky**    | Claude Sonnet 4.5 (32k thinking) | Moderate  | Auto-delegating orchestrator (primary) |
| **explore**       | Gemini 3 Flash (via MCP)         | Free      | Code search, always async              |
| **dewey**         | Gemini 3 Flash + WebSearch       | Cheap     | Documentation research, always async   |
| **code-reviewer** | Claude Sonnet (native)           | Cheap     | Quality analysis, always async         |
| **debugger**      | Claude Sonnet (native)           | Medium    | Root cause (after 2+ failures)         |
| **frontend**      | Gemini 3 Pro High (via MCP)      | Medium    | ALL visual changes (blocking)          |
| **delphi**        | GPT-5.2 Medium (via MCP)         | Expensive | Architecture (after 3+ failures)       |

### Delegation Rules (oh-my-opencode Pattern)

- **Always Async**: explore, dewey, code-reviewer (free/cheap)
- **Blocking**: debugger (2+ failures), frontend (ALL visual), delphi (3+ failures or architecture)
- **Never Work Alone**: Orchestrator blocks Read/Grep/Bash via PreToolUse hooks

---

## Project Structure

```
stravinsky/
├── mcp_bridge/           # Python MCP server
│   ├── server.py         # Entry point
│   ├── auth/             # OAuth (Google & OpenAI)
│   ├── tools/            # Model invoke, search, skills
│   ├── prompts/          # Agent system prompts
│   └── config/           # Bridge configuration
├── .claude/
│   ├── agents/           # Native subagent definitions
│   ├── commands/         # Slash commands (skills)
│   └── rules/            # Project rules
├── .mcp.json             # Claude Code config
├── pyproject.toml        # Build system
└── CLAUDE.md             # Project guide
```

---

## Key Rules

### Integration Wiring (Lesson Learned: 2026-01-11)

**Problem:** Sub-agents fail silently when tools are "wired in" but not actually usable.

**Integration Checklist:**

1. ✅ Verify invocation method (invoke_gemini_agentic for tool access)
2. ✅ Verify prerequisites (index exists, LSP running, auth configured)
3. ✅ Verify parent agent guidance (orchestrator tells when to use tools)
4. ✅ End-to-end test works

### Deployment Safety

**CRITICAL: Pre-Deployment Checklist**

```bash
# Run this BEFORE every deployment
./pre_deploy_check.sh
```

**Mandatory Checks:**

1. Import Test
2. Version Consistency (pyproject.toml and __init__.py)
3. Command Works (stravinsky --version)
4. All Tools Import
5. Tests Pass
6. Linting Clean
7. Git Clean

### PyPI Deployment Process

**Step 1: Clean Build Artifacts (MANDATORY)**

```bash
python3 -c "import shutil; from pathlib import Path; [shutil.rmtree(p) for p in [Path('dist'), Path('build')] if p.exists()]; print('✅ Cleaned')"
```

**Step 2: Version Consistency**

```bash
VERSION_TOML=$(grep -E "^version = " pyproject.toml | head -1 | cut -d'"' -f2)
VERSION_INIT=$(grep -E "^__version__ = " mcp_bridge/__init__.py | cut -d'"' -f2)
```

**Step 3: Build**

```bash
uv build
```

**Step 4: Publish**

```bash
source .env
uv publish --token "$PYPI_API_TOKEN"
```

**Step 5: Force uvx Cache Clear (MANDATORY)**

```bash
python3 -c "import shutil; from pathlib import Path; cache = Path.home() / '.cache' / 'uv'; shutil.rmtree(cache, ignore_errors=True); print('✅ Cleared uvx cache')"
```

---

## Global Instructions

**From ~/.claude/CLAUDE.md:**

- ALWAYS use `uv pip` to run files and `uv add` to add packages
- ALWAYS determine if task is complex - if so, create a task list

---

## Slash Commands

- `/strav` - Task Orchestrator & Planner
- `/delphi` - Architecture & Debug Advisor
- `/dewey` - Documentation & Research
- `/get-context` - Refresh Git/Rules/Todo context
- `/health` - Comprehensive system check

---

## ULTRATHINK / ULTRAWORK

- **ULTRATHINK**: Engage exhaustive deep reasoning with extended thinking budget (32k tokens)
- **ULTRAWORK**: Maximum parallel execution - spawn all async agents immediately

---

## Parallel Execution (MANDATORY)

For ANY task with 2+ independent steps:

1. **Immediately use agent_spawn** for each independent component
2. Fire all agents simultaneously
3. **CRITICAL**: After spawning, automatically collect results in THE SAME RESPONSE using
   `agent_output(task_id, block=True)`

Example pattern:

```python
# Spawn all agents (parallel)
task_id_1 = agent_spawn(...)
task_id_2 = agent_spawn(...)
task_id_3 = agent_spawn(...)

# Collect ALL results in same response (blocks until complete)
result_1 = agent_output(task_id_1, block=True)
result_2 = agent_output(task_id_2, block=True)
result_3 = agent_output(task_id_3, block=True)

# Now synthesize the results
```

---

**End of Context Snapshot**
