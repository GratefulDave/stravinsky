# Semantic Indexing Quick Start Guide

This guide covers how to create and manage semantic search indexes for your codebase.

## System Overview

```
mcp_bridge/tools/semantic_search.py
|
+-- Embedding Providers
|   +-- OllamaProvider (local, free) - nomic-embed-text (768 dims)
|   +-- MxbaiProvider (local, free) - mxbai-embed-large (1024 dims)
|   +-- GeminiProvider (cloud) - gemini-embedding-001 (768 dims)
|   +-- OpenAIProvider (cloud) - text-embedding-3-small (1536 dims)
|   +-- HuggingFaceProvider (cloud) - all-mpnet-base-v2 (768 dims)
|
+-- CodebaseVectorStore
|   +-- ChromaDB storage (~/.stravinsky/vectordb/)
|   +-- AST-aware chunking (Python)
|   +-- Smart metadata extraction
|   +-- Incremental indexing with manifest
|   +-- File locking for concurrency
|
+-- Search Functions
|   +-- semantic_search() - Natural language queries
|   +-- enhanced_search() - Auto-selects mode
|   +-- hybrid_search() - Semantic + AST patterns
|   +-- multi_query_search() - Query expansion
|   +-- decomposed_search() - Complex queries
|
+-- Index Management
|   +-- index_codebase() - Create/update index
|   +-- semantic_stats() - View statistics
|   +-- semantic_health() - Check provider status
|   +-- delete_index() - Remove index
|   +-- cancel_indexing() - Stop ongoing indexing
|
+-- File Watcher
    +-- start_file_watcher() - Auto-reindex on changes
    +-- stop_file_watcher() - Stop watching
    +-- list_file_watchers() - View active watchers
    +-- get_file_watcher() - Get specific watcher
```

## Getting Started (3 Steps)

### Step 1: Install an Embedding Provider

**Option A: Ollama (Local, Free) - Recommended**

```bash
# Install Ollama
brew install ollama

# Start the service
ollama serve

# Pull the lightweight model (274MB)
ollama pull nomic-embed-text
```

**Why nomic-embed-text?**
- Lightweight (274MB) - works well on laptops
- Fast indexing and search
- Good quality for code search
- No authentication required
- Runs 100% locally

**Option B: Mxbai (Local, Free, Better Accuracy)**

```bash
# After installing Ollama
ollama pull mxbai-embed-large
```

**Model Comparison:**

| Model | Size | Dimensions | Speed | Accuracy | Best For |
|-------|------|------------|-------|----------|----------|
| **nomic-embed-text** | 274MB | 768 | Fast | Good | Most users |
| **mxbai-embed-large** | 670MB | 1024 | Medium | Better | Power users |

**Option C: Cloud Providers (OAuth)**

```bash
# Gemini (free tier available)
stravinsky-auth login gemini

# OpenAI (requires subscription)
stravinsky-auth login openai
```

**Option D: HuggingFace (Token-based)**

```bash
# Set token from https://huggingface.co/settings/tokens
export HF_TOKEN="your_hf_token_here"

# Or use HF CLI
huggingface-cli login
```

**Note:** HuggingFace free tier has limited model availability. Many models have been moved to paid tiers. Consider Ollama for reliable local embeddings.

### Step 2: Index Your Codebase

**Via Python:**

```python
import asyncio
from mcp_bridge.tools.semantic_search import index_codebase

# Basic indexing with default provider (ollama)
result = asyncio.run(index_codebase(project_path="."))
print(result)

# Index with specific provider
result = asyncio.run(index_codebase(
    project_path=".",
    provider="mxbai"
))
```

**Via Claude Code (MCP tool):**

```
Call tool: semantic_index(project_path=".", force=false, provider="ollama")
```

**Force Full Reindex:**

```python
# Clear and rebuild entire index
result = asyncio.run(index_codebase(
    project_path=".",
    force=True
))
```

### Step 3: Search

```python
from mcp_bridge.tools.semantic_search import semantic_search

# Basic search
results = await semantic_search(
    query="authentication logic",
    project_path="."
)
print(results)
```

## Index Management

### Check Index Status

