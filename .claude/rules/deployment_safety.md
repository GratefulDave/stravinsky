# Deployment Safety Rules

## CRITICAL: Pre-Deployment Checklist

**NEVER deploy code to PyPI without passing ALL checks:**

```bash
# Run this BEFORE every deployment
./pre_deploy_check.sh
```

## Mandatory Checks (BLOCKING)

1. **Import Test** - `python3 -c "import mcp_bridge.server"` must succeed
2. **Version Consistency** - pyproject.toml and __init__.py versions must match
3. **Command Works** - `stravinsky --version` must succeed
4. **All Tools Import** - Every tool module must import without errors
5. **Tests Pass** - If tests exist, `pytest` must pass
6. **Linting Clean** - `ruff check` must have zero errors
7. **Git Clean** - No uncommitted changes

## Deployment Process

```bash
# Step 1: Run safety checks
./pre_deploy_check.sh || {
    echo "❌ FAILED: Fix errors before deploying"
    exit 1
}

# Step 2: Deploy (only if checks pass)
./deploy.sh
```

## Why This Matters

**Recent failures prevented by these checks:**
- **v0.4.30 (2026-01-09)**: `NameError: name 'logger' is not defined` - would be caught by import test
- Future: Type errors, missing imports, broken commands all caught before PyPI

## Consequences of Skipping Checks

- Broken installations for all users globally
- Version number burned (can't re-upload to PyPI)
- Force version bump to fix
- User trust eroded
- Support burden increased

## Rule

**You MUST run `./pre_deploy_check.sh` before EVERY deployment. NO EXCEPTIONS.**
