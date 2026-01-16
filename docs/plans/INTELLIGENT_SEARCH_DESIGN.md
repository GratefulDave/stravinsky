# Intelligent Search Wrapper Design Specification

**Status**: Design Complete, Ready for Implementation
**File**: `mcp_bridge/tools/intelligent_search.py`
**Dependencies**: query_classifier, semantic_search, code_search, asyncio

---

## Overview

The `intelligent_search()` function is a unified search interface that automatically routes queries to the optimal search strategy (grep, AST, semantic, or hybrid) based on query classification. It supports multiple execution modes, parallel execution, result deduplication via Reciprocal Rank Fusion, and LRU caching.

**Key Features:**
- **Automatic Routing**: Uses `query_classifier` to select optimal search tool
- **6 Execution Modes**: auto, semantic_first, pattern_first, hybrid, parallel, fast
- **Parallel Execution**: Concurrent search strategies with asyncio
- **Result Deduplication**: RRF (Reciprocal Rank Fusion) for merging ranked lists
- **LRU Caching**: 5-minute TTL, 100 query max size
- **Graceful Degradation**: Falls back if preferred strategy unavailable

---

## Function Signature

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class SearchMatch:
    """Individual search match with metadata."""
    file_path: str              # Absolute path to file
    start_line: int             # Starting line number
    end_line: int               # Ending line number
    code_preview: str           # Code snippet (max 500 chars)
    relevance: float            # Confidence score 0.0-1.0
    strategy: str               # Which strategy found it
    language: str               # Programming language
    node_type: str | None       # Function, class, method, etc.
    metadata: dict              # Additional context

@dataclass
class SearchResult:
    """Aggregated search results from intelligent_search."""
    query: str                  # Original query
    total_matches: int          # Total found across all strategies
    strategies_used: list[str]  # Which strategies were invoked
    execution_time_ms: float    # Total search time
    matches: list[SearchMatch]  # Deduplicated, ranked results
    classification: dict        # Query classification metadata

async def intelligent_search(
    query: str,
    project_path: str = ".",
    mode: Literal["auto", "semantic_first", "pattern_first", "hybrid", "parallel", "fast"] = "auto",
    n_results: int = 10,
    language: str | None = None,
    node_type: str | None = None,
    provider: Literal["ollama", "mxbai", "gemini", "openai", "huggingface"] = "ollama",
    enable_parallel: bool = True,
    confidence_threshold: float = 0.6,
    **kwargs
) -> SearchResult:
    """
    Intelligent search wrapper with automatic strategy selection.

    Args:
        query: Natural language or pattern-based search query
        project_path: Path to project root (default: ".")
        mode: Search execution mode:
            - "auto": Classify query and route automatically (default)
            - "semantic_first": Try semantic, fallback to pattern
            - "pattern_first": Try grep/AST, fallback to semantic
            - "hybrid": Run semantic + AST in parallel, merge with RRF
            - "parallel": Run all strategies concurrently, use RRF
            - "fast": grep only (fastest)
        n_results: Maximum results to return (default: 10)
        language: Filter by language (e.g., 'py', 'ts', 'js')
        node_type: Filter by node type (e.g., 'function', 'class')
        provider: Embedding provider for semantic search
        enable_parallel: Run multiple strategies in parallel when beneficial
        confidence_threshold: Minimum relevance score to include (0.0-1.0)

    Returns:
        SearchResult with deduplicated, ranked matches

    Examples:
        # Auto mode (classify and route)
        >>> await intelligent_search("find authentication logic")
        SearchResult(
            query="find authentication logic",
            total_matches=8,
            strategies_used=["semantic_search"],
            execution_time_ms=450,
            matches=[...],
            classification={"category": "semantic", "confidence": 0.92}
        )

        # Semantic-first mode (fallback to grep if semantic unavailable)
        >>> await intelligent_search("error handling", mode="semantic_first")

        # Parallel mode (run all strategies, merge results)
        >>> await intelligent_search("authentication", mode="parallel", n_results=20)

        # Fast mode (grep only, no classification)
        >>> await intelligent_search("API_KEY", mode="fast")
    """
```

---

## Execution Modes

### Mode 1: Auto (Default)

**Behavior**: Classify query → route to optimal single strategy

```python
async def _mode_auto(query: str, **kwargs) -> SearchResult:
    """Auto mode: classify and route to best strategy."""
    classification = classify_query(query)

    # Route based on classification
    if classification.suggested_tool == "semantic_search":
        results = await semantic_search(query, **kwargs)
        strategy = "semantic"
    elif classification.suggested_tool == "grep_search":
        results = await grep_search(query, **kwargs)
        strategy = "grep"
    elif classification.suggested_tool == "ast_grep_search":
        results = await ast_grep_search(query, **kwargs)
        strategy = "ast"
    else:  # hybrid or enhanced
        results = await enhanced_search(query, **kwargs)
        strategy = "enhanced"

    return SearchResult(
        query=query,
        strategies_used=[strategy],
        matches=results,
        classification=dataclasses.asdict(classification),
        ...
    )