```python
from mcp_bridge.tools.semantic_search import semantic_stats, semantic_health

# Get statistics
stats = await semantic_stats(project_path=".", provider="ollama")
print(stats)
# Output:
# Project: /path/to/project
# Database: /Users/.../.stravinsky/vectordb/project_ollama
# Chunks indexed: 1,247
# Embedding provider: ollama (768 dims)

# Check health
health = await semantic_health(project_path=".", provider="ollama")
print(health)
# Output:
# Provider (ollama): Online
# Vector DB: Online (1,247 documents)
```

### Delete Index

```python
from mcp_bridge.tools.semantic_search import delete_index

# Delete specific provider index for project
result = delete_index(project_path=".", provider="ollama")
print(result)

# Delete all provider indexes for project
result = delete_index(project_path=".")
print(result)

# Delete ALL indexes for ALL projects
result = delete_index(delete_all=True)
print(result)
```

### Cancel Ongoing Indexing

```python
from mcp_bridge.tools.semantic_search import cancel_indexing

# Request cancellation (happens between batches)
result = cancel_indexing(project_path=".", provider="ollama")
print(result)
```

## Provider Comparison

| Provider | Type | Size | Cost | Speed | Dims | Status |
|----------|------|------|------|-------|------|--------|
| **nomic-embed-text** | Local | 274MB | Free | Fast | 768 | Stable |
| **mxbai-embed-large** | Local | 670MB | Free | Medium | 1024 | Stable |
| **Gemini** | Cloud | N/A | Free tier | Medium | 768 | Stable |
| **OpenAI** | Cloud | N/A | $0.02/M | Medium | 1536 | Stable |
| **HuggingFace** | Cloud | N/A | Free/Pro | Medium | 768 | Limited |

**Recommendations:**
- **Most users (local):** nomic-embed-text - lightweight, fast, good quality
- **Power users (local):** mxbai-embed-large - better accuracy
- **Cloud (free):** gemini - generous free tier, OAuth auth
- **Cloud (paid):** openai - highest quality, predictable costs
- **HuggingFace:** Use Ollama instead for reliable local embeddings

## File Locations

```
Implementation:
  mcp_bridge/
  +-- tools/
      +-- semantic_search.py (main implementation)

Vector Storage:
  ~/.stravinsky/vectordb/<project_name>_<provider>/
  +-- chroma.sqlite3
  +-- hnswlib_data/
  +-- data.parquet
  +-- .chromadb.lock
  +-- manifest.json (incremental indexing state)

Logs:
  ~/.stravinsky/logs/file_watcher.log
```

## Indexing Details

### Chunking Strategy

**Python files (AST-aware):**
- Each function becomes a chunk
- Each class becomes a chunk
- Methods are separate chunks (for granular search)
- Module-level code chunked if no functions/classes
- Metadata includes: decorators, async status, base classes, return types

**Other languages (line-based):**
- 50 lines per chunk
- 10 lines overlap between chunks
- Skips tiny files (<5 lines)

### Supported Languages

```python
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".go", ".rs", ".rb", ".java",
    ".c", ".cpp", ".h", ".hpp", ".cs",
    ".swift", ".kt", ".scala",
    ".vue", ".svelte",
    ".md", ".txt", ".yaml", ".yml", ".json", ".toml"
}
```

### Skipped Directories

```python
SKIP_DIRS = {
    # Python
    "__pycache__", ".venv", "venv", "env", ".env",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",

    # Node.js
    "node_modules", ".npm", ".yarn",

    # Build outputs
    "dist", "build", "out", ".next", ".nuxt",

    # Version control
    ".git", ".svn", ".hg",

    # IDE/Editor
    ".idea", ".vscode", ".vs",

    # Misc
    ".stravinsky", "logs", "tmp", "temp"
}
```

### Whitelist Mode (.stravinskyadd)

Create a `.stravinskyadd` file to index ONLY specific paths:

```bash
# .stravinskyadd - whitelist specific files/directories
src/
lib/
*.py
src/**/*.ts
!src/generated/
```

When `.stravinskyadd` exists, only listed paths are indexed.

### Gitignore Support

The indexer respects:
- `.gitignore` - standard git ignore patterns
- `.stravignore` - Stravinsky-specific ignore patterns

```bash
# .stravignore
*.generated.py
test_fixtures/
experimental/
```

