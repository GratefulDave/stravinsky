# Semantic Watcher - Quick Start Guide

## What is the Semantic Watcher?

The Semantic Watcher automatically monitors your Python codebase and updates the semantic search index whenever you make changes. No manual reindexing needed!

**Every change triggers an update**: Edit a function, change a class, modify imports - the vector database stays in sync automatically.

## Installation & Setup

### 1. Ensure Dependencies Are Installed

The FileWatcher requires `watchdog` (already in `pyproject.toml`):

```bash
# Already installed, but verify:
uv pip list | grep watchdog
```

### 2. Start the Semantic Index

Before watching, initialize the index:

```bash
# Option 1: Use Claude Code (recommended)
# In Claude Code, run:
@semantic_index project_path="."

# Option 2: Command line (if integrated)
stravinsky semantic-index /path/to/project
```

### 3. Start the File Watcher

```python
from mcp_bridge.tools.semantic_search import start_file_watcher

# Start watching your project
watcher = start_file_watcher(
    project_path="/path/to/project",
    provider="ollama"  # or mxbai, gemini, openai
)

print(f"Watching {watcher.project_path} for changes...")
```

## Common Workflows

### Workflow 1: Development Session

```python
# At start of work session
from mcp_bridge.tools.semantic_search import start_file_watcher

watcher = start_file_watcher(".", provider="ollama")

# Now work normally - files are auto-indexed as you edit
# Edit src/auth.py - automatically indexed
# Create new src/models/user.py - automatically indexed
# Delete src/old_code.py - automatically reindexed

# At end of work session
from mcp_bridge.tools.semantic_search import stop_file_watcher
stop_file_watcher(".")
```

### Workflow 2: Long-Running Server

```python
# In your main server initialization
from mcp_bridge.tools.semantic_search import start_file_watcher

async def initialize_watchers():
    """Start file watchers for all projects."""
    projects = [
        "/Users/dev/projects/frontend",
        "/Users/dev/projects/backend",
        "/Users/dev/projects/ml",
    ]
    
    for project in projects:
        watcher = start_file_watcher(project, provider="ollama")
        print(f"Watching {project}")
```

### Workflow 3: CI/CD Integration

```python
# In your CI pipeline
from mcp_bridge.tools.semantic_search import (
    start_file_watcher,
    stop_file_watcher,
)

# Start watcher for test environment
watcher = start_file_watcher(".", provider="ollama")

# Run tests - any file changes are tracked
run_tests()

# Ensure index is up-to-date before deployment
stop_file_watcher(".")
```

## Usage with Claude Code

### Option 1: Direct Python Integration

```python
# In Claude Code, create a skill or script:
from mcp_bridge.tools.semantic_search import start_file_watcher

# Start watching
watcher = start_file_watcher(".")
print(f"FileWatcher running for {watcher.project_path}")
```

### Option 2: Using MCP Tools (when exposed)

```
# In Claude Code chat:
Use the semantic_watcher_start tool to monitor my codebase
@semantic_watcher_start project_path="."

# Check status
@semantic_watcher_list

# Stop watching
@semantic_watcher_stop project_path="."
```

## Monitoring and Debugging

### Check Active Watchers

```python
from mcp_bridge.tools.semantic_search import list_file_watchers

watchers = list_file_watchers()
for w in watchers:
    print(f"{w['project_path']}: {w['status']}")
    print(f"  Provider: {w['provider']}")
    print(f"  Debounce: {w['debounce_seconds']}s")
```

Output:
```
/Users/dev/projects/myapp: running
  Provider: ollama
  Debounce: 2.0s
```

### Enable Debug Logging

```python
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

from mcp_bridge.tools.semantic_search import start_file_watcher

watcher = start_file_watcher(".")
# Now you'll see detailed logs of all file changes and reindexing
```

Sample debug output:
```
DEBUG:mcp_bridge.tools.semantic_search:File modified: src/auth.py
DEBUG:mcp_bridge.tools.semantic_search:File created: src/models/user.py
INFO:mcp_bridge.tools.semantic_search:Reindexing codebase due to changes: ['src/auth.py', 'src/models/user.py']
INFO:mcp_bridge.tools.semantic_search:Reindexing completed
```

## Troubleshooting

### Problem: Watcher Doesn't Start

**Symptom**: `FileWatcher failed to start`

**Solutions**:
1. Check that `watchdog` is installed: `pip list | grep watchdog`
2. Verify project path exists: `ls /path/to/project`
3. Check file permissions: `ls -la /path/to/project`

### Problem: Reindexing Fails

**Symptom**: "Error during file watcher reindex"

**Solutions**:
1. Check embedding service is running:
   - For Ollama: `ollama serve`
   - For Gemini: Ensure authentication is valid
2. Check database isn't locked:
   - Wait a few seconds, watcher will retry
3. Check available disk space for vector database

### Problem: Too Many Reindexes (Slow)

**Symptom**: Reindexing happens every second, slowing down work

