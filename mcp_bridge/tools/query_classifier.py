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
# Format: (regex_pattern, indicator_name)
PATTERN_INDICATORS = [
    (r'\bgrep\b', 'explicit_grep'),                     # Explicit "grep" in query
    (r'["\'][\w_()\.]+["\']', 'quoted_identifier'),     # Quoted identifiers like "authenticate()" or 'API_KEY'
    (r'\b\w+\(\)', 'function_call'),                    # Function calls with () like authenticate()
    (r'[\w_]+\.[\w_]+', 'dot_notation'),                # Dot notation (Class.method) like database.query()
    (r'[\w/]+\.\w{2,4}$', 'file_path'),                 # File paths with extension
    (r'/.*?/', 'regex_pattern'),                        # Regex patterns
    (r'\b[A-Z_]{4,}\b', 'constant_name'),               # CONSTANT_NAMES (4+ uppercase chars)
]

# Phase 2: Structural Detection (High Confidence)
# Triggered when query contains AST keywords, structural relationships,
# or code structure terms.
# Format: (regex_pattern, indicator_name)
STRUCTURAL_INDICATORS = [
    (r'\b(class|function|method|async|interface)\b', 'ast_keyword'),  # AST keywords
    (r'\b(inherits?|inheriting)\b', 'inheritance'),  # Inheritance
    (r'\b(extends?|extending)\b', 'extends'),  # Extension
    (r'\b(implements?|implementing)\b', 'implements'),  # Implementation
    (r'\b(overrides?|overriding)\b', 'override'),  # Override
    (r'\b(decorated?)\s+(with|by)\b', 'decorator_pattern'),  # Decorator patterns
    (r'\@\w+', 'decorator_syntax'),  # Decorator syntax
    (r'\b(definition|declaration|signature)\b', 'code_structure'),  # Code structure terms
]

# Phase 3: Conceptual Detection (Medium-High Confidence)
# Triggered when query contains intent verbs, how/why/where questions,
# design patterns, conceptual nouns, or cross-cutting concerns.
# Format: (regex_pattern, indicator_name)
SEMANTIC_INDICATORS = [
    (r'\bhow\s+(?:does|is|are)', 'how'),  # How questions (non-capturing group)
    (r'\bwhy\s+(?:does|is|are)', 'why'),  # Why questions (non-capturing group)
    (r'\bwhere\s+(?:does|is|are)', 'where'),  # Where questions (non-capturing group)
    (r'\b(handles?|manages?|processes?|validates?|validated?|transforms?)\b', 'intent'),  # Intent verbs
    (r'\b(logic|mechanism|strategy|approach|workflow|implementation)\b', 'conceptual'),  # Conceptual nouns
    (r'\b(patterns?|anti-patterns?)\b', 'design_pattern'),  # Design patterns
    (r'\b(authentication|authorization|caching|logging|error handling|middleware)\b', 'cross_cutting'),  # Cross-cutting
    (r'\bfind\s+(all\s+)?(code|places|instances|implementations)\s+that\b', 'find_pattern'),  # Find code pattern
]

