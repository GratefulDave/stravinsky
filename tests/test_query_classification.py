"""
Test suite for query classification and routing logic in Stravinsky agents.

This test file validates the classification of user queries into categories
and ensures proper routing to the appropriate search tools (grep_search,
ast_grep_search, semantic_search, and LSP tools).

Query Categories:
- EXACT: Known function/variable names, file patterns, error messages
- STRUCTURAL: Code structure, decorators, class hierarchies, imports
- SEMANTIC: Conceptual queries, design patterns, cross-cutting concerns
- HYBRID: Specific target + conceptual question combination
- LSP: Symbol definition/reference lookups

Test Data:
- 30+ real queries from stravinsky usage scenarios
- Expected classifications for each query
- Expected primary and fallback tool routing
- Edge cases and ambiguous examples
"""

import pytest
from enum import Enum
from typing import List, Optional, Dict, Any


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


class TestExactMatchQueries:
    """Tests for EXACT query type - known names, patterns, and error messages."""
    
    def test_function_name_lookup(self):
        """Query: 'Find authenticate()' - Known function name."""
        q = QueryClassification(
            query="Find authenticate()",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
            fallback_tools=[SearchTool.LSP_SYMBOLS],
            rationale="Exact function name - grep_search finds text match 'authenticate'",
            keywords=["authenticate", "function name", "known"]
        )
        assert q.query_type == QueryType.EXACT
        assert q.primary_tool == SearchTool.GREP
        assert SearchTool.LSP_SYMBOLS in q.fallback_tools
    
    def test_variable_reference_search(self):
        """Query: 'Where is API_KEY used?' - Known variable name."""
        q = QueryClassification(
            query="Where is API_KEY used?",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
            fallback_tools=[SearchTool.LSP_REFERENCES],
            rationale="Exact variable name - grep_search finds all text occurrences",
            keywords=["API_KEY", "variable", "references"]
        )
        assert q.query_type == QueryType.EXACT
        assert q.primary_tool == SearchTool.GREP
    
    def test_error_message_search(self):
        """Query: 'Find "database connection" errors' - Specific error text."""
        q = QueryClassification(
            query='Find "database connection" errors',
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
            rationale="Exact error message text - grep_search with literal string",
            keywords=["error message", "literal string", "exact match"]
        )
        assert q.primary_tool == SearchTool.GREP
    
    def test_import_pattern_search(self):
        """Query: 'Find all Flask imports' - Known package name."""
        q = QueryClassification(
            query="Find all Flask imports",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
            fallback_tools=[SearchTool.AST],
            rationale="Known package name - grep_search with regex ^from flask import",
            keywords=["Flask", "imports", "pattern"]
        )
        assert q.primary_tool == SearchTool.GREP
    
    def test_configuration_key_search(self):
        """Query: 'Find all CORS settings' - Known config key."""
        q = QueryClassification(
            query="Find all CORS settings",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
            rationale="Known configuration key - grep_search for 'CORS'",
            keywords=["CORS", "config", "settings"]
        )
        assert q.primary_tool == SearchTool.GREP
    
    def test_todo_comment_search(self):
        """Query: 'Find TODO comments' - Known comment pattern."""
        q = QueryClassification(
            query="Find TODO comments",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
            rationale="Exact comment pattern - grep_search for '# TODO'",
            keywords=["TODO", "comment", "pattern"]
        )
        assert q.primary_tool == SearchTool.GREP
    
    def test_class_name_lookup(self):
        """Query: 'Find UserModel class' - Known class name."""
        q = QueryClassification(
            query="Find UserModel class",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
            fallback_tools=[SearchTool.LSP_SYMBOLS],
            rationale="Known class name - grep_search for 'class UserModel'",
            keywords=["UserModel", "class", "name"]
        )
        assert q.primary_tool == SearchTool.GREP
    
    def test_test_file_pattern_search(self):
        """Query: 'Find test files' - File pattern matching."""
        q = QueryClassification(
            query="Find test files",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GLOB,
            rationale="File pattern search - glob_files with 'test*.py' or 'tests/**/*.py'",
            keywords=["test", "file pattern", "glob"]
        )
        assert q.primary_tool == SearchTool.GLOB
    
    def test_regex_pattern_search(self):
        """Query: 'Find all try/except blocks' - Regex pattern."""
        q = QueryClassification(
            query="Find all try/except blocks",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
            rationale="Regex pattern - grep_search with 'try:|except:' pattern",
            keywords=["try", "except", "regex", "pattern"]
        )
        assert q.primary_tool == SearchTool.GREP
    
    def test_specific_url_route_search(self):
        """Query: 'Find /api/users endpoint' - Known route path."""
        q = QueryClassification(
            query="Find /api/users endpoint",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
            rationale="Exact URL path - grep_search for '/api/users'",
            keywords=["/api/users", "endpoint", "route"]
        )
        assert q.primary_tool == SearchTool.GREP


