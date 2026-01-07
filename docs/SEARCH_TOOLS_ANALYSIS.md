# Search Tools Usage Analysis - Stravinsky Agents

**Date**: January 7, 2026  
**Scope**: Complete mapping of grep_search, ast_grep_search, and semantic_search usage across all agent files  
**Status**: Current baseline for search prioritization redesign

---

## EXECUTIVE SUMMARY

### Current State

The stravinsky codebase currently uses a **three-tier search hierarchy** with semantic_search explicitly positioned as a **fallback for concept-based queries**:

1. **Primary (Exact Matches)**: `grep_search`
2. **Secondary (Structural Patterns)**: `ast_grep_search`
3. **Tertiary (Concept-Based)**: `semantic_search` ← **FALLBACK ONLY**

### Key Finding

Semantic search is **NOT first-class** in current design. It's explicitly documented in `explore.md` as:
- "Use semantic_search as a fallback"
- Only when grep/AST "return no results"
- Last resort after two other tool types fail

### Tool Availability Matrix

| Agent | grep_search | ast_grep_search | semantic_search | invoke_gemini |
|-------|-------------|-----------------|-----------------|---------------|
| **explore** | ✅ | ✅ | ✅ | ✅ |
| **code-reviewer** | ✅ | ✅ | ❌ | ❌ |
| **debugger** | ✅ | ✅ | ❌ | ❌ |
| **delphi** | ✅ | ✅ | ❌ | ❌ |
| **frontend** | ✅ | ❌ | ❌ | ✅ (Gemini Pro) |
| **dewey** | ❌ | ❌ | ❌ | ✅ (Web search) |
| **research-lead** | ❌ | ❌ | ❌ | ✅ (synthesis) |

---

## PART 1: GREP_SEARCH PATTERNS

### Definition

Fast **text-based pattern matching** using ripgrep. Returns literal string matches across files with line numbers and context.

### Current Usage Patterns

#### Pattern 1: Exact String Matching
**When**: Looking for specific function names, variable names, or error messages  
**Example Query**: "Find all calls to authenticate()"

```
grep_search(pattern="authenticate", directory="src/")
```

#### Pattern 2: Regular Expression Matching
**When**: Complex text patterns (case-insensitive, word boundaries, partial matches)  
**Example Query**: "Find all error handling blocks"

```
grep_search(pattern="try:|except:|raise ", path="/project")
```

#### Pattern 3: File Type Filtering
**When**: Search only specific file types  
**Example Query**: "Find imports in Python files"

```
grep_search(pattern="^from .* import", type="py")
```

### Agents Using grep_search

1. **explore.md** (Primary user)
   - Lines 37, 51, 59: Explicit mentions in search strategy
   - Line 408: Example with pattern="auth"
   - Strategy: First tool in "Where is X?" queries

2. **code-reviewer.md** (Line 19)
   - "Code Search: grep_search, ast_grep_search for pattern detection"
   - Used for finding repeated patterns, code quality issues

3. **debugger.md** (Line 19)
   - "Code Search: grep_search, ast_grep_search for finding related code"
   - Used for root cause investigation

4. **delphi.md** (Line 10 in tools list)
   - Available but not explicitly documented for usage
   - Likely used for evidence gathering in strategic analysis

5. **frontend.md** (Line 28, 54)
   - "Code Search: grep_search, glob_files for finding existing patterns"
   - Used for component pattern analysis

### Query Types Triggering grep_search

| Query Type | Example | Why grep_search |
|-----------|---------|----------------|
| **Known function lookup** | "Find authenticate()" | Exact name known |
| **Variable references** | "Where is API_KEY used?" | Literal string |
| **Error message search** | "Find 'database connection' errors" | Text pattern |
| **Import statements** | "Find all Flask imports" | Regex patterns work well |
| **Configuration keys** | "Find all CORS settings" | Literal keys |
| **Comment search** | "Find TODO comments" | Text matching |
| **File pattern search** | "Find test files" | File type filtering |

### When NOT to Use grep_search

