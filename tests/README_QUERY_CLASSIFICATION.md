# Query Classification Test Suite - Complete Package

## Files Created

1. **test_query_classification.py** (982 lines)
   - Executable pytest test suite
   - 62+ test cases covering all query types
   - Design validation only (no implementation tested)
   - Ready to be implemented against actual classifier

2. **QUERY_CLASSIFICATION_GUIDE.md** 
   - Comprehensive test documentation
   - Query category definitions with examples
   - Tool selection rules and decision logic
   - Real-world scenario examples
   - Integration points and next steps

3. **README_QUERY_CLASSIFICATION.md** (this file)
   - Quick reference and navigation

## Quick Start

### Run the Tests
```bash
cd /Users/davidandrews/PycharmProjects/stravinsky
uv pip install pytest
uv run pytest tests/test_query_classification.py -v
```

### Understand the Test Structure
1. Read `QUERY_CLASSIFICATION_GUIDE.md` first (big picture)
2. Scan test class names in `test_query_classification.py` (organization)
3. Read individual test docstrings (examples)

### Test Class Map

| Class | Purpose | Test Count |
|-------|---------|-----------|
| `TestExactMatchQueries` | Known names/patterns | 10 |
| `TestStructuralQueries` | Code structure | 10 |
| `TestSemanticQueries` | Conceptual/design | 10 |
| `TestHybridQueries` | Specific + conceptual | 5 |
| `TestLSPQueries` | Symbol lookup | 3 |
| `TestEdgeCasesAndAmbiguities` | Edge cases | 9 |
| `TestRealWorldScenarios` | Real usage patterns | 8 |
| `TestQueryClassificationRules` | Decision rules | 8 |
| `TestClassificationMetadata` | Metadata validation | 3 |
| `TestQueryClassificationComparison` | Comparison tests | 3 |
| `TestEdgeCasesRequiringHuman` | Ambiguous cases | 3 |
| **TOTAL** | | **62+** |

## Query Classification Model

### 5 Query Types

```
EXACT       → Known identifiers, patterns, errors
             Primary: grep_search
             Examples: "Find authenticate()", "Where is API_KEY?"

STRUCTURAL  → Code structure, syntax patterns
             Primary: ast_grep_search
             Examples: "@requires_auth", "extends BaseHandler"

SEMANTIC    → Conceptual, design intent, cross-cutting
             Primary: semantic_search
             Examples: "Find authentication logic", "How does caching work?"

HYBRID      → Specific target + conceptual question
             Primary: lsp_goto_definition
             Examples: "How does UserModel handle passwords?"
             User request: "I can ask about a specific component or class 
             and have a semantic question about it"

LSP         → Symbol definition/reference lookup
             Primary: lsp_workspace_symbols, lsp_find_references
             Examples: "Jump to definition", "Find all references"
```

### Decision Rules (8 Rules)

1. **Known exact name beats concept** - Try LSP/GREP before SEMANTIC
2. **Structural beats exact for patterns** - AST understands context
3. **"How" questions typically semantic** - Mechanism/implementation
4. **"Where" questions flexible** - Depends on specificity
5. **"Find all" suggests GREP or AST** - Except for conceptual patterns
6. **Quotes indicate literal string** - GREP only
7. **camelCase/snake_case suggests EXACT** - Known identifier
8. **Design vocabulary suggests semantic** - pattern, architecture, concern

## Key Design Insights

### User's Hybrid Query Example
User mentioned: *"I can ask about a specific component or class and have a semantic question about it"*

This is a **HYBRID query** - one of the most powerful use cases:
```python
# Example: "How does UserModel handle password hashing?"
# Stage 1: Find UserModel (LSP_DEFINITION)
# Stage 2: Analyze within context (SEMANTIC)
QueryClassification(
    query_type=QueryType.HYBRID,
    primary_tool=SearchTool.LSP_DEFINITION,
    fallback_tools=[SearchTool.SEMANTIC]
)
```

### Semantic Search is Primary, Not Fallback
Current documentation positions semantic_search as "last resort fallback". 
Tests validate it should be **primary tool for conceptual queries**:
- GREP/AST fallback only if semantic index unavailable
- Not "try grep, then ast, then semantic"
- Instead: "grep for exact, ast for structure, semantic for concepts"

### Tool Hierarchy is Context-Dependent
Not a linear order. Context matters:
- EXACT queries → GREP (primary) → LSP (better for symbols)
- STRUCTURAL → AST (primary) → GREP (literal fallback)
- SEMANTIC → SEMANTIC (primary) → GREP/AST (if index unavailable)

## Real-World Query Examples

### Debugger: Error Tracking
```
"Where is this error raised: ValueError: invalid token"
→ EXACT / grep_search
```

### Code Reviewer: Security Pattern
```
"Find all places where we build SQL directly"
→ SEMANTIC / semantic_search
```

### Architect: Understanding Flow
```
"How does the request flow from API endpoint to database?"
→ SEMANTIC / semantic_search
```

### Refactoring: Finding Duplicates
```
"Where are we validating email addresses?"
→ SEMANTIC / semantic_search
```

### Feature: Finding Extension Point
```
"Where do we handle webhook events?"
→ SEMANTIC / semantic_search
```

## Test Data Quality

### Breadth
- 62+ test cases
- 5 query types
- 8 real-world scenarios
- 8 decision rules validated
- 9 edge cases

