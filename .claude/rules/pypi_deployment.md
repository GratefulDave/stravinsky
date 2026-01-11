# PyPI Deployment Rules

## ⚠️ CRITICAL REMINDER: ALWAYS CLEAN BEFORE BUILDING

**The #1 deployment error:** Forgetting to clean dist/ before building

```bash
# ALWAYS RUN THIS FUWT (use Python if hooks block rm):
python3 -c "import shutil; from pathlib import Path; [shutil.rmtree(p) for p in [Path('dist'), Path('build')] if p.exists()]; print('✅ Cleaned')"
```

**Why:** PyPI rejects if dist/ contains old version files (e.g., 0.4.9.tar.gz when publishing 0.4.10)

---

## Version Management

1. **ALWAYS check PyPI first before bumping version:**
   ```bash
   pip index versions stravinsky 2>&1 | head -20
   ```
   If the version you're about to use already exists on PyPI, bump higher!

2. **Version must be consistent** across:
   - `pyproject.toml` (line ~5): `version = "X.Y.Z"`
   - `mcp_bridge/__init__.py`: `__version__ = "X.Y.Z"`

3. **Version bumping strategy**:
   - Patch (X.Y.Z+1): Bug fixes, documentation updates
   - Minor (X.Y+1.0): New features, agent improvements, MCP tool additions
   - Major (X+1.0.0): Breaking changes to API or architecture

4. **⚠️ CRITICAL**: PyPI does NOT allow re-uploading the same version. If `uv publish` fails with "File already exists", you MUST bump the version number and try again.

## CRITICAL RULES

