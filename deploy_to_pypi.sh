#!/usr/bin/env bash
set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 Stravinsky PyPI Deployment Script"
echo "===================================="
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

# Step 2: Check git status
echo "📋 Step 2: Checking git status..."
if [[ -n $(git status --porcelain) ]]; then
  echo -e "${YELLOW}⚠️  Warning: Uncommitted changes detected${NC}"
  git status --short
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
  fi
else
  echo -e "${GREEN}✅ Working directory clean${NC}"
fi
echo ""

# Step 3: Clean build artifacts
echo "📋 Step 3: Cleaning build artifacts..."
find dist -name "stravinsky-$VERSION_TOML*" -delete 2>/dev/null || true
echo -e "${GREEN}✅ Cleaned old build for version $VERSION_TOML${NC}"
echo ""

# Step 4: Build package
echo "📋 Step 4: Building package..."
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

# Step 5: Load PyPI token
echo "📋 Step 5: Loading PyPI token..."
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

# Step 6: Publish to PyPI
echo "📋 Step 6: Publishing to PyPI..."
echo -e "${YELLOW}Publishing only version $VERSION_TOML...${NC}"

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

# Step 7: Create git tag
echo "📋 Step 7: Creating git tag..."
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
  git push origin --tags
  echo -e "${GREEN}✅ Tagged as $TAG_NAME${NC}"
fi
echo ""

# Step 8: Verify deployment
echo "📋 Step 8: Verifying deployment..."
echo "Waiting 10 seconds for PyPI to update..."
sleep 10

if pip index versions stravinsky 2>&1 | grep -q "$VERSION_TOML"; then
  echo -e "${GREEN}✅ Version $VERSION_TOML is live on PyPI!${NC}"
else
  echo -e "${YELLOW}⚠️  Version not yet visible (PyPI may need more time)${NC}"
fi
echo ""

# Success summary
echo "🎉 Deployment Complete!"
echo "======================="
echo ""
echo "Version: $VERSION_TOML"
echo "Package: https://pypi.org/project/stravinsky/$VERSION_TOML/"
echo ""
echo "Users with stravinsky@latest will get this version on next Claude restart."
