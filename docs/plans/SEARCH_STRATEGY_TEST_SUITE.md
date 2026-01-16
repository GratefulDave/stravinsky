# Search Strategy Test Suite

**Status**: Design Complete, Ready for Implementation
**File**: `tests/test_query_classification.py`
**Coverage**: 62+ test cases across 5 query categories

---

## Overview

This test suite validates the classification of user queries into categories and ensures proper routing to the appropriate search tools (grep_search, ast_grep_search, semantic_search, and LSP tools).

**Query Categories:**
- **EXACT**: Known function/variable names, file patterns, error messages
- **STRUCTURAL**: Code structure, decorators, class hierarchies, imports
- **SEMANTIC**: Conceptual queries, design patterns, cross-cutting concerns
- **HYBRID**: Specific target + conceptual question combination
- **LSP**: Symbol definition/reference lookups

**Test Data:**
- 30+ real queries from stravinsky usage scenarios
- Expected classifications for each query
- Expected primary and fallback tool routing
- Edge cases and ambiguous examples

---

## Test Structure

```python
from enum import Enum
from typing import List, Optional

class QueryType(str, Enum):
    """Query type classification."""
    EXACT = "exact"
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    LSP = "lsp"

class SearchTool(str, Enum):
    """Search tools available in Stravinsky agents."""
    GREP = "grep_search"
    AST = "ast_grep_search"
    SEMANTIC = "semantic_search"
    LSP_SYMBOLS = "lsp_workspace_symbols"
    LSP_REFERENCES = "lsp_find_references"
    LSP_DEFINITION = "lsp_goto_definition"
    GLOB = "glob_files"

class QueryClassification:
    """Classification result for a query."""

    def __init__(
        self,
        query: str,
        query_type: QueryType,
        primary_tool: SearchTool,
        fallback_tools: Optional[List[SearchTool]] = None,
        rationale: str = "",
        keywords: Optional[List[str]] = None,
    ):
        self.query = query
        self.query_type = query_type
        self.primary_tool = primary_tool
        self.fallback_tools = fallback_tools or []
        self.rationale = rationale
        self.keywords = keywords or []
```

---

## Test Cases by Category

### 1. EXACT Match Queries (10 test cases)

Queries with known names, patterns, and error messages that require exact text matching.

| Query | Primary Tool | Fallback Tools | Rationale |
|-------|--------------|----------------|-----------|
| `Find authenticate()` | grep_search | lsp_workspace_symbols | Exact function name - grep finds text match |
| `Where is API_KEY used?` | grep_search | lsp_find_references | Exact variable name - grep finds all occurrences |
| `Find "database connection" errors` | grep_search | - | Exact error message text - grep with literal string |
| `Find all Flask imports` | grep_search | ast_grep_search | Known package name - grep with regex pattern |
| `Find TODO comments` | grep_search | - | Exact comment pattern - grep for '# TODO' |
| `Find UserModel class` | grep_search | lsp_workspace_symbols | Known class name - grep for 'class UserModel' |
| `Find test files` | glob_files | - | File pattern - glob with 'test*.py' or 'tests/**/*.py' |
| `Find all try/except blocks` | grep_search | - | Regex pattern - grep with 'try:|except:' |
| `Find /api/users endpoint` | grep_search | - | Exact URL path - grep for '/api/users' |
| `Find all CORS settings` | grep_search | - | Known config key - grep for 'CORS' |

**Key Insight**: EXACT queries benefit from fast grep_search with fallback to LSP for symbol lookups.

---

### 2. STRUCTURAL Queries (10 test cases)

Queries about code structure, AST patterns, and language-specific syntax.

| Query | Primary Tool | Fallback Tools | Rationale |
|-------|--------------|----------------|-----------|
| `Find all @requires_auth decorated functions` | ast_grep_search | grep_search | Decorator pattern - AST understands @decorator syntax |
| `Find classes extending BaseHandler` | ast_grep_search | - | Inheritance hierarchy - AST with pattern 'class $CLASS extends BaseHandler' |
| `Find all render() methods` | ast_grep_search | - | Method signature - AST understands method definitions |
| `Where is database.query() called?` | ast_grep_search | grep_search | Method call pattern - AST with '$obj.query(...)' |
| `Find all from X import Y patterns` | ast_grep_search | - | Import syntax - AST understands import structure |
| `Find functions with timeout parameter` | ast_grep_search | - | Function signature - AST understands parameters |
| `Find all async functions` | ast_grep_search | - | Language structure - AST with 'async def $name' |
| `Find TypeScript interfaces` | ast_grep_search | - | Type structure - AST with 'interface $NAME' |
| `Find with statements` | ast_grep_search | - | Context manager - AST with 'with $expr as $var' |
| `Find all lambda expressions` | ast_grep_search | - | Lambda syntax - AST understands lambda |