```

### Mode 2: Semantic First

**Behavior**: Try semantic → fallback to grep/AST if semantic unavailable or no results

```python
async def _mode_semantic_first(query: str, **kwargs) -> SearchResult:
    """Try semantic first, fallback to pattern search."""
    try:
        results = await semantic_search(query, **kwargs)
        if results and len(results) > 0:
            return SearchResult(strategies_used=["semantic"], matches=results, ...)

    except Exception as e:
        logger.warning(f"Semantic search failed: {e}, falling back to pattern")

    # Fallback to pattern
    classification = classify_query(query)
    if "class" in query.lower() or "function" in query.lower():
        results = await ast_grep_search(query, **kwargs)
        strategy = "ast"
    else:
        results = await grep_search(query, **kwargs)
        strategy = "grep"

    return SearchResult(strategies_used=["semantic (failed)", strategy], matches=results, ...)
```

### Mode 3: Pattern First

**Behavior**: Try grep/AST → fallback to semantic if no results

```python
async def _mode_pattern_first(query: str, **kwargs) -> SearchResult:
    """Try pattern first, fallback to semantic."""
    # Try pattern strategies
    classification = classify_query(query)

    if classification.category == QueryCategory.STRUCTURAL:
        results = await ast_grep_search(query, **kwargs)
        strategy = "ast"
    else:
        results = await grep_search(query, **kwargs)
        strategy = "grep"

    if results and len(results) > 0:
        return SearchResult(strategies_used=[strategy], matches=results, ...)

    # No results - fallback to semantic
    logger.info(f"Pattern search returned no results, trying semantic")
    results = await semantic_search(query, **kwargs)
    return SearchResult(strategies_used=[strategy, "semantic"], matches=results, ...)
```

### Mode 4: Hybrid

**Behavior**: Run semantic + AST in parallel → merge with RRF

```python
async def _mode_hybrid(query: str, **kwargs) -> SearchResult:
    """Run semantic + AST in parallel, merge results."""
    tasks = [
        semantic_search(query, **kwargs),
        ast_grep_search(query, **kwargs),
    ]

    # Run in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter errors
    valid_results = [r for r in results if not isinstance(r, Exception)]

    # Merge with RRF
    merged = _apply_rrf(valid_results)

    return SearchResult(
        strategies_used=["semantic", "ast"],
        matches=merged,
        ...
    )
```

### Mode 5: Parallel

**Behavior**: Run ALL strategies concurrently → merge with RRF

```python
async def _mode_parallel(query: str, **kwargs) -> SearchResult:
    """Run all strategies in parallel, merge with RRF."""
    tasks = [
        grep_search(query, **kwargs),
        ast_grep_search(query, **kwargs),
        semantic_search(query, **kwargs),
    ]

    # Gather results with timeout
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter errors
    valid_results = [r for r in results if not isinstance(r, Exception)]

    # Merge and deduplicate
    return _merge_results(valid_results, n_results=kwargs.get('n_results', 10))
```

### Mode 6: Fast

**Behavior**: Grep only (no classification, no semantic)

```python
async def _mode_fast(query: str, **kwargs) -> SearchResult:
    """Fast mode: grep only."""
    results = await grep_search(query, **kwargs)
    return SearchResult(
        strategies_used=["grep"],
        matches=results,
        classification=None,
        ...
    )
```

---

## Result Deduplication

### File-Line Deduplication

```python
def _deduplicate_results(
    results: list[SearchMatch],
    n_results: int
) -> list[SearchMatch]:
    """
    Deduplicate and rank search results.

    Strategy:
    1. Group by (file_path, start_line, end_line) tuple
    2. For duplicates, keep highest relevance score
    3. Add strategy annotations to show which tools found it
    4. Apply Reciprocal Rank Fusion (RRF) for cross-strategy scoring
    5. Return top N results
    """

    seen: dict[tuple, SearchMatch] = {}

    for match in results:
        key = (match.file_path, match.start_line, match.end_line)

        if key not in seen:
            seen[key] = match
        else:
            # Merge: boost relevance, combine strategies
            existing = seen[key]
            existing.relevance = max(existing.relevance, match.relevance)
            existing.strategy = f"{existing.strategy} + {match.strategy}"

    # Sort by relevance descending
    ranked = sorted(seen.values(), key=lambda m: m.relevance, reverse=True)

    return ranked[:n_results]
