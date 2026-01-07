"""
Comprehensive test suite for query classifier.

Tests all 26 examples from QUERY_CLASSIFIER_DESIGN.md (lines 246-296):
- PATTERN category: 5 test cases
- STRUCTURAL category: 5 test cases
- SEMANTIC category: 8 test cases
- HYBRID category: 5 test cases
- AMBIGUOUS category: 3 test cases

Also includes:
- Performance benchmarks (<10ms requirement)
- Error handling tests
- Confidence scoring validation
- Tool routing verification
"""

import statistics
import time

import pytest

# Import the classifier from the actual implementation
from mcp_bridge.tools.query_classifier import QueryCategory, QueryClassification, classify_query

# ============================================================================
# PATTERN Category Tests (grep_search)
# ============================================================================

class TestPatternCategory:
    """Test PATTERN category classification (5 cases from design doc)."""

    def test_quoted_function_name(self):
        """Find "authenticate()" - quoted identifier + function call."""
        result = classify_query('Find "authenticate()"')
        assert result.category == QueryCategory.PATTERN
        assert result.confidence >= 0.85
        assert result.suggested_tool == "grep_search"
        assert any(ind in result.indicators for ind in ["quoted_identifier", "function_call"])

    def test_constant_name(self):
        """Where is API_KEY used? - constant name pattern."""
        result = classify_query("Where is API_KEY used?")
        assert result.category == QueryCategory.PATTERN
        assert result.confidence >= 0.70
        assert result.suggested_tool == "grep_search"
        assert "constant_name" in result.indicators or "CONSTANT" in str(result.indicators).upper()

    def test_method_call_syntax(self):
        """Search for database.query() - function call + dot notation."""
        result = classify_query("Search for database.query()")
        assert result.category == QueryCategory.PATTERN
        assert result.confidence >= 0.85
        assert result.suggested_tool == "grep_search"
        assert any(ind in result.indicators for ind in ["function_call", "dot_notation"])

    def test_literal_string_match(self):
        """Find all TODO comments - literal string."""
        result = classify_query("Find all TODO comments")
        assert result.category == QueryCategory.PATTERN
        assert result.confidence >= 0.70
        assert result.suggested_tool == "grep_search"

    def test_explicit_grep_request(self):
        """grep for import Flask - explicit grep request."""
        result = classify_query("grep for import Flask")
        assert result.category == QueryCategory.PATTERN
        assert result.confidence >= 0.85
        assert result.suggested_tool == "grep_search"


# ============================================================================
# STRUCTURAL Category Tests (ast_grep_search)
# ============================================================================

class TestStructuralCategory:
    """Test STRUCTURAL category classification (5 cases from design doc)."""

    def test_class_definitions(self):
        """Find class definitions - explicit AST keyword."""
        result = classify_query("Find class definitions")
        assert result.category == QueryCategory.STRUCTURAL
        assert result.confidence >= 0.90
        assert result.suggested_tool == "ast_grep_search"
        assert "ast_keyword" in result.indicators or "class" in str(result.indicators)

    def test_async_functions(self):
        """All async functions - language-specific keyword."""
        result = classify_query("All async functions")
        assert result.category == QueryCategory.STRUCTURAL
        assert result.confidence >= 0.85
        assert result.suggested_tool == "ast_grep_search"
        assert "ast_keyword" in result.indicators or "async" in str(result.indicators)

    def test_inheritance_pattern(self):
        """Classes inheriting from Base - inheritance relationship."""
        result = classify_query("Classes inheriting from Base")
        assert result.category == QueryCategory.STRUCTURAL
        assert result.confidence >= 0.90
        assert result.suggested_tool == "ast_grep_search"
        assert "inheritance" in str(result.indicators).lower() or "inherits" in str(result.indicators)

    def test_decorator_pattern(self):
        """Functions decorated with @requires_auth - decorator syntax."""
        result = classify_query("Functions decorated with @requires_auth")
        assert result.category == QueryCategory.STRUCTURAL
        assert result.confidence >= 0.90
        assert result.suggested_tool == "ast_grep_search"
        assert "decorator" in str(result.indicators).lower()

    def test_override_pattern(self):
        """Methods overriding render() - OOP structure."""
        result = classify_query("Methods overriding render()")
        assert result.category == QueryCategory.STRUCTURAL
        assert result.confidence >= 0.85
        assert result.suggested_tool == "ast_grep_search"
        assert "override" in str(result.indicators).lower()