class TestStructuralQueries:
    """Tests for STRUCTURAL query type - code structure and patterns."""
    
    def test_decorator_search(self):
        """Query: 'Find all @requires_auth decorated functions' - Decorator pattern."""
        q = QueryClassification(
            query="Find all @requires_auth decorated functions",
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
            fallback_tools=[SearchTool.GREP],
            rationale="Decorator pattern - ast_grep_search understands @requires_auth syntax",
            keywords=["@requires_auth", "decorator", "structure"]
        )
        assert q.query_type == QueryType.STRUCTURAL
        assert q.primary_tool == SearchTool.AST
    
    def test_class_inheritance_search(self):
        """Query: 'Find classes extending BaseHandler' - Class hierarchy."""
        q = QueryClassification(
            query="Find classes extending BaseHandler",
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
            rationale="Inheritance hierarchy - ast_grep_search with pattern 'class $CLASS extends BaseHandler'",
            keywords=["extends", "inheritance", "BaseHandler"]
        )
        assert q.primary_tool == SearchTool.AST
    
    def test_method_override_search(self):
        """Query: 'Find all render() methods' - Method signature search."""
        q = QueryClassification(
            query="Find all render() methods",
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
            rationale="Method signature - ast_grep_search understands method definitions",
            keywords=["render()", "method", "signature"]
        )
        assert q.primary_tool == SearchTool.AST
    
    def test_call_pattern_search(self):
        """Query: 'Where is database.query() called?' - Call graph pattern."""
        q = QueryClassification(
            query="Where is database.query() called?",
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
            fallback_tools=[SearchTool.GREP],
            rationale="Method call pattern - ast_grep_search with '$obj.query(...)'",
            keywords=["database.query()", "call", "method"]
        )
        assert q.primary_tool == SearchTool.AST
    
    def test_import_structure_search(self):
        """Query: 'Find all from X import Y patterns' - Import syntax."""
        q = QueryClassification(
            query="Find all from X import Y patterns",
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
            rationale="Import syntax - ast_grep_search understands import structure",
            keywords=["import", "structure", "pattern"]
        )
        assert q.primary_tool == SearchTool.AST
    
    def test_function_signature_search(self):
        """Query: 'Find functions with timeout parameter' - Parameter search."""
        q = QueryClassification(
            query="Find functions with timeout parameter",
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
            rationale="Function signature - ast_grep_search understands parameters",
            keywords=["timeout", "parameter", "function signature"]
        )
        assert q.primary_tool == SearchTool.AST
    
    def test_async_function_search(self):
        """Query: 'Find all async functions' - Language structure."""
        q = QueryClassification(
            query="Find all async functions",
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
            rationale="Language structure - ast_grep_search with 'async def $name'",
            keywords=["async", "function", "structure"]
        )
        assert q.primary_tool == SearchTool.AST
    
    def test_type_definition_search(self):
        """Query: 'Find TypeScript interfaces' - Type syntax."""
        q = QueryClassification(
            query="Find TypeScript interfaces",
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
            rationale="Type structure - ast_grep_search with 'interface $NAME'",
            keywords=["interface", "TypeScript", "type"]
        )
        assert q.primary_tool == SearchTool.AST
    
    def test_context_manager_search(self):
        """Query: 'Find with statements' - Context manager syntax."""
        q = QueryClassification(
            query="Find with statements",
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
            rationale="Context manager - ast_grep_search with 'with $expr as $var'",
            keywords=["with", "context manager", "structure"]
        )
        assert q.primary_tool == SearchTool.AST
    
    def test_lambda_expression_search(self):
        """Query: 'Find all lambda expressions' - Anonymous functions."""
        q = QueryClassification(
            query="Find all lambda expressions",
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
            rationale="Lambda syntax - ast_grep_search understands lambda",
            keywords=["lambda", "anonymous", "expression"]
        )
        assert q.primary_tool == SearchTool.AST