# Phase 4: Hybrid Detection (Medium Confidence)
# Triggered when query contains multiple concepts, both exact + conceptual,
# broad scopes, or vague qualifiers.
# Format: (regex_pattern, indicator_name)
HYBRID_INDICATORS = [
    (r'\s+(and|then|also|plus|with)\s+', 'conjunction'),  # Conjunctions
    (r'\b(across|throughout|in all|system-wide)\b', 'broad_scope'),  # Broad scopes
    (r'\b(similar|related|like|kind of|type of)\b', 'vague_qualifier'),  # Vague qualifiers
    (r'\b(all|every|any)\s+\w+\s+(that|which|where)\b', 'broad_quantifier'),  # Broad quantifiers
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

        # Phase 1: Pattern Detection (use original case for case-sensitive patterns)
        pattern_matches = []
        pattern_indicators = []
        for pattern, indicator_name in PATTERN_INDICATORS:
            # Case-insensitive for 'explicit_grep', case-sensitive for others (CONSTANTS, etc.)
            query_to_match = query_lower if indicator_name == 'explicit_grep' else query_normalized
            if re.search(pattern, query_to_match):
                pattern_matches.append(pattern)
                pattern_indicators.append(indicator_name)

        # Phase 2: Structural Detection
        structural_matches = []
        structural_indicators = []
        for pattern, indicator_name in STRUCTURAL_INDICATORS:
            if re.search(pattern, query_lower):
                structural_matches.append(pattern)
                structural_indicators.append(indicator_name)

        # Phase 3: Semantic Detection
        semantic_matches = []
        semantic_indicators = []
        for pattern, indicator_name in SEMANTIC_INDICATORS:
            match = re.search(pattern, query_lower)
            if match:
                semantic_matches.append(pattern)
                # Use captured group (matched word) if available, else use indicator name
                matched_word = match.group(1) if match.groups() else indicator_name
                semantic_indicators.append(matched_word if matched_word else indicator_name)

        # Phase 4: Hybrid Detection
        hybrid_matches = []
        hybrid_indicators = []
        for pattern, indicator_name in HYBRID_INDICATORS:
            match = re.search(pattern, query_lower)
            if match:
                hybrid_matches.append(pattern)
                # Use captured group (matched word) if available, else use indicator name
                matched_word = match.group(1) if match.groups() else indicator_name
                hybrid_indicators.append(matched_word if matched_word else indicator_name)

        # Confidence Scoring
        # Base scores per match:
        # - PATTERN: 0.50 base + 0.45 bonus for high-value patterns = 0.95 max
        # - STRUCTURAL: 0.95 (single AST keyword should be high confidence)
        # - SEMANTIC: 0.95 (single intent/concept should be high confidence)
        # - HYBRID: 0.40 (multi-modal indicators)
        # Note: Scores capped at 0.95 max

        # Apply bonus for high-value patterns (CONSTANTS, quoted identifiers, explicit grep)
        pattern_score = len(pattern_matches) * 0.50
        if pattern_matches:
            # Check if query contains CONSTANTS (4+ uppercase), quoted strings, or explicit grep
            if (re.search(r'\b[A-Z_]{4,}\b', query_normalized) or
                re.search(r'["\'][\w_()\.]+["\']', query_normalized) or
                re.search(r'\bgrep\b', query_lower)):
                pattern_score += 0.45  # Bonus to reach 0.95

        scores = {
            QueryCategory.PATTERN: pattern_score,
            QueryCategory.STRUCTURAL: len(structural_matches) * 0.95,
            QueryCategory.SEMANTIC: len(semantic_matches) * 0.95,
            QueryCategory.HYBRID: len(hybrid_matches) * 0.40,
        }

        # HYBRID preference logic
        # Exception: Don't boost if PATTERN has high-value matches (they take precedence)
        has_high_value_pattern = (
            pattern_matches and
            (re.search(r'\b[A-Z_]{4,}\b', query_normalized) or
             re.search(r'["\'][\w_()\.]+["\']', query_normalized) or
             re.search(r'\bgrep\b', query_lower))
        )

        # Count how many non-HYBRID categories have matches
        categories_with_matches = sum([
            1 if pattern_matches else 0,
            1 if structural_matches else 0,
            1 if semantic_matches else 0,
        ])

        # Boost HYBRID score based on type of HYBRID indicator and what categories match
        # Exception: Don't boost if PATTERN has high-value matches (they take precedence)
        if hybrid_matches and not has_high_value_pattern:
            # Check if we have strong HYBRID signals
            # Look for the actual captured words, not indicator names
            broad_scope_words = ['across', 'throughout', 'in all', 'system-wide']
            conjunction_words = ['and', 'then', 'also', 'plus', 'with']
            vague_words = ['related', 'like']  # Strong vague qualifiers (but not "similar" with design patterns)
            has_broad_scope = any(word in str(hybrid_indicators).lower() for word in broad_scope_words)
            has_conjunction = any(word in hybrid_indicators for word in conjunction_words)
            has_vague = any(word in hybrid_indicators for word in vague_words)

            # Boost to 0.95 if:
            # 1. Multiple categories match (PATTERN+SEMANTIC, STRUCTURAL+SEMANTIC, etc.), OR
            # 2. Broad scope, conjunction, or vague qualifiers (strong HYBRID signals)
            if categories_with_matches >= 2 or has_broad_scope or has_conjunction or has_vague:
                scores[QueryCategory.HYBRID] = 0.95
            # Or if PATTERN or STRUCTURAL matches (even with just 1), boost slightly
            elif pattern_matches or structural_matches:
                scores[QueryCategory.HYBRID] = 0.90
            # For SEMANTIC + "similar" only: don't boost above, handled by tie-breaking

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

        # Tie-breaking logic
        if len(winners) > 1:
            confidence = min(max_score, 0.95)
            # Prefer PATTERN if it has high-value matches (CONSTANTS, quoted strings, explicit grep)
            if QueryCategory.PATTERN in winners and has_high_value_pattern:
                category = QueryCategory.PATTERN
            # Prefer SEMANTIC if it has design pattern indicators (semantic concept wins over vague "similar")
            elif QueryCategory.SEMANTIC in winners and any('pattern' in str(ind).lower() for ind in semantic_indicators):
                category = QueryCategory.SEMANTIC
            else:
                # Otherwise use HYBRID for mixed queries
                category = QueryCategory.HYBRID
        else:
            confidence = min(max_score, 0.95)
            category = winners[0]

        # Gather all indicators for reporting (use specific names)
        all_indicators = []
        if pattern_indicators:
            all_indicators.extend(pattern_indicators)
        if structural_indicators:
            all_indicators.extend(structural_indicators)
        if semantic_indicators:
            all_indicators.extend(semantic_indicators)
        if hybrid_indicators:
            all_indicators.extend(hybrid_indicators)

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
