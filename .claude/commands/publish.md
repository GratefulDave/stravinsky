---
description: Bump version, publish to PyPI, and upgrade local installation
allowed-tools: Bash, Read, Edit
---

# Publish Stravinsky

Publish a new version to PyPI and upgrade local installation.

## Workflow

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