### Depth
- Each test includes: query, type, primary tool, fallbacks, rationale, keywords
- Real examples from actual stravinsky usage
- Comprehensive edge case coverage
- Ambiguity handling validation

### Coverage
- ✓ Single-word queries
- ✓ Multi-part queries  
- ✓ Quoted strings
- ✓ Decorator patterns
- ✓ Method signatures
- ✓ Design patterns
- ✓ Negation queries ("without")
- ✓ Comparison queries
- ✓ Hypothetical questions
- ✓ Context-dependent queries

## Implementation Roadmap

### Phase 1: Build Components (This Test Suite)
✓ Query classification specification
✓ Test cases with expected behaviors
✓ Decision rules documented
✓ Real-world examples included

### Phase 2: Implement Classifier
- [ ] Query tokenization
- [ ] Pattern matching (quoted strings, decorators, etc.)
- [ ] Named entity recognition (class/function names)
- [ ] Query intent detection (How/Where/Find/Compare)
- [ ] Tool selection algorithm
- [ ] Confidence scoring
- [ ] Fallback generation

### Phase 3: Run Test Suite
- [ ] Implement actual QueryClassifier
- [ ] Run pytest suite
- [ ] Fix failing tests
- [ ] Measure accuracy

### Phase 4: Benchmark & Validate
- [ ] Performance testing
- [ ] Real user query validation
- [ ] A/B testing vs. baselines
- [ ] Iterate on decision rules

## Expected vs. Actual Behavior

This test suite is **design validation**, not implementation validation.

```
Current State:
- Documentation: Test cases specify EXPECTED behavior
- Implementation: Does NOT exist yet
- Status: Ready for implementation

After Implementation:
- Documentation: Test cases specify REQUIRED behavior
- Implementation: QueryClassifier class with 5 methods
- Status: Passing test suite = quality classifier
```

## Key Metrics for Success

When implementation is complete, measure:

1. **Accuracy**: % of queries classified as user would expect
   - Target: 85%+ for common query types
   - 95%+ for EXACT queries
   - 80%+ for SEMANTIC queries

2. **Precision**: Primary tool is correct before fallback
   - Target: 75%+ first-choice accuracy

3. **Latency**: Classification time < 100ms
   - No index lookups needed
   - Pure rule-based decision

4. **Robustness**: Handles edge cases gracefully
   - Ambiguous queries have sensible fallbacks
   - Vague queries default to SEMANTIC

## Integration with Stravinsky

### In Explore Agent
```python
# Current: Manual tool selection
grep_search(...)  # User hopes this works
ast_grep_search(...)  # User hopes this works
semantic_search(...)  # Last resort

# After implementation: Intelligent routing
classification = classify_query(user_query)
tool = get_tool(classification.primary_tool)
results = tool(...)
if not results and classification.fallback_tools:
    for fallback_tool in classification.fallback_tools:
        results = get_tool(fallback_tool)(...)
        if results:
            break
```

### In Other Agents
```python
# Code Reviewer
classification = classify_query(user_query)
# Use semantic_search if available (not current)

# Debugger  
classification = classify_query(user_query)
# Route to appropriate search tool

# Delphi
classification = classify_query(user_query)
# Might use HYBRID for architectural questions
```

## Files Summary

```
tests/
├── test_query_classification.py (982 lines)
│   ├── QueryType enum (5 types)
│   ├── SearchTool enum (7 tools)
│   ├── QueryClassification class
│   ├── 11 test classes
│   └── 62+ test methods
├── QUERY_CLASSIFICATION_GUIDE.md
│   ├── Query categories (5)
│   ├── Tool selection rules (8)
│   ├── Test coverage breakdown
│   ├── Data structure docs
│   ├── Pseudocode classifier
│   └── Implementation roadmap
└── README_QUERY_CLASSIFICATION.md (this file)
    ├── Quick start
    ├── Test class map
    ├── Classification model
    ├── Design insights
    └── Implementation roadmap
```

## Validation Checklist

Before implementing, verify:

- [ ] Read QUERY_CLASSIFICATION_GUIDE.md completely
- [ ] Understand all 5 query types
- [ ] Review all 8 decision rules
- [ ] Scan real-world examples
- [ ] Identify any gaps in test coverage
- [ ] Plan implementation phases
- [ ] Set success metrics

## Next: Implementation Phase

When ready to implement the actual QueryClassifier:

1. Create `mcp_bridge/tools/query_classifier.py`
2. Implement `QueryClassifier` class with methods:
   - `classify(query: str) -> QueryClassification`
   - `tokenize(query: str) -> List[Token]`
   - `detect_intent(tokens: List[Token]) -> Intent`
   - `select_tool(type: QueryType, intent: Intent) -> SearchTool`
   - `generate_fallbacks(primary: SearchTool) -> List[SearchTool]`
3. Run: `uv run pytest tests/test_query_classification.py -v`
4. Iterate on decision rules until tests pass

## Questions?

Refer to:
- **QUERY_CLASSIFICATION_GUIDE.md** - Detailed documentation
- **test_query_classification.py** - Test examples
- **docs/SEARCH_TOOLS_ANALYSIS.md** - Tool characteristics
- **mcp_bridge/prompts/explore.md** - Agent context

---

**Status**: Design complete, ready for implementation  
**Test Suite**: 62+ comprehensive test cases  
**Coverage**: All query types, decision rules, edge cases, real-world scenarios  
**Quality**: High (based on SEARCH_TOOLS_ANALYSIS.md research + user feedback)
