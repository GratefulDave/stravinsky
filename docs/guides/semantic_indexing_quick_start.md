# Semantic Indexing Quick Start Guide

## Current Status

Stravinsky has a **fully functional semantic search system** with these components:

```
semantic_search.py (1754 lines)
├── Embedding Providers
│   ├── OllamaProvider (local, free) - nomic-embed-text
│   ├── MxbaiProvider (local, free) - mxbai-embed-large (better)
│   ├── GeminiProvider (cloud) - Google embeddings
│   ├── OpenAIProvider (cloud) - OpenAI embeddings
│   └── HuggingFaceProvider (cloud) - sentence-transformers
├── CodebaseVectorStore
│   ├── ChromaDB storage (~/.stravinsky/vectordb/)
│   ├── AST-aware chunking (Python)
│   ├── Smart metadata extraction
│   └── File locking for concurrency
└── Search Functions
    ├── semantic_search() - Natural language queries
    ├── enhanced_search() - Auto-selects mode
    ├── hybrid_search() - Semantic + AST patterns
    ├── multi_query_search() - Query expansion
    ├── decomposed_search() - Complex queries
    ├── index_codebase() - Manual indexing
    ├── semantic_stats() - Index info
    └── semantic_health() - Provider health
```

## Getting Started (3 Steps)

### Step 1: Install Embedding Provider

**Option A: Local (Free, No Auth) - RECOMMENDED**

```bash
# Install Ollama (one-time setup)
brew install ollama

# Pull the recommended lightweight model (274MB)
ollama pull nomic-embed-text
```

**Why nomic-embed-text?**
- Lightweight (274MB) - perfect for MacBooks and space-constrained systems
- Fast indexing and search
- Works great for code search
- No authentication required
- Runs 100% locally (no API calls)

**Advanced Option: Better Accuracy (670MB)**
```bash
# For power users who want maximum accuracy
ollama pull mxbai-embed-large
```

**Model Comparison:**

| Model | Size | Dimensions | Speed | Accuracy | Best For |
|-------|------|------------|-------|----------|----------|
| **nomic-embed-text** | 274MB | 768 | Fast | Good | **Most users (recommended)** |
| **mxbai-embed-large** | 670MB | 1024 | Medium | Better | Power users with disk space |

**Option B: Cloud (OAuth)**
```bash
stravinsky auth login gemini   # Google embeddings
# or
stravinsky auth login openai   # OpenAI embeddings
```

**Option C: HuggingFace (Token-based)**
```bash
# Install HuggingFace CLI
pip install huggingface-hub

# Login with your HF token
huggingface-cli login

# Or set environment variable
export HF_TOKEN="your_hf_token_here"

# Or set in .env file
echo "HF_TOKEN=your_hf_token_here" >> .env
```

**Getting a HuggingFace token:**
1. Go to https://huggingface.co/settings/tokens
2. Create a new token (read access is sufficient)
3. Copy the token and use one of the methods above

**Note:** HuggingFace free Inference API has limited model availability. Many models have been moved to paid tiers or removed. The provider is implemented but may require:
- A paid HuggingFace Pro subscription for reliable access
- Specifying a different model that's available on the free tier
- Consider using Ollama (local, free) instead for consistent availability

### Step 2: Index Your Codebase

**First time (one-shot):**
```bash
# Via CLI (if exposed)
stravinsky semantic_index --project .

# Via Python
python -c "
import asyncio
from mcp_bridge.tools.semantic_search import index_codebase
asyncio.run(index_codebase(project_path='.'))
"

# Via Claude Code (MCP tool)
# Call tool: semantic_index(project_path=".", force=false, provider="ollama")
```

**Incremental updates (only new/changed files):**
```bash
# Same command, but it detects what changed
# Only re-indexes modified files
stravinsky semantic_index --project .
```

**Force full reindex (clear and rebuild):**
```bash
# Via Python
asyncio.run(index_codebase(project_path=".", force=True))

# Via Claude Code
# Call tool: semantic_index(project_path=".", force=true, provider="ollama")
```

### Step 3: Search!

