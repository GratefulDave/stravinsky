---
description: /str:stats - View semantic search index statistics (indexed files, chunks, embeddings)
---

# Semantic Search Index Statistics

View detailed statistics about the semantic search index for your project.

## What This Does

Displays comprehensive information about the semantic search index including:
- Number of indexed files
- Total chunks/embeddings created
- Index size on disk
- Provider information
- Last update timestamp
- Indexed programming languages

## Prerequisites

An index must exist. Run `/index` first to create the semantic search index.

## Usage

Use the `semantic_stats` MCP tool to view index statistics:

**Parameters:**
- `project_path`: Path to project root (default: ".")

## Example

```
semantic_stats(project_path=".")
```

## Output

Displays information like:
```
Index Statistics
================
Project: /path/to/project
Provider: ollama
Status: Ready

Files Indexed: 142
Chunks: 3,847
Total Embeddings: 3,847
Index Size: 45.2 MB

Languages:
  - Python: 98 files
  - Markdown: 28 files
  - JSON: 16 files

Last Updated: 2025-01-07 18:32:15
```

## Troubleshooting

**"Index not found"**: Run `/index` to create the index first.

**"Index is stale"**: Run `/index` again to update it with new/modified files.

**"Rebuild index"**: Run `/index force=true` to completely rebuild from scratch.

## Tips

- Check stats regularly to ensure your index is up-to-date
- Use stats to verify index coverage before running `/search` queries
- Stats help identify if re-indexing is needed (large file count changes)
