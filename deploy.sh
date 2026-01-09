#!/usr/bin/env bash
set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🚀 Stravinsky Deployment Script"
echo "================================"
echo ""

# Step 1: Verify version consistency
echo "📋 Step 1: Checking version consistency..."
VERSION_TOML=$(grep -E "^version = " pyproject.toml | head -1 | cut -d'"' -f2)
VERSION_INIT=$(grep -E "^__version__ = " mcp_bridge/__init__.py | cut -d'"' -f2)

if [ "$VERSION_TOML" != "$VERSION_INIT" ]; then
  echo -e "${RED}❌ Version mismatch!${NC}"
  echo "   pyproject.toml: $VERSION_TOML"
  echo "   __init__.py:    $VERSION_INIT"
  exit 1
fi

echo -e "${GREEN}✅ Version consistent: $VERSION_TOML${NC}"
echo ""

# Step 2: Check git status and commit if needed
echo "📋 Step 2: Checking git status..."
GIT_STATUS=$(git status --porcelain)

if [[ -n "$GIT_STATUS" ]]; then
  echo -e "${YELLOW}⚠️  Uncommitted changes detected:${NC}"
  git status --short
  echo ""

  # Check if only version files are modified
  ONLY_VERSION_FILES=true
  while IFS= read -r line; do
    file=$(echo "$line" | awk '{print $2}')
    if [[ "$file" != "pyproject.toml" ]] && \
       [[ "$file" != "mcp_bridge/__init__.py" ]] && \
       [[ "$file" != "mcp_bridge/tools/semantic_search.py" ]]; then
      ONLY_VERSION_FILES=false
      break
    fi
  done <<< "$GIT_STATUS"

  if [[ "$ONLY_VERSION_FILES" == "true" ]]; then
    echo -e "${BLUE}Detected version bump changes. Committing...${NC}"
    read -p "Enter commit message (or press Enter for default): " COMMIT_MSG

    if [[ -z "$COMMIT_MSG" ]]; then
      COMMIT_MSG="fix: release v$VERSION_TOML

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
    fi

    git add pyproject.toml mcp_bridge/__init__.py mcp_bridge/tools/semantic_search.py 2>/dev/null || true
    git commit -m "$COMMIT_MSG"
    echo -e "${GREEN}✅ Changes committed${NC}"
  else
    echo -e "${RED}❌ Non-version files modified. Please commit or stash them first.${NC}"
    exit 1
  fi
else
  echo -e "${GREEN}✅ Working directory clean${NC}"
fi
echo ""

# Step 3: Push commits to origin
echo "📋 Step 3: Pushing to origin..."
CURRENT_BRANCH=$(git branch --show-current)

if ! git push origin "$CURRENT_BRANCH"; then
  echo -e "${RED}❌ Failed to push to origin${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Pushed to origin/$CURRENT_BRANCH${NC}"
echo ""

# Step 4: Clean build artifacts (only for current version)
echo "📋 Step 4: Cleaning old build artifacts..."
find dist -name "stravinsky-$VERSION_TOML*" -delete 2>/dev/null || true
echo -e "${GREEN}✅ Cleaned old build for version $VERSION_TOML${NC}"
echo ""

# Step 5: Build package
echo "📋 Step 5: Building package..."
if ! uv build; then
  echo -e "${RED}❌ Build failed${NC}"
  exit 1
fi

# Verify build outputs
if [[ ! -f "dist/stravinsky-$VERSION_TOML-py3-none-any.whl" ]] || \
   [[ ! -f "dist/stravinsky-$VERSION_TOML.tar.gz" ]]; then
  echo -e "${RED}❌ Build artifacts not found${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Build successful${NC}"
ls -lh dist/stravinsky-$VERSION_TOML*
echo ""

# Step 6: Load PyPI token
echo "📋 Step 6: Loading PyPI token..."
if [[ ! -f .env ]]; then
  echo -e "${RED}❌ .env file not found${NC}"
  exit 1
fi

source .env

if [[ -z "$PYPI_API_TOKEN" ]]; then
  echo -e "${RED}❌ PYPI_API_TOKEN not found in .env${NC}"
  exit 1
fi

echo -e "${GREEN}✅ PyPI token loaded${NC}"
echo ""

# Step 7: Publish to PyPI
echo "📋 Step 7: Publishing to PyPI..."
echo -e "${YELLOW}Publishing version $VERSION_TOML...${NC}"

if ! uv publish \
  --token "$PYPI_API_TOKEN" \
  "dist/stravinsky-$VERSION_TOML-py3-none-any.whl" \
  "dist/stravinsky-$VERSION_TOML.tar.gz"; then

  echo -e "${RED}❌ Publish failed${NC}"
  echo ""
  echo "Possible reasons:"
  echo "  - Version $VERSION_TOML already exists on PyPI"
  echo "  - Network error"
  echo "  - Invalid PyPI token"
  exit 1
fi

echo -e "${GREEN}✅ Published to PyPI${NC}"
echo ""

# Step 8: Create and push git tag
echo "📋 Step 8: Creating git tag..."
TAG_NAME="v$VERSION_TOML"

if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
  echo -e "${YELLOW}⚠️  Tag $TAG_NAME already exists${NC}"
  read -p "Delete and recreate? (y/N) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    git tag -d "$TAG_NAME"
    git push origin ":refs/tags/$TAG_NAME" 2>/dev/null || true
  else
    echo "Skipping tag creation"
    TAG_NAME=""
  fi
fi

if [[ -n "$TAG_NAME" ]]; then
  git tag -a "$TAG_NAME" -m "chore: release v$VERSION_TOML"
  git push origin "$TAG_NAME"
  echo -e "${GREEN}✅ Tagged and pushed as $TAG_NAME${NC}"
fi
echo ""

# Step 9: Verify deployment
echo "📋 Step 9: Verifying deployment..."
echo "Waiting 10 seconds for PyPI to update..."
sleep 10

if pip index versions stravinsky 2>&1 | grep -q "$VERSION_TOML"; then
  echo -e "${GREEN}✅ Version $VERSION_TOML is live on PyPI!${NC}"
else
  echo -e "${YELLOW}⚠️  Version not yet visible (PyPI may need more time)${NC}"
fi
echo ""

# Step 10: Force uvx cache clear (CRITICAL FOR @latest TO WORK)
echo "📋 Step 10: Clearing uvx cache..."
echo -e "${YELLOW}⚠️  CRITICAL: Forcing fresh PyPI fetch on next uvx run${NC}"

python3 -c "import shutil; from pathlib import Path; cache = Path.home() / '.cache' / 'uv'; shutil.rmtree(cache, ignore_errors=True); print('✅ Cleared uvx cache')"

echo -e "${GREEN}✅ Cache cleared - restart Claude Code to fetch v$VERSION_TOML${NC}"
echo ""

# Success summary
echo "🎉 Deployment Complete!"
echo "======================="
echo ""
echo "Version:  $VERSION_TOML"
echo "Package:  https://pypi.org/project/stravinsky/$VERSION_TOML/"
echo "Git Tag:  $TAG_NAME"
echo ""
echo -e "${GREEN}✅ uvx cache cleared - restart Claude Code to get v$VERSION_TOML${NC}"
echo -e "${YELLOW}⚠️  Without restarting Claude Code, you'll stay on the old cached version!${NC}"
