# Semantic Indexing in Stravinsky - Current State Analysis

## Executive Summary

Stravinsky has a **fully implemented semantic search and indexing system**, but **auto-indexing is NOT currently active**. The system is in place, ready to use, but requires manual invocation. This report documents the current state and available options for automatic indexing.

---

## 1. Current Semantic Search Architecture

### 1.1 Core Components

Located in: `/Users/davidandrews/PycharmProjects/stravinsky/mcp_bridge/tools/semantic_search.py` (1754 lines)

**Key Classes:**

1. **BaseEmbeddingProvider** (abstract)
   - OllamaProvider (local, free) - nomic-embed-text (768 dims)
   - MxbaiProvider (local, free) - mxbai-embed-large (1024 dims, better for code)
   - GeminiProvider (cloud, OAuth) - gemini-embedding-001 (768-3072 dims)
   - OpenAIProvider (cloud, OAuth) - text-embedding-3-small (1536 dims)

2. **CodebaseVectorStore** (main class)
   - Storage: `~/.stravinsky/vectordb/<project_hash>_<provider>/`
   - Uses ChromaDB for persistent storage
   - File locking for single-process access (prevents corruption)
   - AST-aware chunking for Python files
   - Smart metadata extraction (decorators, async flags, base classes, etc.)

### 1.2 Available Search Functions

| Function | Purpose | Auto-triggered |
|----------|---------|-----------------|
| `semantic_search()` | Natural language query search | No |
| `hybrid_search()` | Semantic + AST pattern matching | No |
| `semantic_index()` | Manual indexing (full/incremental) | No |
| `semantic_stats()` | Check index statistics | No |
| `semantic_health()` | Verify provider availability | No |
| `multi_query_search()` | Query expansion with LLM | No |
| `decomposed_search()` | Complex query decomposition | No |
| `enhanced_search()` | Unified search with auto-mode selection | No |

### 1.3 Chunking Strategy

**Python Files (AST-aware):**
- Respects function/class boundaries
- Extracts docstrings, decorators, parameters, return types
- Creates separate chunks for classes and methods
- Falls back to line-based if AST parsing fails
- Includes descriptive headers with file:line info

**Other Languages (line-based):**
- CHUNK_SIZE: 50 lines
- CHUNK_OVERLAP: 10 lines
- Fallback for all non-Python files

**Indexable Extensions:**
`.py, .js, .ts, .tsx, .jsx, .go, .rs, .rb, .java, .c, .cpp, .h, .hpp, .cs, .swift, .kt, .scala, .vue, .svelte, .md, .txt, .yaml, .yml, .json, .toml`

**Skipped Directories:**
`node_modules, .git, __pycache__, .venv, venv, env, dist, build, .next, .nuxt, target, .tox, .pytest_cache, .mypy_cache, .ruff_cache, coverage, .stravinsky`

---

## 2. Current Auto-Indexing State

### 2.1 No Auto-Indexing Currently Active

**Findings:**
- ✅ Semantic index tools registered in server.py (lines 498-551)
- ✅ Index_codebase() function fully implemented
- ❌ No startup hooks trigger automatic indexing
- ❌ No session-based auto-indexing
- ❌ No file watcher for incremental updates
- ❌ No lifecycle hooks in MCP server startup

### 2.2 Server Startup Flow

**File:** `mcp_bridge/server.py` (lines 628-662)

```python
async def async_main():
    # Step 1: Initialize hooks
    from .hooks import initialize_hooks
    initialize_hooks()
    
    # Step 2: Start background token refresh
    from .auth.token_refresh import background_token_refresh
    asyncio.create_task(background_token_refresh(get_token_store()))
    
    # Step 3: Run MCP server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(...)
```

**Hook Opportunities:**
- Line 634: `initialize_hooks()` - Could trigger semantic indexing
- Line 642: Background token refresh scheduler - Model for background tasks
- Line 662: Shutdown hook - Could persist index state

---

## 3. Hook System Architecture

### 3.1 Hook Manager

**Location:** `mcp_bridge/hooks/manager.py`