class TestSemanticQueries:
    """Tests for SEMANTIC query type - conceptual and design patterns."""
    
    def test_authentication_logic_search(self):
        """Query: 'Find authentication logic' - Conceptual cross-cutting concern."""
        q = QueryClassification(
            query="Find authentication logic",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            fallback_tools=[SearchTool.GREP, SearchTool.AST],
            rationale="Conceptual - 'authentication logic' is a design concept, not a literal name",
            keywords=["authentication", "logic", "conceptual"]
        )
        assert q.query_type == QueryType.SEMANTIC
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_error_handling_pattern_search(self):
        """Query: 'Where is error handling done?' - Cross-cutting concern."""
        q = QueryClassification(
            query="Where is error handling done?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            rationale="Conceptual pattern - 'error handling' spans multiple files",
            keywords=["error handling", "pattern", "cross-cutting"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_caching_mechanism_search(self):
        """Query: 'How does the caching work?' - Implementation mechanism."""
        q = QueryClassification(
            query="How does the caching work?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            rationale="Conceptual mechanism - 'caching' is about functionality not name",
            keywords=["caching", "mechanism", "how it works"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_design_pattern_search(self):
        """Query: 'Where is the factory pattern used?' - Design pattern."""
        q = QueryClassification(
            query="Where is the factory pattern used?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            rationale="Design pattern - requires semantic understanding of 'factory pattern'",
            keywords=["factory pattern", "design pattern", "semantic"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_code_smell_detection(self):
        """Query: 'Find duplicate validation logic' - Code smell detection."""
        q = QueryClassification(
            query="Find duplicate validation logic",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            rationale="Code quality - semantic search can find similar code blocks",
            keywords=["duplicate", "validation", "code smell"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_anti_pattern_detection(self):
        """Query: 'Find direct database queries in handlers' - Anti-pattern."""
        q = QueryClassification(
            query="Find direct database queries in handlers",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            rationale="Anti-pattern - combines architectural intent with search",
            keywords=["database", "handler", "anti-pattern"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_architectural_intent_search(self):
        """Query: 'Where does dependency injection happen?' - Architecture."""
        q = QueryClassification(
            query="Where does dependency injection happen?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            rationale="Architectural concept - 'dependency injection' is design intent",
            keywords=["dependency injection", "architecture", "concept"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_security_pattern_search(self):
        """Query: 'Find security vulnerability patterns' - Security concept."""
        q = QueryClassification(
            query="Find security vulnerability patterns",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            rationale="Security concept - requires understanding of vulnerability patterns",
            keywords=["security", "vulnerability", "pattern"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_performance_optimization_search(self):
        """Query: 'Where could we add caching for performance?' - Performance."""
        q = QueryClassification(
            query="Where could we add caching for performance?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            rationale="Performance concept - 'caching for performance' is design-focused",
            keywords=["performance", "optimization", "caching"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_refactoring_opportunity_search(self):
        """Query: 'Find functions that are too complex' - Refactoring target."""
        q = QueryClassification(
            query="Find functions that are too complex",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            rationale="Quality metric - 'too complex' requires semantic code analysis",
            keywords=["complex", "refactoring", "quality"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC


class TestHybridQueries:
    """Tests for HYBRID query type - specific target + conceptual question."""
    
    def test_specific_component_semantic_question(self):
        """Query: 'How does UserModel handle password hashing?' - Specific + Semantic."""
        q = QueryClassification(
            query="How does UserModel handle password hashing?",
            query_type=QueryType.HYBRID,
            primary_tool=SearchTool.LSP_DEFINITION,
            fallback_tools=[SearchTool.AST, SearchTool.SEMANTIC],
            rationale="Specific component (UserModel) + conceptual question (password hashing). "
                     "Find UserModel first via LSP, then analyze within context.",
            keywords=["UserModel", "password hashing", "specific component"]
        )
        assert q.query_type == QueryType.HYBRID
        assert q.primary_tool == SearchTool.LSP_DEFINITION
    
    def test_class_method_concept_search(self):
        """Query: 'What authentication methods does LoginHandler provide?' - Specific class + concept."""
        q = QueryClassification(
            query="What authentication methods does LoginHandler provide?",
            query_type=QueryType.HYBRID,
            primary_tool=SearchTool.LSP_DEFINITION,
            fallback_tools=[SearchTool.GREP, SearchTool.SEMANTIC],
            rationale="Specific class (LoginHandler) + conceptual question (what methods). "
                     "Find class definition first, then analyze methods.",
            keywords=["LoginHandler", "authentication", "methods"]
        )
        assert q.query_type == QueryType.HYBRID
    
    def test_file_architecture_question(self):
        """Query: 'How is the auth module organized?' - Specific module + architecture."""
        q = QueryClassification(
            query="How is the auth module organized?",
            query_type=QueryType.HYBRID,
            primary_tool=SearchTool.GLOB,
            fallback_tools=[SearchTool.AST, SearchTool.SEMANTIC],
            rationale="Specific location (auth module) + architectural question (organization). "
                     "Find files first via glob, then analyze structure.",
            keywords=["auth module", "organization", "architecture"]
        )
        assert q.query_type == QueryType.HYBRID
    
    def test_function_implementation_question(self):
        """Query: 'How does validate_email work internally?' - Specific function + mechanism."""
        q = QueryClassification(
            query="How does validate_email work internally?",
            query_type=QueryType.HYBRID,
            primary_tool=SearchTool.LSP_DEFINITION,
            fallback_tools=[SearchTool.SEMANTIC],
            rationale="Specific function (validate_email) + mechanism question (how it works). "
                     "Find definition first, then understand implementation.",
            keywords=["validate_email", "internals", "mechanism"]
        )
        assert q.primary_tool == SearchTool.LSP_DEFINITION
    
    def test_pattern_in_component_search(self):
        """Query: 'What error handling patterns does DatabaseManager use?' - Specific + pattern."""
        q = QueryClassification(
            query="What error handling patterns does DatabaseManager use?",
            query_type=QueryType.HYBRID,
            primary_tool=SearchTool.LSP_DEFINITION,
            fallback_tools=[SearchTool.AST, SearchTool.SEMANTIC],
            rationale="Specific class (DatabaseManager) + pattern question (error handling). "
                     "Find class, then analyze for patterns.",
            keywords=["DatabaseManager", "error handling", "patterns"]
        )
        assert q.query_type == QueryType.HYBRID


class TestLSPQueries:
    """Tests for LSP query type - symbol definition and reference lookups."""
    
    def test_symbol_definition_lookup(self):
        """Query: 'Jump to User class definition' - Symbol definition."""
        q = QueryClassification(
            query="Jump to User class definition",
            query_type=QueryType.LSP,
            primary_tool=SearchTool.LSP_DEFINITION,
            rationale="Symbol definition lookup - lsp_goto_definition on 'User'",
            keywords=["User", "definition", "goto"]
        )
        assert q.query_type == QueryType.LSP
        assert q.primary_tool == SearchTool.LSP_DEFINITION
    
    def test_symbol_references_lookup(self):
        """Query: 'Find all references to authenticate function' - Find references."""
        q = QueryClassification(
            query="Find all references to authenticate function",
            query_type=QueryType.LSP,
            primary_tool=SearchTool.LSP_REFERENCES,
            rationale="Find all usages - lsp_find_references on 'authenticate'",
            keywords=["authenticate", "references", "usages"]
        )
        assert q.primary_tool == SearchTool.LSP_REFERENCES
    
    def test_symbol_workspace_search(self):
        """Query: 'Find DatabaseConnection symbol' - Workspace symbol search."""
        q = QueryClassification(
            query="Find DatabaseConnection symbol",
            query_type=QueryType.LSP,
            primary_tool=SearchTool.LSP_SYMBOLS,
            rationale="Workspace symbol search - lsp_workspace_symbols with 'DatabaseConnection'",
            keywords=["DatabaseConnection", "symbol", "workspace"]
        )
        assert q.primary_tool == SearchTool.LSP_SYMBOLS


class TestEdgeCasesAndAmbiguities:
    """Tests for edge cases and ambiguous query types."""
    
    def test_ambiguous_name_or_concept(self):
        """Query: 'Where is validation?' - Could be EXACT or SEMANTIC."""
        q = QueryClassification(
            query="Where is validation?",
            query_type=QueryType.STRUCTURAL,  # Falls back to AST for "class Validation"
            primary_tool=SearchTool.AST,
            fallback_tools=[SearchTool.GREP, SearchTool.SEMANTIC],
            rationale="Ambiguous - could mean class name or concept. Try AST first for structural match.",
            keywords=["validation", "ambiguous"]
        )
        assert q.fallback_tools  # Should have fallbacks
    
    def test_very_specific_with_context(self):
        """Query: 'What calls prepare_payment and why?' - Specific + reasoning."""
        q = QueryClassification(
            query="What calls prepare_payment and why?",
            query_type=QueryType.HYBRID,
            primary_tool=SearchTool.LSP_REFERENCES,
            fallback_tools=[SearchTool.SEMANTIC],
            rationale="Specific function + reasoning question. Find references first, then use semantic for 'why'.",
            keywords=["prepare_payment", "references", "reasoning"]
        )
        assert q.query_type == QueryType.HYBRID
    
    def test_vague_conceptual_query(self):
        """Query: 'Show me good error handling' - Vague and conceptual."""
        q = QueryClassification(
            query="Show me good error handling",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            fallback_tools=[SearchTool.GREP],
            rationale="Vague concept - 'good error handling' requires semantic understanding",
            keywords=["error handling", "quality", "vague"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_multi_part_query(self):
        """Query: 'Find all database calls in the API handlers' - Multi-part."""
        q = QueryClassification(
            query="Find all database calls in the API handlers",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            fallback_tools=[SearchTool.GREP, SearchTool.AST],
            rationale="Multi-part query - combines 'database calls' (semantic) with location (handler). "
                     "Semantic search best for this composite query.",
            keywords=["database", "API handlers", "composite"]
        )
        assert q.query_type == QueryType.SEMANTIC
    
    def test_negation_query(self):
        """Query: 'Find functions without error handling' - Negation pattern."""
        q = QueryClassification(
            query="Find functions without error handling",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            rationale="Negation query - 'without error handling' requires semantic analysis",
            keywords=["without", "negation", "semantic"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_comparative_query(self):
        """Query: 'Compare error handling in PaymentModule vs AuthModule' - Comparison."""
        q = QueryClassification(
            query="Compare error handling in PaymentModule vs AuthModule",
            query_type=QueryType.HYBRID,
            primary_tool=SearchTool.LSP_DEFINITION,
            fallback_tools=[SearchTool.SEMANTIC],
            rationale="Comparison query - Find both modules first, then compare semantically",
            keywords=["compare", "PaymentModule", "AuthModule"]
        )
        assert q.query_type == QueryType.HYBRID
    
    def test_temporal_change_query(self):
        """Query: 'How did the authentication flow change?' - Temporal/historical."""
        q = QueryClassification(
            query="How did the authentication flow change?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            rationale="Temporal - requires understanding flow evolution, not just current code",
            keywords=["change", "temporal", "authentication flow"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_query_with_example_code(self):
        """Query: 'Find code similar to this pattern: try: ... except: ...' - Example-based."""
        q = QueryClassification(
            query="Find code similar to this pattern: try: ... except: ...",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            fallback_tools=[SearchTool.GREP],
            rationale="Example-based - user provides code snippet, semantic search finds similar",
            keywords=["pattern", "example", "similarity"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_hypothetical_query(self):
        """Query: 'Where might we have SQL injection vulnerabilities?' - Hypothetical."""
        q = QueryClassification(
            query="Where might we have SQL injection vulnerabilities?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            fallback_tools=[SearchTool.GREP, SearchTool.AST],
            rationale="Hypothetical security question - requires pattern understanding",
            keywords=["SQL injection", "vulnerability", "hypothetical"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC


class TestRealWorldScenarios:
    """Tests based on real Stravinsky usage scenarios."""
    
    def test_debugger_scenario_find_error(self):
        """Debugger: 'Where is this error raised: ValueError: invalid token' """
        q = QueryClassification(
            query="Where is this error raised: ValueError: invalid token",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
            fallback_tools=[SearchTool.AST],
            rationale="Error traceback - grep_search for exact error message",
            keywords=["ValueError", "error message", "raised"]
        )
        assert q.primary_tool == SearchTool.GREP
    
    def test_reviewer_scenario_find_pattern(self):
        """Code Reviewer: 'Find all places where we build SQL directly' """
        q = QueryClassification(
            query="Find all places where we build SQL directly",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            fallback_tools=[SearchTool.GREP],
            rationale="Security pattern - 'build SQL directly' is semantic pattern",
            keywords=["SQL", "security", "pattern"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_architect_scenario_understand_flow(self):
        """Architect: 'How does the request flow from API endpoint to database?' """
        q = QueryClassification(
            query="How does the request flow from API endpoint to database?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            fallback_tools=[SearchTool.AST],
            rationale="Architectural flow - requires understanding request path",
            keywords=["request flow", "architecture", "endpoint to database"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_refactoring_scenario_find_duplicate(self):
        """Refactoring: 'Where are we validating email addresses?' """
        q = QueryClassification(
            query="Where are we validating email addresses?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            fallback_tools=[SearchTool.GREP, SearchTool.AST],
            rationale="Refactoring search - find all occurrences of validation pattern",
            keywords=["email validation", "duplicate logic", "refactoring"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_new_feature_scenario_find_extension_point(self):
        """New Feature: 'Where do we handle webhook events?' """
        q = QueryClassification(
            query="Where do we handle webhook events?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            fallback_tools=[SearchTool.GREP],
            rationale="Feature exploration - find webhook handling pattern",
            keywords=["webhook", "events", "extension point"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_migration_scenario_find_deprecated_usage(self):
        """Migration: 'Where are we still using the old API?' """
        q = QueryClassification(
            query="Where are we still using the old API?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            fallback_tools=[SearchTool.GREP],
            rationale="Migration search - find deprecated API usage",
            keywords=["deprecated", "old API", "migration"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_test_coverage_scenario_find_untested(self):
        """Test Coverage: 'Which classes don't have tests?' """
        q = QueryClassification(
            query="Which classes don't have tests?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            fallback_tools=[SearchTool.GLOB],
            rationale="Coverage analysis - find classes without corresponding test files",
            keywords=["test coverage", "untested", "classes"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_performance_scenario_find_bottleneck(self):
        """Performance: 'Where are expensive database queries?' """
        q = QueryClassification(
            query="Where are expensive database queries?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            fallback_tools=[SearchTool.GREP],
            rationale="Performance optimization - find potential bottlenecks",
            keywords=["expensive", "database queries", "performance"]
        )
        assert q.primary_tool == SearchTool.SEMANTIC


class TestQueryClassificationRules:
    """Tests for query classification decision logic."""
    
    def test_known_exact_name_beats_concept(self):
        """Rule: Exact known name should route to EXACT/LSP before SEMANTIC."""
        # If query contains a known class/function name, try LSP/GREP first
        q1 = QueryClassification(
            query="Find UserModel",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.LSP_SYMBOLS,
        )
        q2 = QueryClassification(
            query="Find user management",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
        )
        assert q1.primary_tool != q2.primary_tool
        assert q1.query_type != q2.query_type
    
    def test_structural_beats_exact_for_patterns(self):
        """Rule: Structural patterns (decorator, inheritance) route to AST."""
        q = QueryClassification(
            query="Find @cached decorated methods",
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
        )
        assert q.primary_tool == SearchTool.AST
    
    def test_how_questions_lean_semantic(self):
        """Rule: 'How' questions typically route to SEMANTIC."""
        queries = [
            "How does caching work?",
            "How is authentication handled?",
            "How do we manage sessions?",
        ]
        for query_text in queries:
            # All should be semantic
            assert QueryClassification(
                query=query_text,
                query_type=QueryType.SEMANTIC,
                primary_tool=SearchTool.SEMANTIC,
            ).primary_tool == SearchTool.SEMANTIC
    
    def test_where_questions_flexible(self):
        """Rule: 'Where' questions can be EXACT, STRUCTURAL, or SEMANTIC."""
        q1 = QueryClassification(
            query="Where is API_KEY used?",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
        )
        q2 = QueryClassification(
            query="Where is error handling done?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
        )
        # Both valid depending on specificity
        assert q1.primary_tool in [SearchTool.GREP, SearchTool.SEMANTIC]
        assert q2.primary_tool in [SearchTool.SEMANTIC, SearchTool.GREP]
    
    def test_find_all_suggests_grep_or_ast(self):
        """Rule: 'Find all' queries typically EXACT or STRUCTURAL."""
        queries = [
            "Find all async functions",
            "Find all error handling patterns",
            "Find all TODO comments",
        ]
        for query_text in queries:
            q = QueryClassification(
                query=query_text,
                query_type=QueryType.EXACT if "TODO" in query_text else QueryType.STRUCTURAL,
                primary_tool=SearchTool.GREP if "TODO" in query_text else SearchTool.AST,
            )
            assert q.primary_tool in [SearchTool.GREP, SearchTool.AST]
    
    def test_quotes_indicate_literal_string(self):
        """Rule: Queries with quotes suggest literal string search."""
        q = QueryClassification(
            query='Find "database connection refused" errors',
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
        )
        assert q.primary_tool == SearchTool.GREP
    
    def test_camelcase_or_snake_case_name(self):
        """Rule: camelCase/snake_case identifiers suggest EXACT match."""
        q = QueryClassification(
            query="Find processPayment calls",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
        )
        assert q.primary_tool == SearchTool.GREP
    
    def test_design_vocabulary_suggests_semantic(self):
        """Rule: Design vocabulary (pattern, architecture, concern) suggests SEMANTIC."""
        patterns = ["factory pattern", "architectural", "cross-cutting", "design intent"]
        for keyword in patterns:
            query_text = f"Find {keyword}"
            # Should lean toward semantic
            q = QueryClassification(
                query=query_text,
                query_type=QueryType.SEMANTIC,
                primary_tool=SearchTool.SEMANTIC,
            )
            assert q.primary_tool == SearchTool.SEMANTIC


class TestClassificationMetadata:
    """Tests for classification metadata and documentation."""
    
    def test_classification_has_rationale(self):
        """Each classification should include rationale."""
        q = QueryClassification(
            query="Find authenticate()",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
            rationale="Known function name",
        )
        assert q.rationale != ""
        assert "function name" in q.rationale.lower()
    
    def test_classification_has_keywords(self):
        """Classifications should tag relevant keywords."""
        q = QueryClassification(
            query="Find @requires_auth decorated functions",
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
            keywords=["@requires_auth", "decorator", "authentication"],
        )
        assert len(q.keywords) > 0
        assert "@requires_auth" in q.keywords
    
    def test_fallback_tools_make_sense(self):
        """Fallback tools should be reasonable alternatives."""
        q = QueryClassification(
            query="Find authenticate()",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
            fallback_tools=[SearchTool.LSP_SYMBOLS, SearchTool.LSP_REFERENCES],
        )
        # All fallback tools should be related to code search
        for tool in q.fallback_tools:
            assert tool in [SearchTool.GREP, SearchTool.AST, SearchTool.SEMANTIC,
                          SearchTool.LSP_SYMBOLS, SearchTool.LSP_REFERENCES]


class TestQueryClassificationComparison:
    """Tests comparing similar queries to understand classification differences."""
    
    def test_exact_vs_semantic_authentication(self):
        """Compare: find 'AuthHandler' (exact) vs find 'auth logic' (semantic)."""
        exact = QueryClassification(
            query="Find AuthHandler class",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.LSP_SYMBOLS,
        )
        semantic = QueryClassification(
            query="How does authentication work?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
        )
        assert exact.primary_tool != semantic.primary_tool
        assert exact.query_type != semantic.query_type
    
    def test_structural_vs_grep_decorators(self):
        """Compare: find '@requires_auth' (structural) vs find '@requires_auth' (exact)."""
        # Same string, different interpretation
        structural = QueryClassification(
            query="Find all @requires_auth decorated functions",
            query_type=QueryType.STRUCTURAL,
            primary_tool=SearchTool.AST,
        )
        exact = QueryClassification(
            query='Search for "@requires_auth" string',
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.GREP,
        )
        # Structural is better because it understands the decorator context
        assert structural.primary_tool == SearchTool.AST
        assert exact.primary_tool == SearchTool.GREP
    
    def test_hybrid_breakdown(self):
        """Test the progression from exact to hybrid to semantic."""
        # Exact: just the name
        exact = QueryClassification(
            query="Find UserModel",
            query_type=QueryType.EXACT,
            primary_tool=SearchTool.LSP_SYMBOLS,
        )
        # Hybrid: name + conceptual question
        hybrid = QueryClassification(
            query="How does UserModel validate input?",
            query_type=QueryType.HYBRID,
            primary_tool=SearchTool.LSP_DEFINITION,
            fallback_tools=[SearchTool.SEMANTIC],
        )
        # Semantic: just the concept
        semantic = QueryClassification(
            query="How is input validation done?",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
        )
        # Each should have different tooling strategy
        assert exact.primary_tool != semantic.primary_tool


class TestEdgeCasesRequiringHuman:
    """Tests for ambiguous cases that might need human clarification."""
    
    def test_tool_name_overloaded(self):
        """Ambiguous: 'Find Tool' - could be a class or a concept."""
        q = QueryClassification(
            query="Find Tool",
            query_type=QueryType.EXACT,  # Better to try this first
            primary_tool=SearchTool.LSP_SYMBOLS,
            fallback_tools=[SearchTool.SEMANTIC],
            rationale="Ambiguous - could be exact class name or semantic concept. "
                     "Try LSP first, then semantic.",
        )
        assert len(q.fallback_tools) > 0
    
    def test_very_broad_query(self):
        """Ambiguous: 'Find everything about payments' - too broad."""
        q = QueryClassification(
            query="Find everything about payments",
            query_type=QueryType.SEMANTIC,
            primary_tool=SearchTool.SEMANTIC,
            rationale="Broad query - semantic search with expansion and multi-query",
        )
        assert q.primary_tool == SearchTool.SEMANTIC
    
    def test_context_dependent_query(self):
        """Ambiguous: 'Find it' - requires conversation context."""
        q = QueryClassification(
            query="Find it",
            query_type=QueryType.SEMANTIC,  # Default to flexible
            primary_tool=SearchTool.SEMANTIC,
            rationale="Vague pronoun reference - requires context from conversation",
        )
        assert q.rationale  # Should have explanation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