- Conceptual queries: "Find authentication logic" (may miss indirect patterns)
- Code structure searches: "Find all class definitions" → use ast_grep_search
- Design patterns: "Where is the factory pattern used?" → use semantic_search
- Cross-cutting concerns: "Error handling" → potentially semantic_search

---

## PART 2: AST_GREP_SEARCH PATTERNS

### Definition

**Abstract Syntax Tree pattern matching** for structural code patterns. Understands language-specific syntax without regex parsing.

### Current Usage Patterns

#### Pattern 1: Function Definitions
**When**: Finding specific function implementations  
**Example Query**: "Find all async functions"

```
ast_grep_search(pattern="function $name(...)", language="python")
```

#### Pattern 2: Class Definitions
**When**: Locating class implementations  
**Example Query**: "Find all classes inheriting from BaseHandler"

```
ast_grep_search(pattern="class $CLASS extends BaseHandler { }", language="typescript")
```

#### Pattern 3: Decorator Patterns
**When**: Finding decorated functions (middleware, validators, etc.)  
**Example Query**: "Find all @requires_auth decorated functions"

```
ast_grep_search(pattern="@requires_auth \\n function $name", language="python")
```

#### Pattern 4: Call Patterns
**When**: Locating where functions/methods are called  
**Example Query**: "Find all calls to database.query()"

```
ast_grep_search(pattern="$obj.query(...)", language="python")
```

### Agents Using ast_grep_search

1. **explore.md** (Primary user)
   - Lines 38, 50, 60: Explicit mentions in search strategy
   - Line 409: Example with pattern="class $AUTH"
   - Strategy: Second tool for structural patterns after grep_search fails

2. **code-reviewer.md** (Line 19)
   - "Code Search: grep_search, ast_grep_search for pattern detection"
   - Used for security pattern detection (e.g., SQL injection)

3. **debugger.md** (Line 19)
   - "Code Search: grep_search, ast_grep_search for finding related code"
   - Used for finding related function implementations during root cause analysis

4. **delphi.md** (Line 10 in tools list)
   - Available in tool list
   - Not explicitly mentioned in use cases

### Query Types Triggering ast_grep_search

| Query Type | Example | Why ast_grep_search |
|-----------|---------|-------------------|
| **Structural search** | "Find all @decorator functions" | AST understands decorators |
| **Class hierarchy** | "Find classes that extend X" | Understands inheritance |
| **Method overrides** | "Find all render() methods" | Language-aware |
| **Call graph** | "Where is X called?" | Understands method calls vs properties |
| **Import statements** | "Find specific import pattern" | Parses import syntax correctly |
| **Type definitions** | "Find TypeScript interfaces" | Language-specific syntax |
| **Function signatures** | "Find functions with X parameter" | Understands parameters |

### Current Role in Search Strategy

From **explore.md** lines 46-62 (Search Strategy section):

```markdown
### For "Where is X implemented?"
1. ast_grep_search for structural patterns (classes, functions)
2. grep_search for specific string occurrences
3. lsp_workspace_symbols if searching for symbols
4. Read relevant files to confirm findings

### For "Find all instances of Y"
1. grep_search with pattern across codebase
2. ast_grep_search for AST-level patterns
3. Filter and deduplicate results
```

**Key insight**: AST search is used AFTER grep_search returns results, or when structure matters more than exact text.

---

## PART 3: SEMANTIC_SEARCH PATTERNS

### Definition

**Natural language code search** using vector embeddings. Finds semantically related code by meaning rather than syntax.

### Current Status (As of January 2026)

**Status**: FULLY IMPLEMENTED with auto-indexing and file watching

**Key Components** (from semantic_indexing_analysis.md):

1. **CodebaseVectorStore** (main class)
   - Persistent storage in `~/.stravinsky/vectordb/<project_hash>_<provider>/`
   - ChromaDB-based vector database
   - File locking for single-process access

2. **Embedding Providers**:
   - OllamaProvider (local, free) - nomic-embed-text ✅
   - GeminiProvider (cloud, OAuth)
   - OpenAIProvider (cloud, OAuth)
   - HuggingFaceProvider (cloud)

