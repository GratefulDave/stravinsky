# Semantic Search Best Practices Guide

Learn when and how to effectively use semantic search in Stravinsky for code discovery and analysis.

**For quick examples, see:** [Quick Start](./SEMANTIC_SEARCH_QUICK_START.md)  
**For system overview, see:** [Indexing Index](./SEMANTIC_INDEXING_INDEX.md)  
**For file watching, see:** [Watcher Usage](./SEMANTIC_WATCHER_USAGE.md)

---

## Table of Contents

1. [When to Use Semantic Search](#when-to-use-semantic-search)
2. [Query Examples by Category](#query-examples-by-category)
3. [Search Functions Reference](#search-functions-reference)
4. [Common Pitfalls & Solutions](#common-pitfalls--solutions)
5. [Performance Characteristics](#performance-characteristics)
6. [Agent Workflow Integration](#agent-workflow-integration)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Techniques](#advanced-techniques)

---

## When to Use Semantic Search

### Quick Decision Matrix

| Scenario | Use Semantic? | Reason | Alternative |
|----------|---------------|--------|-------------|
| **Finding "authentication logic"** | ✅ Yes | Concept-based, exact terms unknown | grep for "auth", "login" |
| **Looking for a function by exact name** | ❌ No | Too specific, use LSP tools | `lsp_workspace_symbols` |
| **Finding error handling patterns** | ✅ Yes | Cross-cutting concern, varied naming | grep + manual review |
| **Locating file by full path** | ❌ No | Fast exact match available | `glob_files` |
| **Understanding caching strategy** | ✅ Yes | Conceptual pattern, multiple files | Read several files manually |
| **Finding all imports of a module** | ❌ No | Structural/exact match needed | `ast_grep_search` |
| **Discovering deprecated patterns** | ✅ Yes | Fuzzy matching, legacy code | grep for patterns + semantic |
| **Finding specific error type** | ⚠️ Maybe | Use grep first, semantic for context | `grep "KeyError"` + semantic |
| **Locating performance bottlenecks** | ✅ Yes | Concept-based, varied implementations | grep + code review |
| **Finding all function definitions** | ❌ No | Structural, use LSP | `lsp_document_symbols` |

### When Semantic Search Excels

Use semantic search when you need to find code by **what it does** rather than **what it's named**.

#### Pattern 1: Concept-Based Discovery
```
Query: "how does the application authenticate users"
Why: Multiple files, different approaches (JWT, OAuth, sessions)
Traditional approach: grep "auth|login" → too many false positives
Semantic: Understands intent, finds authentication logic wherever it exists
```

#### Pattern 2: Fuzzy Requirements
```
Query: "caching mechanism"
Why: Could be named cache, memoization, lru, redis_client
Traditional approach: Would need multiple grep patterns
Semantic: Finds caching implementations by semantic meaning
```

#### Pattern 3: Anti-Patterns & Technical Debt
```
Query: "deprecated code that should be removed"
Query: "code that has no error handling"
Query: "hardcoded credentials in source"
Why: Context-dependent, needs understanding of patterns
Traditional approach: Code review + grep
Semantic: Identifies patterns across codebase
```

#### Pattern 4: Cross-Cutting Concerns
```
Query: "database connection management"
Query: "retry logic and exponential backoff"
Query: "request validation"
Why: Scattered across multiple files, mixed with business logic
Traditional approach: Manual exploration
Semantic: Identifies implementations regardless of location
```

### When NOT to Use Semantic Search

❌ **Exact structural matches** - Use `ast_grep_search`
```python
# DON'T do this:
semantic_search("class MyClass definition")

# DO this:
ast_grep_search(pattern="class MyClass { $$$ }")
```

❌ **Exact file paths** - Use `glob_files`
```python
# DON'T do this:
semantic_search("find auth.py file")

# DO this:
glob_files(pattern="**/auth.py")
```

❌ **Exact function/variable names** - Use `lsp_workspace_symbols`
```python
# DON'T do this:
semantic_search("find authenticate_user function")

# DO this:
lsp_workspace_symbols(query="authenticate_user")
```

---

## Query Examples by Category

### Authentication & Authorization

**Query 1: Finding OAuth implementations**
```python
results = await semantic_search(
    query="OAuth 2.0 authentication flow and token handling",
    project_path=".",
    n_results=10
)
```
**Expected:** OAuth login handlers, token refresh logic, provider integrations

**Query 2: JWT token management**
```python
results = await semantic_search(
    query="JWT token creation validation and refresh",
    project_path=".",
    language="py",
    node_type="function"
)
```
**Expected:** Token encoding, decoding, expiration checking

**Query 3: Session management**
```python
results = await semantic_search(
    query="user session creation and validation",
    project_path=".",
    n_results=5
)
```
**Expected:** Session stores, middleware, CSRF protection

### Error Handling & Logging

**Query 1: Exception handling patterns**
```python
results = await semantic_search(
    query="catching and handling exceptions gracefully",
    project_path=".",
    language="py",
    node_type="function"
)
```
**Expected:** Try-except blocks, error recovery, error logging

**Query 2: Logging strategy**
```python
results = await semantic_search(
    query="structured logging and error context",
    project_path=".",
    n_results=15
)
```
**Expected:** Logger setup, log levels, context information

**Query 3: Error validation**
```python
results = await semantic_search(
    query="input validation and error messages",
    project_path=".",
    language="py",
    node_type="function"
)
```
**Expected:** Validation functions, error messaging

### Data Management

**Query 1: Database connections**
```python
results = await semantic_search(
    query="database connection pooling and lifecycle",
    project_path=".",
    n_results=10
)
```
**Expected:** Connection setup, pooling, cleanup

**Query 2: Data transformation**
```python
results = await semantic_search(
    query="serialization deserialization of data structures",
    project_path=".",
    language="py"
)
```
**Expected:** Serializers, marshaling, format conversion

**Query 3: Caching strategies**
```python
results = await semantic_search(
    query="caching data for performance optimization",
    project_path=".",
    n_results=10
)
```
**Expected:** Cache implementations, invalidation logic, TTL handling

### API & Integration

**Query 1: REST API endpoints**
```python
results = await semantic_search(
    query="REST API request handling and response formatting",
    project_path=".",
    language="py",
    node_type="function"
)
```
**Expected:** Route handlers, request parsing, response building

**Query 2: Webhook processing**
```python
results = await semantic_search(
    query="receiving and processing webhook events",
    project_path=".",
    n_results=5
)
```
**Expected:** Webhook handlers, signature verification, event processing

**Query 3: Rate limiting**
```python
results = await semantic_search(
    query="rate limiting and request throttling",
    project_path=".",
    language="py"
)
```
**Expected:** Rate limiter implementations, middleware

### Performance & Optimization

**Query 1: Async operations**
```python
results = await semantic_search(
    query="async operations and concurrent execution",
    project_path=".",
    language="py",
    is_async=True
)
```
**Expected:** Async functions, concurrency patterns, task scheduling

**Query 2: Query optimization**
```python
results = await semantic_search(
    query="database query optimization and indexing",
    project_path=".",
    n_results=10
)
```
**Expected:** Query builders, optimization comments, index usage

**Query 3: Memory efficiency**
```python
results = await semantic_search(
    query="memory management and resource cleanup",
    project_path=".",
    language="py",
    node_type="function"
)
```
**Expected:** Context managers, cleanup code, memory-efficient patterns

### Real-World Example: Stravinsky's Own Code

Finding authentication in Stravinsky:
```python
# Query: Authentication and OAuth flow
results = await semantic_search(
    query="OAuth 2.0 authentication token refresh",
    project_path="/Users/davidandrews/PycharmProjects/stravinsky",
    language="py",
    n_results=10
)
# Returns: token_store.py, oauth flows, auth CLI modules
```

Finding error handling in Stravinsky:
```python
# Query: Semantic search error handling
results = await semantic_search(
    query="error recovery and retry logic with exponential backoff",
    project_path="/Users/davidandrews/PycharmProjects/stravinsky",
    language="py"
)
# Returns: retry decorators, error handling in semantic_search.py
```

---

## Search Functions Reference

### Basic: `semantic_search()`

**Purpose:** Core natural language code search

**Signature:**
```python
async def semantic_search(
    query: str,                              # Natural language query
    project_path: str = ".",
    n_results: int = 10,                     # Number of results
    language: str | None = None,             # Filter: "py", "ts", "js"
    node_type: str | None = None,            # Filter: "function", "class", "method"
    decorator: str | None = None,            # Filter: "@property", "@staticmethod"
    is_async: bool | None = None,            # Filter: async functions only
    base_class: str | None = None,           # Filter: by base class
    provider: EmbeddingProvider = "ollama"   # Provider: ollama|mxbai|gemini|openai|huggingface
) -> str
```

**When to use:**
- Exploring unfamiliar codebases
- Discovering implementation details
- Finding patterns by concept

**Example:**
```python
results = await semantic_search(
    query="how does the system validate user input",
    project_path=".",
    language="py",
    n_results=5
)
```

---

### Hybrid: `hybrid_search()`

**Purpose:** Combines semantic + structural (AST) matching for precision

**Signature:**
```python
async def hybrid_search(
    query: str,                          # Natural language query
    pattern: str | None = None,          # ast-grep pattern (optional)
    project_path: str = ".",
    n_results: int = 10,
    language: str | None = None,
    node_type: str | None = None,
    decorator: str | None = None,
    is_async: bool | None = None,
    base_class: str | None = None,
    provider: EmbeddingProvider = "ollama"
) -> str
```

**When to use:**
- Need both semantic meaning AND structural specificity
- Want to verify semantic results match a pattern
- Combining multiple search strategies

**Example:**
```python
# Find async functions that handle authentication
results = await hybrid_search(
    query="user authentication and token validation",
    pattern="async def $FUNC($$$):",  # Must be async function
    language="py",
    is_async=True
)
# Returns only async functions related to authentication
```

**Hybrid markers:**
```
1. src/auth.py:45-67 (relevance: 0.92) 🎯 [structural match]
   ^^^^^^^^^^^^^^^^^^^ Semantic match
                                         ^^^^^^^^^^^^^^^^^^ Structural pattern matched
```

---

### Advanced: `multi_query_search()`

**Purpose:** Expands queries for better recall (finds more relevant results)

**Signature:**
```python
async def multi_query_search(
    query: str,                      # Original natural language query
    project_path: str = ".",
    n_results: int = 10,
    num_expansions: int = 3,         # Generate 3 query variations
    language: str | None = None,
    node_type: str | None = None,
    provider: EmbeddingProvider = "ollama"
) -> str
```

**How it works:**
1. Takes your query: `"authentication logic"`
2. Generates variations: `"login", "session management", "user verification"`
3. Searches all variations
4. Combines and ranks results
5. Returns top N overall matches

**When to use:**
- Initial query returns too few results
- Need comprehensive coverage
- Synonyms/alternative terms matter
- Query is ambiguous or vague

**Example:**
```python
# Find all caching implementations (might be named differently)
results = await multi_query_search(
    query="caching strategy",
    num_expansions=5,  # Try 5 different phrasings
    n_results=15
)
# Could find: cache, memoization, lru, redis, performance optimization
```

---

### Complex: `decomposed_search()`

**Purpose:** Breaks complex multi-part queries into sub-queries for better accuracy

**Signature:**
```python
async def decomposed_search(
    query: str,                      # Complex query
    project_path: str = ".",
    n_results: int = 10,
    language: str | None = None,
    provider: EmbeddingProvider = "ollama"
) -> str
```

**How it works:**
1. Takes complex query: `"how does oauth authentication work with token refresh and error handling"`
2. Decomposes: `["OAuth authentication", "token refresh", "error handling"]`
3. Searches each part
4. Merges results intelligently
5. Filters for most relevant

**When to use:**
- Complex queries with multiple concepts
- Want breakdown by sub-topic
- Searching for architectural patterns
- Multi-step processes

**Example:**
```python
# Find complete authentication pipeline
results = await decomposed_search(
    query="oauth token generation token refresh revocation and logout handling",
    project_path=".",
    n_results=20
)
# Searches for: token generation, refresh, revocation, logout separately
# Then combines results showing full pipeline
```

---

### Auto: `enhanced_search()`

**Purpose:** Automatically chooses best strategy based on query complexity

**Signature:**
```python
async def enhanced_search(
    query: str,                      # Let the system decide strategy
    project_path: str = ".",
    n_results: int = 10,
    language: str | None = None,
    provider: EmbeddingProvider = "ollama"
) -> str
```

**Decision logic:**
- Simple query (1-2 words)? → `semantic_search()`
- Multiple concepts? → `decomposed_search()`
- Many results needed? → `multi_query_search()`

**When to use:**
- Don't know which strategy fits
- Want automatic optimization
- Building tools that need flexibility

**Example:**
```python
# System picks best strategy automatically
results = await enhanced_search(
    query="database migration and schema versioning",
    project_path=".",
    n_results=15
)
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Over-Broad Queries

**Problem:** Too many vague results
```python
# TOO BROAD
results = await semantic_search(query="code")
# Returns: Every file (relevance 0.5-0.6)

results = await semantic_search(query="error")
# Returns: All error handling code (500+ matches, very noisy)
```

**Solution:** Be specific and add filters
```python
# BETTER - Specific + filters
results = await semantic_search(
    query="handling network timeout errors in HTTP requests",
    language="py",
    node_type="function",
    n_results=10
)

# OR - Decompose into parts
results = await decomposed_search(
    query="HTTP client with retry logic for network failures",
    n_results=10
)
```

**Diagnosis:** Check if:
- Query is too generic ("code", "error", "logic", "system")
- Too many low-relevance results (0.4-0.6)
- Results from unrelated domains

**Fix strategy:**
1. Add domain-specific terms: "HTTP" instead of "network"
2. Use filters (`language`, `node_type`)
3. Try `decomposed_search()` to break it up
4. Or use traditional grep/AST for exact patterns

---

### Pitfall 2: Under-Specific Queries

**Problem:** Missing relevant code
```python
# TOO VAGUE
results = await semantic_search(query="token")
# Finds: JWT tokens, auth tokens, CSRF tokens, random tokens
# Misses: Specific OAuth implementation details

results = await semantic_search(query="database")
# Finds: Generic DB code, not your specific ORM usage
```

**Solution:** Add context and use right function
```python
# BETTER - More specific
results = await semantic_search(
    query="JWT bearer token validation in authentication middleware",
    language="py",
    n_results=10
)

# OR - Use decomposed for complex intent
results = await decomposed_search(
    query="OAuth 2.0 flow with PKCE for secure authorization",
    n_results=10
)

# OR - Use hybrid with structural pattern
results = await hybrid_search(
    query="database query with transaction management",
    pattern="def $FUNC($$$): $$$ = db.transaction()",  # Structural hint
    n_results=5
)
```

**Diagnosis:** Check if:
- Query returns generic results
- Context is lost in vague wording
- Multiple unrelated implementations appear

**Fix strategy:**
1. Add context words: "JWT" not "token", "PostgreSQL" not "database"
2. Try `multi_query_search()` to find synonyms
3. Use `hybrid_search()` if you know approximate structure
4. Add language/node_type filters

---

### Pitfall 3: Wrong Search Function for the Job

**Problem:** Using semantic_search when exact match is needed
```python
# WRONG - Searching semantically for exact function
results = await semantic_search(query="authenticate_user function")
# Returns: multiple functions that might do authentication

# RIGHT - Use LSP for exact name
symbol = await lsp_workspace_symbols(query="authenticate_user")
# Returns: Exact function definition
```

**Solution:** Choose right tool per your need

| Need | Tool | Why |
|------|------|-----|
| Find exact function | `lsp_workspace_symbols` | Fast, precise |
| Understand what function does | `semantic_search` | Finds context |
| Find all calls to function | `lsp_find_references` | Complete graph |
| Find functions matching pattern | `ast_grep_search` | Structural matching |
| Find implementations of concept | `semantic_search` | Semantic understanding |

---

### Pitfall 4: Index Staleness

**Problem:** Added new files but search doesn't find them
```python
# Created new auth module: src/auth/oauth.py
results = await semantic_search(query="OAuth implementation")
# Doesn't find the new file - index is stale!
```

**Solution:** Reindex before critical searches
```python
# Option 1: Manual reindex
from mcp_bridge.tools.semantic_search import index_codebase
await index_codebase("/path/to/project")

# Option 2: Use file watcher (auto-reindex)
from mcp_bridge.tools.semantic_search import start_file_watcher
watcher = start_file_watcher("/path/to/project", provider="ollama")
# Now searches always use current code

# Option 3: Check index status
from mcp_bridge.tools.semantic_search import semantic_health
health = await semantic_health(".")
print(health)  # Shows last index time
```

**Prevention:**
- Always start with `await index_codebase(".")` in scripts
- Use file watcher during development
- Check health before critical searches

---

### Pitfall 5: Provider Performance Mismatches

**Problem:** Slow searches or poor quality results

| Provider | Latency | Cost | Quality | Best For |
|----------|---------|------|---------|----------|
| **ollama** | 200-500ms | Free | Good | Local dev, fast iteration |
| **mxbai** | 200-500ms | Free | Better | Better code understanding |
| **gemini** | 1-2s | Free tier | Excellent | Production, high quality |
| **openai** | 1-3s | ~$0.02/M | Excellent | Complex queries |
| **huggingface** | 2-5s | Free tier | Good | Budget searches |

**Solution:** Pick provider for your use case
```python
# During development - fast and free
results = await semantic_search(
    query="authentication flow",
    provider="mxbai"  # ~300ms, local
)

# Production code review - highest quality
results = await semantic_search(
    query="security vulnerability patterns",
    provider="gemini"  # Best quality, ~1.5s
)

# Batch searches - cost-conscious
for query in queries:
    results = await semantic_search(
        query=query,
        provider="ollama"  # Cheapest, local
    )
```

---

### Pitfall 6: Mismatched Filters

**Problem:** Filters too restrictive, no results
```python
# TypeScript project, searching only Python
results = await semantic_search(
    query="authentication",
    language="py"  # Project is all TypeScript!
)
# Returns: No results found
```

**Solution:** Check language and validate filters
```python
# First, discover languages present
files = await glob_files(pattern="**/*.{ts,js,tsx,jsx}")
languages_in_project = ["ts", "tsx", "js"]

# Then search with correct language
results = await semantic_search(
    query="authentication",
    language="ts"
)

# Or search all languages
results = await semantic_search(
    query="authentication"
    # No language filter = all languages
)
```

---

## Performance Characteristics

### Indexing Performance

**First-time indexing:**
```
Small project (<50 files):    ~5-10 seconds
Medium project (50-500 files):  ~10-30 seconds
Large project (500+ files):     ~30-60+ seconds
```

**Factors affecting speed:**
- Embedding provider (local < cloud)
- File complexity (Python AST parsing takes time)
- Network latency (cloud providers)
- Disk I/O speed

**Example: Stravinsky project**
```
mcp_bridge/ = 15,000+ lines of Python
First index with ollama: ~15 seconds
Incremental update (1 file): ~0.5 seconds
```

### Search Performance

**Latency breakdown:**
```
Query embedding:      100-500ms (provider dependent)
Vector search:        10-50ms
Result formatting:    10-20ms
─────────────────
Total per query:      200-600ms (local)
                      1-3 seconds (cloud)
```

**Provider comparison:**
```
ollama/mxbai:   ████ 200-500ms (local, no network)
gemini:         ████████ 1-2s (API call, high quality)
openai:         ███████████ 1-3s (API call, highest quality)
huggingface:    █████████████ 2-5s (slower embeddings)
```

### Storage Overhead

**Vector database size:**
```
Per 1000 code chunks:  ~1-5 MB (ChromaDB)
Metadata:              ~50-100 KB
Total per project:     Varies by size
```

**Example: Stravinsky**
```
mcp_bridge/ chunks: ~1500
Index size: ~3-5 MB
Metadata: ~100 KB
Storage location: ~/.stravinsky/vectordb/
```

### Cost Analysis

**Free options:**
- Ollama: $0 (runs locally, no API costs)
- Mxbai: $0 (runs locally)
- HuggingFace: Free tier available

**Paid options:**
- Gemini: Free tier (limited), $0.075 per 1M input tokens
- OpenAI: $0.02 per 1M input tokens (text-embedding-3-small)

**Cost comparison for 100 searches:**
```
Ollama:      $0     (100 queries × 0ms)
Gemini:      ~$0.10 (100 queries × 10K tokens average)
OpenAI:      ~$0.05 (100 queries × 5K tokens average)
```

---

## Agent Workflow Integration

### How Explore Agent Uses Semantic Search

The Explore agent (`explore.md`) uses semantic_search as a **fallback** strategy:

```
┌─────────────────────────────────────────────┐
│  User Query: "Find authentication logic"    │
├─────────────────────────────────────────────┤
│                                             │
│  1. Try grep_search → No exact matches      │
│     (keyword "authentication" not found)    │
│                                             │
│  2. Try ast_grep_search → Too broad         │
│     (patterns like "def login" too many)    │
│                                             │
│  3. Try lsp_workspace_symbols → No symbol  │
│     named "authentication_logic"            │
│                                             │
│  4. Fallback: semantic_search               │
│     "authentication logic"                  │
│     ✅ Finds OAuth.py, JWT handler, etc.   │
│                                             │
└─────────────────────────────────────────────┘
```

**From explore.md:**
```python
# If grep/AST searches return no useful results for conceptual queries
semantic_results = semantic_search(
    query="authentication logic",
    project_path=".",
    n_results=10
)
```

### Combining Search Strategies

**Pattern 1: Grep + Semantic**
```python
# First try exact match
exact_results = await grep_search(pattern="JWT|oauth", path=".")

if not exact_results:
    # Fallback to semantic if no exact matches
    concept_results = await semantic_search(
        query="user authentication and token handling",
        n_results=10
    )
```

**Pattern 2: AST + Semantic**
```python
# Find functions matching pattern
ast_results = await ast_grep_search(pattern="async def authenticate($$$)")

# For each result, add semantic context
for file_path in ast_results:
    semantic_context = await semantic_search(
        query="authentication flow",
        language="py",
        n_results=3
    )
    # Combine for understanding
```

**Pattern 3: Hybrid Search**
```python
# Use hybrid when you have both semantic intent and structure hint
results = await hybrid_search(
    query="database connection and pooling",
    pattern="class $CLASS(BasePool):",  # Structural hint
    language="py",
    n_results=10
)
# Returns only results matching both semantic meaning + structure
```

### Caching Search Results

**Pattern: Results cache across queries**
```python
# Don't reindex for every query
store = get_store(".", provider="ollama")

# Query 1: Authentication
results1 = await store.search("authentication")

# Query 2: Token handling (reuses embeddings)
results2 = await store.search("token refresh")

# Same store, no re-indexing needed
```

**Pattern: Batch searches efficiently**
```python
queries = [
    "authentication logic",
    "error handling",
    "database operations",
    "API validation"
]

store = get_store(".", provider="ollama")

results = []
for query in queries:
    # All queries share same index
    result = await store.search(query, n_results=5)
    results.append(result)
```

---

## Troubleshooting

### "No documents indexed"

**Symptom:** Search returns `Error: No documents indexed`

**Causes:**
1. Index doesn't exist
2. Project path is wrong
3. No Python files in project

**Solutions:**
```python
# Solution 1: Initialize index
from mcp_bridge.tools.semantic_search import index_codebase
await index_codebase(".")

# Solution 2: Check path
import os
assert os.path.isdir("/path/to/project"), "Path doesn't exist!"

# Solution 3: Verify files exist
from mcp_bridge.tools.semantic_search import glob_files
files = await glob_files(pattern="**/*.py", path="/path/to/project")
assert files, "No Python files found!"
```

---

### "Embedding service not available"

**Symptom:** `Error: Embedding service not available: Connection refused`

**Causes:**
1. Ollama not running
2. Ollama running on different port
3. Model not downloaded

**Solutions:**

For **Ollama** (local):
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve

# If model missing
ollama pull nomic-embed-text
ollama pull mxbai-embed-large  # Better for code
```

For **Gemini** (cloud):
```bash
# Check authentication
stravinsky-auth status

# If not authenticated
stravinsky-auth login gemini

# Use provider
results = await semantic_search(..., provider="gemini")
```

For **OpenAI** (cloud):
```bash
stravinsky-auth login openai
results = await semantic_search(..., provider="openai")
```

---

### "Too many results, low relevance scores"

**Symptom:** Returns 10 results but relevance 0.4-0.6 (very fuzzy)

**Causes:**
1. Query too generic
2. Too many results requested
3. Wrong provider for task

**Solutions:**
```python
# Solution 1: Be more specific
results = await semantic_search(
    query="JWT token validation in authentication middleware",
    # Instead of: "token"
)

# Solution 2: Reduce result count
results = await semantic_search(
    query="authentication",
    n_results=5  # Instead of 10
)

# Solution 3: Use better provider
results = await semantic_search(
    query="authentication",
    provider="gemini"  # Higher quality than ollama
)

# Solution 4: Use decomposed_search for complex intent
results = await decomposed_search(
    query="OAuth token generation refresh and revocation",
    n_results=10
)
```

---

### "Wrong results returned"

**Symptom:** Search returns irrelevant code

**Causes:**
1. Query is ambiguous
2. Code comments are misleading
3. Semantic similarity false positives

**Solutions:**
```python
# Solution 1: Add filters
results = await semantic_search(
    query="cache",
    language="py",
    node_type="function",  # Only functions, not classes
    n_results=5
)

# Solution 2: Use hybrid search for verification
results = await hybrid_search(
    query="caching mechanism",
    pattern="class.*Cache",  # Verify structure
    language="py"
)

# Solution 3: Use multi-query to find variations
results = await multi_query_search(
    query="performance optimization",
    num_expansions=5
)

# Solution 4: Manually review top results
for result in results[:3]:  # Check top 3
    print(result['relevance'])  # Check scores
    print(result['code_preview'])  # Verify content
```

---

### "Search is too slow"

**Symptom:** Queries taking >3 seconds

**Causes:**
1. Using slow provider (HuggingFace, OpenAI)
2. Large project, first time indexing
3. Network latency

**Solutions:**

**For indexing:**
```python
# Use local provider for faster indexing
await index_codebase(".", provider="mxbai")  # Faster than ollama

# Or run incrementally
store = get_store(".")
await store.incremental_index()  # Only changed files
```

**For searches:**
```python
# Use local provider for development
results = await semantic_search(
    query="authentication",
    provider="mxbai"  # ~300ms vs 2-3s cloud
)

# For production, cloud is fine (1-2s acceptable)
```

**For large projects:**
```python
# Reduce scope
results = await semantic_search(
    query="authentication",
    language="py",  # Single language
    n_results=5    # Fewer results
)

# Or cache results
cache = {}
query = "authentication"
if query not in cache:
    cache[query] = await semantic_search(query)
results = cache[query]
```

---

### Provider-Specific Issues

**Ollama: Model not found**
```bash
# Check available models
ollama list

# Download missing model
ollama pull nomic-embed-text

# Start with specific model
OLLAMA_MODELS=nomic-embed-text ollama serve
```

**Ollama: Out of memory**
```bash
# Reduce model size
ollama pull nomic-embed-text  # 758M
# or
ollama pull mxbai-embed-large  # 1GB (but better quality)

# Run with resource limits
OLLAMA_MAX_VRAM=8000000000 ollama serve  # 8GB max
```

**Gemini: Quota exceeded**
```bash
# Check quota in Google Cloud Console
# Use local provider (ollama) as fallback
results = await semantic_search(
    query="authentication",
    provider="ollama"  # Free fallback
)
```

**OpenAI: Port 1455 in use**
```bash
# Codex CLI uses same port, stop it
killall codex

# Or authenticate with different provider
results = await semantic_search(
    query="authentication",
    provider="gemini"  # Alternative
)
```

---

## Advanced Techniques

### Custom Chunk Filtering

**Filter by node type:**
```python
# Only function definitions
results = await semantic_search(
    query="error handling",
    node_type="function",
    n_results=10
)

# Only classes
results = await semantic_search(
    query="data models",
    node_type="class",
    n_results=10
)

# Only methods
results = await semantic_search(
    query="user authentication",
    node_type="method",
    n_results=5
)
```

**Filter by decorator:**
```python
# Only @property methods
results = await semantic_search(
    query="data access",
    decorator="@property",
    n_results=5
)

# Only @staticmethod functions
results = await semantic_search(
    query="utility functions",
    decorator="@staticmethod",
    n_results=10
)
```

**Filter by async status:**
```python
# Only async functions
results = await semantic_search(
    query="concurrent operations",
    is_async=True,
    n_results=10
)

# Only synchronous functions
results = await semantic_search(
    query="blocking operations",
    is_async=False,
    n_results=5
)
```

**Filter by base class:**
```python
# Only classes inheriting from specific base
results = await semantic_search(
    query="event handling",
    base_class="EventHandler",
    n_results=10
)
```

### Language-Specific Searches

**Search only Python:**
```python
results = await semantic_search(
    query="async concurrent execution",
    language="py",
    n_results=10
)
```

**Search only TypeScript:**
```python
results = await semantic_search(
    query="type definitions and interfaces",
    language="ts",
    n_results=10
)
```

**Search multiple languages:**
```python
# No language filter = all languages
results = await semantic_search(
    query="REST API endpoint",
    n_results=15
)
```

### Multi-Query Expansion Settings

**Conservative (exact matches preferred):**
```python
results = await multi_query_search(
    query="authentication",
    num_expansions=1,  # Minimal variation
    n_results=5
)
```

**Moderate (balanced):**
```python
results = await multi_query_search(
    query="authentication",
    num_expansions=3,  # Default
    n_results=10
)
```

**Aggressive (find all related):**
```python
results = await multi_query_search(
    query="caching",
    num_expansions=7,  # Many variations
    n_results=20
)
```

### Decomposed Search for Complex Queries

**Breaking down architecturally complex queries:**
```python
# Complex: Multi-service architecture
results = await decomposed_search(
    query="microservice inter-communication with circuit breaker pattern and retry logic",
    n_results=15
)
# Decomposes into: microservices, circuit breaker, retry logic
```

**Breaking down process-heavy queries:**
```python
# Complex: Multi-step process
results = await decomposed_search(
    query="user registration email verification payment processing and account activation",
    n_results=20
)
# Finds each step independently, then combines
```

**Breaking down cross-cutting concern queries:**
```python
# Complex: Multiple aspects
results = await decomposed_search(
    query="database transactions with rollback retry and logging",
    n_results=10
)
# Finds: transactions, rollback, retry, logging separately
```

---

## Summary

### Quick Decision Guide

| Question | Answer | Use |
|----------|--------|-----|
| "What is this code for?" | Concept-based | `semantic_search()` |
| "Find code like this pattern" | Structural | `ast_grep_search()` or `hybrid_search()` |
| "Where is this called from?" | Reference graph | `lsp_find_references()` |
| "Does this file exist?" | Path matching | `glob_files()` |
| "Find function X exactly" | Exact name | `lsp_workspace_symbols()` |
| "Find all implementations of X" | Pattern matching | `semantic_search()` with filters |
| "I'm not sure what I need" | Exploration | `enhanced_search()` (auto-selects) |

### Performance Checklist

- [ ] Use `mxbai` or `ollama` for development (fast)
- [ ] Use `gemini` for production (best quality)
- [ ] Index once, reuse for multiple queries
- [ ] Use file watcher for auto-reindexing
- [ ] Add filters (language, node_type) to reduce results
- [ ] Use `decomposed_search()` for complex queries
- [ ] Use `multi_query_search()` if few results

### Best Practices

1. **Be specific in queries** - Add context words
2. **Use filters liberally** - Language, node_type narrow results
3. **Choose right search function** - Semantic ≠ exact matching
4. **Keep index fresh** - Use file watcher in development
5. **Monitor relevance scores** - <0.6 is too fuzzy
6. **Combine strategies** - Semantic + grep + AST for best results
7. **Profile performance** - Know your provider's latency
8. **Cache results** - Reuse index across queries

---

## See Also

- [Quick Start Guide](./SEMANTIC_SEARCH_QUICK_START.md) - Get started in 5 minutes
- [Indexing Index](./SEMANTIC_INDEXING_INDEX.md) - System overview
- [File Watcher Usage](./SEMANTIC_WATCHER_USAGE.md) - Auto-indexing setup
- [USAGE.md](./USAGE.md) - All MCP tool reference
- [Explore Agent](../.claude/agents/explore.md) - How agents use semantic search

---

**Last Updated:** January 7, 2026  
**Status:** Comprehensive best practices guide complete
