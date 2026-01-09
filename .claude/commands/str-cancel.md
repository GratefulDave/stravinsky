---
description: Cancel ongoing semantic indexing operation
allowed-tools: mcp__stravinsky__cancel_indexing
---

# Cancel Semantic Indexing

Gracefully cancel an ongoing `semantic_index()` operation. Useful for large codebases where indexing takes several minutes.

## What This Does

Sets a cancellation flag that's checked between batches (every 50 chunks). The current batch completes before stopping, ensuring no partial writes to ChromaDB.

## Usage

Call `cancel_indexing` with parameters:
- `project_path`: "." (current directory)
- `provider`: "ollama" (must match the provider used for indexing)

## Example

```python
# In one session: Start indexing
semantic_index(project_path=".", provider="ollama")

# From another call (or same session): Cancel it
cancel_indexing(project_path=".", provider="ollama")
```

## Output Example

```
✅ Cancellation requested for /path/to/project
Indexing will stop after current batch completes.
```

The indexing operation will return partial results:

```
⚠️ Indexing cancelled
Indexed 150 chunks from 75 files before cancellation
Cancelled after 150/500 chunks
```

## Notes

- **Graceful**: Current batch (50 chunks) completes before stopping
- **Progress preserved**: All completed batches remain indexed
- **Thread-safe**: Uses locks to prevent race conditions
- **Provider must match**: Use the same provider you started indexing with
- Flag automatically clears at start of next indexing operation
