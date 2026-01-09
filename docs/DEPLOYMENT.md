# Stravinsky v0.4.9 Deployment

## Release Summary

**Version:** 0.4.9
**Type:** Patch (Bug Fix)
**Date:** 2026-01-09

### Changes

#### Fix: Auto-detect and remove stale ChromaDB locks

Resolves "Connection closed" errors when `start_file_watcher` is called after closing Claude Code without stopping the watcher.

**Root Cause:**
When Claude Code is closed without stopping file watchers, `filelock` persists lock files that block subsequent lock acquisitions. This causes 30-second timeouts that exceed MCP transport timeout limits.

**Solution:**

1. **Stale lock detection** in `CodebaseVectorStore.client` property
   - Checks lock file age before acquisition
   - Auto-deletes locks older than 5 minutes (300 seconds)
   - Prevents 30s timeout that causes MCP transport closure

2. **Graceful shutdown** via atexit handler
   - Stops all active watchers on normal Python exit
   - Ensures locks are properly released

### Files Changed

- `mcp_bridge/tools/semantic_search.py`: Added stale lock detection and atexit cleanup
- `pyproject.toml`: Version bump to 0.4.9
- `mcp_bridge/__init__.py`: Version bump to 0.4.9

### Installation

Users with `stravinsky@latest` will automatically get v0.4.9 on next Claude Code restart.

To manually upgrade:

```bash
claude mcp add --global stravinsky -- uvx --python python3.13 stravinsky@latest
```

### Testing

The fix prevents "Connection closed" errors in this scenario:

```bash
# In Claude Code, without stopping watcher
# Close Claude Code (watcher thread dies, lock persists)

# Next session
/strav
⏺ stravinsky - start_file_watcher (MCP)(project_path: ".", provider: "ollama", debounce_seconds: 2)
# Now works! (auto-detects and removes stale 5+ min old lock)
```

## Deployment Commands

### Step 1: Publish to PyPI

```bash
source .env && uv publish \
  --token "$PYPI_API_TOKEN" \
  "dist/stravinsky-0.4.9-py3-none-any.whl" \
  "dist/stravinsky-0.4.9.tar.gz"
```

### Step 2: Create git tag

```bash
git tag -a "v0.4.9" -m "chore: release v0.4.9"
git push origin --tags
```

### Automated Deployment (Future)

For future releases, use the deployment script:

```bash
./deploy.sh
```

This handles:
1. Version consistency checks
2. Git status validation
3. Build verification
4. PyPI publishing
5. Git tagging
6. Deployment verification

## Troubleshooting

### "Version X already exists on PyPI"

The version was already published. This is normal if rerunning deployment steps.

### "Connection closed" still occurring

1. Clear stale locks manually:
   ```bash
   rm ~/.stravinsky/vectordb/*/chromadb.lock
   ```

2. Verify Ollama is running:
   ```bash
   ollama serve
   ```

3. Check semantic index exists:
   ```bash
   semantic_stats(project_path=".", provider="ollama")
   ```

## Release Notes

- Fixed "Connection closed" MCP errors from stale ChromaDB lock files
- Added automatic stale lock detection (5+ minute age threshold)
- Added graceful watcher cleanup on Python exit via atexit handler
- Enhanced `deploy.sh` script for streamlined deployments
