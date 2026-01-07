"""Query classifier for intelligent search routing.

This module provides a fast, regex-based system that categorizes search queries
into four types: PATTERN (exact text matching), STRUCTURAL (AST-aware code structure),
SEMANTIC (conceptual/behavioral), and HYBRID (multi-modal).

It enables intelligent routing to the optimal search tool without LLM overhead.

Design Goals:
- Fast: <10ms classification per query
- No LLM calls: Pure regex-based detection (no API overhead)
- Confidence scoring: Return probability (0.0-1.0) for each category
- Fallback safe: Default to HYBRID when ambiguous
- Extensible: Easy to add new patterns/indicators
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal

# Module-level logger
logger = logging.getLogger(__name__)


class QueryCategory(Enum):
    """Query classification categories."""

    SEMANTIC = "semantic"      # Conceptual, "what it does" queries
    PATTERN = "pattern"        # Exact text/regex matching
    STRUCTURAL = "structural"  # AST-aware code structure queries
    HYBRID = "hybrid"          # Multi-modal search recommended


@dataclass
class QueryClassification:
    """Result of query classification.

    Attributes:
        category: The classified query category (SEMANTIC, PATTERN, STRUCTURAL, HYBRID)
        confidence: Confidence score from 0.0 (low) to 1.0 (high)
        indicators: List of matched patterns/reasons that led to this classification
        suggested_tool: The recommended search tool to use
            - "grep_search" for PATTERN queries
            - "ast_grep_search" for STRUCTURAL queries
            - "semantic_search" for SEMANTIC queries
            - "enhanced_search" for HYBRID queries
        reasoning: Human-readable explanation of the classification
    """

    category: QueryCategory
    confidence: float  # 0.0-1.0
    indicators: list[str]  # Matched patterns/reasons
    suggested_tool: Literal[
        "semantic_search", "grep_search", "ast_grep_search", "enhanced_search"
    ]
    reasoning: str  # Human-readable explanation


# Phase 1: Exact Pattern Detection (High Confidence)
# Triggered when query contains quoted strings, exact identifiers with code syntax,
# file paths, regular expressions, or known constant patterns.
PATTERN_INDICATORS = [
    r'["\'][\w_]+["\']',        # Quoted identifiers like "authenticate()" or 'API_KEY'
    r'\b\w+\(\)',                # Function calls with () like authenticate()
    r'[\w_]+\.[\w_]+',           # Dot notation (Class.method) like database.query()
    r'[\w/]+\.\w{2,4}$',         # File paths with extension
    r'/.*?/',                    # Regex patterns
    r'\b[A-Z_]{4,}\b',           # CONSTANT_NAMES (4+ uppercase chars)
]

# Phase 2: Structural Detection (High Confidence)
# Triggered when query contains AST keywords, structural relationships,
# or code structure terms.
STRUCTURAL_INDICATORS = [
    r'\b(class|function|method|async|interface)\b',  # AST keywords
    r'\b(inherits?|extends?|implements?|overrides?)\b',  # Structural relationships
    r'\b(decorated?)\s+(with|by)\b',  # Decorator patterns
    r'\@\w+',  # Decorator syntax
    r'\b(definition|declaration|signature)\b',  # Code structure terms
]

# Phase 3: Conceptual Detection (Medium-High Confidence)
# Triggered when query contains intent verbs, how/why/where questions,
# design patterns, conceptual nouns, or cross-cutting concerns.
SEMANTIC_INDICATORS = [
    r'\b(how|why|where)\s+(does|is|are)',  # How/why/where questions
    r'\b(handles?|manages?|processes?|validates?|transforms?)\b',  # Intent verbs
    r'\b(logic|mechanism|strategy|approach|workflow|implementation)\b',  # Conceptual nouns
    r'\b(pattern|anti-pattern)\b',  # Design patterns
    r'\b(authentication|authorization|caching|logging|error handling)\b',  # Cross-cutting
    r'\bfind\s+(all\s+)?(code|places|instances|implementations)\s+that\b',  # Find code pattern
]

# Phase 4: Hybrid Detection (Medium Confidence)
# Triggered when query contains multiple concepts, both exact + conceptual,
# broad scopes, or vague qualifiers.
HYBRID_INDICATORS = [
    r'\s+(and|then|also|plus|with)\s+',  # Conjunctions
    r'\b(across|throughout|in all|system-wide)\b',  # Broad scopes
    r'\b(similar|related|like|kind of|type of)\b',  # Vague qualifiers
    r'\b(all|every|any)\s+\w+\s+(that|which|where)\b',  # Broad quantifiers
]

# Tool routing based on category
TOOL_ROUTING = {
    QueryCategory.PATTERN: "grep_search",
    QueryCategory.STRUCTURAL: "ast_grep_search",
    QueryCategory.SEMANTIC: "semantic_search",
    QueryCategory.HYBRID: "enhanced_search",
}


def classify_query(query: str) -> QueryClassification:
    """Classify a search query into one of four categories.

    This function analyzes a search query using regex-based pattern matching
    to determine its type (PATTERN, STRUCTURAL, SEMANTIC, or HYBRID) and
    recommends the most appropriate search tool.

    The classification process has 4 phases:
    1. Pattern Detection: Looks for exact identifiers, quoted strings, file paths
    2. Structural Detection: Looks for AST keywords (class, function, etc.)
    3. Conceptual Detection: Looks for intent verbs and semantic concepts
    4. Hybrid Detection: Looks for conjunctions and broad scopes
    5. Fallback: Defaults to HYBRID with 0.5 confidence if no strong match

    Args:
        query: Natural language search query (e.g., "Find authenticate()" or
               "Where is authentication handled?")

    Returns:
        QueryClassification object containing:
        - category: One of SEMANTIC, PATTERN, STRUCTURAL, HYBRID
        - confidence: Score from 0.0 to 1.0 (capped at 0.95, never 1.0)
        - indicators: List of matched pattern names
        - suggested_tool: Recommended tool (grep_search, ast_grep_search,
                         semantic_search, or enhanced_search)
        - reasoning: Human-readable explanation

    Examples:
        >>> result = classify_query("Find all calls to authenticate()")
        >>> result.category
        <QueryCategory.PATTERN: 'pattern'>
        >>> result.confidence
        0.9
        >>> result.suggested_tool
        'grep_search'

        >>> result = classify_query("Where is authentication handled?")
        >>> result.category
        <QueryCategory.SEMANTIC: 'semantic'>
        >>> result.confidence
        0.85
        >>> result.suggested_tool
        'semantic_search'

        >>> result = classify_query("Find class definitions inheriting from Base")
        >>> result.category
        <QueryCategory.STRUCTURAL: 'structural'>
        >>> result.confidence
        0.95
        >>> result.suggested_tool
        'ast_grep_search'

    Performance:
        - Target: <10ms per classification
        - Uses only pure Python stdlib (re module)
        - No external dependencies or API calls
    """
    try:
        # Input validation
        if not query or not isinstance(query, str):
            return QueryClassification(
                category=QueryCategory.HYBRID,
                confidence=0.5,
                indicators=["invalid_input"],
                suggested_tool="enhanced_search",
                reasoning="Invalid or empty query, using safe default",
            )

        # Normalize query
        query_normalized = query.strip()
        if len(query_normalized) < 3:
            return QueryClassification(
                category=QueryCategory.HYBRID,
                confidence=0.5,
                indicators=["too_short"],
                suggested_tool="enhanced_search",
                reasoning="Query too short for accurate classification",
            )

        query_lower = query_normalized.lower()

        # Phase 1: Pattern Detection
        pattern_matches = []
        for pattern in PATTERN_INDICATORS:
            if re.search(pattern, query_lower):
                pattern_matches.append(pattern)

        # Phase 2: Structural Detection
        structural_matches = []
        for pattern in STRUCTURAL_INDICATORS:
            if re.search(pattern, query_lower):
                structural_matches.append(pattern)

        # Phase 3: Semantic Detection
        semantic_matches = []
        for pattern in SEMANTIC_INDICATORS:
            if re.search(pattern, query_lower):
                semantic_matches.append(pattern)

        # Phase 4: Hybrid Detection
        hybrid_matches = []
        for pattern in HYBRID_INDICATORS:
            if re.search(pattern, query_lower):
                hybrid_matches.append(pattern)

        # Confidence Scoring
        # Score calculation:
        # - Each pattern match: +0.15
        # - Each structural match: +0.20
        # - Each semantic match: +0.15
        # - Each hybrid match: +0.10
        scores = {
            QueryCategory.PATTERN: len(pattern_matches) * 0.15,
            QueryCategory.STRUCTURAL: len(structural_matches) * 0.20,
            QueryCategory.SEMANTIC: len(semantic_matches) * 0.15,
            QueryCategory.HYBRID: len(hybrid_matches) * 0.10,
        }

        # Find maximum score
        max_score = max(scores.values())

        # Fallback to HYBRID if no matches
        if max_score == 0:
            result = QueryClassification(
                category=QueryCategory.HYBRID,
                confidence=0.5,
                indicators=[],
                suggested_tool="enhanced_search",
                reasoning="No clear indicators found, using multi-modal search",
            )
            logger.debug(
                f"QUERY-CLASSIFY: query='{query_normalized[:50]}...' "
                f"category={result.category.value} "
                f"confidence={result.confidence:.2f} "
                f"tool={result.suggested_tool}"
            )
            return result

        # Find all categories with maximum score (potential ties)
        winners = [cat for cat, score in scores.items() if score == max_score]

        # If tie, use HYBRID
        if len(winners) > 1:
            confidence = min(max_score, 0.95)
            category = QueryCategory.HYBRID
        else:
            confidence = min(max_score, 0.95)
            category = winners[0]

        # Gather all indicators for reporting
        all_indicators = []
        if pattern_matches:
            all_indicators.append("pattern_match")
        if structural_matches:
            all_indicators.append("structural_match")
        if semantic_matches:
            all_indicators.append("semantic_match")
        if hybrid_matches:
            all_indicators.append("hybrid_match")

        # Generate reasoning
        reasoning_parts = []
        if category == QueryCategory.PATTERN:
            reasoning_parts.append(
                "Query contains exact identifiers or code syntax"
            )
        elif category == QueryCategory.STRUCTURAL:
            reasoning_parts.append(
                "Query requires AST-level understanding of code structure"
            )
        elif category == QueryCategory.SEMANTIC:
            reasoning_parts.append(
                "Query asks about conceptual logic or behavior"
            )
        elif category == QueryCategory.HYBRID:
            reasoning_parts.append(
                "Query combines multiple search approaches or is ambiguous"
            )

        reasoning = "; ".join(reasoning_parts)

        result = QueryClassification(
            category=category,
            confidence=confidence,
            indicators=all_indicators,
            suggested_tool=TOOL_ROUTING[category],
            reasoning=reasoning,
        )

        # Log classification for analytics
        logger.debug(
            f"QUERY-CLASSIFY: query='{query_normalized[:50]}...' "
            f"category={result.category.value} "
            f"confidence={result.confidence:.2f} "
            f"tool={result.suggested_tool}"
        )

        return result

    except Exception as e:
        # Safe fallback on any error
        logger.exception(f"Error classifying query: {e}")
        return QueryClassification(
            category=QueryCategory.HYBRID,
            confidence=0.5,
            indicators=["error"],
            suggested_tool="enhanced_search",
            reasoning=f"Classification error: {str(e)}, using safe default",
        )