**Basic semantic search:**
```
query: "find authentication logic"
```

**Enhanced search (auto-mode):**
```
query: "how does the database connection work"
mode: "auto"  # Detects complexity, uses expand or decompose
```

**Hybrid search (semantic + AST patterns):**
```
query: "error handling"
pattern: "try ... except"  # ast-grep pattern
```

**Multi-query expansion:**
```
query: "database connection"
# Automatically expands to:
# - "SQLAlchemy engine configuration"
# - "postgres connection setup"
# - "db session factory pattern"
```

**Decomposed search (for complex queries):**
```
query: "initialize the DB and create a user model"
# Splits into:
# - "database initialization"
# - "user model definition"
```

## File Locations

```
Implementation:
  /Users/davidandrews/PycharmProjects/stravinsky/
  ├── mcp_bridge/
  │   ├── server.py (lines 498-551: tool dispatch)
  │   └── tools/
  │       └── semantic_search.py (main, 1754 lines)
  └── docs/
      └── semantic_indexing_analysis.md (detailed analysis)

Vector Storage:
  ~/.stravinsky/vectordb/<project_hash>_<provider>/
  ├── chroma.sqlite3
  ├── hnswlib_data/
  ├── data.parquet
  └── .chromadb.lock

Status:
  ✅ Fully implemented
  ✅ Multiple providers supported
  ✅ Advanced search capabilities
  ❌ No auto-indexing on startup (requires manual trigger)
```

## Provider Comparison

| Provider | Type | Size | Cost | Speed | Setup | Dims | Status |
|----------|------|------|------|-------|-------|------|--------|
| **nomic-embed-text** | Local | 274MB | Free | Fast | `ollama pull` | 768 | ✅ Stable |
| **mxbai-embed-large** | Local | 670MB | Free | Medium | `ollama pull` | 1024 | ✅ Stable |
| **Gemini** | Cloud | N/A | $0/30K tokens | Medium | OAuth | 768-3072 | ✅ Stable |
| **OpenAI** | Cloud | N/A | $0.02/M tokens | Medium | OAuth | 1536 | ✅ Stable |
| **HuggingFace** | Cloud | N/A | Free/Pro | Medium | HF Token | 768 | ⚠️ Limited availability |

**Recommendations:**
- **Best for most users (local):** `nomic-embed-text` - lightweight (274MB), fast, works great for code search, perfect for space-constrained systems
- **Best for power users (local):** `mxbai-embed-large` - better accuracy, larger model (670MB), ideal if you have disk space
- **Best for cloud (free):** `gemini` - generous free tier, OAuth auth
- **Best for scale (cloud):** `openai` - highest quality, predictable costs
- **HuggingFace:** Implemented but many models unavailable on free tier. Use Ollama instead for reliable local embeddings.

## Index Statistics

After indexing, check what's in your index:

```bash
# Via Python
python -c "
import asyncio
from mcp_bridge.tools.semantic_search import semantic_stats, semantic_health
print(asyncio.run(semantic_stats(project_path='.')))
print(asyncio.run(semantic_health(project_path='.')))
"
```

**Sample Output:**
```
Project: /Users/davidandrews/PycharmProjects/stravinsky
Database: /Users/davidandrews/.stravinsky/vectordb/abc123def456_ollama
Chunks indexed: 1,247
Embedding provider: ollama (1024 dims)

Provider (ollama): Online
Vector DB: Online (1,247 documents)
```

## Troubleshooting

### "Embedding service not available"

**For Ollama providers:**
```bash
ollama serve
# In another terminal:
ollama list  # Should show your models
```

**Check model is downloaded:**
```bash
ollama pull nomic-embed-text
ollama pull mxbai-embed-large
```

**For HuggingFace provider:**
```bash
# Check if token is set
echo $HF_TOKEN

# Or check HF CLI config
cat ~/.cache/huggingface/token
cat ~/.huggingface/token

# If not found, login:
huggingface-cli login
```

**For OAuth providers (Gemini/OpenAI):**
```bash
stravinsky-auth status
# If not authenticated:
stravinsky-auth login gemini
# or
stravinsky-auth login openai
```

