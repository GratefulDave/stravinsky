"""
Tool Search - BM25-based relevance search across MCP tools

Provides intelligent tool discovery using BM25 (Okapi) ranking algorithm.
Enables queries like "find github tools", "search semantic code", etc.

Features:
- BM25Okapi relevance scoring across tool names, descriptions, parameters
- Tag filtering (e.g., "github", "lsp", "semantic")
- Category filtering (e.g., "search", "code", "git")
- Top-K result ranking with scores
- Comprehensive error handling with timeouts
- Query logging for debugging

Architecture:
- Uses rank-bm25 for fast text-based relevance ranking
- Searches across: tool name, description, parameter names, parameter descriptions, tags
- Returns ranked list of tool names with relevance scores
- Supports both broad queries ("find code") and specific queries ("github file search")
"""

import logging
import signal
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import to avoid startup cost
_bm25 = None
_import_lock = None


def get_bm25():
    """Lazy import of rank_bm25."""
    global _bm25, _import_lock
    if _bm25 is None:
        if _import_lock is None:
            import threading

            _import_lock = threading.Lock()

        with _import_lock:
            if _bm25 is None:
                try:
                    from rank_bm25 import BM25Okapi

                    _bm25 = BM25Okapi
                except ImportError as e:
                    raise ImportError(
                        "rank-bm25 is required for tool search. "
                        "Install with: uv add rank-bm25"
                    ) from e
    return _bm25


class TimeoutError(Exception):
    """Raised when tool search times out."""

    pass


@contextmanager
def timeout(seconds: int):
    """Context manager for operation timeout."""

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Tool search timed out after {seconds} seconds")

    # Set the signal handler
    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Restore original handler and cancel alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)


def extract_tool_text(tool: Any) -> str:
    """
    Extract searchable text from a tool definition.

    Args:
        tool: Tool object (Pydantic model from mcp.types) with name, description, inputSchema, etc.

    Returns:
        Combined text for BM25 indexing (lowercased, space-separated).
    """
    parts = []

    # Tool name (most important - add multiple times for weight boost)
    name = getattr(tool, "name", "")
    if name:
        parts.extend([name, name, name])  # Triple weight for name

    # Description (second most important - add twice)
    description = getattr(tool, "description", "")
    if description:
        parts.extend([description, description])

    # Parameter names and descriptions
    input_schema = getattr(tool, "inputSchema", {})
    properties = input_schema.get("properties", {}) if isinstance(input_schema, dict) else {}
    for param_name, param_info in properties.items():
        parts.append(param_name)
        param_desc = param_info.get("description", "") if isinstance(param_info, dict) else ""
        if param_desc:
            parts.append(param_desc)

    # Tags (if present - add twice for importance)
    # Note: tags may be in tool.meta if present
    meta = getattr(tool, "meta", None)
    tags = meta.get("tags", []) if meta and isinstance(meta, dict) else []
    if tags:
        parts.extend(tags)
        parts.extend(tags)  # Double weight for tags

    # Category (if present - add twice)
    category = meta.get("category", "") if meta and isinstance(meta, dict) else ""
    if category:
        parts.extend([category, category])

    # Join and tokenize
    text = " ".join(str(p) for p in parts if p).lower()
    return text


def tokenize(text: str) -> list[str]:
    """
    Simple tokenization for BM25.

    Args:
        text: Input text to tokenize.

    Returns:
        List of lowercase tokens (split on whitespace and punctuation).
    """
    # Replace common punctuation with spaces
    for char in ".,;:!?()[]{}\"'`-_/\\|@#$%^&*+=<>":
        text = text.replace(char, " ")

    # Split on whitespace and filter empty strings
    tokens = [t.lower() for t in text.split() if t.strip()]
    return tokens