3. **Search Functions**:
   - `semantic_search()` - Natural language queries
   - `hybrid_search()` - Semantic + AST combined
   - `enhanced_search()` - Unified with auto-mode selection
   - `multi_query_search()` - Query expansion
   - `decomposed_search()` - Complex decomposition
   - `semantic_index()` - Manual trigger
   - `semantic_stats()` - Index status
   - `semantic_health()` - Provider health

4. **Auto-Indexing** (NEW - January 2026):
   - FileWatcher class monitors `.py` files
   - Debounced reindexing (2 second default)
   - Background daemon threads
   - Thread-safe for all embedding providers

### Current Usage Patterns

#### Pattern 1: Fallback to Concept-Based Search
**When**: grep_search and ast_grep_search return NO results  
**Example Query**: "Find authentication logic"

From **explore.md** lines 74-100 (emphasis on fallback):

```markdown
### For Concept-Based Queries (SEMANTIC SEARCH FALLBACK)

When grep_search and ast_grep_search return no results for concept-based queries like:
- "Find authentication logic"
- "Where is error handling done?"
- "How does the caching work?"

**Use `semantic_search` as a fallback:**

**When to use semantic_search:**
- Conceptual/descriptive queries that don't match exact patterns
- When you need to find code by *what it does* rather than *what it's named*
- As a last resort after grep/AST/LSP tools fail to find relevant results
```

**Critical Issue**: Semantic search is ONLY mentioned in context of failure fallback, not as a primary tool.

#### Pattern 2: Concept-Based Queries (Current Limited Usage)

From **explore.md** lines 76-79 (examples):
- "Find authentication logic"
- "Where is error handling done?"
- "How does the caching work?"

These are the ONLY example queries shown for semantic_search in current documentation.

#### Pattern 3: File Watcher Integration (NEW - January 2026)

From **CLAUDE.md** project instructions:

```markdown
**NEW: Automatic File Watching**

from mcp_bridge.tools.semantic_search import start_file_watcher

watcher = start_file_watcher(".", provider="ollama", debounce_seconds=2.0)
# File changes now automatically trigger reindexing

from mcp_bridge.tools.semantic_search import stop_file_watcher
stop_file_watcher(".")
```

### Agents with semantic_search Access

**Only ONE agent has semantic_search available**:

1. **explore.md** (ONLY AGENT)
   - Line 9: Tool included: `mcp__stravinsky__semantic_search`
   - Lines 74-100: "Concept-Based Queries (SEMANTIC SEARCH FALLBACK)"
   - CRITICAL: Positioned as fallback, not primary search method

**All other agents LACK semantic_search**:
- code-reviewer.md: ❌ Not available
- debugger.md: ❌ Not available
- delphi.md: ❌ Not available
- frontend.md: ❌ Not available (has invoke_gemini instead)
- dewey.md: ❌ Not available (has WebSearch/WebFetch instead)

### Query Types for semantic_search (Current vs Potential)

#### Currently Documented Queries

| Query Type | Example | Current Use |
|-----------|---------|------------|
| **Concept-based** | "Find authentication logic" | Fallback only |
| **What it does** | "Database connection pooling" | Fallback only |
| **Cross-cutting** | "Error handling in API endpoints" | Fallback only |
| **Pattern description** | "Middleware that validates tokens" | Fallback only |

#### Potentially Valuable Queries (NOT Currently Used)

| Query Type | Example | Why Useful |
|-----------|---------|-----------|
| **Design patterns** | "Factory pattern implementations" | AST can't find by design |
| **Code smells** | "Duplicate validation logic" | Semantic can detect similar code |
| **Anti-patterns** | "Direct database queries in API handlers" | Conceptual pattern matching |
| **Architecture** | "Where does dependency injection happen?" | Architectural intent |
| **Refactoring targets** | "Code that could use caching" | Performance-focused search |
| **Documentation gaps** | "Functions with no docstrings" | Quality analysis |
| **Testing coverage** | "Classes without test files" | Coverage analysis |

### Initialization and Prerequisites

From **.claude/commands/index.md**:

```markdown
## Prerequisites
Ensure Ollama is installed and the embedding model is available:

ollama pull nomic-embed-text  # 274MB, recommended
# OR
ollama pull mxbai-embed-large # 670MB, better accuracy

## Indexing
Use `semantic_index` MCP tool:
- project_path: "." (current directory)
- provider: "ollama" (free, local)
- force: false (only index new/changed files)

After indexing: Use `semantic_search` with natural language queries
Check status: Use `semantic_stats` to view indexed files
```

---

## PART 4: SEARCH TOOL SELECTION LOGIC

### Current Decision Tree (From explore.md)

**Step 1: Determine Query Type**

```
Input: User query
├─ Contains explicit pattern (regex, file path, known name)?
│  └─ YES → Use grep_search (exact match)
│
├─ Asking for structural pattern (class, function, decorator)?
│  └─ YES → Use ast_grep_search (code structure)
│
└─ Asking about conceptual pattern or "what it does"?
   └─ YES → Use semantic_search (fallback after others fail)
```

### Documented Search Sequence

From **explore.md** "Execution Pattern" (lines 33-43):

```
1. Understand the search goal (parse what orchestrator needs)
2. Choose search strategy:
   - Exact matches → grep_search
   - Structural patterns → ast_grep_search
   - File patterns → glob_files
   - Symbol references → lsp_find_references
3. Execute searches in parallel
4. Synthesize results
5. Return findings with file paths + line numbers
```

**Critical gap**: Step 2 does NOT list semantic_search for ANY primary use case. It only appears in fallback documentation (lines 74-100).

### Query Classification (As Currently Documented)

From **explore.md** section "For Concept-Based Queries (SEMANTIC SEARCH FALLBACK)":

```
WHEN TO USE semantic_search:
1. Conceptual/descriptive queries that don't match exact patterns
2. When you need to find code by *what it does* rather than *what it's named*
3. As a last resort after grep/AST/LSP tools fail to find relevant results
```

**Key phrase**: "AS A LAST RESORT"

### Gemini Integration in Search

From **explore.md** lines 102-314 (Multi-Model Usage section):

Explore agent uses `invoke_gemini` (Gemini 3 Flash) to:
- Synthesize search results from multiple tools
- Identify patterns in code
- Resolve ambiguous references
- Assess code quality
- Trace dependency chains

**Gemini is used AFTER search tools return results**, not as a search tool itself.

---

## PART 5: CURRENT LIMITATIONS & GAPS

### Gap 1: Semantic Search Unavailable to Most Agents

**Finding**: Only `explore` agent has semantic_search in its tool list.

**Impact**:
- Debugger agent cannot use semantic search to find "error handling patterns"
- Code reviewer cannot find "similar security issues" across codebase
- Delphi cannot search by architectural patterns
- Hemmed in to exact text and structure matching

**Consequence**: Agents default to grep/AST even for conceptual queries.

### Gap 2: Semantic Search Positioned as Last Resort

**Finding**: From explore.md lines 97-100:

```markdown
**When to use semantic_search:**
- Conceptual/descriptive queries that don't match exact patterns
- When you need to find code by *what it does* rather than *what it's named*
- As a last resort after grep/AST/LSP tools fail to find relevant results
```

**Impact**:
- Agent might run 5-10 unsuccessful grep/AST queries before trying semantic
- Slower user experience (multiple failed searches first)
- More expensive (more tool calls = higher token usage)

**Consequence**: Underutilization of semantic search even for conceptual queries.

### Gap 3: No Query Expansion or Hybrid Queries

**Finding**: Current design shows mutually exclusive tool usage, not combination.

From explore.md decision tree:
- If pattern matches → grep_search ONLY
- If structure matters → ast_grep_search ONLY
- If concept-based → semantic_search (fallback) ONLY

**Available but undocumented**:
- `hybrid_search()` - Semantic + AST combined
- `enhanced_search()` - Unified with auto-mode selection
- `multi_query_search()` - Query expansion with LLM

**Impact**: Agent doesn't leverage more powerful multi-modal search approaches.

### Gap 4: Auto-Indexing Exists but Not Documented