```

### Reciprocal Rank Fusion

For combining results from multiple strategies with different ranking systems:

```python
def _apply_rrf(results: list[list[SearchMatch]], k: int = 60) -> list[SearchMatch]:
    """
    Apply Reciprocal Rank Fusion to merge ranked lists.

    RRF formula: score(d) = Σ 1/(k + rank(d))
    where k=60 is standard constant
    """

    scores: dict[tuple, float] = {}
    matches: dict[tuple, SearchMatch] = {}

    for result_list in results:
        for rank, match in enumerate(result_list):
            key = (match.file_path, match.start_line, match.end_line)
            rrf_score = 1.0 / (k + rank + 1)

            scores[key] = scores.get(key, 0.0) + rrf_score

            if key not in matches or match.relevance > matches[key].relevance:
                matches[key] = match

    # Sort by RRF score
    ranked = sorted(
        matches.items(),
        key=lambda item: scores[item[0]],
        reverse=True
    )

    return [match for _, match in ranked]
```

---

## Error Handling and Fallback

### Provider Unavailability

```python
async def _handle_provider_unavailable(
    query: str,
    preferred_strategy: str,
    **kwargs
) -> SearchResult:
    """Handle cases where preferred search strategy is unavailable."""

    fallback_chain = {
        "semantic": ["ast", "grep"],
        "hybrid": ["semantic", "ast", "grep"],
        "multi_query": ["semantic", "hybrid", "ast"],
    }

    for fallback in fallback_chain.get(preferred_strategy, ["grep"]):
        try:
            logger.info(f"Preferred strategy '{preferred_strategy}' unavailable, trying '{fallback}'")
            return await _route_to_strategy(query, fallback, **kwargs)
        except Exception as e:
            logger.debug(f"Fallback '{fallback}' also failed: {e}")
            continue

    # Ultimate fallback: grep_search (always available)
    return await _run_grep_search(query, **kwargs)
```

### Index Not Found

```python
async def _ensure_index(project_path: str, provider: str) -> bool:
    """Ensure semantic index exists before semantic search."""

    try:
        stats = await semantic_stats(project_path, provider)

        # Check if index exists and is not empty
        if "chunks_indexed" in stats and stats["chunks_indexed"] > 0:
            return True

        # Index doesn't exist or is empty
        logger.info(f"Semantic index not found for {project_path}, creating...")
        await index_codebase(project_path, provider=provider)
        return True

    except Exception as e:
        logger.warning(f"Failed to ensure index: {e}")
        return False