def search_tools(
    query: str,
    tools: list[Any],
    top_k: int = 10,
    tag_filter: str | None = None,
    category_filter: str | None = None,
    timeout_seconds: int = 5,
) -> list[dict[str, Any]]:
    """
    Search tools using BM25 relevance ranking.

    Args:
        query: Natural language search query (e.g., "find github tools")
        tools: List of Tool objects (Pydantic models from mcp.types)
        top_k: Maximum number of results to return (default: 10)
        tag_filter: Optional tag to filter by (e.g., "github", "lsp")
        category_filter: Optional category to filter by (e.g., "search", "code")
        timeout_seconds: Maximum execution time (default: 5 seconds)

    Returns:
        List of dicts with keys: name, score, tool (original tool object)
        Sorted by relevance score (highest first).

    Raises:
        TimeoutError: If search exceeds timeout_seconds
        ValueError: If query is empty or tools list is invalid
        ImportError: If rank-bm25 is not installed

    Example:
        >>> tools = [...]  # List of Tool objects from MCP
        >>> results = search_tools("find github tools", tools, top_k=5)
        >>> print(results[0]["name"])  # "github_search"
    """
    # Input validation
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    if not tools or not isinstance(tools, list):
        raise ValueError("Tools must be a non-empty list")

    if top_k <= 0:
        raise ValueError("top_k must be positive")

    logger.info(
        f"Tool search: query='{query}', tools={len(tools)}, "
        f"tag_filter={tag_filter}, category_filter={category_filter}, top_k={top_k}"
    )

    try:
        with timeout(timeout_seconds):
            # Apply filters first (reduce search space)
            filtered_tools = tools
            if tag_filter:
                tag_lower = tag_filter.lower()
                filtered_tools = [
                    t
                    for t in filtered_tools
                    if tag_lower in [
                        tag.lower()
                        for tag in (getattr(t, "meta", {}).get("tags", []) if isinstance(getattr(t, "meta", None), dict) else [])
                    ]
                ]
                logger.debug(f"Tag filter '{tag_filter}' reduced to {len(filtered_tools)} tools")

            if category_filter:
                cat_lower = category_filter.lower()
                filtered_tools = [
                    t for t in filtered_tools
                    if (getattr(t, "meta", {}).get("category", "") if isinstance(getattr(t, "meta", None), dict) else "").lower() == cat_lower
                ]
                logger.debug(
                    f"Category filter '{category_filter}' reduced to {len(filtered_tools)} tools"
                )

            if not filtered_tools:
                logger.warning("No tools remaining after filtering")
                return []

            # Extract and tokenize tool text
            tool_texts = [extract_tool_text(t) for t in filtered_tools]
            tokenized_corpus = [tokenize(text) for text in tool_texts]

            # Initialize BM25
            BM25Okapi = get_bm25()
            bm25 = BM25Okapi(tokenized_corpus)

            # Tokenize query
            query_tokens = tokenize(query)
            logger.debug(f"Query tokens: {query_tokens}")

            # Score all documents
            scores = bm25.get_scores(query_tokens)

            # Create results with scores
            results = [
                {"name": getattr(tool, "name", ""), "score": float(score), "tool": tool}
                for tool, score in zip(filtered_tools, scores)
            ]

            # Sort by score (descending) and take top K
            results.sort(key=lambda x: x["score"], reverse=True)
            top_results = results[:top_k]

            # Log results
            logger.info(
                f"Tool search results: {len(top_results)} tools found "
                f"(top score: {top_results[0]['score']:.2f} if top_results else 0)"
            )
            for i, result in enumerate(top_results[:5], 1):  # Log top 5
                logger.debug(f"  {i}. {result['name']} (score: {result['score']:.2f})")

            return top_results

    except TimeoutError:
        logger.error(f"Tool search timed out after {timeout_seconds}s: query='{query}'")
        raise
    except Exception as e:
        logger.error(f"Tool search failed: query='{query}', error={e}", exc_info=True)
        raise


def search_tool_names(
    query: str,
    tools: list[Any],
    top_k: int = 10,
    tag_filter: str | None = None,
    category_filter: str | None = None,
) -> list[str]:
    """
    Convenience function that returns just tool names (no scores).

    Args:
        query: Search query
        tools: List of Tool objects (Pydantic models from mcp.types)
        top_k: Maximum results
        tag_filter: Optional tag filter
        category_filter: Optional tag filter

    Returns:
        List of tool names ordered by relevance.

    Example:
        >>> tools = [...]  # List of Tool objects
        >>> names = search_tool_names("github search", tools, top_k=5)
        >>> print(names)  # ["github_search", "search_code", ...]
    """
    results = search_tools(query, tools, top_k, tag_filter, category_filter)
    return [r["name"] for r in results]


def format_search_results(results: list[dict[str, Any]], include_scores: bool = True) -> str:
    """
    Format search results for display.

    Args:
        results: List of result dicts from search_tools()
        include_scores: Whether to include relevance scores

    Returns:
        Formatted string for display.

    Example:
        >>> results = search_tools("github", tools)
        >>> print(format_search_results(results))
        Found 3 tools:
        1. github_search (score: 8.52)
        2. github_create_issue (score: 6.31)
        3. search_code (score: 2.14)
    """
    if not results:
        return "No tools found"

    lines = [f"Found {len(results)} tool(s):"]
    for i, result in enumerate(results, 1):
        name = result["name"]
        if include_scores:
            score = result["score"]
            lines.append(f"{i}. {name} (score: {score:.2f})")
        else:
            lines.append(f"{i}. {name}")

    return "\n".join(lines)