**Solutions**:
1. Increase debounce period:
   ```python
   watcher = start_file_watcher(".", debounce_seconds=5.0)
   ```
2. Stop watcher during heavy editing:
   ```python
   stop_file_watcher(".")
   # ... heavy editing ...
   start_file_watcher(".")
   ```

### Problem: Watcher Doesn't Detect Some Changes

**Possible causes**:
1. File is in ignored directory (`.git`, `__pycache__`, `venv`, etc.)
2. File isn't a `.py` file (only Python files are watched)
3. File is hidden (starts with `.`)

**Verify**: Check `CodebaseVectorStore.SKIP_DUW` for excluded directories

## Performance Tips

### For Small Projects (<100 files)

```python
# Use aggressive debounce
watcher = start_file_watcher(".", debounce_seconds=0.5)
```

### For Medium Projects (100-1000 files)

```python
# Use default debounce
watcher = start_file_watcher(".", debounce_seconds=2.0)
```

### For Large Projects (>1000 files)

```python
# Use conservative debounce
watcher = start_file_watcher(".", debounce_seconds=5.0)
```

### For Very Large Projects (>10k files)

```python
# Stop watcher during active development
# Manually trigger reindexes when needed
from mcp_bridge.tools.semantic_search import get_store

store = get_store(".")
await store.index_codebase()  # Manual reindex when ready
```

## Real-World Examples

### Example 1: Development Environment Setup

```python
# setup_dev_env.py
from mcp_bridge.tools.semantic_search import (
    start_file_watcher,
    index_codebase,
)

async def setup_development():
    """Set up semantic search for development."""
    
    # Initialize vector index
    stats = await index_codebase(".")
    print(f"Indexed {stats['indexed']} chunks")
    
    # Start file watcher for continuous updates
    watcher = start_file_watcher(".", provider="ollama")
    print(f"Watching {watcher.project_path}")
    
    return watcher

if __name__ == "__main__":
    import asyncio
    watcher = asyncio.run(setup_development())
    print("Development environment ready!")
```

### Example 2: Multi-Project Workspace

```python
# watch_workspace.py
from mcp_bridge.tools.semantic_search import (
    start_file_watcher,
    list_file_watchers,
)

async def watch_workspace(workspace_dir):
    """Watch all projects in a workspace."""
    from pathlib import Path
    
    workspace = Path(workspace_dir)
    
    # Find all subdirectories with git repos
    projects = [d for d in workspace.iterdir() if (d / ".git").exists()]
    
    for project in projects:
        watcher = start_file_watcher(str(project), provider="ollama")
        print(f"Started watching {project.name}")
    
    # Show status
    watchers = list_file_watchers()
    print(f"\nWatching {len(watchers)} projects:")
    for w in watchers:
        print(f"  - {Path(w['project_path']).name}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(watch_workspace("/Users/dev/projects"))
```

### Example 3: Semantic Search with Auto-Indexing

```python
# search_with_watcher.py
from mcp_bridge.tools.semantic_search import (
    start_file_watcher,
    semantic_search,
    index_codebase,
)

async def search_with_auto_index(query, project_path="."):
    """Search semantic index, with file watcher keeping it fresh."""
    
    # Ensure initial index exists
    await index_codebase(project_path)
    
    # Start watching for changes
    watcher = start_file_watcher(project_path)
    
    # Perform semantic search
    results = await semantic_search(query, project_path)
    
    return results

# Usage:
# results = await search_with_auto_index("authentication logic")
```

## Best Practices

1. **Always Initialize Index First**
   ```python
   # ✅ DO THIS
   await index_codebase(".")
   watcher = start_file_watcher(".")
   
   # ❌ DON'T start watcher without initial index
   ```

2. **Use Appropriate Debounce Period**
   ```python
   # ✅ DO THIS - match your workflow
   watcher = start_file_watcher(".", debounce_seconds=2.0)
   
   # ❌ DON'T use very small debounce (0.1s)
   ```

3. **Stop Watcher When Done**
   ```python
   # ✅ DO THIS - clean shutdown
   stop_file_watcher(".")
   
   # ❌ DON'T leave watchers running if you won't need them
   ```

4. **Monitor Watcher Health**
   ```python
   # ✅ DO THIS - check if watcher is still active
   watcher = get_file_watcher(".")
   if watcher and watcher.is_running():
       print("Watcher healthy")
   
   # ❌ DON'T assume watcher is running
   ```

5. **Handle Errors Gracefully**
   ```python
   # ✅ DO THIS - watcher handles errors automatically
   try:
       watcher = start_file_watcher(".")
   except Exception as e:
       print(f"Watcher failed: {e}, semantic search still available")
   
   # ❌ DON'T let watcher errors crash your app
   ```

## See Also

- [FileWatcher Implementation Details](./FILE_WATCHER.md)
- [Semantic Search Guide](./SEMANTIC_SEARCH.md)
- [Embedding Providers](./EMBEDDING_PROVIDERS.md)