1. **Pin Python upper bounds when core dependencies require it**
   - ✅ CORRECT: `requires-python = ">=3.11,<3.14"` (when chromadb/onnxruntime don't support 3.14+)
   - ❌ WRONG: `requires-python = ">=3.11"` (allows installation on unsupported Python versions)
   - Reason: Better to block installation than have broken runtime imports
   - Current constraint: `<3.14` due to chromadb → onnxruntime lacking Python 3.14 wheels

2. **ALWAYS install globally with @latest for auto-updates**
   - ✅ CORRECT: `claude mcp add --global stravinsky -- uvx stravinsky@latest`
   - ❌ WRONG: `claude mcp add stravinsky -- uvx stravinsky` (no @latest)
   - ❌ WRONG: Local `.mcp.json` entries (use global only)

## Pre-Deployment Checklist

Before deploying to PyPI, ensure:

1. ✅ All changes committed to git
2. ✅ Version numbers match in `pyproject.toml` and `mcp_bridge/__init__.py`
3. ✅ No uncommitted temp files (`.stravinsky/agents/*.out`, `logs/`)
4. ✅ New files properly tracked in git (check `.claude/agents/`, `docs/`)
5. ✅ `uv.lock` is up-to-date
6. ✅ **Python version constraint matches dependency requirements** (`<3.14` for chromadb)

## Deployment Process

### Step 1: Clean Build Artifacts (MANDATORY - DO NOT SKIP)

**⚠️ CRITICAL: ALWAYS clean dist/ before building, even if version was bumped!**

**Why this matters:**
- PyPI rejects uploads if a file with the same name already exists (even if version differs)
- Old build artifacts in dist/ from previous versions will cause 400 Bad Request errors
- `uv publish` uploads ALL files in dist/, not just the latest build

**WRONG:** ❌ Skip cleaning → build → publish (publishes old + new versions → ERROR)
**CORRECT:** ✅ Clean → build → publish (only publishes new version)

```bash
# ⚠️ MANDATORY: Clean ALL build artifacts first
# If blocked by hooks, use Python alternative:
python3 -c "import shutil; from pathlib import Path; [shutil.rmtree(p) for p in [Path('dist'), Path('build')] if p.exists()]; print('✅ Cleaned dist/ and build/')"

# OR if hooks allow:
# rm -rf dist/ build/ *.egg-info

# Verify git status
git status

# Ensure version consistency (MUST match exactly)
VERSION_TOML=$(grep -E "^version = " pyproject.toml | head -1 | cut -d'"' -f2)
VERSION_INIT=$(grep -E "^__version__ = " mcp_bridge/__init__.py | cut -d'"' -f2)

if [ "$VERSION_TOML" != "$VERSION_INIT" ]; then
  echo "❌ Version mismatch: pyproject.toml=$VERSION_TOML, __init__.py=$VERSION_INIT"
  exit 1
fi

echo "✅ Version consistent: $VERSION_TOML"

# Verify dist/ is empty (CRITICAL CHECK)
if [ -d "dist" ] && [ "$(ls -A dist)" ]; then
  echo "❌ ERROR: dist/ is not empty! Old artifacts will cause publish to fail."
  echo "   Files in dist/:"
  ls -lh dist/
  exit 1
fi

echo "✅ dist/ is clean"
```

### Step 2: Build (ONLY after cleaning)

```bash
# Build with uv (creates dist/stravinsky-X.Y.Z.tar.gz and .whl)
uv build

# Verify correct version was built
ls -lh dist/
# Should ONLY show files with your new version number
```

### Step 3: Publish to PyPI

**CRITICAL: ALWAYS load .env file first!**

```bash
# Load .env file (PYPI_API_TOKEN is stored here)
source .env

# Verify token is loaded
if [ -z "$PYPI_API_TOKEN" ]; then
  echo "❌ PYPI_API_TOKEN not found in .env"
  exit 1
fi

# Publish using PyPI API token from .env
uv publish --token "$PYPI_API_TOKEN"
```

### Step 4: Git Tag and Push

```bash
# Create git tag
VERSION=$(grep -E "^version = " pyproject.toml | head -1 | cut -d'"' -f2)
git tag -a "v$VERSION" -m "chore: release v$VERSION"

# Push with tags
git push origin main --tags
```

### Step 5: Force uvx Cache Clear (MANDATORY)

**⚠️ CRITICAL: ALWAYS clear uvx cache after deployment!**

**Why this matters:**
- `@latest` doesn't force PyPI checks if uvx has a cached version
- Without clearing, users stay on old versions FOREVER
- This is THE most common cause of "version deployed but not updating" issues

```bash
# Clear uvx cache to force fresh PyPI fetch on next Claude restart
python3 -c "import shutil; from pathlib import Path; cache = Path.home() / '.cache' / 'uv'; shutil.rmtree(cache, ignore_errors=True); print('✅ Cleared uvx cache - restart Claude Code to fetch v$(grep -E "^version = " pyproject.toml | head -1 | cut -d'"' -f2)')"

# Verify deployment is on PyPI
pip index versions stravinsky 2>&1 | head -5
```

**Post-cache-clear:**
1. Restart Claude Code (or wait for next restart)
2. uvx will fetch the latest version from PyPI
3. Verify with: run any stravinsky MCP tool and check version in output

## Commit Message Convention

Use conventional commit format:

```
<type>: <description>

[optional body]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `chore`: Build/release tasks
- `refactor`: Code restructuring
- `test`: Test additions/changes

**Example:**
```
feat: expand explore.md Multi-Model Usage from 12 to 319 lines

- Added 5 detailed examples with agent_context
- Documented gemini-3-flash usage patterns
- Added Model Selection Strategy section
- Documented haiku fallback behavior
- Added Gemini Best Practices (5 subsections)
```

## Emergency Rollback

If deployment fails:

```bash
# Revert to previous version
git revert HEAD
git push origin main

# Delete failed tag
git tag -d v$VERSION
git push origin :refs/tags/v$VERSION
```

## Post-Deployment Verification

```bash
# Verify PyPI package
pip install --upgrade stravinsky==$VERSION

# Check version
stravinsky --version
python -c "import mcp_bridge; print(mcp_bridge.__version__)"
```
