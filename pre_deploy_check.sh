#!/usr/bin/env bash
# Pre-Deployment Safety Checks for Stravinsky
# Run this BEFORE every deployment to prevent shipping broken code

set -e  # Exit on first error

echo "🔍 Pre-Deployment Safety Checks"
echo "================================"
echo ""

# Check 1: Python import test (use uv to ensure deps are available)
echo "✓ Check 1: Basic import test"
uv run python -c "import mcp_bridge.server" || {
    echo "❌ FAILED: mcp_bridge.server cannot be imported"
    exit 1
}
echo "  ✅ mcp_bridge.server imports successfully"

# Check 2: Version consistency
echo ""
echo "✓ Check 2: Version consistency"
VERSION_TOML=$(grep -E "^version = " pyproject.toml | head -1 | cut -d'"' -f2)
VERSION_INIT=$(grep -E "^__version__ = " mcp_bridge/__init__.py | cut -d'"' -f2)

if [ "$VERSION_TOML" != "$VERSION_INIT" ]; then
    echo "❌ FAILED: Version mismatch"
    echo "  pyproject.toml: $VERSION_TOML"
    echo "  __init__.py: $VERSION_INIT"
    exit 1
fi
echo "  ✅ Version consistent: $VERSION_TOML"

# Check 3: Stravinsky command works
echo ""
echo "✓ Check 3: Stravinsky command test"
stravinsky --version >/dev/null 2>&1 || {
    echo "❌ FAILED: stravinsky command fails"
    exit 1
}
echo "  ✅ stravinsky command works"

# Check 4: All tool modules import
echo ""
echo "✓ Check 4: Tool module imports"
for tool in invoke_gemini invoke_openai agent_tools semantic_search lsp_tools; do
    uv run python -c "from mcp_bridge.tools import $tool" 2>/dev/null || {
        echo "❌ FAILED: mcp_bridge.tools.$tool cannot be imported"
        exit 1
    }
    echo "  ✅ $tool imports successfully"
done

# Check 5: Run pytest if tests exist
echo ""
echo "✓ Check 5: Test suite"
if [ -d "tests" ] && [ -n "$(find tests -name 'test_*.py' -o -name '*_test.py')" ]; then
    uv run pytest tests/ -v || {
        echo "❌ FAILED: Tests failed"
        exit 1
    }
    echo "  ✅ All tests passed"
else
    echo "  ⚠️  No tests found (tests/ directory empty or missing)"
fi

# Check 6: Ruff linting
echo ""
echo "✓ Check 6: Ruff linting"
ruff check mcp_bridge/ --quiet || {
    echo "❌ FAILED: Ruff linting errors"
    echo "  Run: ruff check mcp_bridge/ --fix"
    exit 1
}
echo "  ✅ No linting errors"

# Check 7: Git status clean
echo ""
echo "✓ Check 7: Git status"
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ FAILED: Uncommitted changes detected"
    git status --short
    exit 1
fi
echo "  ✅ No uncommitted changes"

echo ""
echo "================================"
echo "✅ ALL CHECKS PASSED"
echo ""
echo "Safe to deploy version $VERSION_TOML"
