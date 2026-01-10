# MCP Tool Test Coverage Analysis

**Generated:** 2026-01-10
**Project:** Stravinsky MCP Bridge

## Executive Summary

| Metric | Value |
|--------|-------|
| Total MCP Tools | 50 |
| Tools with Tests | ~8 |
| Tools without Tests | ~42 |
| **Test Coverage** | **~16%** |

## Test Files Found

1. **test_mcp_server_integration.py** - Server startup, protocol compliance, version consistency
2. **test_api_key_auth.py** - Gemini API key authentication
3. **test_direct_gemini.py** - invoke_gemini tool testing
4. **test_hooks.py** - Hook system testing
5. **test_new_hooks.py** - New hook patterns
6. **test_file_watcher.py** - Semantic search file watching
7. **test_file_watcher_no_index.py** - File watcher error handling
8. **test_auto_indexing.py** - Semantic indexing
9. **test_query_classifier.py** - Query classification
10. **test_query_classification.py** - Query classification patterns
11. **test_symlink_boundary.py** - Symlink handling
12. **test_update_manager.py** - Update management
13. **test_lsp_cleanup.py** (root) - LSP cleanup
14. **test_lsp_manager.py** (root) - LSP manager
15. **test_agentic_api.py** (root) - Agentic API

## Tested MCP Tools (✅ ~8 tools)

### Model Invocation
- ✅ **invoke_gemini** - test_api_key_auth.py, test_direct_gemini.py

### Semantic Search
- ✅ **semantic_index** - test_auto_indexing.py, test_file_watcher.py
- ✅ **semantic_search** - test_auto_indexing.py, verify_semantic_search.py
- ✅ **start_file_watcher** - test_file_watcher.py, test_file_watcher_no_index.py
- ✅ **stop_file_watcher** - test_file_watcher.py
- ✅ **semantic_stats** - test_auto_indexing.py

### Infrastructure
- ✅ **stravinsky_version** - test_mcp_server_integration.py (version consistency)
- ✅ **get_system_health** - Implied in integration tests

## Untested MCP Tools (❌ ~42 tools)

### 🔴 HIGH PRIORITY (Core Tools - CRITICAL GAPS)

#### Model Invocation
- ❌ **invoke_gemini_agentic** - Agentic loop with tool calls (CRITICAL)
- ❌ **invoke_openai** - OpenAI/GPT integration (CRITICAL)

#### Agent Management (ALL UNTESTED - CRITICAL!)
- ❌ **agent_spawn** - Spawn background agents
- ❌ **agent_output** - Get agent results
- ❌ **agent_cancel** - Cancel running agents
- ❌ **agent_list** - List all agents
- ❌ **agent_progress** - Monitor agent progress
- ❌ **agent_retry** - Retry failed agents

#### Background Tasks (ALL UNTESTED)
- ❌ **task_spawn** - Spawn background tasks
- ❌ **task_status** - Check task status
- ❌ **task_list** - List all tasks

### 🟡 MEDIUM PRIORITY (Advanced Features)

#### LSP Tools (ALL 12 UNTESTED - MAJOR GAP!)
- ❌ **lsp_hover** - Type info and docs
- ❌ **lsp_goto_definition** - Jump to definition
- ❌ **lsp_find_references** - Find symbol references
- ❌ **lsp_document_symbols** - File outline
- ❌ **lsp_workspace_symbols** - Workspace symbol search
- ❌ **lsp_prepare_rename** - Validate rename
- ❌ **lsp_rename** - Rename symbol
- ❌ **lsp_code_actions** - Quick fixes
- ❌ **lsp_code_action_resolve** - Apply fixes
- ❌ **lsp_extract_refactor** - Extract code
- ❌ **lsp_servers** - List LSP servers
- ❌ **lsp_diagnostics** - Errors/warnings

#### Code Search
- ❌ **ast_grep_search** - AST pattern search
- ❌ **ast_grep_replace** - AST-aware replace
- ❌ **grep_search** - Text search (ripgrep)
- ❌ **glob_files** - File pattern matching