**Hook Types Available:**
1. `pre_tool_call` - Before tool execution
2. `post_tool_call` - After tool execution
3. `pre_model_invoke` - Before model calls
4. `session_idle` - When session becomes idle
5. `pre_compact` - Before context compaction

### 3.2 Session Idle Hook Pattern

**Location:** `mcp_bridge/hooks/session_idle.py`

Currently used for: **TODO continuation prompts**

```python
async def session_idle_hook(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Detects idle sessions with pending todos.
    Injects continuation prompts.
    """
```

**Key Insights:**
- Hooks execute at runtime in MCP server context
- Have access to session state
- Can perform async operations (e.g., API calls)
- Can modify/inject prompts
- ✅ Could be adapted for semantic indexing

---

## 4. Three Options for Automatic Indexing

### Option A: Server Startup Indexing (Simplest)

**Trigger:** MCP server initialization  
**Location:** `mcp_bridge/server.py:initialize_hooks()`

**Pros:**
- ✅ Simple to implement
- ✅ Runs once per session start
- ✅ Can be made async/background
- ✅ No file watchers needed

**Cons:**
- ❌ Only on server restart
- ❌ Delays server startup if not async
- ❌ May index unchanged files

**Implementation:**
```python
async def async_main():
    try:
        from .hooks import initialize_hooks
        initialize_hooks()
    except Exception as e:
        logger.error(f"Failed to initialize hooks: {e}")
    
    # NEW: Spawn background indexing task
    try:
        from .tools.semantic_search import index_codebase
        asyncio.create_task(index_codebase(project_path="."))
        logger.info("Background semantic indexing started")
    except Exception as e:
        logger.warning(f"Failed to start semantic indexing: {e}")
```

---

### Option B: Session-Based Auto-Indexing (Medium Complexity)

**Trigger:** First session interaction  
**Location:** New hook in `mcp_bridge/hooks/`

**Pros:**
- ✅ Lazy loading - only when needed
- ✅ Doesn't delay server startup
- ✅ Works per-project
- ✅ Can detect changes since last index

**Cons:**
- ❌ First query might be slow
- ❌ Requires session tracking
- ❌ Needs persistence across sessions

**Implementation:**
```python
# File: mcp_bridge/hooks/semantic_auto_index.py
async def pre_model_invoke_hook(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Auto-index on first semantic search query.
    Checks if index exists, creates if missing.
    """
    # Check if semantic_search in params
    # If not indexed yet, trigger index_codebase()
```

---

### Option C: Scheduled Background Indexing (Most Robust)

**Trigger:** Background scheduler task  
**Location:** Similar to token refresh scheduler

**Pros:**
- ✅ Incremental updates
- ✅ No UI blocking
- ✅ Can run on interval
- ✅ Detects file changes

**Cons:**
- ❌ More complex
- ❌ Resource intensive
- ❌ Requires file stat tracking

**Implementation:**
```python
# File: mcp_bridge/background_indexing.py
async def background_semantic_indexing_loop():
    """
    Periodically index the codebase.
    Incremental by default (only new/changed files).
    """
    while True:
        try:
            await index_codebase(
                project_path=".",
                force=False  # Incremental
            )
            await asyncio.sleep(300)  # Every 5 minutes
        except Exception as e:
            logger.warning(f"Background indexing failed: {e}")
```

---

## 5. Current Tool Integration Points

### 5.1 Tools Already Exposed in MCP

From `mcp_bridge/server.py`:

```python
# Line 498-551
elif name == "semantic_index":
    result_content = await index_codebase(
        project_path=arguments.get("project_path", "."),
        force=arguments.get("force", False),
        provider=arguments.get("provider", "ollama"),
    )
```

**Status:** ✅ Ready to use via MCP tool call
**Manual Trigger:** User explicitly calls `semantic_index` tool

### 5.2 Search Tools Available

```python
elif name == "semantic_search":
    result_content = await semantic_search(...)

elif name == "enhanced_search":
    result_content = await enhanced_search(
        query=arguments["query"],
        mode=arguments.get("mode", "auto"),
        ...
    )
```

