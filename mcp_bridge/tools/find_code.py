"""
Smart code search routing tool.

Automatically routes queries to the optimal search strategy:
- AST patterns (e.g., "class $X", "def $FUNC") → ast_grep_search
- Natural language (e.g., "authentication logic") → semantic_search
- Complex queries (e.g., "JWT AND middleware") → hybrid_search
"""

import re
from typing import Literal

# Import search tools
from mcp_bridge.tools.code_search import ast_grep_search, grep_search
from mcp_bridge.tools.semantic_search import semantic_search, hybrid_search


SearchType = Literal["auto", "exact", "semantic", "hybrid", "ast", "grep"]


def has_ast_pattern(query: str) -> bool:
    """
    Detect if query contains AST-grep pattern syntax.

    AST-grep patterns use metavariables ($VAR, $$$) and structural markers.

    Examples:
        - "class $NAME" → True (has metavariable)
        - "def $FUNC($$$):" → True (has metavariable and wildcard)
        - "interface{}" → True (structural pattern)
        - "find auth code" → False (natural language)
    """
    # AST-grep metavariable patterns
    if re.search(r'\$[A-Z_]+', query):  # $VAR, $NAME, etc.
        return True
    if re.search(r'\$\$\$', query):  # Wildcard args
        return True

    # Common structural patterns (without natural language words)
    structural_keywords = [
        r'\bclass\s+\w+\s*[:{(]',  # class Foo: or class Foo {
        r'\bdef\s+\w+\s*\(',        # def func(
        r'\bfunction\s+\w+\s*\(',   # function func(
        r'\binterface\s+\w+\s*[{<]', # interface Foo {
        r'\bstruct\s+\w+\s*[{<]',   # struct Foo {
    ]

    for pattern in structural_keywords:
        if re.search(pattern, query):
            # Only if it looks like code, not prose
            # "class Foo:" is code, "class that handles auth" is prose
            if not re.search(r'\b(that|which|handles|manages|for|with|the)\b', query, re.IGNORECASE):
                return True

    return False


def has_boolean_operators(query: str) -> bool:
    """
    Detect boolean operators indicating complex query logic.

    Examples:
        - "JWT AND middleware" → True
        - "auth OR login" → True
        - "NOT deprecated" → True
        - "authentication logic" → False
    """
    # Match boolean operators (case-insensitive, word boundaries)
    return bool(re.search(r'\b(AND|OR|NOT)\b', query, re.IGNORECASE))


def is_natural_language(query: str) -> bool:
    """
    Detect if query is natural language vs code pattern.

    Natural language queries use prose phrases, not code syntax.

    Examples:
        - "find authentication logic" → True
        - "error handling patterns" → True
        - "class $NAME" → False (AST pattern)
        - "JWT middleware" → True (conceptual)
    """
    # If it's an AST pattern, it's not natural language
    if has_ast_pattern(query):
        return False

    # Natural language indicators
    nl_indicators = [
        r'\b(find|search|look for|locate|where|show|get)\b',  # Action verbs
        r'\b(all|any|every|some)\b',  # Quantifiers
        r'\b(that|which|with|using|for)\b',  # Connectors
        r'\b(logic|code|pattern|implementation|function|method|class)\b',  # Meta terms
        r'\b(how|what|when|why)\b',  # Question words
    ]

    for pattern in nl_indicators:
        if re.search(pattern, query, re.IGNORECASE):
            return True

    # If query has spaces and no code symbols, likely natural language
    if ' ' in query and not re.search(r'[(){}\[\]<>;,]', query):
        return True

    return False


def detect_search_type(query: str) -> SearchType:
    """
    Auto-detect optimal search type based on query pattern.

    Detection logic:
    1. AST pattern → "ast" (ast_grep_search)
    2. Boolean operators + natural language → "hybrid" (hybrid_search)
    3. Natural language → "semantic" (semantic_search)
    4. Simple text → "grep" (grep_search)

    Args:
        query: Search query string

    Returns:
        Detected search type (ast/hybrid/semantic/grep)
    """
    # Priority 1: AST patterns
    if has_ast_pattern(query):
        return "ast"

    # Priority 2: Complex boolean queries
    if has_boolean_operators(query):
        return "hybrid"

    # Priority 3: Natural language
    if is_natural_language(query):
        return "semantic"

    # Default: Simple text search
    return "grep"