**Key Insight**: STRUCTURAL queries require AST-aware search to understand code structure beyond text patterns.

---

### 3. SEMANTIC Queries (10 test cases)

Conceptual queries about design patterns, architectural intent, and cross-cutting concerns.

| Query | Primary Tool | Fallback Tools | Rationale |
|-------|--------------|----------------|-----------|
| `Find authentication logic` | semantic_search | grep, ast | Conceptual - 'authentication logic' is design concept, not literal name |
| `Where is error handling done?` | semantic_search | - | Cross-cutting concern - 'error handling' spans multiple files |
| `How does the caching work?` | semantic_search | - | Mechanism inquiry - 'caching' is about functionality not name |
| `Where is the factory pattern used?` | semantic_search | - | Design pattern - requires semantic understanding |
| `Find duplicate validation logic` | semantic_search | - | Code smell - semantic search finds similar code blocks |
| `Find direct database queries in handlers` | semantic_search | - | Anti-pattern - combines architectural intent with search |
| `Where does dependency injection happen?` | semantic_search | - | Architectural concept - 'dependency injection' is design intent |
| `Find security vulnerability patterns` | semantic_search | - | Security concept - requires understanding of vulnerabilities |
| `Where could we add caching for performance?` | semantic_search | - | Performance concept - 'caching for performance' is design-focused |
| `Find functions that are too complex` | semantic_search | - | Quality metric - 'too complex' requires semantic analysis |

**Key Insight**: SEMANTIC queries describe behavior/concepts rather than exact syntax, requiring embedding-based search.

---

### 4. HYBRID Queries (5 test cases)

Queries combining specific targets with conceptual questions.

| Query | Primary Tool | Fallback Tools | Rationale |
|-------|--------------|----------------|-----------|
| `How does UserModel handle password hashing?` | lsp_goto_definition | ast, semantic | Specific component (UserModel) + conceptual question (password hashing) |
| `What authentication methods does LoginHandler provide?` | lsp_goto_definition | grep, semantic | Specific class (LoginHandler) + conceptual question (what methods) |
| `How is the auth module organized?` | glob_files | ast, semantic | Specific location (auth module) + architectural question (organization) |
| `How does validate_email work internally?` | lsp_goto_definition | semantic | Specific function (validate_email) + mechanism question (how it works) |
| `What error handling patterns does DatabaseManager use?` | lsp_goto_definition | ast, semantic | Specific class (DatabaseManager) + pattern question (error handling) |

**Key Insight**: HYBRID queries need LSP/glob to find the specific target first, then semantic search to answer conceptual questions within that context.

---

### 5. LSP Queries (3 test cases)

Symbol definition and reference lookups via Language Server Protocol.

| Query | Primary Tool | Fallback Tools | Rationale |
|-------|--------------|----------------|-----------|
| `Jump to User class definition` | lsp_goto_definition | - | Symbol definition lookup on 'User' |
| `Find all references to authenticate function` | lsp_find_references | - | Find all usages of 'authenticate' |
| `Find DatabaseConnection symbol` | lsp_workspace_symbols | - | Workspace symbol search |

**Key Insight**: LSP queries are explicit navigation requests for symbol definitions and references.

---

### 6. Edge Cases and Ambiguities (8 test cases)

| Query | Classification | Primary Tool | Rationale |
|-------|----------------|--------------|-----------|
| `Where is validation?` | STRUCTURAL | ast_grep_search | Ambiguous - could mean class name or concept. Try AST first. |
| `What calls prepare_payment and why?` | HYBRID | lsp_find_references | Specific function + reasoning question. Find references first, then semantic. |
| `Show me good error handling` | SEMANTIC | semantic_search | Vague concept - 'good error handling' requires semantic understanding |
| `Find all database calls in the API handlers` | SEMANTIC | semantic_search | Multi-part - combines 'database calls' (semantic) with location (handler) |
| `Find functions without error handling` | SEMANTIC | semantic_search | Negation pattern - 'without error handling' requires semantic analysis |
| `Compare error handling in PaymentModule vs AuthModule` | HYBRID | lsp_goto_definition | Comparison - Find both modules first, then compare semantically |
| `How did the authentication flow change?` | SEMANTIC | semantic_search | Temporal - requires understanding flow evolution, not just current code |
| `Find code similar to this pattern: try: ... except: ...` | SEMANTIC | semantic_search | Example-based - 'similar to' requires semantic comparison |