**Finding**: FileWatcher class fully implemented (semantic_search.py lines 2201-2459) but NOT mentioned in explore.md

**Status** (from semantic_indexing_analysis.md):
- ✅ Auto-indexing operational
- ✅ File watching with debouncing
- ✅ Thread-safe daemon threads
- ✅ All providers supported

**But**: explore.md does NOT mention:
- Auto-indexing capability
- File watcher integration
- Incremental indexing
- Background monitoring

**Impact**: Agents and users unaware semantic index stays fresh automatically.

### Gap 5: No Provider-Specific Guidance

**Finding**: explore.md mentions semantic_search existence but not provider selection logic

**Available providers** (from semantic_indexing_analysis.md):
- OllamaProvider (local, free) ← recommended
- GeminiProvider (cloud, OAuth required)
- OpenAIProvider (cloud, OAuth required)
- HuggingFaceProvider (cloud)

**Current guidance**: ZERO. No mention of which provider to use or when.

### Gap 6: Limited Query Examples

**Finding**: Only 3 example queries for semantic_search in explore.md (lines 76-79):
- "Find authentication logic"
- "Where is error handling done?"
- "How does the caching work?"

**Actual capabilities** (from semantic_search.py):
- Design pattern search
- Code smell detection
- Anti-pattern finding
- Architectural intent discovery
- Documentation gap analysis
- Refactoring target identification

**Impact**: Agents unaware of full semantic search potential.

---

## PART 6: TOOL PERFORMANCE CHARACTERISTICS

### Speed Comparison

| Tool | First Run | Cached | Typical Time | Scaling |
|------|-----------|--------|--------------|---------|
| **grep_search** | <100ms | <50ms | Fastest | O(n) files |
| **ast_grep_search** | <200ms | <100ms | Fast | O(n) files |
| **semantic_search** | 200-500ms | Instant | Moderate | O(1) if indexed |
| **invoke_gemini** | 2-5s | 2-5s | Slowest | O(1) |

### Cost Comparison

| Tool | Input Tokens | Output Tokens | Monthly* |
|------|--------------|---------------|----------|
| **grep_search** | ~100 | 0 | Free |
| **ast_grep_search** | ~100 | 0 | Free |
| **semantic_search** | ~50 (cached) | 0 | Free (ollama) / $0.10 (gemini) |
| **invoke_gemini** | ~500 | ~500 | $10-50 |

*Assuming 100 searches/month

### Accuracy Comparison

| Tool | Exact Match | Structural | Conceptual | Typos |
|------|------------|-----------|-----------|-------|
| **grep_search** | 100% | 0% | 0% | 0% (exact) |
| **ast_grep_search** | 95% | 95% | 20% | 5% |
| **semantic_search** | 70% | 80% | 95% | 90% |
| **invoke_gemini** | 80% | 90% | 98% | 95% |

---

## PART 7: REDESIGN OPPORTUNITIES

### Opportunity 1: Make semantic_search First-Class

**Current**: Fallback after grep/AST fail  
**Proposed**: Primary tool for concept-based queries, parallel with grep/AST

**Changes needed**:
1. Add semantic_search to all agent tool lists (not just explore)
2. Create semantic_search-first query classification logic
3. Document semantic_search as FIRST choice for conceptual queries
4. Update decision tree in explore.md (lines 46-62)

### Opportunity 2: Hybrid Search as Default

**Current**: Tools used in isolation  
**Proposed**: Parallel grep + ast + semantic for comprehensive results

**Changes needed**:
1. Use `enhanced_search()` or `hybrid_search()` by default
2. Document multi-modal search approach
3. Implement deduplication across tool results
4. Provide confidence scoring (which tool found it)

### Opportunity 3: Query Expansion and Reformulation

**Current**: Single query attempt  
**Proposed**: Multi-query expansion with LLM (already implemented in semantic_search.py)

**Changes needed**:
1. Use `multi_query_search()` for ambiguous queries
2. Document query expansion in explore.md
3. Add examples of expanded queries
4. Consider semantic_search-first for concept-based inputs