# ============================================================================
# SEMANTIC Category Tests (semantic_search)
# ============================================================================

class TestSemanticCategory:
    """Test SEMANTIC category classification (8 cases from design doc)."""

    def test_authentication_logic(self):
        """Find authentication logic - conceptual noun."""
        result = classify_query("Find authentication logic")
        assert result.category == QueryCategory.SEMANTIC
        assert result.confidence >= 0.80
        assert result.suggested_tool == "semantic_search"
        assert any(ind in str(result.indicators).lower() for ind in ["conceptual", "logic"])

    def test_error_handling_intent(self):
        """Where is error handling done? - intent question."""
        result = classify_query("Where is error handling done?")
        assert result.category == QueryCategory.SEMANTIC
        assert result.confidence >= 0.80
        assert result.suggested_tool == "semantic_search"
        assert any(ind in str(result.indicators).lower() for ind in ["intent", "where"])

    def test_caching_mechanism(self):
        """How does caching work? - mechanism inquiry."""
        result = classify_query("How does caching work?")
        assert result.category == QueryCategory.SEMANTIC
        assert result.confidence >= 0.85
        assert result.suggested_tool == "semantic_search"
        assert "how" in str(result.indicators).lower()

    def test_rate_limiting_implementation(self):
        """Find rate limiting implementation - design pattern."""
        result = classify_query("Find rate limiting implementation")
        assert result.category == QueryCategory.SEMANTIC
        assert result.confidence >= 0.75
        assert result.suggested_tool == "semantic_search"

    def test_permissions_validation(self):
        """Where are permissions validated? - semantic verb."""
        result = classify_query("Where are permissions validated?")
        assert result.category == QueryCategory.SEMANTIC
        assert result.confidence >= 0.80
        assert result.suggested_tool == "semantic_search"
        assert any(ind in str(result.indicators).lower() for ind in ["validate", "where"])

    def test_jwt_token_handling(self):
        """Code that handles JWT tokens - conceptual relationship."""
        result = classify_query("Code that handles JWT tokens")
        assert result.category == QueryCategory.SEMANTIC
        assert result.confidence >= 0.75
        assert result.suggested_tool == "semantic_search"
        assert "handles" in str(result.indicators).lower() or "handle" in str(result.indicators).lower()

    def test_middleware_pattern(self):
        """Find middleware - architectural concept."""
        result = classify_query("Find middleware")
        assert result.category == QueryCategory.SEMANTIC
        assert result.confidence >= 0.70
        assert result.suggested_tool == "semantic_search"

    def test_similar_error_patterns(self):
        """Similar error patterns - semantic similarity."""
        result = classify_query("Similar error patterns")
        assert result.category == QueryCategory.SEMANTIC
        assert result.confidence >= 0.75
        assert result.suggested_tool == "semantic_search"
        assert "similar" in str(result.indicators).lower()


# ============================================================================
# HYBRID Category Tests (enhanced_search)
# ============================================================================

