# Query Classifier Design Specification

**Status**: Design Complete, Ready for Implementation
**File**: `mcp_bridge/tools/query_classifier.py`
**Dependencies**: Pure Python stdlib only (no external packages)

---

## Overview

The query classifier is a fast, regex-based system that categorizes search queries into four types: PATTERN (exact text matching), STRUCTURAL (AST-aware code structure), SEMANTIC (conceptual/behavioral), and HYBRID (multi-modal). It enables intelligent routing to the optimal search tool without LLM overhead.

**Design Goals:**
1. **Fast**: <10ms classification per query
2. **No LLM calls**: Pure regex-based detection (no API overhead)
3. **Confidence scoring**: Return probability (0.0-1.0) for each category
4. **Fallback safe**: Default to HYBRID when ambiguous
5. **Extensible**: Easy to add new patterns/indicators

---

## Current Limitations

Stravinsky currently has 5 search tools:
1. **grep_search** - Fast text/regex pattern matching
2. **ast_grep_search** - Structural code search (AST-aware)
3. **semantic_search** - Natural language/conceptual queries (embeddings)
4. **hybrid_search** - Combines semantic + AST with weighted fusion
5. **enhanced_search** - Auto-mode selector using complexity heuristics

**Current limitation**: Query classification is basic regex pattern matching in `enhanced_search()` (lines 2152-2154 in semantic_search.py), detecting only explicit conjunctions like "and", "then", "also". This misses many conceptual queries that would benefit from semantic search.

---

## Function Signature

```python
from dataclasses import dataclass
from enum import Enum
from typing import Literal

class QueryCategory(Enum):
    """Query classification categories."""
    SEMANTIC = "semantic"      # Conceptual, "what it does" queries
    PATTERN = "pattern"        # Exact text/regex matching
    STRUCTURAL = "structural"  # AST-aware code structure queries
    HYBRID = "hybrid"          # Multi-modal search recommended

@dataclass
class QueryClassification:
    """Result of query classification."""
    category: QueryCategory
    confidence: float  # 0.0-1.0
    indicators: list[str]  # Matched patterns/reasons
    suggested_tool: Literal["semantic_search", "grep_search", "ast_grep_search", "hybrid_search", "enhanced_search"]
    reasoning: str  # Human-readable explanation

def classify_query(query: str) -> QueryClassification:
    """
    Classify a search query into one of four categories.

    Args:
        query: Natural language search query

    Returns:
        QueryClassification with category, confidence, and routing suggestion

    Examples:
        >>> classify_query("Find all calls to authenticate()")
        QueryClassification(
            category=QueryCategory.PATTERN,
            confidence=0.9,
            indicators=["exact_function_name", "quoted_identifier"],
            suggested_tool="grep_search",
            reasoning="Query contains exact function name with parentheses"
        )

        >>> classify_query("Where is authentication handled?")
        QueryClassification(
            category=QueryCategory.SEMANTIC,
            confidence=0.85,
            indicators=["conceptual_verb", "intent_question"],
            suggested_tool="semantic_search",
            reasoning="Query asks about conceptual logic, not specific identifiers"
        )

        >>> classify_query("Find class definitions inheriting from BaseModel")
        QueryClassification(
            category=QueryCategory.STRUCTURAL,
            confidence=0.95,
            indicators=["ast_keyword", "inheritance_pattern"],
            suggested_tool="ast_grep_search",
            reasoning="Query requires AST-level understanding of class hierarchy"
        )
    """
    pass
```

---

## Classification Algorithm

### Phase 1: Exact Pattern Detection (High Confidence)

#### PATTERN Category

Triggered when query contains:
- Quoted strings: `"authenticate()"`, `'API_KEY'`
- Exact identifiers with code syntax: `authenticate()`, `BaseClass.method()`
- File paths: `src/auth/login.py`, `*.test.js`
- Regular expressions: `/pattern/`, `\bword\b`
- Known variable/constant patterns: `API_KEY`, `DATABASE_URL`, `MAX_RETRIES`

**Regex patterns:**
```python
PATTERN_INDICATORS = [
    r'["\'][\w_]+["\']',           # Quoted identifiers
    r'\b\w+\(\)',                   # Function calls with ()
    r'[\w_]+\.[\w_]+',              # Dot notation (Class.method)
    r'[\w/]+\.\w{2,4}$',            # File paths with extension
    r'/.*?/',                       # Regex patterns
    r'\b[A-Z_]{3,}\b',              # CONSTANT_NAMES
]
```

#### STRUCTURAL Category

