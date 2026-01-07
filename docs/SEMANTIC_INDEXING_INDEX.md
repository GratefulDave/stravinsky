# Semantic Indexing Documentation Index

This directory contains comprehensive documentation on Stravinsky's semantic search and indexing system.

## Documents

### 1. semantic_indexing_quick_start.md (307 lines)
**For:** Users wanting to get started immediately
**Contains:**
- Current status overview
- 3-step getting started guide
- Provider comparison table
- Troubleshooting guide
- Advanced usage patterns
- Ideas for enhancement

**Read this if:** You want to understand and use semantic search NOW

### 2. semantic_indexing_analysis.md (434 lines)
**For:** Architects and implementers
**Contains:**
- Executive summary
- Complete system architecture (Section 1-3)
- Three options for auto-indexing (Section 4, detailed)
- Current tool integration points (Section 5)
- Recommendations for implementation (Section 6)
- Complete infrastructure inventory (Section 7)
- File location reference (Section 8)
- Next steps roadmap (Section 9)

**Read this if:** You want to understand the ENTIRE system or implement features

## Quick Decision Tree

### "I want to use semantic search right now"
→ Read: **semantic_indexing_quick_start.md** (sections 1-3)
→ Then: Follow the 3-step getting started guide

### "I want to understand the current system"
→ Read: **semantic_indexing_analysis.md** (sections 1-3)
→ 15 minutes for overview

### "I want to implement auto-indexing"
→ Read: **semantic_indexing_analysis.md** (section 4)
→ Sections explain all 3 options with pros/cons
→ Code examples provided

### "I'm getting an error"
→ Read: **semantic_indexing_quick_start.md** (Troubleshooting section)
→ Most common issues covered

### "I want to use advanced features"
→ Read: **semantic_indexing_quick_start.md** (Advanced Usage)
→ Filtering, custom chunking, etc.

## System Overview

```
┌─────────────────────────────────────────────────┐
│  Stravinsky Semantic Search System              │
├─────────────────────────────────────────────────┤
│                                                 │
│  Embedding Providers                            │
│  ├─ Ollama (local, free)                        │
│  │  ├─ nomic-embed-text                         │
│  │  └─ mxbai-embed-large (RECOMMENDED)          │
│  ├─ Gemini (cloud, OAuth)                       │
│  └─ OpenAI (cloud, OAuth)                       │
│                                                 │
│  Vector Storage (ChromaDB)                      │
│  └─ ~/.stravinsky/vectordb/<hash>_<provider>/   │
│                                                 │
│  Search Functions                               │
│  ├─ semantic_search()      - Basic NL queries   │
│  ├─ enhanced_search()      - Auto-mode          │
│  ├─ hybrid_search()        - Semantic + AST     │
│  ├─ multi_query_search()   - Query expansion    │
│  └─ decomposed_search()    - Complex queries    │
│                                                 │
│  Indexing                                       │
│  └─ index_codebase()       - Manual trigger     │
│                             (Currently required)│
│                                                 │
└─────────────────────────────────────────────────┘
```

## Key Files in Codebase

### Implementation
- **mcp_bridge/tools/semantic_search.py** (1754 lines)
  - Core semantic search implementation
  - All embedding providers
  - CodebaseVectorStore class
  - All search functions

- **mcp_bridge/server.py** (lines 498-551)
  - MCP tool dispatch for semantic tools
  - Connects to Claude Code

### Hooks Infrastructure (for auto-indexing)
- **mcp_bridge/hooks/manager.py**
  - HookManager class
  - Hook registration and execution
  - Ready to add indexing triggers

- **mcp_bridge/hooks/session_idle.py**
  - Example of background hook pattern
  - Can be adapted for indexing

- **mcp_bridge/server.py** (line 634)
  - `async_main()` entry point
  - Where startup triggers would go

## Architecture Highlights

### Auto-Indexing Options

| Option | Trigger | Implementation | Complexity | Recommended |
|--------|---------|-----------------|------------|-------------|
| A | Startup | Add to `async_main()` | Simple | YES |
| B | Session | New pre-model-invoke hook | Medium | Maybe |
| C | Scheduled | Background task loop | Complex | Advanced |

**Detailed comparison:** See semantic_indexing_analysis.md Section 4

### Current Status

- ✅ Embedding providers: 4 options (local + cloud)
- ✅ Vector storage: ChromaDB with file locking
- ✅ Search capabilities: 5 advanced variants
- ✅ Metadata extraction: Language-aware, AST-aware
- ✅ Incremental updates: Only changed files
- ❌ Auto-indexing: NOT implemented (requires manual trigger)

## Implementation Checklist for Auto-Indexing

If you decide to implement Option A (recommended):

- [ ] Create `mcp_bridge/background_indexing.py`
- [ ] Add async task creation to `async_main()` 
- [ ] Make it configurable with `STRAVINSKY_AUTO_INDEX` env var
- [ ] Add logging/progress to stderr
- [ ] Test with incremental updates
- [ ] Document in CLAUDE.md
- [ ] Add to .claude/commands/ for easy manual trigger

## Embedding Provider Setup

### Local (Recommended for Code)
```bash
# Install Ollama: https://ollama.ai
ollama serve              # Start server
ollama pull mxbai-embed-large  # Download model (1GB)
# Then use: provider="mxbai" or "ollama"
```

### Cloud (Alternative)
```bash
# Gemini (free tier available)
stravinsky auth login gemini
# Then use: provider="gemini"

# OpenAI (paid, ~$0.02/M tokens)
stravinsky auth login openai
# Then use: provider="openai"
```

## Performance Notes

### Indexing Speed
- First run: ~5-30 seconds (depends on project size)
- Subsequent runs: ~1-5 seconds (only changed files)
- Overhead: None if async/background

### Search Speed
- Query embedding: ~100-500ms (Ollama local)
- Vector search: ~10-100ms
- Total: ~200-600ms per query
- LLM expansion: +1-2 seconds if enabled

### Storage
- Vector DB: ~1-10MB per 1000 chunks
- Metadata: Minimal
- Location: User home `~/.stravinsky/vectordb/`

## Troubleshooting Quick Links

| Problem | Solution | Details |
|---------|----------|---------|
| "Embedding service not available" | Start Ollama server | semantic_indexing_quick_start.md |
| "No documents indexed" | Run semantic_index | semantic_indexing_quick_start.md |
| Slow indexing | Use mxbai-embed-large | semantic_indexing_quick_start.md |
| Index goes stale | Run incremental reindex | semantic_indexing_quick_start.md |
| Want auto-indexing | Read Option A | semantic_indexing_analysis.md Section 4 |

## Next Steps

1. **Immediate:** Try semantic search manually
   - Follow quick_start.md steps 1-3
   - ~10 minutes

2. **Short-term:** Decide on auto-indexing
   - Read analysis.md section 4
   - ~15 minutes

3. **Medium-term:** Implement chosen option
   - Option A: ~1-2 hours
   - Includes testing & documentation

4. **Long-term:** Monitor and refine
   - Track indexing performance
   - Gather user feedback
   - Optimize based on patterns

## Questions?

- **System architecture?** → See semantic_indexing_analysis.md (Section 1-3)
- **How to use?** → See semantic_indexing_quick_start.md
- **Auto-indexing?** → See semantic_indexing_analysis.md (Section 4-6)
- **Troubleshooting?** → See semantic_indexing_quick_start.md (Troubleshooting)
- **Integration?** → See semantic_indexing_analysis.md (Section 5)