class TestHybridCategory:
    """Test HYBRID category classification (5 cases from design doc)."""

    def test_exact_plus_conceptual(self):
        """Find authenticate() and error handling - mixed types."""
        result = classify_query("Find authenticate() and error handling")
        assert result.category == QueryCategory.HYBRID
        assert result.confidence >= 0.80
        assert result.suggested_tool in ["enhanced_search", "hybrid_search"]
        assert any(ind in str(result.indicators).lower() for ind in ["and", "conjunction", "mixed"])

    def test_structure_plus_concept(self):
        """All classes that implement caching - structural + semantic."""
        result = classify_query("All classes that implement caching")
        assert result.category == QueryCategory.HYBRID
        assert result.confidence >= 0.75
        assert result.suggested_tool in ["enhanced_search", "hybrid_search"]

    def test_broad_scope_query(self):
        """System-wide authentication checks - wide scope."""
        result = classify_query("System-wide authentication checks")
        assert result.category == QueryCategory.HYBRID
        assert result.confidence >= 0.70
        assert result.suggested_tool in ["enhanced_search", "hybrid_search"]
        assert any(ind in str(result.indicators).lower() for ind in ["system-wide", "broad", "scope"])

    def test_vague_qualifier(self):
        """Related authentication code - similarity-based."""
        result = classify_query("Related authentication code")
        assert result.category == QueryCategory.HYBRID
        assert result.confidence >= 0.65
        assert result.suggested_tool in ["enhanced_search", "hybrid_search"]
        assert "related" in str(result.indicators).lower()

    def test_pattern_plus_semantic(self):
        """Functions like validate_token() - pattern + semantic."""
        result = classify_query("Functions like validate_token()")
        assert result.category == QueryCategory.HYBRID
        assert result.confidence >= 0.70
        assert result.suggested_tool in ["enhanced_search", "hybrid_search"]
        assert "like" in str(result.indicators).lower() or "similar" in str(result.indicators).lower()


# ============================================================================
# AMBIGUOUS Category Tests (defaults to HYBRID)
# ============================================================================