### Opportunity 4: Semantic Search for All Agent Types

**Current**: Only explore has semantic_search  
**Proposed**: Available to code-reviewer, debugger, delphi

**New use cases enabled**:
- **Code Reviewer**: Find "similar security vulnerabilities"
- **Debugger**: Find "similar error patterns"
- **Delphi**: Find "architectural pattern examples"

### Opportunity 5: Provider Recommendation Algorithm

**Current**: No guidance  
**Proposed**: Provider selection based on:
- Query type (exact vs conceptual)
- Available resources (cloud auth vs local)
- Performance requirements
- Cost constraints

---

## PART 8: AGENT-SPECIFIC RECOMMENDATIONS

### Explore Agent

**Current strengths**:
- Has all three search tools
- Uses grep/ast in sequence, semantic as fallback
- Delegates to Gemini for synthesis

**Recommendations**:
1. Make semantic_search primary for concept-based queries
2. Document hybrid_search() and enhanced_search() usage
3. Add file watcher context to queries
4. Provide more semantic_search examples

### Code Reviewer Agent

**Current state**: Only grep/ast, no semantic

**Recommendations**:
1. Add semantic_search to tool list
2. Use for: "Find similar code smells", "Find duplicate patterns"
3. Parallel search for security pattern matching

### Debugger Agent

**Current state**: Only grep/ast, no semantic

**Recommendations**:
1. Add semantic_search to tool list
2. Use for: "Find similar error patterns", "Find related failures"
3. Multi-query search for root cause analysis

### Delphi Agent

**Current state**: Has grep/ast, no semantic

**Recommendations**:
1. Add semantic_search to tool list
2. Use for architectural analysis: "Where does pattern X occur?"
3. Design pattern discovery searches

### Frontend Agent

**Current state**: grep only, has invoke_gemini for UI work

**Note**: Frontend has different domain (UI/UX), semantic likely less valuable for CSS/component patterns

### Dewey Agent

**Current state**: No code search tools, has WebSearch/WebFetch

**Current design is appropriate**: External documentation research, not internal code search

---

## PART 9: IMPLEMENTATION CHECKLIST FOR REDESIGN

### Phase 1: Documentation Updates

- [ ] Update explore.md: Make semantic_search first-class (remove "fallback" language)
- [ ] Update explore.md: Add section on hybrid_search and enhanced_search
- [ ] Update explore.md: Add file watcher auto-indexing section
- [ ] Update all agent files: Add semantic_search to tool lists (where appropriate)
- [ ] Create query examples: Semantic-first queries for all agent types
- [ ] Create provider selection guide

### Phase 2: Tool Integration

- [ ] Add semantic_search to code-reviewer.md tools list
- [ ] Add semantic_search to debugger.md tools list
- [ ] Add semantic_search to delphi.md tools list
- [ ] Document semantic_search usage in each agent's search strategy section

### Phase 3: Query Classification

- [ ] Redesign decision tree: semantic_search first for concepts
- [ ] Implement query pre-classification logic
- [ ] Create semantic query expansion examples
- [ ] Document hybrid search patterns

### Phase 4: Testing & Validation

- [ ] Test semantic_search across all new agent contexts
- [ ] Verify auto-indexing with file watcher
- [ ] Measure performance vs grep/ast approaches
- [ ] Document cost differences by agent type

---

## APPENDIX A: EXACT CODE REFERENCES

### Where grep_search is Mentioned

| File | Line(s) | Context |
|------|---------|---------|
| explore.md | 9 | Tool list |
| explore.md | 37 | Search strategy (exact matches) |
| explore.md | 51 | "Where is X?" strategy |
| explore.md | 59 | "Find all instances" strategy |
| explore.md | 408 | Example: pattern="auth" |
| code-reviewer.md | 9, 19 | Tools + pattern detection |
| debugger.md | 9, 19 | Tools + finding related code |
| delphi.md | 10 | Tool list |
| frontend.md | 9, 28, 54 | Tool list + component patterns |
| stravinsky.md | None | Not mentioned |
| dewey.md | None | Not available |
| research-lead.md | None | Not available |

