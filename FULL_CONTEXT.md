# Stravinsky - Complete Project Context

**Generated:** 2026-01-16
**Branch:** release/v0.4.41
**Status:** 1 file modified (context-snapshot.md)

---

## 🌿 Git Context

**Current Branch:** `release/v0.4.41`
**Main Branch:** `main`
**Status:** 1 files modified (staged/unstaged)

**Recent Commits:**
- `9aca01f` - fix: fix test suite failures and prepare for v0.4.55 deployment
- `f276ac5` - chore: update lockfile for version 0.4.54
- `ff9913c` - feat: manifest-based incremental indexing for semantic search
- `e2d44cc` - chore: update lockfile for 0.4.53
- `90693fc` - fix: bump version to 0.4.53 due to PyPI conflict

---

## 📜 Local Project Rules

### Rule 1: Integration Wiring

**Lesson Learned:** Tool-Agent Integration (2026-01-11)

**Problem:** Sub-agents fail silently when tools are "wired in" but not actually usable.

**Root Cause:** Adding a tool to an agent's tool list doesn't guarantee the agent can USE it.

#### Integration Checklist (MANDATORY)

When integrating Tool X into Agent Y:

**1. Verify Invocation Method**

| Agent Type | Invocation Method | Tool Access |
|------------|-------------------|-------------|
| `invoke_gemini` | Simple completion | NO tool calling |
| `invoke_gemini_agentic` | Agentic loop | YES - full tool access |
| `invoke_openai` | Direct call | Depends on model |

**CRITICAL:** If agent needs to call tools, it MUST use the `_agentic` variant.

```python
# WRONG: Agent can't use tools
invoke_gemini(prompt="Find auth code", model="gemini-3-flash")

# RIGHT: Agent can call semantic_search, grep, etc.
invoke_gemini_agentic(
    prompt="Find auth code using semantic_search",
    model="gemini-3-flash",
    max_iterations=5
)
```

**2. Verify Prerequisites**

| Tool | Prerequisite | Check |
|------|--------------|-------|
| `semantic_search` | Index must exist | Run `semantic_index()` first |
| `lsp_*` | LSP server must be running | Check `lsp_servers()` |
| `invoke_*` | Auth must be configured | Run `stravinsky-auth status` |

**3. Verify Parent Agent Guidance**

| Level | Responsibility |
|-------|----------------|
| **Orchestrator** (stravinsky) | Tell sub-agents WHEN to use which tools |
| **Coordinator** (research-lead) | Tell explore/dewey HOW to use tools for query types |
| **Worker** (explore) | Actually CALL the tools |

**4. Verification Pattern**

```
Step 1: Tool is in agent's tool list      ✓
Step 2: Agent uses correct invocation     ✓
Step 3: Prerequisites are met/checked     ✓
Step 4: Parent agents guide usage         ✓
Step 5: End-to-end test works             ✓
```

**Rule:** When adding a tool to an agent, verify the FULL integration chain. Silent failures waste hours of debugging. Fail early, fail loudly.

---

### Rule 2: Deployment Safety

**CRITICAL: Pre-Deployment Checklist**

**NEVER deploy code to PyPI without passing ALL checks:**

```bash
# Run this BEFORE every deployment
./pre_deploy_check.sh
```

#### Mandatory Checks (BLOCKING)

1. **Import Test** - `python3 -c "import mcp_bridge.server"` must succeed
2. **Version Consistency** - pyproject.toml and __init__.py versions must match
3. **Command Works** - `stravinsky --version` must succeed
4. **All Tools Import** - Every tool module must import without errors
5. **Tests Pass** - If tests exist, `pytest` must pass
6. **Linting Clean** - `ruff check` must have zero errors
7. **Git Clean** - No uncommitted changes

#### Why This Matters

**Recent failures prevented by these checks:**
- **v0.4.30 (2026-01-09)**: `NameError: name 'logger' is not defined` - would be caught by import test
- Future: Type errors, missing imports, broken commands all caught before PyPI

#### Consequences of Skipping Checks