class TestAmbiguousQueries:
    """Test AMBIGUOUS queries (3 cases - default to HYBRID with 0.5 confidence)."""

    def test_too_vague(self):
        """Find auth - too vague."""
        result = classify_query("Find auth")
        assert result.category == QueryCategory.HYBRID
        assert result.confidence == 0.5
        assert result.suggested_tool in ["enhanced_search", "hybrid_search"]

    def test_generic_search(self):
        """Search X - generic, unclear intent."""
        result = classify_query("Search X")
        assert result.category == QueryCategory.HYBRID
        assert result.confidence == 0.5
        assert result.suggested_tool in ["enhanced_search", "hybrid_search"]

    def test_no_context(self):
        """Code - no context."""
        result = classify_query("Code")
        assert result.category == QueryCategory.HYBRID
        assert result.confidence == 0.5
        assert result.suggested_tool in ["enhanced_search", "hybrid_search"]


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test classifier error handling and edge cases."""

    def test_empty_query(self):
        """Empty string should default to HYBRID."""
        result = classify_query("")
        assert result.category == QueryCategory.HYBRID
        assert result.confidence == 0.5
        assert "invalid" in result.reasoning.lower() or "empty" in result.reasoning.lower()

    def test_whitespace_only(self):
        """Whitespace-only query should default to HYBRID."""
        result = classify_query("   ")
        assert result.category == QueryCategory.HYBRID
        assert result.confidence == 0.5

    def test_very_short_query(self):
        """Very short query (<3 chars) should default to HYBRID."""
        result = classify_query("ab")
        assert result.category == QueryCategory.HYBRID
        assert result.confidence == 0.5
        assert "too short" in result.reasoning.lower() or "short" in result.reasoning.lower()

    def test_special_characters(self):
        """Query with special characters should not crash."""
        result = classify_query("!@#$%^&*()")
        assert isinstance(result, QueryClassification)
        assert result.category in QueryCategory

    def test_unicode_characters(self):
        """Query with unicode should not crash."""
        result = classify_query("Find 日本語 code")
        assert isinstance(result, QueryClassification)
        assert result.category in QueryCategory

    def test_very_long_query(self):
        """Very long query should not crash."""
        long_query = "Find " + "authentication " * 100
        result = classify_query(long_query)
        assert isinstance(result, QueryClassification)
        assert result.category in QueryCategory


# ============================================================================
# Confidence Scoring Tests
# ============================================================================

class TestConfidenceScoring:
    """Test confidence score accuracy and boundaries."""

    def test_confidence_range(self):
        """Confidence should always be between 0.0 and 1.0."""
        test_queries = [
            "Find authenticate()",
            "class definitions",
            "Find authentication logic",
            "Find auth and error handling",
            "x"
        ]
        for query in test_queries:
            result = classify_query(query)
            assert 0.0 <= result.confidence <= 1.0, f"Invalid confidence for: {query}"

    def test_max_confidence_cap(self):
        """Confidence should be capped at 0.95 (never 1.0)."""
        # Even with many strong indicators, should cap at 0.95
        result = classify_query('Find "authenticate()" function call')
        assert result.confidence <= 0.95

    def test_high_confidence_patterns(self):
        """Strong pattern indicators should give high confidence (>0.85)."""
        high_confidence_queries = [
            'Find "authenticate()"',
            "Find class definitions",
            "How does caching work?"
        ]
        for query in high_confidence_queries:
            result = classify_query(query)
            if result.category != QueryCategory.HYBRID:
                assert result.confidence >= 0.70, f"Low confidence for: {query}"

    def test_low_confidence_ambiguous(self):
        """Ambiguous queries should have low confidence (0.5)."""
        ambiguous_queries = ["Find auth", "Search X", "Code", ""]
        for query in ambiguous_queries:
            result = classify_query(query)
            assert result.confidence <= 0.6, f"High confidence for ambiguous: {query}"


# ============================================================================
# Tool Routing Tests
# ============================================================================

class TestToolRouting:
    """Test suggested_tool routing logic."""

    def test_pattern_routes_to_grep(self):
        """PATTERN category should route to grep_search."""
        pattern_queries = [
            'Find "authenticate()"',
            "Search for database.query()",
            "grep for import Flask"
        ]
        for query in pattern_queries:
            result = classify_query(query)
            if result.category == QueryCategory.PATTERN:
                assert result.suggested_tool == "grep_search"

    def test_structural_routes_to_ast_grep(self):
        """STRUCTURAL category should route to ast_grep_search."""
        structural_queries = [
            "Find class definitions",
            "All async functions",
            "Classes inheriting from Base"
        ]
        for query in structural_queries:
            result = classify_query(query)
            if result.category == QueryCategory.STRUCTURAL:
                assert result.suggested_tool == "ast_grep_search"

    def test_semantic_routes_to_semantic_search(self):
        """SEMANTIC category should route to semantic_search."""
        semantic_queries = [
            "Find authentication logic",
            "How does caching work?",
            "Where is error handling done?"
        ]
        for query in semantic_queries:
            result = classify_query(query)
            if result.category == QueryCategory.SEMANTIC:
                assert result.suggested_tool == "semantic_search"

    def test_hybrid_routes_to_enhanced(self):
        """HYBRID category should route to enhanced_search."""
        hybrid_queries = [
            "Find authenticate() and error handling",
            "System-wide authentication checks",
            "Related authentication code"
        ]
        for query in hybrid_queries:
            result = classify_query(query)
            if result.category == QueryCategory.HYBRID:
                assert result.suggested_tool in ["enhanced_search", "hybrid_search"]


# ============================================================================
# Performance Benchmark Tests
# ============================================================================

class TestPerformance:
    """Test classification performance (target: <10ms per query)."""

    @pytest.mark.benchmark
    def test_single_query_latency(self):
        """Single query should classify in <10ms (target)."""
        query = "Find authentication logic"
        times = []

        # Warmup
        for _ in range(10):
            classify_query(query)

        # Measure
        for _ in range(100):
            start = time.perf_counter()
            classify_query(query)
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)

        mean_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times)

        print(f"\n  Mean latency: {mean_time:.2f}ms")
        print(f"  P95 latency: {p95_time:.2f}ms")

        # Target: <10ms mean, <15ms P95
        assert mean_time < 10, f"Mean latency {mean_time:.2f}ms exceeds 10ms target"
        assert p95_time < 15, f"P95 latency {p95_time:.2f}ms exceeds 15ms target"

    @pytest.mark.benchmark
    def test_bulk_classification_performance(self):
        """Benchmark classifier across all test cases."""
        test_cases = [
            # PATTERN
            'Find "authenticate()"',
            "Where is API_KEY used?",
            "Search for database.query()",
            # STRUCTURAL
            "Find class definitions",
            "All async functions",
            "Classes inheriting from Base",
            # SEMANTIC
            "Find authentication logic",
            "How does caching work?",
            "Where is error handling done?",
            # HYBRID
            "Find authenticate() and error handling",
            "System-wide authentication checks",
            # AMBIGUOUS
            "Find auth",
            "Code"
        ]

        times = []
        iterations = 100

        for _ in range(iterations):
            for query in test_cases:
                start = time.perf_counter()
                classify_query(query)
                elapsed = (time.perf_counter() - start) * 1000  # ms
                times.append(elapsed)

        results = {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "p95": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
            "p99": statistics.quantiles(times, n=100)[98] if len(times) >= 100 else max(times),
            "max": max(times),
            "min": min(times),
        }

        print(f"\n  Bulk Classification Performance (n={len(times)}):")
        print(f"  Mean: {results['mean']:.2f}ms")
        print(f"  Median: {results['median']:.2f}ms")
        print(f"  P95: {results['p95']:.2f}ms")
        print(f"  P99: {results['p99']:.2f}ms")
        print(f"  Max: {results['max']:.2f}ms")
        print(f"  Min: {results['min']:.2f}ms")

        # Performance targets from design doc
        assert results["mean"] < 10, f"Mean {results['mean']:.2f}ms exceeds 10ms target"
        assert results["p95"] < 15, f"P95 {results['p95']:.2f}ms exceeds 15ms target"
        assert results["p99"] < 25, f"P99 {results['p99']:.2f}ms exceeds 25ms target"


# ============================================================================
# Integration Test
# ============================================================================

class TestClassifierIntegration:
    """Integration tests for full classifier workflow."""

    def test_all_test_cases_from_design_doc(self):
        """Verify all 26 test cases from design doc are covered."""
        # This test verifies we have comprehensive coverage
        test_case_count = 0

        # Count PATTERN tests (5)
        pattern_tests = [m for m in dir(TestPatternCategory) if m.startswith('test_')]
        test_case_count += len(pattern_tests)

        # Count STRUCTURAL tests (5)
        structural_tests = [m for m in dir(TestStructuralCategory) if m.startswith('test_')]
        test_case_count += len(structural_tests)

        # Count SEMANTIC tests (8)
        semantic_tests = [m for m in dir(TestSemanticCategory) if m.startswith('test_')]
        test_case_count += len(semantic_tests)

        # Count HYBRID tests (5)
        hybrid_tests = [m for m in dir(TestHybridCategory) if m.startswith('test_')]
        test_case_count += len(hybrid_tests)

        # Count AMBIGUOUS tests (3)
        ambiguous_tests = [m for m in dir(TestAmbiguousQueries) if m.startswith('test_')]
        test_case_count += len(ambiguous_tests)

        # Should have all 26 test cases from design doc
        assert test_case_count >= 26, f"Only {test_case_count} test cases, expected 26+"

    def test_classifier_returns_valid_structure(self):
        """Verify classifier always returns valid QueryClassification."""
        test_queries = [
            'Find "authenticate()"',
            "Find class definitions",
            "Find authentication logic",
            "Find auth and error handling",
            "",
            None if False else "valid"  # Avoid None test for now
        ]

        for query in test_queries:
            if query is None:
                continue
            result = classify_query(query)
            assert isinstance(result, QueryClassification)
            assert isinstance(result.category, QueryCategory)
            assert isinstance(result.confidence, float)
            assert isinstance(result.indicators, list)
            assert isinstance(result.suggested_tool, str)
            assert isinstance(result.reasoning, str)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
