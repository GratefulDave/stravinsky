---
description: Bump version, publish to PyPI, and upgrade local installation
allowed-tools: Bash, Read, Edit
---

# Publish Stravinsky

Publish a new version to PyPI and upgrade local installation.

## ⚡ Quick Start (Recommended)

**The user runs `./deploy.sh` manually** - This is a complete deployment script that handles:

1. ✅ **Version consistency checks** - Verifies `pyproject.toml` and `mcp_bridge/__init__.py` match
2. ✅ **Git commit** - Auto-commits version changes if only version files modified
3. ✅ **Push to repo** - Pushes commits to origin/main
4. ✅ **Clean build** - Removes old artifacts, builds only current version
5. ✅ **Publish to PyPI** - Uploads wheel and tarball with API token
6. ✅ **Create git tag** - Tags the release (e.g., v0.4.13)
7. ✅ **Push tag to repo** - Pushes tag with `git push origin v0.4.X` (NOT --tags)
8. ✅ **Deployment verification** - Waits 10s and checks PyPI for new version

**Your role:**
- Help bump the version in `pyproject.toml` and `mcp_bridge/__init__.py` if requested
- Tell the user to run `./deploy.sh` - that's it!
- **NEVER** run the deployment yourself - the script must run in the user's terminal for interactive prompts

## Manual Workflow (Legacy)

If the user prefers manual control:

1. **Bump version** in pyproject.toml (patch by default, or specify: major, minor, patch)
2. **Commit** the version bump
3. **Tag** with version
4. **Push** to trigger GitHub Actions publish workflow
5. **Wait** for PyPI to update (~60 seconds)
6. **Upgrade** local uv tool installation

## Usage

```
/publish           # Bump patch version (0.2.56 -> 0.2.57)
/publish minor     # Bump minor version (0.2.56 -> 0.3.0)
/publish major     # Bump major version (0.2.56 -> 1.0.0)
```

## Implementation

Execute the following steps:

### Step 1: Get current version
```bash
grep "^version" pyproject.toml
```

### Step 2: Calculate new version
Parse the current version and increment based on argument (default: patch).

### Step 3: Update pyproject.toml
Edit the version line to the new version.

### Step 4: Commit and tag
```bash
git add pyproject.toml
git commit -m "chore: bump version to X.Y.Z for PyPI release"
git tag vX.Y.Z
git push origin main --tags
```

### Step 5: Wait for PyPI
```bash
echo "Waiting 60s for PyPI publish..."
sleep 60
```

### Step 6: Upgrade local installation
```bash
uv tool upgrade stravinsky
```

### Step 7: Verify
```bash
uv tool list | grep stravinsky
```

IMPORTANT: Always complete ALL steps. The local upgrade is critical - never skip it.