async def find_code(
    query: str,
    search_type: SearchType = "auto",
    project_path: str = ".",
    language: str | None = None,
    n_results: int = 10,
    provider: str = "ollama",
) -> str:
    """
    Smart code search with automatic routing to optimal search strategy.

    Automatically detects whether query is:
    - AST pattern (e.g., "class $X") → routes to ast_grep_search
    - Natural language (e.g., "auth logic") → routes to semantic_search
    - Complex query (e.g., "JWT AND middleware") → routes to hybrid_search
    - Simple text → routes to grep_search

    Args:
        query: Search query (pattern or natural language)
        search_type: Search strategy ("auto" for detection, or "ast"/"semantic"/"hybrid"/"grep")
        project_path: Path to project root (default: ".")
        language: Filter by language (e.g., "py", "ts", "js")
        n_results: Maximum results to return (default: 10)
        provider: Embedding provider for semantic search (default: "ollama")

    Returns:
        Formatted search results with file paths and code snippets.

    Examples:
        # AST pattern search (auto-detected)
        find_code("class $NAME")

        # Semantic search (auto-detected)
        find_code("authentication logic")

        # Hybrid search (auto-detected)
        find_code("JWT AND middleware")

        # Force specific search type
        find_code("error handling", search_type="semantic")
    """
    # Auto-detect search type if requested
    if search_type == "auto":
        detected_type = detect_search_type(query)
        search_type = detected_type

    # Route to appropriate search tool
    if search_type == "ast":
        # AST-grep search for structural patterns
        return await ast_grep_search(
            pattern=query,
            directory=project_path,
            language=language or "",
        )

    elif search_type == "semantic":
        # Semantic search for natural language queries
        return await semantic_search(
            query=query,
            project_path=project_path,
            n_results=n_results,
            language=language,
            provider=provider,  # type: ignore
        )

    elif search_type == "hybrid":
        # Hybrid search for complex queries
        # Parse boolean operators into pattern if possible
        pattern = None
        if has_boolean_operators(query):
            # For now, pass full query to semantic, rely on hybrid's logic
            # Future: parse "JWT AND middleware" into pattern
            pass

        return await hybrid_search(
            query=query,
            pattern=pattern,
            project_path=project_path,
            n_results=n_results,
            language=language,
            provider=provider,  # type: ignore
        )

    elif search_type in ("grep", "exact"):
        # Text-based grep search
        file_pattern = ""
        if language:
            # Map language to file extension
            lang_map = {
                "py": "*.py",
                "python": "*.py",
                "ts": "*.ts",
                "typescript": "*.ts",
                "js": "*.js",
                "javascript": "*.js",
                "tsx": "*.tsx",
                "jsx": "*.jsx",
                "go": "*.go",
                "rust": "*.rs",
                "java": "*.java",
                "cpp": "*.cpp",
                "c": "*.c",
            }
            file_pattern = lang_map.get(language.lower(), f"*.{language}")

        return await grep_search(
            pattern=query,
            directory=project_path,
            file_pattern=file_pattern,
        )

    else:
        return f"Error: Unknown search_type '{search_type}'. Use 'auto', 'ast', 'semantic', 'hybrid', or 'grep'."


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    # Test pattern detection
    test_cases = [
        ("class $NAME", "ast"),
        ("def $FUNC($$$):", "ast"),
        ("find authentication logic", "semantic"),
        ("error handling patterns", "semantic"),
        ("JWT AND middleware", "hybrid"),
        ("auth OR login", "hybrid"),
        ("import os", "grep"),
    ]

    print("Pattern Detection Tests:")
    print("=" * 60)
    for query, expected in test_cases:
        detected = detect_search_type(query)
        status = "✅" if detected == expected else "❌"
        print(f"{status} '{query}' → {detected} (expected: {expected})")

    # Test actual search (requires running codebase)
    async def test_search():
        print("\n\nSearch Tests:")
        print("=" * 60)

        # Test semantic search
        result = await find_code("authentication logic", search_type="auto")
        print(f"\nQuery: 'authentication logic'")
        print(f"Result: {result[:200]}...")

    # Uncomment to run tests
    # asyncio.run(test_search())