```

---

## Caching Strategy

### Query Cache

```python
class SearchCache:
    """LRU cache for search results."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self._cache: dict[str, tuple[float, SearchResult]] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds

    def get(self, query: str, mode: str, **filters) -> SearchResult | None:
        """Get cached result if exists and not expired."""
        cache_key = self._make_key(query, mode, **filters)

        if cache_key in self._cache:
            timestamp, result = self._cache[cache_key]

            # Check TTL
            if time.time() - timestamp < self._ttl:
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return result
            else:
                # Expired
                del self._cache[cache_key]

        return None

    def put(self, query: str, mode: str, result: SearchResult, **filters):
        """Store result in cache."""
        cache_key = self._make_key(query, mode, **filters)

        # LRU eviction if full
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][0])
            del self._cache[oldest_key]

        self._cache[cache_key] = (time.time(), result)

    @staticmethod
    def _make_key(query: str, mode: str, **filters) -> str:
        """Create cache key from query parameters."""
        import hashlib
        key_parts = [query, mode] + [f"{k}={v}" for k, v in sorted(filters.items())]
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()

# Global cache instance
_search_cache = SearchCache(max_size=100, ttl_seconds=300)
```

---

## Output Format

### String Format

```
🔍 INTELLIGENT-SEARCH: "find authentication logic"
   Classification: conceptual (confidence: 0.92)
   Strategy: semantic_search
   Time: 450ms

Found 8 results:

1. src/auth/oauth.py:45-67 (relevance: 0.94) [semantic]
   ```python
   async def authenticate_user(token: str) -> User:
       """Validate JWT token and return user object."""
       payload = jwt.decode(token, settings.SECRET_KEY)
       return await User.get(id=payload['user_id'])
   ```

2. src/middleware/auth.py:12-28 (relevance: 0.89) [semantic + grep]
   ```python
   class AuthenticationMiddleware:
       async def __call__(self, request):
           token = request.headers.get('Authorization')
           if not token:
               raise Unauthorized()
   ```

[Results from: semantic_search (6), grep_search (2), deduplicated to 8 unique]
```

---

## Integration with MCP Server

### Server Registration

Add to `mcp_bridge/server.py`:

```python
elif name == "intelligent_search":
    from .tools.intelligent_search import intelligent_search

    result_content = await intelligent_search(
        query=arguments["query"],
        project_path=arguments.get("project_path", "."),
        mode=arguments.get("mode", "auto"),
        n_results=arguments.get("n_results", 10),
        language=arguments.get("language"),
        node_type=arguments.get("node_type"),
        provider=arguments.get("provider", "ollama"),
        enable_parallel=arguments.get("enable_parallel", True),
        confidence_threshold=arguments.get("confidence_threshold", 0.6),
    )
```

### Tool Definition

Add to `mcp_bridge/server_tools.py`:

```python
Tool(
    name="intelligent_search",
    description=(
        "Intelligent search wrapper that automatically routes to the best search strategy. "
        "Automatically classifies queries and uses grep, AST, semantic, or hybrid search. "
        "Supports parallel execution and result deduplication. "
        "Use this as the primary search tool for all code discovery needs."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language or pattern-based search query",
            },
            "project_path": {
                "type": "string",
                "description": "Path to the project root",
                "default": ".",
            },
            "mode": {
                "type": "string",
                "description": "Search mode: auto (default), semantic_first, pattern_first, hybrid, parallel, fast",
                "enum": ["auto", "semantic_first", "pattern_first", "hybrid", "parallel", "fast"],
                "default": "auto",
            },
            "n_results": {
                "type": "integer",
                "description": "Maximum number of results to return",
                "default": 10,
            },
            "language": {
                "type": "string",
                "description": "Filter by language (e.g., 'py', 'ts', 'js')",
            },
            "node_type": {
                "type": "string",
                "description": "Filter by node type (e.g., 'function', 'class', 'method')",
            },
            "provider": {
                "type": "string",
                "description": "Embedding provider for semantic search",
                "enum": ["ollama", "mxbai", "gemini", "openai", "huggingface"],
                "default": "ollama",
            },
            "enable_parallel": {
                "type": "boolean",
                "description": "If true, run multiple strategies in parallel when beneficial",
                "default": True,
            },
            "confidence_threshold": {
                "type": "float",
                "description": "Minimum relevance score to include (0.0-1.0)",
                "default": 0.6,
            },
        },
        "required": ["query"],
    },
)
```

---

## Performance Characteristics

### Latency Budget

| Mode | Expected Latency | Max Latency |
|------|------------------|-------------|
| fast | <200ms | 500ms |
| auto (exact match) | <200ms | 500ms |
| auto (structural) | <300ms | 800ms |
| auto (conceptual) | 300-600ms | 2s |
| parallel | 500-800ms | 3s |
| hybrid | 400-700ms | 2s |

### Optimization Strategies

1. **Early termination** - Stop if grep finds high-confidence exact matches
2. **Parallel execution** - Run grep + AST + semantic concurrently
3. **Provider selection** - Use mxbai (local) by default for speed
4. **Result limiting** - Fetch 2x n_results, deduplicate to n_results
5. **Cache aggressively** - 5-minute TTL for query results

---

## Success Criteria

The intelligent_search() wrapper will be considered successful if:

1. **Agents can use single tool** - No need to manually choose grep/AST/semantic
2. **Improved search quality** - Higher relevance scores than single-strategy
3. **Acceptable latency** - <1s for 90% of queries
4. **High cache hit rate** - >60% cache hits for repeated queries
5. **Graceful degradation** - Always returns results even if semantic unavailable

---

## Migration Path

### Phase 1: Add Tool (No Breaking Changes)
- Implement intelligent_search() alongside existing tools
- Add to server.py and server_tools.py
- Update explore.md to mention as alternative

### Phase 2: Update Agent Prompts
- Update explore.md to recommend intelligent_search()
- Add intelligent_search() to other agents (code-reviewer, debugger, delphi)
- Provide migration examples

### Phase 3: Deprecation (Future)
- Mark grep_search, ast_grep_search as "prefer intelligent_search()"
- Eventually remove direct calls in agent prompts

---

## Critical Files for Implementation

Based on this design, the 5 most critical files for implementing intelligent_search():

1. **mcp_bridge/tools/intelligent_search.py** - NEW FILE: Core implementation of intelligent_search() wrapper, query classification, routing logic, and result deduplication

2. **mcp_bridge/server.py** - Dispatch handler: Add elif branch for "intelligent_search" tool (lines 427-525 region for search tools)

3. **mcp_bridge/server_tools.py** - Tool definition: Add Tool() entry for intelligent_search with full schema (after line 958 where enhanced_search ends)

4. **mcp_bridge/tools/semantic_search.py** - Reference pattern: Contains semantic_search(), hybrid_search(), enhanced_search() implementations to follow

5. **mcp_bridge/tools/code_search.py** - Reference pattern: Contains grep_search() and ast_grep_search() implementations that intelligent_search() will call internally

---

**End of Design Document**

This design provides a complete, implementable specification for an intelligent search wrapper that unifies all search strategies behind a single, intuitive interface with automatic routing, parallel execution, and robust error handling.