- Broken installations for all users globally
- Version number burned (can't re-upload to PyPI)
- Force version bump to fix
- User trust eroded
- Support burden increased

**Rule:** You MUST run `./pre_deploy_check.sh` before EVERY deployment. NO EXCEPTIONS.

---

### Rule 3: PyPI Deployment

**⚠️ CRITICAL REMINDER: ALWAYS CLEAN BEFORE BUILDING**

**The #1 deployment error:** Forgetting to clean dist/ before building

```bash
# ALWAYS RUN THIS FIRST (use Python if hooks block rm):
python3 -c "import shutil; from pathlib import Path; [shutil.rmtree(p) for p in [Path('dist'), Path('build')] if p.exists()]; print('✅ Cleaned')"
```

**Why:** PyPI rejects if dist/ contains old version files (e.g., 0.4.9.tar.gz when publishing 0.4.10)

#### Version Management

1. **ALWAYS check PyPI first before bumping version:**
   ```bash
   pip index versions stravinsky 2>&1 | head -20
   ```

2. **Version must be consistent** across:
   - `pyproject.toml` (line ~5): `version = "X.Y.Z"`
   - `mcp_bridge/__init__.py`: `__version__ = "X.Y.Z"`

3. **Version bumping strategy:**
   - Patch (X.Y.Z+1): Bug fixes, documentation updates
   - Minor (X.Y+1.0): New features, agent improvements, MCP tool additions
   - Major (X+1.0.0): Breaking changes to API or architecture

4. **⚠️ CRITICAL**: PyPI does NOT allow re-uploading the same version

#### CRITICAL RULES

1. **Pin Python upper bounds when core dependencies require it**
   - ✅ CORRECT: `requires-python = ">=3.11,<3.14"` (chromadb/onnxruntime constraint)
   - ❌ WRONG: `requires-python = ">=3.11"` (allows unsupported versions)

2. **ALWAYS install globally with @latest for auto-updates**
   - ✅ CORRECT: `claude mcp add --global stravinsky -- uvx stravinsky@latest`
   - ❌ WRONG: `claude mcp add stravinsky -- uvx stravinsky` (no @latest)

#### Deployment Process

**Step 1: Clean Build Artifacts (MANDATORY)**

```bash
python3 -c "import shutil; from pathlib import Path; [shutil.rmtree(p) for p in [Path('dist'), Path('build')] if p.exists()]; print('✅ Cleaned dist/ and build/')"
```

**Step 2: Verify Version Consistency**

```bash
VERSION_TOML=$(grep -E "^version = " pyproject.toml | head -1 | cut -d'"' -f2)
VERSION_INIT=$(grep -E "^__version__ = " mcp_bridge/__init__.py | cut -d'"' -f2)

if [ "$VERSION_TOML" != "$VERSION_INIT" ]; then
  echo "❌ Version mismatch"
  exit 1
fi
```

**Step 3: Build**

```bash
uv build
ls -lh dist/  # Verify correct version
```

**Step 4: Publish**

```bash
source .env
uv publish --token "$PYPI_API_TOKEN"
```

**Step 5: Git Tag and Push**

```bash
VERSION=$(grep -E "^version = " pyproject.toml | head -1 | cut -d'"' -f2)
git tag -a "v$VERSION" -m "chore: release v$VERSION"
git push origin main --tags
```

**Step 6: Force uvx Cache Clear (MANDATORY)**

```bash
python3 -c "import shutil; from pathlib import Path; cache = Path.home() / '.cache' / 'uv'; shutil.rmtree(cache, ignore_errors=True); print('✅ Cleared uvx cache')"
```

---

## 📝 Pending Todos (Top 20)

From `BASELINE_INDEX.md`:
- [ ] I can explain what Stravinsky does in 1 sentence
- [ ] I know the 8 agent types and their roles
- [ ] I understand the 4 search strategies
- [ ] I can explain parallel execution
- [ ] I know what's missing (hooks)
- [ ] I know the critical gap (PreToolUse hook)
- [ ] I understand Phase 1 requirements
- [ ] I can identify which files need changes
- [ ] I understand cost optimization impact
- [ ] I can explain why hooks are needed
- [ ] I can find which tool to use for a task
- [ ] I can navigate between documents
- [ ] I know where source code lives
- [ ] I understand the delegation decision matrix
- [ ] I can estimate implementation effort

From `ARCHITECTURE_MAP.md`:
- [ ] **PreToolUse** hook (`.claude/agents/hooks/pre_tool_use.sh`) - Block direct tools, force delegation
- [ ] **PostToolUse** hook (`.claude/agents/hooks/post_tool_use.sh`) - Aggregate specialist results
- [ ] **UserPromptSubmit** hook (`.claude/agents/hooks/user_prompt_submit.sh`) - Context injection
- [ ] **PreCompact** hook (`.claude/agents/hooks/pre_compact.sh`) - Save state before compression
- [ ] **SessionEnd** hook (`.claude/agents/hooks/session_end.sh`) - Cleanup, final reporting

---

## 🛠️ Project Overview

**Stravinsky** - The Avant-Garde MCP Bridge for Claude Code

Multi-model AI orchestration with OAuth authentication for Claude Code.

### Key Features

- 🔐 **OAuth Authentication** - Secure browser-based auth for Google (Gemini) and OpenAI (ChatGPT)
- 🤖 **Multi-Model Support** - Seamlessly invoke Gemini and GPT models from Claude
- 🎯 **Native Subagent Orchestration** - Auto-delegating orchestrator with parallel execution
- 🛠️ **47 MCP Tools** - Model invocation, code search, semantic search, LSP refactoring, session management
- 🧠 **9 Specialized Native Agents** - Stravinsky, Research Lead, Implementation Lead, Delphi, Dewey, Explore, Frontend, Code Reviewer, Debugger
- 🔄 **Hook-Based Delegation** - PreToolUse hooks enforce delegation patterns
- 📝 **LSP Integration** - Full Language Server Protocol support (35x speedup)
- 🔍 **AST-Aware Search** - Structural code search and refactoring with ast-grep
- 🧠 **Semantic Code Search** - Natural language queries with local embeddings (ChromaDB + Ollama)

---

## 📦 Installation

**CRITICAL: Always use --scope user with @latest for auto-updates and Python 3.13**

```bash
# CORRECT: User-level installation with Python 3.13 and automatic updates
claude mcp add --scope user stravinsky -- uvx --python python3.13 stravinsky@latest

# Why this matters:
# - --scope user: Works across all projects (stored in ~/.claude.json)
# - @latest: Auto-checks PyPI on every Claude restart (no stale cache)
# - --python python3.13: Required due to chromadb → onnxruntime dependency
```

**⚠️ Python 3.13 Required:** Python 3.14+ is not supported due to chromadb → onnxruntime dependency.

---

## 🔐 Authentication

### Option 1: OAuth (Recommended - Primary Method)

```bash
# Login to Google (Gemini)
stravinsky-auth login gemini

# Login to OpenAI (ChatGPT Plus/Pro required)
stravinsky-auth login openai

# Check status
stravinsky-auth status
```

**Rate Limit Architecture:**
1. OAuth is tried first (if configured)
2. On OAuth 429 rate limit → Automatically switch to API key (Tier 3 quotas) for 5 minutes
3. After 5-minute cooldown → Retry OAuth

### Option 2: API Key (Tier 3 High Quotas - Automatic Fallback)

Add to `.env`:
```bash
GEMINI_API_KEY=your_tier_3_api_key_here
```

**Get your API key:** Visit [Google AI Studio](https://aistudio.google.com/app/apikey)

---

## 🤖 Native Subagent Architecture

| Agent | Model | Cost | Use For |
|-------|-------|------|---------|
| **stravinsky** | Claude Sonnet 4.5 (32k thinking) | Moderate | Auto-delegating orchestrator (primary) |
| **explore** | Gemini 3 Flash (via MCP) | Free | Code search, always async |
| **dewey** | Gemini 3 Flash + WebSearch | Cheap | Documentation research, always async |
| **code-reviewer** | Claude Sonnet (native) | Cheap | Quality analysis, always async |
| **debugger** | Claude Sonnet (native) | Medium | Root cause (after 2+ failures) |
| **frontend** | Gemini 3 Pro High (via MCP) | Medium | ALL visual changes (blocking) |
| **delphi** | GPT-5.2 Medium (via MCP) | Expensive | Architecture (after 3+ failures) |

### Delegation Rules (oh-my-opencode Pattern)

- **Always Async**: explore, dewey, code-reviewer (free/cheap)
- **Blocking**: debugger (2+ failures), frontend (ALL visual), delphi (3+ failures or architecture)
- **Never Work Alone**: Orchestrator blocks Read/Grep/Bash via PreToolUse hooks

---

## 🛠️ Tools (47 Total)

| Category | Tools |
|----------|-------|
| **Model Invoke** | invoke_gemini, invoke_gemini_agentic, invoke_openai (3) |
| **Environment** | get_project_context, get_system_health, stravinsky_version, system_restart, semantic_health, lsp_health (6) |
| **Background Tasks** | task_spawn, task_status, task_list (3) |
| **Agents** | agent_spawn, agent_output, agent_cancel, agent_list, agent_progress, agent_retry (6) |
| **Code Search** | ast_grep_search, ast_grep_replace, grep_search, glob_files (4) |
| **Semantic** | semantic_search, hybrid_search, semantic_index, semantic_stats, start_file_watcher, stop_file_watcher, cancel_indexing, delete_index, list_file_watchers, multi_query_search, decomposed_search, enhanced_search (12) |
| **LSP** | lsp_diagnostics, lsp_hover, lsp_goto_definition, lsp_find_references, lsp_document_symbols, lsp_workspace_symbols, lsp_prepare_rename, lsp_rename, lsp_code_actions, lsp_code_action_resolve, lsp_extract_refactor, lsp_servers (12) |
| **Sessions** | session_list, session_read, session_search (3) |
| **Skills** | skill_list, skill_get (2) |

---

## 📂 Project Structure

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

## 🎯 Slash Commands (Skills)

- `/strav` - Task Orchestrator & Planner
- `/delphi` - Architecture & Debug Advisor
- `/dewey` - Documentation & Research
- `/get-context` - Refresh Git/Rules/Todo context
- `/health` - Comprehensive system check

---

## 🚀 Parallel Execution (MANDATORY)

For ANY task with 2+ independent steps:

1. **Immediately use agent_spawn** for each independent component
2. Fire all agents simultaneously
3. **CRITICAL**: After spawning, automatically collect results in THE SAME RESPONSE using `agent_output(task_id, block=True)`

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

## 🧠 ULTRATHINK / ULTRAWORK

- **ULTRATHINK**: Engage exhaustive deep reasoning with extended thinking budget (32k tokens)
- **ULTRAWORK**: Maximum parallel execution - spawn all async agents immediately

---

## 📚 Global Instructions

**From ~/.claude/CLAUDE.md:**
- ALWAYS use `uv pip` to run files and `uv add` to add packages
- ALWAYS determine if task is complex - if so, create a task list

---

**End of Full Context Snapshot**