#### Advanced Semantic Search
- ❌ **hybrid_search** - Semantic + AST search
- ❌ **multi_query_search** - Query expansion
- ❌ **decomposed_search** - Query decomposition
- ❌ **enhanced_search** - Unified advanced search
- ❌ **cancel_indexing** - Cancel indexing
- ❌ **delete_index** - Delete semantic indexes
- ❌ **list_file_watchers** - List active watchers

### 🟢 LOW PRIORITY (Utility/Metadata)

#### Environment/Context
- ❌ **get_project_context** - Git status, rules, todos
- ❌ **system_restart** - Restart MCP server

#### Session Management (ALL UNTESTED)
- ❌ **session_list** - List Claude Code sessions
- ❌ **session_read** - Read session messages
- ❌ **session_search** - Search session history

#### Skill/Command Management (ALL UNTESTED)
- ❌ **skill_list** - List available skills
- ❌ **skill_get** - Get skill content

## Coverage by Category

| Category | Total | Tested | Coverage |
|----------|-------|--------|----------|
| **Model Invocation** | 3 | 1 | 33% |
| **Agent Management** | 6 | 0 | 0% ⚠️ |
| **Background Tasks** | 3 | 0 | 0% ⚠️ |
| **LSP Tools** | 12 | 0 | 0% ⚠️ |
| **Code Search** | 4 | 0 | 0% ⚠️ |
| **Semantic Search** | 13 | 5 | 38% |
| **Environment** | 2 | 1 | 50% |
| **Sessions** | 3 | 0 | 0% ⚠️ |
| **Skills** | 2 | 0 | 0% ⚠️ |
| **Infrastructure** | 2 | 2 | 100% ✅ |

## Recommended Test Priorities

### Phase 1: Critical Core Tools (Immediate)
1. **agent_spawn** + **agent_output** - Core parallel execution
2. **invoke_gemini_agentic** - Agentic loop testing
3. **invoke_openai** - Multi-model support
4. **task_spawn** + **task_status** - Background task system

### Phase 2: LSP & Code Search (High Value)
1. **lsp_diagnostics** - Error detection
2. **lsp_hover** + **lsp_goto_definition** - Navigation
3. **ast_grep_search** - AST pattern matching
4. **grep_search** + **glob_files** - Basic search

### Phase 3: Advanced Search (Medium Value)
1. **hybrid_search** - Combined search
2. **multi_query_search** - Query expansion
3. **enhanced_search** - Unified search

### Phase 4: Management Tools (Low Value)
1. **session_list** + **session_search** - Session management
2. **skill_list** + **skill_get** - Skill management
3. **get_project_context** - Context gathering

## Test Infrastructure Gaps

### Missing Test Utilities
- No MCP tool mocking framework
- No fixture for fake agent responses
- No test data generators for code samples
- No LSP server mocking
- No OAuth token mocking

### Missing Integration Tests
- End-to-end agent spawn → output workflow
- Multi-agent parallel execution
- LSP manager lifecycle testing
- Semantic search with multiple providers

### Missing Edge Case Tests
- Tool error handling
- Timeout scenarios
- Resource cleanup on failures
- Concurrent tool invocations

## Recommendations

### Immediate Actions (Week 1)
1. **Create agent management test suite** - test_agent_manager.py
2. **Create LSP tools test suite** - test_lsp_tools.py
3. **Add invoke_gemini_agentic tests** to test_direct_gemini.py
4. **Add invoke_openai tests** - test_openai.py

### Short-term Actions (Week 2-3)
1. **Create code search test suite** - test_code_search.py
2. **Expand semantic search tests** - test_semantic_search.py
3. **Create session management tests** - test_sessions.py
4. **Add error handling tests** for all tools

### Long-term Actions (Month 1)
1. **Build test framework** - Shared fixtures, mocks, utilities
2. **Add integration tests** - End-to-end workflows
3. **Add performance tests** - Load testing, timeout scenarios
4. **Add security tests** - Input validation, injection attacks

## Conclusion

**Current state:** Only 16% of MCP tools have test coverage.

**Critical gaps:**
- Agent management (0% coverage)
- LSP tools (0% coverage)
- Background tasks (0% coverage)
- Code search (0% coverage)

**Recommendation:** Prioritize agent management and LSP tool testing as these are core features heavily used in production. Aim for 80% coverage within 4 weeks.