Triggered when query contains:
- AST keywords: `class`, `function`, `method`, `decorator`, `async`, `interface`, `extends`, `implements`
- Structural relationships: `inherits from`, `implements`, `overrides`, `decorated with`
- Code structure terms: `definition`, `declaration`, `signature`, `parameters`

**Regex patterns:**
```python
STRUCTURAL_INDICATORS = [
    r'\b(class|function|method|async|interface)\b',
    r'\b(inherits?|extends?|implements?|overrides?)\b',
    r'\bdecorated?\s+(with|by)\b',
    r'\@\w+',                       # Decorator syntax
    r'\b(definition|declaration|signature)\b',
]
```

### Phase 2: Conceptual Detection (Medium-High Confidence)

#### SEMANTIC Category

Triggered when query contains:
- Intent verbs: `handles`, `manages`, `processes`, `validates`, `transforms`
- How/why/where questions: `How does`, `Why is`, `Where is ... handled`
- Design patterns: `factory pattern`, `singleton`, `middleware`, `observer`
- Conceptual nouns: `logic`, `mechanism`, `strategy`, `approach`, `implementation`
- Cross-cutting concerns: `error handling`, `logging`, `caching`, `authentication`

**Regex patterns:**
```python
SEMANTIC_INDICATORS = [
    r'\b(how|why|where)\s+(does|is|are)',
    r'\b(handles?|manages?|processes?|validates?|transforms?)\b',
    r'\b(logic|mechanism|strategy|approach|workflow)\b',
    r'\b(pattern|anti-pattern)\b',
    r'\b(authentication|authorization|caching|logging|error handling)\b',
    r'\bfind\s+(all\s+)?(code|places|instances)\s+that\b',
]
```

### Phase 3: Hybrid Detection (Medium Confidence)

#### HYBRID Category

Triggered when query contains:
- Multiple concepts: `and`, `then`, `also`, `with`, conjunctions
- Both exact + conceptual: `Find authenticate() function and all error handling`
- Broad scopes: `across the codebase`, `in all modules`, `system-wide`
- Vague qualifiers: `similar`, `related`, `like`, `kind of`

**Regex patterns:**
```python
HYBRID_INDICATORS = [
    r'\s+(and|then|also|plus|with)\s+',
    r'\b(across|throughout|in all|system-wide)\b',
    r'\b(similar|related|like|kind of|type of)\b',
    r'\b(all|every|any)\s+\w+\s+(that|which|where)\b',
]
```

### Phase 4: Fallback Logic

If no strong indicators match:
- Default to **HYBRID** with confidence 0.5
- Reasoning: "Ambiguous query, using multi-modal search"

---

## Confidence Scoring

```python
def calculate_confidence(indicators: dict[str, list[str]]) -> tuple[QueryCategory, float]:
    """
    Calculate confidence score based on matched indicators.

    Scoring:
    - Each pattern match: +0.15
    - Each structural match: +0.20
    - Each semantic match: +0.15
    - Each hybrid match: +0.10

    Max confidence capped at 0.95 (never 1.0, always some uncertainty)
    """
    scores = {
        QueryCategory.PATTERN: len(indicators.get("pattern", [])) * 0.15,
        QueryCategory.STRUCTURAL: len(indicators.get("structural", [])) * 0.20,
        QueryCategory.SEMANTIC: len(indicators.get("semantic", [])) * 0.15,
        QueryCategory.HYBRID: len(indicators.get("hybrid", [])) * 0.10,
    }

    # Winner takes all, but check for ties
    max_score = max(scores.values())
    if max_score == 0:
        return QueryCategory.HYBRID, 0.5

    winners = [cat for cat, score in scores.items() if score == max_score]
    if len(winners) > 1:
        # Tie - default to HYBRID
        return QueryCategory.HYBRID, min(max_score, 0.95)

    return winners[0], min(max_score, 0.95)
```

---

## Tool Routing Logic

```python
TOOL_ROUTING = {
    QueryCategory.PATTERN: "grep_search",
    QueryCategory.STRUCTURAL: "ast_grep_search",
    QueryCategory.SEMANTIC: "semantic_search",
    QueryCategory.HYBRID: "enhanced_search",  # Auto-mode selector
}
```

---

## Test Cases (20+ Examples)

### PATTERN Category (grep_search)

| Query | Confidence | Indicators | Reasoning |
|-------|-----------|-----------|-----------|
| `Find "authenticate()"` | 0.90 | quoted_identifier, function_call | Exact quoted function name |
| `Where is API_KEY used?` | 0.75 | constant_name | Known constant pattern |
| `Search for database.query()` | 0.90 | function_call, dot_notation | Exact method call syntax |
| `Find all TODO comments` | 0.75 | quoted_identifier | Literal string match |
| `grep for import Flask` | 0.90 | exact_import | Explicit grep request |

