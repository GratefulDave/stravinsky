# Index Project for Semantic Search

Index the current project for natural language code search using Ollama embeddings.

## What This Does

Creates a vector database for semantic code search that enables queries like:
- "find authentication logic"
- "error handling in API endpoints"
- "database connection pooling"

## Related Commands

- `/str:watch` - Start automatic file watching for background reindexing
- `/str:unwatch` - Stop file watcher
- `/str:cancel` - Cancel ongoing indexing operation
- `/str:clean` - Delete indexes to free disk space

## Prerequisites

Ensure Ollama is installed and the embedding model is available:

```bash
# Install Ollama (if not already installed)
brew install ollama

# Pull the lightweight embedding model (274MB, recommended)
ollama pull nomic-embed-text

# Or for better accuracy (670MB):
ollama pull mxbai-embed-large
```

## Indexing

Use the `semantic_index` MCP tool to index the current project:

**Parameters:**
- `project_path`: "." (current directory)
- `provider`: "ollama" (free, local)
- `force`: false (only index new/changed files)

After indexing, you can use `semantic_search` with natural language queries.

**Check index status:** Use `semantic_stats` to view indexed files and metadata.

## Re-indexing

Run `/index` again to incrementally update the index with new or modified files. Use `force=true` to rebuild the entire index from scratch.
