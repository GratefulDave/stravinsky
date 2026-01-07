# Query Classification and Routing Test Suite

## Overview

This test suite (`test_query_classification.py`) validates the classification of user queries and their routing to appropriate search tools in Stravinsky agents. It serves as both a specification and design document for query classification logic.

**Status**: Design validation only (no implementation tested yet)

## Query Classification Categories

### 1. EXACT (Known Identifiers)
- **Purpose**: Fast exact matching for known names
- **Examples**:
  - "Find authenticate()" → Exact function name
  - "Where is API_KEY used?" → Known variable
  - 'Find "database connection" errors' → Literal error text
  - "Find all TODO comments" → Known comment pattern
  - "Find /api/users endpoint" → Known route path

- **Primary Tool**: `grep_search`
- **Fallback Tools**: `lsp_workspace_symbols`, `lsp_find_references`
- **Characteristics**:
  - Query contains known identifier (class, function, variable, constant)
  - Literal string matching or regex pattern
  - File patterns (test*.py, tests/**, etc.)
  - Quoted strings indicate literal match

### 2. STRUCTURAL (Code Structure)
- **Purpose**: Language-aware pattern matching for syntax
- **Examples**:
  - "Find all @requires_auth decorated functions" → Decorator pattern
  - "Find classes extending BaseHandler" → Inheritance hierarchy
  - "Where is database.query() called?" → Method call pattern
  - "Find all async functions" → Language structure
  - "Find functions with timeout parameter" → Signature matching

- **Primary Tool**: `ast_grep_search`
- **Fallback Tools**: `grep_search`, `lsp_workspace_symbols`
- **Characteristics**:
  - Query asks about code structure (decorators, inheritance, methods)
  - Language-specific syntax patterns
  - Method signatures and type definitions
  - Context managers, lambdas, async/await

### 3. SEMANTIC (Conceptual/Design)
- **Purpose**: Understand intent and find related code by meaning
- **Examples**:
  - "Find authentication logic" → Conceptual cross-cutting concern
  - "Where is error handling done?" → Design pattern
  - "How does the caching work?" → Implementation mechanism
  - "Find duplicate validation logic" → Code smell detection
  - "Where does dependency injection happen?" → Architectural pattern
  - "Find security vulnerability patterns" → Security concern

- **Primary Tool**: `semantic_search`
- **Fallback Tools**: `grep_search`, `ast_grep_search`
- **Characteristics**:
  - Conceptual/descriptive language (not literal identifiers)
  - "How" questions about implementation
  - Design patterns, architectural concerns
  - Code quality, security, performance concepts
  - Cross-cutting concerns that span multiple files
  - Requires understanding of what code *does*, not what it's *named*

### 4. HYBRID (Specific Target + Conceptual Question)
- **Purpose**: Find a specific component, then analyze it conceptually
- **Examples**:
  - "How does UserModel handle password hashing?" → Class + mechanism
  - "What authentication methods does LoginHandler provide?" → Class + concept
  - "How is the auth module organized?" → Module + architecture
  - "What error handling patterns does DatabaseManager use?" → Class + pattern

- **Primary Tool**: `lsp_goto_definition` or `glob_files` (find target first)
- **Fallback Tools**: `ast_grep_search`, `semantic_search` (analyze target)
- **Characteristics**:
  - Combines specific identifier with conceptual question
  - Two-stage lookup: find specific component, then analyze
  - User mentioned example: "I can ask about a specific component or class and have a semantic question about it"

### 5. LSP (Language Server Protocol - Symbol Lookup)
- **Purpose**: Symbol definition/reference lookups via language server
- **Examples**:
  - "Jump to User class definition" → Symbol definition
  - "Find all references to authenticate function" → Find all usages
  - "Find DatabaseConnection symbol" → Workspace symbol search

- **Primary Tool**: `lsp_goto_definition`, `lsp_find_references`, or `lsp_workspace_symbols`
- **Fallback Tools**: `grep_search`, `semantic_search`
- **Characteristics**:
  - Symbol resolution queries
  - Jump to definition, find references
  - Workspace symbol search
  - Most precise for known symbols

## Tool Selection Rules

### Rule 1: Known Exact Name Beats Concept
- If query contains known class/function name → try LSP/GREP before SEMANTIC
- Example: "Find UserModel" → LSP_SYMBOLS, not semantic_search

### Rule 2: Structural Beats Exact for Patterns
- Decorator, inheritance, and method patterns → AST (understands context)
- Example: "Find @cached decorated methods" → AST_GREP, not GREP alone

### Rule 3: "How" Questions Typically Semantic
- How-based queries → often SEMANTIC (mechanism/implementation)
- "How does X work?" → understand implementation
- Fallback: GREP/AST if X is literal name

### Rule 4: "Where" Questions Flexible
- "Where is X?" depends on X specificity
- "Where is API_KEY used?" → GREP (known variable)
- "Where is error handling done?" → SEMANTIC (concept)

### Rule 5: "Find All" Suggests GREP or AST
- "Find all X" typically EXACT or STRUCTURAL
- "Find all TODO comments" → GREP (literal pattern)
- "Find all async functions" → AST (structure)
- Exception: "Find all error handling patterns" → SEMANTIC (concept)

### Rule 6: Quotes Indicate Literal String
- Single/double quotes around string → GREP (exact match)
- Example: 'Find "database connection refused"' → GREP only

### Rule 7: camelCase/snake_case Suggests EXACT
- Identifiers in code style → likely known name
- Example: "Find processPayment calls" → GREP

### Rule 8: Design Vocabulary Suggests SEMANTIC
- Keywords: pattern, architecture, concern, intent, principle
- Example: "Find factory pattern" → SEMANTIC

## Test Coverage

### Class Breakdown

1. **TestExactMatchQueries** (10 tests)
   - Known function names, variables, errors, imports, configs, comments, classes, files, regex, URLs

2. **TestStructuralQueries** (10 tests)
   - Decorators, inheritance, methods, calls, imports, signatures, async, types, context managers, lambdas

3. **TestSemanticQueries** (10 tests)
   - Authentication, error handling, caching, design patterns, code smells, anti-patterns, architecture, security, performance, refactoring

4. **TestHybridQueries** (5 tests)
   - Component + password hashing, class + methods, module + organization, function + internals, component + patterns

5. **TestLSPQueries** (3 tests)
   - Definition lookup, references, workspace symbols

6. **TestEdgeCasesAndAmbiguities** (9 tests)
   - Ambiguous names, specific + reasoning, vague concepts, multi-part, negation, comparison, temporal, examples, hypothetical

7. **TestRealWorldScenarios** (8 tests)
   - Debugger error lookup, reviewer pattern detection, architect flow analysis, refactoring duplicates, feature webhook handling, migration deprecated API, test coverage, performance bottleneck

8. **TestQueryClassificationRules** (8 tests)
   - Decision rules validation for tool selection

9. **TestClassificationMetadata** (3 tests)
   - Metadata validation (rationale, keywords, fallback tools)

10. **TestQueryClassificationComparison** (3 tests)
    - Comparing similar queries to validate differentiation

11. **TestEdgeCasesRequiringHuman** (3 tests)
    - Overloaded names, very broad queries, context-dependent queries

**Total: 62+ test cases covering all query types and decision logic**

## QueryClassification Data Structure

Each test case uses a `QueryClassification` object with:

```python
class QueryClassification:
    query: str                          # The user's query
    query_type: QueryType               # Classification (EXACT, STRUCTURAL, SEMANTIC, HYBRID, LSP)
    primary_tool: SearchTool            # Primary search tool
    fallback_tools: List[SearchTool]    # Alternative tools if primary fails
    rationale: str                      # Explanation of classification
    keywords: List[str]                 # Tags for classification
```

### Example

```python
q = QueryClassification(
    query="How does UserModel handle password hashing?",
    query_type=QueryType.HYBRID,
    primary_tool=SearchTool.LSP_DEFINITION,
    fallback_tools=[SearchTool.AST, SearchTool.SEMANTIC],
    rationale="Specific component (UserModel) + conceptual question (password hashing). "
             "Find UserModel first via LSP, then analyze within context.",
    keywords=["UserModel", "password hashing", "specific component"]
)
```

## Real-World Query Examples from Tests

### Debugger Scenario
```
Query: "Where is this error raised: ValueError: invalid token"
Type: EXACT
Primary: grep_search
Rationale: Error traceback - grep_search for exact error message
```

### Code Reviewer Scenario
```
Query: "Find all places where we build SQL directly"
Type: SEMANTIC
Primary: semantic_search
Rationale: Security pattern - 'build SQL directly' is semantic pattern
Fallback: grep_search (if index not available)
```

### Architect Scenario
```
Query: "How does the request flow from API endpoint to database?"
Type: SEMANTIC
Primary: semantic_search
Rationale: Architectural flow - requires understanding request path
Fallback: ast_grep_search (for structural analysis)
```

### Refactoring Scenario
```
Query: "Where are we validating email addresses?"
Type: SEMANTIC
Primary: semantic_search
Rationale: Find all occurrences of validation pattern
Fallback: grep_search, ast_grep_search
```

### New Feature Scenario
```
Query: "Where do we handle webhook events?"
Type: SEMANTIC
Primary: semantic_search
Rationale: Feature exploration - find webhook handling pattern
Fallback: grep_search
```

## Tool Performance Matrix (Reference)

From SEARCH_TOOLS_ANALYSIS.md:

| Tool | First Run | Typical | Accuracy (Conceptual) |
|------|-----------|---------|-----|
| grep_search | <100ms | Fastest | 0% (exact only) |
| ast_grep_search | <200ms | Fast | 20% |
| semantic_search | 200-500ms | Moderate | 95% |
| invoke_gemini | 2-5s | Slowest | 98% |

**Strategy**: Use GREP/AST first for performance, semantic for accuracy on conceptual queries.

## Expected Behavior (When Implementation is Created)

### Query Classifier Function (Pseudocode)

```python
def classify_query(query: str) -> QueryClassification:
    """Classify query and determine routing."""
    
    # 1. Check for exact/literal patterns
    if has_quoted_string(query):
        return QueryClassification(
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP
        )
    
    if has_known_identifier(query):  # authenticate, API_KEY, etc.
        return QueryClassification(
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
            fallback_tools=[SearchTool.LSP_SYMBOLS]
        )
    
    # 2. Check for structural patterns
    if has_structural_keywords(query):  # @decorator, extends, async, etc.
        return QueryClassification(
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
            fallback_tools=[SearchTool.GREP]
        )
    
    # 3. Check for hybrid (specific + conceptual)
    if has_specific_component(query) and has_conceptual_question(query):
        return QueryClassification(
            query_type=QueryType.HYBRID,
            primary_tool=SearchTool.LSP_DEFINITION,
            fallback_tools=[SearchTool.SEMANTIC]
        )
    
    # 4. Default to semantic for conceptual queries
    return QueryClassification(
        query_type=QueryType.SEMANTIC,
        primary_tool=SearchTool.SEMANTIC,
        fallback_tools=[SearchTool.GREP, SearchTool.AST]
    )
```

## Key Design Insights

### 1. Ambiguity is Normal
Some queries (like "Where is validation?") can be EXACT or SEMANTIC depending on context. Tests validate that ambiguous queries include sensible fallbacks.

### 2. Hybrid Queries are Important
User feedback: "I can ask about a specific component or class and have a semantic question about it"
This enables powerful two-stage lookups: find component, then analyze it.

### 3. Tool Hierarchy is Context-Dependent
Not a strict linear hierarchy. Instead:
- EXACT queries might fallback to LSP (better than GREP for symbols)
- SEMANTIC queries might fallback to GREP (faster for known patterns)
- STRUCTURAL often benefits from GREP fallback (for literal string matching)

### 4. Semantic Search is NOT a Last Resort
While current docs position semantic_search as fallback, tests validate it as **primary tool for conceptual queries**. GREP/AST are fallbacks if semantic index is not available.

## Next Steps (Implementation Phase)

1. **Query Tokenization**: Parse query to extract keywords, named entities, question type
2. **Pattern Matching**: Match against known patterns (decorators, packages, comments)
3. **Named Entity Recognition**: Detect class/function names in query
4. **Query Intent Detection**: Classify as How/Where/Find/Compare/etc.
5. **Tool Selection**: Apply rules to select primary tool
6. **Fallback Generation**: Create fallback sequence based on confidence
7. **Confidence Scoring**: Rate confidence in primary tool (affects fallback strategy)

## Testing Strategy

### Current (Design Validation)
- ✓ 62+ test cases with expected classifications
- ✓ Real-world query examples
- ✓ Decision rule validation
- ✓ Edge case identification

### Next Phase (Implementation)
- Implement actual `QueryClassifier` class
- Create tokenization and pattern matching
- Add NER and intent detection
- Implement tool selection algorithm
- Add confidence scoring
- Run test suite against implementation

### Validation Phase
- Benchmark classifier accuracy against real user queries
- A/B test tool selection vs. random baseline
- Measure performance (latency of classifications)
- Iterate on rules based on misclassifications

## Documentation

- **This file**: Design specification and test guide
- **test_query_classification.py**: Executable test suite
- **SEARCH_TOOLS_ANALYSIS.md**: Tool characteristics and recommendations
- **explore.md**: Agent-specific search strategies

## Integration Points

This test suite defines the interface for:

1. **Explore Agent**: Uses query classifier to route to appropriate tool
2. **Query Router**: Translates classifications to tool calls
3. **Result Synthesizer**: May adjust tool sequence based on early results
4. **User Feedback Loop**: Tests validate user's expected classifications

---

**Test Suite Location**: `/tests/test_query_classification.py`
**Related Docs**: `/docs/SEARCH_TOOLS_ANALYSIS.md`
**Design Status**: Complete specification, ready for implementation