### STRUCTURAL Category (ast_grep_search)

| Query | Confidence | Indicators | Reasoning |
|-------|-----------|-----------|-----------|
| `Find class definitions` | 0.95 | ast_keyword | Explicit AST structure query |
| `All async functions` | 0.90 | ast_keyword | Language-specific keyword |
| `Classes inheriting from Base` | 0.95 | inheritance_pattern | Requires AST understanding |
| `Functions decorated with @requires_auth` | 0.95 | decorator_pattern | Decorator syntax |
| `Methods overriding render()` | 0.90 | override_pattern | OOP structure |

### SEMANTIC Category (semantic_search)

| Query | Confidence | Indicators | Reasoning |
|-------|-----------|-----------|-----------|
| `Find authentication logic` | 0.85 | conceptual_noun, cross_cutting | Conceptual, not literal |
| `Where is error handling done?` | 0.85 | intent_question, cross_cutting | Asks about behavior |
| `How does caching work?` | 0.90 | how_question, conceptual | Mechanism inquiry |
| `Find rate limiting implementation` | 0.80 | conceptual_noun | Design pattern search |
| `Where are permissions validated?` | 0.85 | intent_verb, semantic_verb | Action-based query |
| `Code that handles JWT tokens` | 0.80 | handles_pattern | Conceptual relationship |
| `Find middleware` | 0.75 | design_pattern | Architectural concept |
| `Similar error patterns` | 0.80 | similarity_indicator | Semantic similarity |

### HYBRID Category (enhanced_search)

| Query | Confidence | Indicators | Reasoning |
|-------|-----------|-----------|-----------|
| `Find authenticate() and error handling` | 0.85 | conjunction, mixed_types | Exact + conceptual |
| `All classes that implement caching` | 0.80 | broad_scope, structural + semantic | Structure + concept |
| `System-wide authentication checks` | 0.75 | broad_scope, vague_qualifier | Wide scope query |
| `Related authentication code` | 0.70 | vague_qualifier | Similarity-based |
| `Functions like validate_token()` | 0.75 | similarity_indicator | Pattern + semantic |

### AMBIGUOUS (Defaults to HYBRID with 0.5 confidence)

| Query | Confidence | Indicators | Reasoning |
|-------|-----------|-----------|-----------|
| `Find auth` | 0.50 | none | Too vague, use hybrid |
| `Search X` | 0.50 | none | Generic, unclear intent |
| `Code` | 0.50 | none | No context, use hybrid |

---

## Integration Points

### 1. Enhanced Search (Primary Integration)

**File**: `mcp_bridge/tools/semantic_search.py`
**Function**: `enhanced_search()` (line 2124)

**Current logic** (lines 2152-2154):
```python
# Detect query complexity
complex_indicators = [" and ", " then ", " also ", " with ", ", then", ". then", "; "]
is_complex = any(ind in query.lower() for ind in complex_indicators)
```

**Proposed replacement**:
```python
# Use query classifier
from mcp_bridge.tools.query_classifier import classify_query

classification = classify_query(query)

# Route based on classification
if classification.suggested_tool == "semantic_search":
    return await semantic_search(...)
elif classification.suggested_tool == "grep_search":
    return await grep_search(...)
elif classification.suggested_tool == "ast_grep_search":
    return await ast_grep_search(...)
else:  # hybrid or enhanced
    # Existing enhanced_search logic
    ...
```

### 2. Hybrid Search Enhancement

**File**: `mcp_bridge/tools/semantic_search.py`
**Function**: `hybrid_search()` (line 1502)

**Enhancement**: Use classifier to decide semantic vs AST weighting
```python
classification = classify_query(query)
if classification.category == QueryCategory.SEMANTIC:
    # Boost semantic results
    semantic_weight = 0.7
    ast_weight = 0.3
elif classification.category == QueryCategory.STRUCTURAL:
    # Boost AST results
    semantic_weight = 0.3
    ast_weight = 0.7
else:
    # Equal weighting
    semantic_weight = 0.5
    ast_weight = 0.5
```

### 3. Explore Agent Integration

**File**: `.claude/agents/explore.md`
**Section**: Search Strategy (lines 46-100)