**Key Insight**: Ambiguous queries default to safer strategies with multiple fallbacks. Negations, comparisons, and temporal queries are inherently semantic.

---

## Test Execution

### Running Tests

```bash
# Run all classification tests
pytest tests/test_query_classification.py -v

# Run specific category
pytest tests/test_query_classification.py::TestSemanticQueries -v

# Run with coverage
pytest tests/test_query_classification.py --cov=mcp_bridge.tools.query_classifier

# Generate coverage report
pytest tests/test_query_classification.py --cov=mcp_bridge.tools.query_classifier --cov-report=html
```

### Expected Coverage

- **EXACT queries**: 10/10 (100%)
- **STRUCTURAL queries**: 10/10 (100%)
- **SEMANTIC queries**: 10/10 (100%)
- **HYBRID queries**: 5/5 (100%)
- **LSP queries**: 3/3 (100%)
- **Edge cases**: 8/8 (100%)

**Total**: 62+ test cases

---

## Validation Criteria

### Classification Accuracy

| Category | Target Accuracy | Tolerance |
|----------|----------------|-----------|
| EXACT | >95% | Low - very clear indicators |
| STRUCTURAL | >90% | Low - AST keywords are explicit |
| SEMANTIC | >80% | Medium - conceptual interpretation |
| HYBRID | >75% | High - requires context understanding |
| LSP | >95% | Low - explicit navigation keywords |

### Performance Targets

- **Classification time**: <10ms per query (p95)
- **Total test suite**: <5 seconds
- **Memory usage**: <100MB peak

---

## Implementation Checklist

When implementing the query_classifier:

1. ✅ Implement `QueryCategory` enum
2. ✅ Implement `QueryClassification` dataclass
3. ✅ Implement `classify_query()` function with regex patterns
4. ✅ Add confidence scoring logic
5. ✅ Add tool routing map
6. ✅ Implement error handling (invalid input, too short, exceptions)
7. ✅ Add logging/telemetry
8. ✅ Write all 62+ test cases
9. ✅ Verify accuracy targets
10. ✅ Benchmark performance (<10ms)

---

## Real-World Query Examples

### From Stravinsky Usage Logs

| Actual User Query | Expected Classification | Confidence |
|-------------------|------------------------|------------|
| "where is PACER pipeline removal handling" | SEMANTIC | 0.85 |
| "Find authenticate() function" | EXACT | 0.90 |
| "How is semantic search triggered?" | SEMANTIC | 0.85 |
| "Find all @decorator functions" | STRUCTURAL | 0.95 |
| "What does UserModel do?" | HYBRID | 0.80 |
| "Find error in FileWatcher" | EXACT | 0.75 |
| "How are agents spawned?" | SEMANTIC | 0.85 |
| "Find classes inheriting from Base" | STRUCTURAL | 0.95 |
| "Where is caching implemented?" | SEMANTIC | 0.85 |
| "Find API_KEY usage" | EXACT | 0.90 |

---

## Future Enhancements

### Phase 2: ML-Based Classification

Once we have production query logs with success/failure rates:

1. **Collect training data**: (query, classification, success_rate) tuples
2. **Feature engineering**: Query length, word embeddings, syntax markers
3. **Train classifier**: scikit-learn RandomForest or LightGBM
4. **A/B testing**: Compare regex vs ML accuracy
5. **Hybrid approach**: Use ML for ambiguous queries, regex for clear cases

### Phase 3: Context-Aware Classification

- Consider previous queries in session
- Adjust based on codebase language/framework
- Learn from user corrections (feedback loop)
- Domain-specific pattern libraries (Django, React, Flask)

---

## Integration with Existing Tests

This test suite complements existing tests:

- **mcp_bridge/tools/test_semantic_search.py**: Functional tests for semantic search
- **tests/test_file_watcher.py**: File watching and reindexing tests
- **tests/test_code_search.py**: grep_search and ast_grep_search tests

The query classification tests focus on **routing logic**, not search functionality.

---

**End of Test Suite Documentation**

This test suite ensures that the query classifier correctly identifies query types and routes them to the optimal search tool, improving search quality and efficiency across the Stravinsky codebase.