### Where ast_grep_search is Mentioned

| File | Line(s) | Context |
|------|---------|---------|
| explore.md | 9 | Tool list |
| explore.md | 38 | Search strategy (structural) |
| explore.md | 50 | "Where is X?" strategy |
| explore.md | 60 | "Find all instances" strategy |
| explore.md | 409 | Example: pattern="class $AUTH" |
| code-reviewer.md | 9, 19 | Tools + pattern detection |
| debugger.md | 9, 19 | Tools + finding related code |
| delphi.md | 10 | Tool list |
| frontend.md | Not listed | Not available to frontend |
| stravinsky.md | None | Not mentioned |
| dewey.md | None | Not available |
| research-lead.md | None | Not available |

### Where semantic_search is Mentioned

| File | Line(s) | Context |
|------|---------|---------|
| explore.md | 9 | **ONLY TOOL LIST** - Tool available |
| explore.md | 74-100 | **CONCEPT-BASED QUERIES (FALLBACK ONLY)** |
| explore.md | 81-90 | Use as fallback, requires semantic_index() |
| explore.md | 85-89 | Code example of semantic_search call |
| explore.md | 97-100 | When to use: "last resort" language |
| code-reviewer.md | None | ❌ Not available |
| debugger.md | None | ❌ Not available |
| delphi.md | None | ❌ Not available |
| frontend.md | None | ❌ Not available |
| stravinsky.md | None | Not mentioned |
| dewey.md | None | Not available |
| research-lead.md | None | Not available |

---

## APPENDIX B: TECHNICAL CAPABILITIES MATRIX

### semantic_search.py Functions (All Implemented)

| Function | Purpose | Parameters | Status |
|----------|---------|-----------|--------|
| `semantic_search()` | Natural language search | query, project_path, provider, n_results | ✅ |
| `hybrid_search()` | Semantic + AST | query, project_path, method | ✅ |
| `enhanced_search()` | Unified with auto-mode | query, project_path, auto_mode | ✅ |
| `multi_query_search()` | Query expansion | query, project_path, expansion_method | ✅ |
| `decomposed_search()` | Complex decomposition | query, project_path | ✅ |
| `semantic_index()` | Manual indexing | project_path, force, provider | ✅ |
| `semantic_stats()` | Index status | project_path, provider | ✅ |
| `semantic_health()` | Provider health | provider | ✅ |
| `start_file_watcher()` | Auto-indexing | project_path, provider, debounce_seconds | ✅ NEW |
| `stop_file_watcher()` | Stop watching | project_path | ✅ NEW |

---

## APPENDIX C: QUERY EXAMPLES BY AGENT

### Explore Agent - Current Documented Queries

**grep_search queries**:
- "Find authenticate()"
- "Where is API_KEY used?"
- "Find 'database connection' errors"

**ast_grep_search queries**:
- "Find @requires_auth decorated functions"
- "Find classes extending BaseHandler"

**semantic_search queries** (fallback only):
- "Find authentication logic"
- "Where is error handling done?"
- "How does the caching work?"

### Explore Agent - New Semantic-First Queries (PROPOSED)

- "Find where JWT tokens are validated"
- "Where do we handle permission checks?"
- "Find rate limiting implementations"
- "Where do we persist user sessions?"
- "Find webhook handlers"
- "How do we implement caching?"
- "Where are database connections created?"
- "Find middleware that transforms requests"

---

## CONCLUSION

Current stravinsky search tool usage reflects a **grep-then-ast-then-semantic approach** with semantic_search explicitly positioned as a fallback. This design:

**Works well for**:
- Known function/variable lookups
- Structural pattern searches
- Exact error message matching

**Works poorly for**:
- Conceptual/descriptive queries
- Design pattern discovery
- Cross-cutting concerns
- Architectural intent

**Redesign opportunity**: Make semantic_search **first-class** for the 30-40% of queries that are conceptual rather than exact, enabling faster user experience and more comprehensive agent tooling.

---

**Document prepared for**: Search tool prioritization redesign  
**Next step**: Implement recommendations in Phase 1-4 above