**Enhancement**: Add pre-classification step
```markdown
### Search Strategy with Query Classification

1. **Classify the query** using query_classifier
2. **Route to optimal tool** based on classification:
   - PATTERN → grep_search (fastest for exact matches)
   - STRUCTURAL → ast_grep_search (AST-aware)
   - SEMANTIC → semantic_search (conceptual)
   - HYBRID → enhanced_search (auto-mode)
3. **Execute search** with appropriate parameters
4. **Synthesize results** and return findings
```

### 4. Stravinsky Orchestrator

**Integration**: Add classifier to task planning
- Classify user queries before spawning agents
- Route to appropriate agent based on classification
- Log classification for analytics

---

## Performance Requirements

### Latency
- **Target**: <10ms per classification
- **P95**: <15ms
- **P99**: <25ms

### Accuracy (Manual Validation)
- **Pattern queries**: >90% correct classification
- **Structural queries**: >85% correct classification
- **Semantic queries**: >80% correct classification
- **Hybrid queries**: >75% correct classification

### Benchmarking

```python
import time
import statistics

def benchmark_classifier(test_cases: list[str], iterations: int = 1000):
    """Benchmark classification performance."""
    times = []
    for _ in range(iterations):
        for query in test_cases:
            start = time.perf_counter()
            classify_query(query)
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)

    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "p95": statistics.quantiles(times, n=20)[18],  # 95th percentile
        "p99": statistics.quantiles(times, n=100)[98],  # 99th percentile
        "max": max(times),
    }
```

---

## Error Handling

```python
def classify_query(query: str) -> QueryClassification:
    """Classify with robust error handling."""
    try:
        if not query or not isinstance(query, str):
            return QueryClassification(
                category=QueryCategory.HYBRID,
                confidence=0.5,
                indicators=["invalid_input"],
                suggested_tool="enhanced_search",
                reasoning="Invalid or empty query, using safe default"
            )

        # Normalize query
        query = query.strip().lower()
        if len(query) < 3:
            return QueryClassification(
                category=QueryCategory.HYBRID,
                confidence=0.5,
                indicators=["too_short"],
                suggested_tool="enhanced_search",
                reasoning="Query too short for accurate classification"
            )

        # Main classification logic...

    except Exception as e:
        # Safe fallback on any error
        return QueryClassification(
            category=QueryCategory.HYBRID,
            confidence=0.5,
            indicators=["error"],
            suggested_tool="enhanced_search",
            reasoning=f"Classification error: {str(e)}, using safe default"
        )
```

---

## Logging and Analytics

```python
import logging

logger = logging.getLogger(__name__)

def classify_query(query: str) -> QueryClassification:
    """Classify with telemetry."""
    result = _classify_internal(query)

    # Log classification for analytics
    logger.debug(
        f"QUERY-CLASSIFY: query='{query[:50]}...' "
        f"category={result.category.value} "
        f"confidence={result.confidence:.2f} "
        f"tool={result.suggested_tool}"
    )

    return result
```

---

## Future Enhancements

1. **ML-based classification** (requires training data)
   - Collect classified queries from production
   - Train lightweight model (scikit-learn)
   - Fallback to regex if model unavailable

2. **User feedback loop**
   - Track search success rates by classification
   - Adjust confidence thresholds based on accuracy
   - Learn from user corrections

3. **Context-aware classification**
   - Consider previous queries in session
   - Adjust based on codebase language/framework
   - Domain-specific pattern libraries

4. **Multi-language support**
   - Language-specific structural patterns
   - Framework-aware classification (Django, React, etc.)
   - Package ecosystem patterns (npm, PyPI)

---

## Critical Files for Implementation

### 1. `mcp_bridge/tools/semantic_search.py`
**Reason**: Primary integration point - Houses `enhanced_search()`, `hybrid_search()`, and all search functions. Classifier will be imported and used here to replace basic regex logic.

### 2. `mcp_bridge/tools/code_search.py`
**Reason**: Contains `grep_search()` and `ast_grep_search()` implementations. Classifier needs to understand these tools' capabilities to make correct routing decisions.

### 3. `.claude/agents/explore.md`
**Reason**: Documents current search strategy. Needs update to reflect classifier-driven search routing. Shows exact patterns agents currently use.

### 4. `docs/SEARCH_TOOLS_ANALYSIS.md`
**Reason**: Comprehensive analysis of current search tool usage patterns. Contains real-world query examples that should inform test cases.

### 5. `mcp_bridge/tools/__init__.py`
**Reason**: Module initialization - Classifier will be exported from here for use across the codebase.

---

**End of Design Document**

This design provides a complete, implementable specification for a fast, regex-based query classifier that can be coded without ambiguity. The classifier will significantly improve search routing in the Stravinsky codebase by intelligently directing queries to the optimal tool based on their characteristics.