---

## 6. Recommendations

### For Immediate Use (Current State)

Users should:
1. Install Ollama with `ollama pull nomic-embed-text`
2. Run server startup
3. Manually call `semantic_index` once per project
4. Then use `semantic_search`, `enhanced_search`, or `hybrid_search`

### For Auto-Indexing Enhancement

**Recommended approach: Option A (Startup Indexing)**

```
Rationale:
- Simplest to implement
- Non-blocking (async/background)
- Clear semantics (index at init time)
- No file watchers needed
- Matches current token refresh pattern
```

**Implementation would require:**
1. Add background indexing task to `async_main()`
2. Make it configurable (env var to enable/disable)
3. Add progress logging to stderr
4. Handle provider availability gracefully

### For Advanced Users

**Option C (Scheduled) would require:**
1. File modification time tracking
2. Incremental re-indexing logic (already exists)
3. Background task scheduler
4. Configuration for index frequency

---

## 7. Infrastructure Already In Place

### 7.1 What Exists and Works

✅ **Embedding Providers:**
- Local (Ollama): nomic-embed-text, mxbai-embed-large
- Cloud (OAuth): Gemini, OpenAI

✅ **Vector Storage:**
- ChromaDB with persistent storage
- File-based locking for concurrency
- Per-project, per-provider isolation

✅ **Chunking:**
- AST-aware for Python
- Language-aware metadata
- Smart filtering (skip node_modules, .git, etc.)

✅ **Search Capabilities:**
- Basic semantic search
- Hybrid search (semantic + AST)
- Multi-query expansion
- Query decomposition
- Advanced filtering (language, node type, async, decorators)

✅ **Health Checks:**
- Provider availability checking
- Vector DB status monitoring
- Statistics and reporting

### 7.2 What's Missing for Auto-Indexing

- [ ] Server startup trigger
- [ ] File watcher for incremental updates
- [ ] Configuration options (enable/disable)
- [ ] Progress UI integration
- [ ] Persistent index state tracking
- [ ] Error recovery mechanisms

---

## 8. File Locations Summary

```
Semantic Search Implementation:
  /Users/davidandrews/PycharmProjects/stravinsky/
  ├── mcp_bridge/
  │   ├── server.py (lines 498-551: tool dispatch)
  │   ├── tools/
  │   │   ├── semantic_search.py (main implementation)
  │   │   └── code_search.py (supporting functions)
  │   ├── hooks/
  │   │   ├── manager.py (hook orchestration)
  │   │   ├── session_idle.py (idle detection pattern)
  │   │   └── ... (other hooks)
  │   └── auth/
  │       └── token_store.py (OAuth token management)
  └── .claude/
      ├── commands/
      │   └── ... (slash commands for manual invocation)
      └── hooks/
          └── ... (Claude Code hooks, external)
```

---

## 9. Next Steps

To enable automatic indexing:

1. **Short term:** Document manual indexing process
   - Create skill/command for easy triggering
   - Add help documentation

2. **Medium term:** Implement Option A
   - Add server startup indexing
   - Make it configurable

3. **Long term:** Implement Option C
   - Add scheduled indexing
   - File change detection
   - Incremental updates

---

## Appendix: Quick Reference

### Manual Indexing (Current State)

**Claude Code Tool Call:**
```
semantic_index(project_path=".", force=false, provider="ollama")
```

**Python API:**
```python
from mcp_bridge.tools.semantic_search import index_codebase
await index_codebase(project_path=".", force=False, provider="ollama")
```

### Search Variants

```
semantic_search(query, project_path, n_results, language, node_type, provider)
enhanced_search(query, project_path, n_results, mode="auto", language, node_type, provider)
hybrid_search(query, pattern, project_path, n_results, language, provider)
multi_query_search(query, project_path, n_results, num_expansions, language, node_type, provider)
decomposed_search(query, project_path, n_results, language, node_type, provider)
```

### Check Index Status

```python
await semantic_stats(project_path=".", provider="ollama")
await semantic_health(project_path=".", provider="ollama")
```

