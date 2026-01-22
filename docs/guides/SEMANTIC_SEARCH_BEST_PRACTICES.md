# Semantic Search Best Practices Guide

Learn when and how to effectively use semantic search in Stravinsky for code discovery and analysis.

**For quick setup, see:** [Quick Start](./SEMANTIC_SEARCH_QUICK_START.md)
**For file watching, see:** [Watcher Usage](./SEMANTIC_WATCHER_USAGE.md)
**For indexing details, see:** [Indexing Quick Start](./semantic_indexing_quick_start.md)

---

## Table of Contents

1. [When to Use Semantic Search](#when-to-use-semantic-search)
2. [Choosing the Right Search Tool](#choosing-the-right-search-tool)
3. [Query Writing Guidelines](#query-writing-guidelines)
4. [Filter Usage](#filter-usage)
5. [Provider Selection](#provider-selection)
6. [Performance Optimization](#performance-optimization)
7. [Common Pitfalls](#common-pitfalls)
8. [Troubleshooting](#troubleshooting)

---

## When to Use Semantic Search

### Quick Decision Matrix

| Scenario | Use Semantic? | Reason | Alternative |
|----------|---------------|--------|-------------|
| **Finding "authentication logic"** | Yes | Concept-based, exact terms unknown | grep for "auth", "login" |
| **Looking for a function by exact name** | No | Too specific, use LSP tools | `lsp_workspace_symbols` |
| **Finding error handling patterns** | Yes | Cross-cutting concern, varied naming | grep + manual review |
| **Locating file by full path** | No | Fast exact match available | `glob_files` |
| **Understanding caching strategy** | Yes | Conceptual pattern, multiple files | Read several files manually |
| **Finding all imports of a module** | No | Structural/exact match needed | `ast_grep_search` |
| **Discovering deprecated patterns** | Yes | Fuzzy matching, legacy code | grep for patterns + semantic |
| **Finding specific error type** | Maybe | Use grep first, semantic for context | `grep "KeyError"` + semantic |
| **Locating performance bottlenecks** | Yes | Concept-based, varied implementations | grep + code review |
| **Finding all function definitions** | No | Structural, use LSP | `lsp_document_symbols` |

### Semantic Search Excels When

Use semantic search when you need to find code by **what it does** rather than **what it's named**.

**Pattern 1: Concept-Based Discovery**
```
Query: "how does the application authenticate users"
Why: Multiple files, different approaches (JWT, OAuth, sessions)
Traditional: grep "auth|login" produces too many false positives
Semantic: Understands intent, finds authentication logic wherever it exists
```

**Pattern 2: Fuzzy Requirements**
```
Query: "caching mechanism"
Why: Could be named cache, memoization, lru, redis_client
Traditional: Would need multiple grep patterns
Semantic: Finds caching implementations by semantic meaning
```

**Pattern 3: Cross-Cutting Concerns**
```
Query: "database connection management"
Query: "retry logic and exponential backoff"
Query: "request validation"
Why: Scattered across multiple files, mixed with business logic
Traditional: Manual exploration
Semantic: Identifies implementations regardless of location
```

### When NOT to Use Semantic Search

**Exact structural matches** - Use `ast_grep_search`:
```python
# Do not use:
semantic_search("class MyClass definition")

# Use instead:
ast_grep_search(pattern="class MyClass { $$$ }")
```

**Exact file paths** - Use `glob_files`:
```python
# Do not use:
semantic_search("find auth.py file")

# Use instead:
glob_files(pattern="**/auth.py")
```

**Exact function names** - Use `lsp_workspace_symbols`:
```python
# Do not use:
semantic_search("find authenticate_user function")

# Use instead:
lsp_workspace_symbols(query="authenticate_user")
```

---

## Choosing the Right Search Tool

### Tool Selection Guide

| Tool | Use When | Query Example |
|------|----------|---------------|
| `semantic_search` | Simple conceptual query | "authentication logic" |
| `hybrid_search` | Need semantic + structural | "async auth functions" + pattern |
| `enhanced_search` | Unsure which approach | Complex or ambiguous queries |
| `multi_query_search` | Need better recall | "caching" (finds cache, memo, lru) |
| `decomposed_search` | Multi-part query | "init DB and create user model" |

### Decision Flowchart

```
Query Analysis
     |
     v
Is query multi-part (contains "and", "then", "also")?
     |
    YES --> decomposed_search()
     |
    NO
     |
     v
Do you need structural pattern matching?
     |
    YES --> hybrid_search() with ast-grep pattern
     |
    NO
     |
     v
Is query vague or might have synonyms?
     |
    YES --> multi_query_search() for better recall
     |
    NO
     |
     v
Unsure or complex?
     |
    YES --> enhanced_search(mode="auto")
     |
    NO --> semantic_search() (basic, fastest)
```

---

## Query Writing Guidelines

### Effective Query Patterns

**Be Specific, Add Context:**

```python
# Too broad (returns many irrelevant results):
await semantic_search(query="error")

# Better (specific context):
await semantic_search(
    query="handling network timeout errors in HTTP requests",
    language="py",
    node_type="function"
)
```

**Use Domain Terminology:**

```python
# Generic (finds unrelated code):
await semantic_search(query="database")

# Domain-specific (finds ORM usage):
await semantic_search(query="SQLAlchemy session management")
```

**Include Implementation Hints:**

```python
# Conceptual only:
await semantic_search(query="caching")

# With implementation hints:
await semantic_search(query="Redis cache with TTL expiration")
```

### Query Length Guidelines

| Query Length | Example | Recommended Tool |
|--------------|---------|------------------|
| 1-3 words | "authentication" | `multi_query_search` (expand it) |
| 4-8 words | "JWT token validation middleware" | `semantic_search` |
| 9+ words | "OAuth flow with PKCE and refresh tokens" | `decomposed_search` |
| Multi-part | "init DB and create user model" | `decomposed_search` |

---

## Filter Usage

### Available Filters

| Filter | Values | Purpose |
|--------|--------|---------|
| `language` | "py", "ts", "js", "go", etc. | Limit to specific language |
| `node_type` | "function", "class", "method" | Limit to code structure type |
| `decorator` | "@property", "@staticmethod" | Filter by Python decorator |
| `is_async` | True, False | Async functions only |
| `base_class` | "BaseClass" | Classes inheriting from base |

### Filter Examples

**Language Filter:**
```python
# Only Python files
await semantic_search(
    query="authentication flow",
    language="py"
)
```

**Node Type Filter:**
```python
# Only functions (not classes or methods)
await semantic_search(
    query="data validation",
    node_type="function"
)

# Only class definitions
await semantic_search(
    query="request handler",
    node_type="class"
)
```

**Decorator Filter:**
```python
# Only @property methods
await semantic_search(
    query="computed fields",
    decorator="@property"
)

# Only @staticmethod functions
await semantic_search(
    query="utility functions",
    decorator="@staticmethod"
)
```

**Async Filter:**
```python
# Only async functions
await semantic_search(
    query="HTTP requests",
    is_async=True
)
```

**Base Class Filter:**
```python
# Only classes inheriting from BaseHandler
await semantic_search(
    query="request processing",
    base_class="BaseHandler"
)
```

**Combined Filters:**
```python
# Async Python functions with @router decorator
await semantic_search(
    query="API endpoints",
    language="py",
    node_type="function",
    decorator="@router",
    is_async=True
)
```

---

## Provider Selection

### Provider Comparison

| Provider | Latency | Cost | Quality | Best For |
|----------|---------|------|---------|----------|
| **ollama** | 200-500ms | Free | Good | Development, fast iteration |
| **mxbai** | 200-500ms | Free | Better | Code-focused searches |
| **gemini** | 1-2s | Free tier | Excellent | Production, quality focus |
| **openai** | 1-3s | $0.02/M | Excellent | Complex reasoning |
| **huggingface** | 2-5s | Free tier | Good | Budget-conscious |

### Provider Selection Guidelines

**Development (prioritize speed):**
```python
# Fast local provider
await semantic_search(
    query="authentication",
    provider="mxbai"  # ~300ms, local
)
```

**Production (prioritize quality):**
```python
# High-quality cloud provider
await semantic_search(
    query="security vulnerability patterns",
    provider="gemini"  # Best quality, ~1.5s
)
```

**Batch Operations (cost-conscious):**
```python
# Free local provider for bulk searches
for query in queries:
    await semantic_search(query=query, provider="ollama")
```

---

## Performance Optimization

### Indexing Performance

| Project Size | First Index Time | Incremental Update |
|--------------|------------------|-------------------|
| Small (<50 files) | 5-10 seconds | <1 second |
| Medium (50-500 files) | 10-30 seconds | 1-5 seconds |
| Large (500+ files) | 30-60+ seconds | 5-15 seconds |

### Search Performance

| Provider | Typical Latency | Notes |
|----------|-----------------|-------|
| Local (ollama/mxbai) | 200-600ms | No network overhead |
| Cloud (gemini/openai) | 1-3s | API call overhead |

### Optimization Strategies

**1. Use Local Providers for Development:**
```python
# Fast iteration during development
await semantic_search(query="...", provider="mxbai")
```

**2. Apply Filters to Reduce Scope:**
```python
# Narrow search space
await semantic_search(
    query="error handling",
    language="py",
    node_type="function",
    n_results=5  # Fewer results = faster
)
```

**3. Use File Watcher for Incremental Updates:**
```python
# Auto-reindex on file changes (no full reindex needed)
await start_file_watcher(project_path=".", debounce_seconds=2.0)
```

**4. Cache Store Instance:**
```python
# Reuse store across queries
from mcp_bridge.tools.semantic_search import get_store

store = get_store(".", provider="ollama")

# Multiple queries share same connection
results1 = await store.search("query1")
results2 = await store.search("query2")
```

---

## Common Pitfalls

### Pitfall 1: Over-Broad Queries

**Problem:** Too many vague results with low relevance.

```python
# Too broad
results = await semantic_search(query="code")
# Returns: Every file (relevance 0.5-0.6)
```

**Solution:** Be specific and add filters.

```python
# Specific + filters
results = await semantic_search(
    query="handling network timeout errors in HTTP requests",
    language="py",
    node_type="function",
    n_results=10
)
```

### Pitfall 2: Wrong Tool for the Job

**Problem:** Using semantic search for exact matches.

```python
# Wrong: Searching semantically for exact function
results = await semantic_search(query="authenticate_user function")
```

**Solution:** Use the right tool.

```python
# Right: Use LSP for exact name
symbol = await lsp_workspace_symbols(query="authenticate_user")
```

### Pitfall 3: Index Staleness

**Problem:** New files not appearing in search results.

**Solution:** Use file watcher or reindex.

```python
# Option 1: Auto-reindex with file watcher
await start_file_watcher(".")

# Option 2: Manual reindex
await index_codebase(".", force=True)
```

### Pitfall 4: Provider Mismatch

**Problem:** Slow searches during development.

**Solution:** Use appropriate provider for context.

```python
# Development: Fast local provider
await semantic_search(query="...", provider="mxbai")

# Production: High-quality cloud provider
await semantic_search(query="...", provider="gemini")
```

### Pitfall 5: Ignoring Relevance Scores

**Problem:** Accepting low-relevance results.

```python
# Results with relevance < 0.6 are often noise
```

**Solution:** Check relevance scores and refine query.

```python
# If relevance < 0.6, query is too vague
# Refine with more specific terms or use decomposed_search
```

---

## Troubleshooting

### "Embedding service not available"

**Ollama (local):**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve

# If model missing
ollama pull nomic-embed-text
ollama pull mxbai-embed-large
```

**Cloud providers:**
```bash
# Check authentication status
stravinsky-auth status

# Re-authenticate if needed
stravinsky-auth login gemini
stravinsky-auth login openai
```

### "No documents indexed"

```python
# Check index status
stats = await semantic_stats(project_path=".")
print(stats)

# If empty, create index
await index_codebase(project_path=".")
```

### "Too many results, low relevance"

1. Make query more specific
2. Add language/node_type filters
3. Reduce n_results
4. Try `decomposed_search()` for complex queries

### "Search is slow"

1. Use local provider (`ollama` or `mxbai`)
2. Reduce result count
3. Add filters to narrow scope
4. Check network connectivity for cloud providers

### HuggingFace-Specific Issues

**410 Model Unavailable:**
```
Many models removed from free tier. Use Ollama instead:
ollama pull mxbai-embed-large
```

**503 Model Loading:**
```
First request takes 20-30s. Provider retries automatically.
```

**429 Rate Limit:**
```
Provider retries with backoff. Consider local provider for high volume.
```

---

## Summary: Quick Reference

### Query Best Practices

1. Be specific with domain terminology
2. Use filters liberally
3. Check relevance scores (>0.6 is good)
4. Choose right tool for query complexity

### Performance Checklist

- [ ] Use local provider for development
- [ ] Apply language/node_type filters
- [ ] Enable file watcher for auto-updates
- [ ] Cache store instance for multiple queries

### Tool Selection

| Need | Tool |
|------|------|
| Simple conceptual query | `semantic_search()` |
| Multi-part query | `decomposed_search()` |
| Need more results | `multi_query_search()` |
| Semantic + structure | `hybrid_search()` |
| Unsure | `enhanced_search(mode="auto")` |

---

## See Also

- [Quick Start Guide](./SEMANTIC_SEARCH_QUICK_START.md) - Get started in minutes
- [File Watcher Usage](./SEMANTIC_WATCHER_USAGE.md) - Auto-indexing setup
- [Indexing Quick Start](./semantic_indexing_quick_start.md) - Index configuration

---

**Last Updated:** January 2026
**Status:** Comprehensive best practices guide