### "No documents indexed"

**Index the codebase first:**
```bash
stravinsky semantic_index --project .
# Wait for it to complete
```

**Check what was indexed:**
```bash
# Should show > 0 documents
python -c "import asyncio; from mcp_bridge.tools.semantic_search import semantic_stats; print(asyncio.run(semantic_stats()))"
```

### Slow indexing?

**Reasons:**
- First indexing is slower (needs to embed all chunks)
- Incremental indexing is faster (only new/changed files)
- Large codebases take longer

**Speed up with Ollama:**
- Use `mxbai-embed-large` instead of `nomic-embed-text`
- Run `ollama` on same machine (local)
- Ensure Ollama has GPU acceleration enabled

### Index goes stale?

**Solution:** Run incremental reindex
```bash
# Only re-indexes changed files
stravinsky semantic_index --project .
```

**Full reset if needed:**
```bash
rm -rf ~/.stravinsky/vectordb/<project_hash>*
stravinsky semantic_index --project . --force
```

### HuggingFace-specific issues

**410 Model Unavailable (Common Issue):**
```
ValueError: Model [...] is no longer available on HF free Inference API (410 Gone)
```
HuggingFace has removed many embedding models from the free Inference API tier. Solutions:
- **Recommended:** Use Ollama instead (`ollama pull mxbai-embed-large`)
- Upgrade to HuggingFace Pro subscription
- Try a different model that may be available on free tier (model availability changes frequently)

**503 Model Loading Error:**
```
⚠️ Model is loading, retrying...
```
HuggingFace Inference API loads models on-demand. First request may take 20-30 seconds. The provider automatically retries with exponential backoff.

**429 Rate Limit:**
```
⚠️ HF API rate limit hit, retrying with backoff...
```
Free HuggingFace accounts have rate limits. The provider automatically retries. For higher limits:
- Upgrade to HuggingFace Pro
- Or use local Ollama provider instead

**401 Authentication Failed:**
```
ValueError: Hugging Face authentication failed
```
Token is invalid or expired. Solutions:
```bash
# Re-login with HF CLI
huggingface-cli login

# Or get a new token from https://huggingface.co/settings/tokens
export HF_TOKEN="new_token_here"
```

## Advanced Usage

### Filtering Search Results

```python
# Only search Python functions
semantic_search(
    query="authentication",
    language="py",
    node_type="function"
)

# Only async functions with @router decorator
semantic_search(
    query="endpoint handler",
    language="py",
    node_type="method",
    decorator="@router",
    is_async=True
)

# Only classes inheriting from BaseHandler
semantic_search(
    query="request processing",
    language="py",
    node_type="class",
    base_class="BaseHandler"
)
```

### Custom Chunking

The system automatically:
- Respects Python function/class boundaries
- Extracts docstrings and type hints
- Preserves file:line metadata for navigation
- Skips auto-generated files and common junk dirs

**To change chunking:**
Edit `CodebaseVectorStore` in `semantic_search.py`:
```python
CHUNK_SIZE = 50      # lines per chunk
CHUNK_OVERLAP = 10   # lines of overlap
SKIP_DUW = {...}    # directories to skip
CODE_EXTENSIONS = {...}  # file types to index
```

## Next Steps

### Recommended Reading

1. **Detailed Architecture:**
   - Read: `/Users/davidandrews/PycharmProjects/stravinsky/docs/semantic_indexing_analysis.md`
   - Sections: 1-3 (current system state)

2. **For Auto-Indexing:**
   - Read: Sections 4-6 (three options for automation)
   - Decision: Which option fits your workflow?

3. **For Integration:**
   - Check: `mcp_bridge/server.py` lines 498-551
   - Learn: How tools are dispatched to Claude Code

### Ideas for Enhancement

1. **Add startup auto-indexing** (Section 4, Option A)
2. **Create slash command** for easy manual indexing
3. **Add progress UI integration** for long indexing jobs
4. **Implement file watcher** for real-time incremental updates
5. **Cache index metadata** to speed up health checks

