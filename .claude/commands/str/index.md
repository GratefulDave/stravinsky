---
description: Index the codebase for semantic search with vector embeddings.
---

# Index Codebase for Semantic Search

Build a semantic search index using vector embeddings to enable natural language code discovery.

## What This Does

Creates a vector database that indexes your codebase for semantic search, enabling queries like:
- "find authentication logic"
- "error handling in API endpoints"
- "database connection pooling"
- "logging and monitoring"
- "caching and performance optimization"

This index enables the `/search` command to find code based on meaning and intent, not just keyword matching.

## Prerequisites

Ensure your embedding provider is ready:

### Ollama (Recommended - Free, Local)

```bash
# Install Ollama (if not already installed)
brew install ollama

# Pull the lightweight embedding model (274MB, recommended)
ollama pull nomic-embed-text

# Or for better accuracy (670MB):
ollama pull mxbai-embed-large
```

### Other Providers

- **Gemini**: Requires OAuth - run `stravinsky-auth login gemini`
- **OpenAI**: Requires ChatGPT Plus/Pro - run `stravinsky-auth login openai`
- **HuggingFace**: No auth needed, cloud-based

## Usage

Call the `semantic_index` MCP tool with your desired parameters:

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_path` | string | "." | Path to project root (absolute or relative) |
| `provider` | string | "ollama" | Embedding provider: "ollama", "gemini", "openai", "huggingface" |
| `force` | boolean | false | Force full reindex (true) or incremental update (false) |

### Examples

**Basic indexing (default Ollama):**
```
semantic_index(project_path=".")
```

**Full reindex with force:**
```
semantic_index(project_path=".", force=true)
```

**Using Gemini provider:**
```
semantic_index(project_path=".", provider="gemini")
```

**Specific project directory:**
```
semantic_index(project_path="/path/to/project", provider="ollama")
```

## Index Management

### Check Index Status

After indexing, view the index statistics:
```
semantic_stats(project_path=".")
```

This shows:
- Number of indexed files
- Total code blocks indexed
- Index size
- Last update time
- Provider information

### Incremental vs Full Reindex

- **Incremental (force=false)**: Only indexes new or modified files. Fast for ongoing development.
- **Full Reindex (force=true)**: Rebuilds the entire index from scratch. Use when:
  - Files have been deleted or moved
  - You're getting stale results
  - Upgrading embedding models
  - You've made significant codebase changes

### When to Reindex

Run `/str:index` again when:
- Adding new files or modules to your project
- Significantly modifying existing files
- Changing the codebase structure
- Want to use a different embedding provider
- Getting stale or outdated search results

Use `force=true` if results become stale:
```
semantic_index(project_path=".", force=true)
```

## Provider Comparison

| Provider | Speed | Accuracy | Cost | Setup |
|----------|-------|----------|------|-------|
| **Ollama** | Fast | Good | Free | Local |
| **Gemini** | Fast | Excellent | Low | OAuth |
| **OpenAI** | Medium | Excellent | Medium | OAuth |
| **HuggingFace** | Slow | Good | Free | Cloud |

## Next Steps

After indexing, use semantic search:

```
/search "find authentication logic"
/search "database connection pooling"
/search "error handling patterns" language=py
```

See `/search` for detailed search command documentation.

## Troubleshooting

### "Ollama connection refused"

Ensure Ollama is running:
```bash
# Check if Ollama is running
lsof -i :11434

# Start Ollama (usually auto-starts, but can manually start)
ollama serve
```

### "Provider not available"

Verify you have the required credentials:
- **Gemini/OpenAI**: Run `stravinsky-auth login <provider>`
- **HuggingFace**: Ensure HF_TOKEN environment variable is set

### "Index is stale"

Rebuild with full reindex:
```
semantic_index(project_path=".", force=true)
```

### Large index size

If your index becomes very large:
1. Exclude directories: Add to `.gitignore` patterns (same dirs are skipped from indexing)
2. Use language filter in search instead of indexing all languages
3. Reindex with different provider for smaller index

## Performance Tips

- **First index**: May take 1-2 minutes depending on codebase size
- **Incremental updates**: Typically 30 seconds or less
- **Ollama locally**: No internet required, very fast once loaded
- **Batch indexing**: Index once, then search many times (cost-effective)

## File Watching (Automatic Reindexing)

Enable automatic reindexing when files change:

```python
from mcp_bridge.tools.semantic_search import start_file_watcher

watcher = start_file_watcher(
    project_path=".",
    provider="ollama",
    debounce_seconds=2.0
)
# Files now automatically reindex when modified
```

Stop automatic watching when done:
```python
from mcp_bridge.tools.semantic_search import stop_file_watcher

stop_file_watcher(".")
```

See `/str:watch` for more details on automatic file watching.