## Incremental Indexing

The indexer uses a manifest to track file changes:

1. **First index:** Full codebase scan and embedding
2. **Subsequent indexes:** Only new/changed files
3. **Manifest tracks:** file path, mtime, size, chunk IDs

**How it works:**
- Compare current file mtime/size to manifest
- Skip unchanged files (reuse existing chunks)
- Re-embed changed files
- Prune deleted file chunks

**Force full reindex:**
```python
await index_codebase(project_path=".", force=True)
```

## File Watcher (Auto-Indexing)

The file watcher automatically reindexes when code changes.

```python
from mcp_bridge.tools.semantic_search import (
    start_file_watcher,
    stop_file_watcher,
    list_file_watchers,
)

# Start watching (auto-starts on first search)
watcher = await start_file_watcher(
    project_path=".",
    provider="ollama",
    debounce_seconds=2.0
)

# Check active watchers
watchers = list_file_watchers()
for w in watchers:
    print(f"{w['project_path']}: {w['status']}")

# Stop watching
stop_file_watcher(".")
```

**Features:**
- 2-second debounce (configurable)
- Batches rapid changes
- Dedicated worker thread (prevents concurrent access)
- Auto-starts on first semantic_search call

## Troubleshooting

### "Embedding service not available"

**For Ollama:**
```bash
# Check if running
curl http://localhost:11434/api/tags

# Start if not running
ollama serve

# Check model installed
ollama list

# Pull missing model
ollama pull nomic-embed-text
```

**For Cloud Providers:**
```bash
# Check auth status
stravinsky-auth status

# Re-authenticate
stravinsky-auth login gemini
stravinsky-auth login openai
```

### "No documents indexed"

```python
# Check stats
stats = await semantic_stats()
print(stats)  # Shows chunks_indexed

# If zero, index the codebase
await index_codebase(".")
```

### Slow Indexing

**Causes:**
- First index is always slower (full embedding)
- Large codebases take longer
- Cloud providers have network latency

**Solutions:**
- Use local provider (ollama/mxbai) for faster indexing
- Use incremental indexing (default, only changed files)
- Add patterns to .stravignore to exclude large directories

### Index Goes Stale

**Solution:** Use file watcher for automatic updates

```python
await start_file_watcher(".")
```

**Or manual reindex:**
```python
await index_codebase(".")  # Incremental
await index_codebase(".", force=True)  # Full rebuild
```

### HuggingFace Issues

**410 Model Unavailable:**
```
Many models removed from free tier.
Use Ollama instead: ollama pull mxbai-embed-large
```

**503 Model Loading:**
```
First request takes 20-30s. Provider retries automatically.
```

**429 Rate Limit:**
```
Provider retries with backoff. Use local provider for high volume.
```

## Advanced Usage

### Custom Store Access

```python
from mcp_bridge.tools.semantic_search import get_store

# Get store instance
store = get_store(".", provider="ollama")

# Direct search (returns list of dicts)
results = await store.search(
    query="authentication",
    n_results=10,
    language="py",
    node_type="function"
)

# Get stats
stats = store.get_stats()

# Check embedding service
available = await store.check_embedding_service()
```

### Batch Embeddings

```python
from mcp_bridge.tools.semantic_search import get_store

store = get_store(".", provider="ollama")

# Parallel embedding with concurrency control
texts = ["query 1", "query 2", "query 3"]
embeddings = await store.get_embeddings_batch(
    texts,
    max_concurrent=10  # Limit concurrent requests
)
```

### Custom Filtering

```python
# Filter by multiple criteria
results = await semantic_search(
    query="API endpoints",
    language="py",
    node_type="function",
    decorator="@router",
    is_async=True,
    n_results=5
)

# Filter by base class
results = await semantic_search(
    query="request handlers",
    base_class="BaseHandler",
    n_results=10
)
```

## See Also

- [Quick Start Guide](./SEMANTIC_SEARCH_QUICK_START.md) - Search usage
- [Best Practices Guide](./SEMANTIC_SEARCH_BEST_PRACTICES.md) - Query optimization
- [File Watcher Usage](./SEMANTIC_WATCHER_USAGE.md) - Auto-indexing setup

---

**Last Updated:** January 2026
**Status:** Complete indexing guide
