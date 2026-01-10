
# Test Plan for Uncovered MCP Tools

This document outlines the test plan for the 42 uncovered MCP tools in the Stravinsky project. The tools are grouped by priority, and each tool has a detailed test plan with test cases, required fixtures, mock requirements, integration test needs, and estimated test count.

## Phase 1: Critical

### Tool: `agent_spawn`

**Priority:** Phase 1 (Critical)

**Test Cases:**
1. **Happy Path**: Successfully spawns an agent with valid parameters.
2. **Invalid Agent Type**: Attempts to spawn an agent with an invalid type, expecting an error.
3. **Missing Required Parameters**: Attempts to spawn an agent without required parameters, expecting an error.
4. **Resource Limits**: Spawns an agent that exceeds resource limits (e.g., memory, CPU), expecting appropriate handling.
5. **Error Handling**: Agent spawn fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`:  Provides a running MCP server instance for integration tests.

**Mocks Needed:**
- Mock `subprocess.Popen`: To control agent process execution and simulate different outcomes (success, failure, resource exhaustion).

**Integration Tests:**
- Verify agent starts and connects to the MCP server.
- Verify agent can execute a simple task.

**Estimated Tests:** 3 unit + 2 integration = 5 total

### Tool: `agent_output`

**Priority:** Phase 1 (Critical)

**Test Cases:**
1. **Happy Path**: Retrieves agent output successfully.
2. **Invalid Agent ID**: Attempts to retrieve output for a non-existent agent, expecting an error.
3. **Empty Output**: Agent has not produced any output yet, ensure proper handling (e.g., empty string or specific message).
4. **Large Output**: Agent generates a large amount of output, ensure it's handled correctly without truncation or errors.
5. **Error Handling**: Agent output retrieval fails, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `spawned_agent`: Provides a pre-spawned agent fixture.

**Mocks Needed:**
- Mock agent process stdout/stderr: To simulate different output scenarios (empty, large, error messages).

**Integration Tests:**
- Verify output is retrieved correctly from a running agent.
- Verify output is streamed correctly.

**Estimated Tests:** 3 unit + 2 integration = 5 total

### Tool: `agent_cancel`

**Priority:** Phase 1 (Critical)

**Test Cases:**
1. **Happy Path**: Successfully cancels a running agent.
2. **Invalid Agent ID**: Attempts to cancel a non-existent agent, expecting an error.
3. **Agent Already Completed**: Attempts to cancel an agent that has already completed, expecting appropriate handling.
4. **Error Handling**: Agent cancellation fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `spawned_agent`: Provides a pre-spawned agent fixture.

**Mocks Needed:**
- Mock agent process termination: To control agent process termination and simulate different outcomes (success, failure).

**Integration Tests:**
- Verify agent is terminated correctly.
- Verify resources are released after cancellation.

**Estimated Tests:** 3 unit + 2 integration = 5 total

### Tool: `agent_list`

**Priority:** Phase 1 (Critical)

**Test Cases:**
1. **Happy Path**: Lists all running agents successfully.
2. **No Agents Running**: No agents are running, ensure an empty list is returned.
3. **Multiple Agents**: Lists multiple agents with different statuses.
4. **Error Handling**: Agent listing fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock agent process list: To simulate different agent states (running, completed, failed).

**Integration Tests:**
- Verify list contains correct information about each agent.

**Estimated Tests:** 3 unit + 1 integration = 4 total

### Tool: `agent_progress`

**Priority:** Phase 1 (Critical)

**Test Cases:**
1. **Happy Path**: Retrieves agent progress successfully.
2. **Invalid Agent ID**: Attempts to retrieve progress for a non-existent agent, expecting an error.
3. **No Progress**: Agent has not made any progress yet, ensure proper handling.
4. **Error Handling**: Agent progress retrieval fails, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `spawned_agent`: Provides a pre-spawned agent fixture.

**Mocks Needed:**
- Mock agent progress updates: To simulate different progress scenarios.

**Integration Tests:**
- Verify progress is updated correctly from a running agent.

**Estimated Tests:** 3 unit + 1 integration = 4 total

### Tool: `agent_retry`

**Priority:** Phase 1 (Critical)

**Test Cases:**
1. **Happy Path**: Successfully retries a failed agent.
2. **Invalid Agent ID**: Attempts to retry a non-existent agent, expecting an error.
3. **Agent Not Failed**: Attempts to retry an agent that has not failed, expecting an error.
4. **Error Handling**: Agent retry fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `spawned_agent`: Provides a pre-spawned agent fixture (in a failed state).

**Mocks Needed:**
- Mock agent process restart: To control agent process restart and simulate different outcomes (success, failure).

**Integration Tests:**
- Verify agent is restarted correctly.
- Verify agent resumes execution from the point of failure.

**Estimated Tests:** 3 unit + 2 integration = 5 total

### Tool: `invoke_gemini_agentic`

**Priority:** Phase 1 (Critical)

**Test Cases:**
1. **Happy Path**: Successfully invokes Gemini with agentic capabilities.
2. **Invalid Prompt**: Invokes Gemini with an invalid prompt, expecting an error.
3. **Missing Required Parameters**: Attempts to invoke Gemini without required parameters, expecting an error.
4. **Rate Limiting**: Invokes Gemini repeatedly to trigger rate limiting, ensure proper handling.
5. **Error Handling**: Gemini invocation fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock Gemini API: To control Gemini API responses and simulate different scenarios (success, failure, rate limiting).

**Integration Tests:**
- Verify Gemini is invoked correctly.
- Verify agentic capabilities are working as expected.

**Estimated Tests:** 3 unit + 2 integration = 5 total

### Tool: `invoke_openai`

**Priority:** Phase 1 (Critical)

**Test Cases:**
1. **Happy Path**: Successfully invokes OpenAI.
2. **Invalid Prompt**: Invokes OpenAI with an invalid prompt, expecting an error.
3. **Missing Required Parameters**: Attempts to invoke OpenAI without required parameters, expecting an error.
4. **Rate Limiting**: Invokes OpenAI repeatedly to trigger rate limiting, ensure proper handling.
5. **Error Handling**: OpenAI invocation fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock OpenAI API: To control OpenAI API responses and simulate different scenarios (success, failure, rate limiting).

**Integration Tests:**
- Verify OpenAI is invoked correctly.

**Estimated Tests:** 3 unit + 2 integration = 5 total

### Tool: `task_spawn`

**Priority:** Phase 1 (Critical)

**Test Cases:**
1. **Happy Path**: Successfully spawns a background task.
2. **Invalid Task Type**: Attempts to spawn a task with an invalid type, expecting an error.
3. **Missing Required Parameters**: Attempts to spawn a task without required parameters, expecting an error.
4. **Error Handling**: Task spawn fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock task execution: To control task execution and simulate different outcomes (success, failure).

**Integration Tests:**
- Verify task starts and completes successfully.

**Estimated Tests:** 3 unit + 2 integration = 5 total

### Tool: `task_status`

**Priority:** Phase 1 (Critical)

**Test Cases:**
1. **Happy Path**: Retrieves task status successfully.
2. **Invalid Task ID**: Attempts to retrieve status for a non-existent task, expecting an error.
3. **Error Handling**: Task status retrieval fails, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `spawned_task`: Provides a pre-spawned task fixture.

**Mocks Needed:**
- Mock task status updates: To simulate different task states (running, completed, failed).

**Integration Tests:**
- Verify status is updated correctly.

**Estimated Tests:** 3 unit + 1 integration = 4 total

### Tool: `task_list`

**Priority:** Phase 1 (Critical)

**Test Cases:**
1. **Happy Path**: Lists all background tasks successfully.
2. **No Tasks Running**: No tasks are running, ensure an empty list is returned.
3. **Multiple Tasks**: Lists multiple tasks with different statuses.
4. **Error Handling**: Task listing fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock task list: To simulate different task states (running, completed, failed).

**Integration Tests:**
- Verify list contains correct information about each task.

**Estimated Tests:** 3 unit + 1 integration = 4 total

## Phase 2: High Value

### Tool: `lsp_diagnostics`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Retrieves LSP diagnostics successfully for a valid file.
2. **Invalid File Path**: Attempts to retrieve diagnostics for a non-existent file, expecting an error.
3. **File with Errors**: Retrieves diagnostics for a file containing errors, ensuring errors are reported correctly.
4. **File Without Errors**: Retrieves diagnostics for a file without errors, ensuring an empty list or appropriate response.
5. **LSP Server Not Running**: LSP server is not running for the file type, ensure appropriate error handling.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `test_file`: Provides a test file fixture.

**Mocks Needed:**
- Mock LSP server responses: To simulate different diagnostic scenarios (errors, warnings, no errors).

**Integration Tests:**
- Verify diagnostics are retrieved correctly from a running LSP server.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `lsp_hover`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Retrieves hover information successfully for a valid position in a file.
2. **Invalid File Path**: Attempts to retrieve hover information for a non-existent file, expecting an error.
3. **Invalid Position**: Attempts to retrieve hover information for an invalid position in a file, expecting an error.
4. **No Hover Information**: No hover information is available for the given position, ensure proper handling.
5. **LSP Server Not Running**: LSP server is not running for the file type, ensure appropriate error handling.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `test_file`: Provides a test file fixture.

**Mocks Needed:**
- Mock LSP server responses: To simulate different hover information scenarios (valid information, no information).

**Integration Tests:**
- Verify hover information is retrieved correctly from a running LSP server.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `lsp_goto_definition`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Navigates to the definition of a symbol successfully.
2. **Invalid File Path**: Attempts to navigate to the definition in a non-existent file, expecting an error.
3. **Invalid Position**: Attempts to navigate to the definition from an invalid position, expecting an error.
4. **No Definition**: No definition is available for the given symbol, ensure proper handling.
5. **LSP Server Not Running**: LSP server is not running for the file type, ensure appropriate error handling.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `test_file`: Provides a test file fixture with defined symbols.

**Mocks Needed:**
- Mock LSP server responses: To simulate different definition scenarios (valid definition, no definition).

**Integration Tests:**
- Verify navigation to definition works correctly from a running LSP server.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `lsp_find_references`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Finds all references to a symbol successfully.
2. **Invalid File Path**: Attempts to find references in a non-existent file, expecting an error.
3. **Invalid Position**: Attempts to find references from an invalid position, expecting an error.
4. **No References**: No references are found for the given symbol, ensure proper handling.
5. **LSP Server Not Running**: LSP server is not running for the file type, ensure appropriate error handling.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `test_file`: Provides a test file fixture with references.

**Mocks Needed:**
- Mock LSP server responses: To simulate different reference scenarios (valid references, no references).

**Integration Tests:**
- Verify finding references works correctly from a running LSP server.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `lsp_document_symbols`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Lists all document symbols successfully.
2. **Invalid File Path**: Attempts to list symbols in a non-existent file, expecting an error.
3. **File Without Symbols**: File contains no symbols, ensure an empty list is returned.
4. **LSP Server Not Running**: LSP server is not running for the file type, ensure appropriate error handling.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `test_file`: Provides a test file fixture.

**Mocks Needed:**
- Mock LSP server responses: To simulate different symbol scenarios (valid symbols, no symbols).

**Integration Tests:**
- Verify listing document symbols works correctly from a running LSP server.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `lsp_workspace_symbols`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Lists all workspace symbols successfully.
2. **Empty Workspace**: Workspace contains no symbols, ensure an empty list is returned.
3. **LSP Server Not Running**: LSP server is not running, ensure appropriate error handling.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock LSP server responses: To simulate different symbol scenarios (valid symbols, no symbols).

**Integration Tests:**
- Verify listing workspace symbols works correctly from a running LSP server.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `lsp_prepare_rename`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Prepares a rename operation successfully.
2. **Invalid File Path**: Attempts to prepare a rename in a non-existent file, expecting an error.
3. **Invalid Position**: Attempts to prepare a rename from an invalid position, expecting an error.
4. **Not Renameable**: Symbol at the given position is not renameable, ensure proper handling.
5. **LSP Server Not Running**: LSP server is not running for the file type, ensure appropriate error handling.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `test_file`: Provides a test file fixture.

**Mocks Needed:**
- Mock LSP server responses: To simulate different rename scenarios (renameable, not renameable).

**Integration Tests:**
- Verify preparing a rename works correctly from a running LSP server.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `lsp_rename`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Renames a symbol successfully.
2. **Invalid File Path**: Attempts to rename a symbol in a non-existent file, expecting an error.
3. **Invalid Position**: Attempts to rename a symbol from an invalid position, expecting an error.
4. **Invalid New Name**: Attempts to rename a symbol with an invalid new name, expecting an error.
5. **LSP Server Not Running**: LSP server is not running for the file type, ensure appropriate error handling.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `test_file`: Provides a test file fixture.

**Mocks Needed:**
- Mock LSP server responses: To simulate different rename scenarios (successful rename, failed rename).

**Integration Tests:**
- Verify renaming a symbol works correctly from a running LSP server.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `lsp_code_actions`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Retrieves code actions successfully.
2. **Invalid File Path**: Attempts to retrieve code actions in a non-existent file, expecting an error.
3. **Invalid Position**: Attempts to retrieve code actions from an invalid position, expecting an error.
4. **No Code Actions**: No code actions are available for the given position, ensure proper handling.
5. **LSP Server Not Running**: LSP server is not running for the file type, ensure appropriate error handling.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `test_file`: Provides a test file fixture.

**Mocks Needed:**
- Mock LSP server responses: To simulate different code action scenarios (valid code actions, no code actions).

**Integration Tests:**
- Verify retrieving code actions works correctly from a running LSP server.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `lsp_code_action_resolve`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Resolves a code action successfully.
2. **Invalid Code Action**: Attempts to resolve a non-existent code action, expecting an error.
3. **LSP Server Not Running**: LSP server is not running for the file type, ensure appropriate error handling.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock LSP server responses: To simulate different resolve scenarios (successful resolve, failed resolve).

**Integration Tests:**
- Verify resolving a code action works correctly from a running LSP server.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `lsp_extract_refactor`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Extracts a refactoring successfully.
2. **Invalid File Path**: Attempts to extract a refactoring in a non-existent file, expecting an error.
3. **Invalid Range**: Attempts to extract a refactoring from an invalid range, expecting an error.
4. **Not Extractable**: Code at the given range is not extractable, ensure proper handling.
5. **LSP Server Not Running**: LSP server is not running for the file type, ensure appropriate error handling.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `test_file`: Provides a test file fixture.

**Mocks Needed:**
- Mock LSP server responses: To simulate different extract scenarios (extractable, not extractable).

**Integration Tests:**
- Verify extracting a refactoring works correctly from a running LSP server.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `lsp_servers`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Lists all running LSP servers successfully.
2. **No LSP Servers Running**: No LSP servers are running, ensure an empty list is returned.
3. **Multiple LSP Servers**: Lists multiple LSP servers with different supported file types.
4. **Error Handling**: LSP server listing fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock LSP server list: To simulate different LSP server states (running, stopped).

**Integration Tests:**
- Verify list contains correct information about each LSP server.

**Estimated Tests:** 3 unit + 1 integration = 4 total

### Tool: `ast_grep_search`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Searches for a pattern in files using ast-grep successfully.
2. **Invalid File Path**: Attempts to search in a non-existent file, expecting an error.
3. **Invalid Pattern**: Searches for an invalid pattern, expecting an error or appropriate handling.
4. **No Matches**: No matches are found for the given pattern, ensure proper handling.
5. **Error Handling**: ast-grep search fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `test_file`: Provides a test file fixture.

**Mocks Needed:**
- Mock ast-grep execution: To control ast-grep execution and simulate different outcomes (matches, no matches, errors).

**Integration Tests:**
- Verify ast-grep search works correctly.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `ast_grep_replace`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Replaces a pattern in files using ast-grep successfully.
2. **Invalid File Path**: Attempts to replace in a non-existent file, expecting an error.
3. **Invalid Pattern**: Attempts to replace with an invalid pattern, expecting an error.
4. **No Matches**: No matches are found for the given pattern, ensure proper handling.
5. **Error Handling**: ast-grep replace fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `test_file`: Provides a test file fixture.

**Mocks Needed:**
- Mock ast-grep execution: To control ast-grep execution and simulate different outcomes (successful replace, failed replace, errors).

**Integration Tests:**
- Verify ast-grep replace works correctly.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `grep_search`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Searches for a pattern in files using ripgrep successfully.
2. **Invalid File Path**: Attempts to search in a non-existent file, expecting an error.
3. **Invalid Pattern**: Searches for an invalid pattern, expecting an error or appropriate handling.
4. **No Matches**: No matches are found for the given pattern, ensure proper handling.
5. **Error Handling**: ripgrep search fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `test_file`: Provides a test file fixture.

**Mocks Needed:**
- Mock ripgrep execution: To control ripgrep execution and simulate different outcomes (matches, no matches, errors).

**Integration Tests:**
- Verify ripgrep search works correctly.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `glob_files`

**Priority:** Phase 2 (High Value)

**Test Cases:**
1. **Happy Path**: Lists files matching a glob pattern successfully.
2. **Invalid Glob Pattern**: Attempts to list files with an invalid glob pattern, expecting an error.
3. **No Matches**: No files match the given glob pattern, ensure an empty list is returned.
4. **Error Handling**: Glob files fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `test_file`: Provides a test file fixture.

**Mocks Needed:**
- Mock globbing: To control file listing and simulate different outcomes (matches, no matches, errors).

**Integration Tests:**
- Verify globbing works correctly.

**Estimated Tests:** 4 unit + 1 integration = 5 total

## Phase 3: Advanced

### Tool: `hybrid_search`

**Priority:** Phase 3 (Advanced)

**Test Cases:**
1. **Happy Path**: Performs a hybrid search successfully.
2. **Invalid Query**: Attempts to search with an invalid query, expecting an error.
3. **No Results**: No results are found for the given query, ensure proper handling.
4. **Error Handling**: Hybrid search fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `vector_store`: Provides a populated vector store fixture.

**Mocks Needed:**
- Mock vector store search: To control vector store search results.

**Integration Tests:**
- Verify hybrid search returns relevant results.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `multi_query_search`

**Priority:** Phase 3 (Advanced)

**Test Cases:**
1. **Happy Path**: Performs a multi-query search successfully.
2. **Invalid Query**: Attempts to search with an invalid query, expecting an error.
3. **No Results**: No results are found for the given queries, ensure proper handling.
4. **Error Handling**: Multi-query search fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `vector_store`: Provides a populated vector store fixture.

**Mocks Needed:**
- Mock vector store search: To control vector store search results.

**Integration Tests:**
- Verify multi-query search returns relevant results.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `decomposed_search`

**Priority:** Phase 3 (Advanced)

**Test Cases:**
1. **Happy Path**: Performs a decomposed search successfully.
2. **Invalid Query**: Attempts to search with an invalid query, expecting an error.
3. **No Results**: No results are found for the given query, ensure proper handling.
4. **Error Handling**: Decomposed search fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `vector_store`: Provides a populated vector store fixture.

**Mocks Needed:**
- Mock vector store search: To control vector store search results.
- Mock query decomposition logic.

**Integration Tests:**
- Verify decomposed search returns relevant results.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `enhanced_search`

**Priority:** Phase 3 (Advanced)

**Test Cases:**
1. **Happy Path**: Performs an enhanced search successfully.
2. **Invalid Query**: Attempts to search with an invalid query, expecting an error.
3. **No Results**: No results are found for the given query, ensure proper handling.
4. **Error Handling**: Enhanced search fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `vector_store`: Provides a populated vector store fixture.

**Mocks Needed:**
- Mock vector store search: To control vector store search results.
- Mock search enhancement logic.

**Integration Tests:**
- Verify enhanced search returns relevant results.

**Estimated Tests:** 4 unit + 1 integration = 5 total

### Tool: `cancel_indexing`

**Priority:** Phase 3 (Advanced)

**Test Cases:**
1. **Happy Path**: Cancels an ongoing indexing process successfully.
2. **No Indexing Running**: Attempts to cancel when no indexing is running, ensure proper handling.
3. **Error Handling**: Cancel indexing fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `vector_store`: Provides a populated vector store fixture.
- Running indexing process.

**Mocks Needed:**
- Mock indexing process: To control indexing process and simulate cancellation.

**Integration Tests:**
- Verify indexing is cancelled correctly.

**Estimated Tests:** 3 unit + 1 integration = 4 total

### Tool: `delete_index`

**Priority:** Phase 3 (Advanced)

**Test Cases:**
1. **Happy Path**: Deletes the vector index successfully.
2. **Index Does Not Exist**: Attempts to delete a non-existent index, ensure proper handling.
3. **Error Handling**: Delete index fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.
- `vector_store`: Provides a populated vector store fixture.

**Mocks Needed:**
- Mock vector store deletion.

**Integration Tests:**
- Verify index is deleted correctly.

**Estimated Tests:** 3 unit + 1 integration = 4 total

### Tool: `list_file_watchers`

**Priority:** Phase 3 (Advanced)

**Test Cases:**
1. **Happy Path**: Lists all file watchers successfully.
2. **No File Watchers**: No file watchers are running, ensure an empty list is returned.
3. **Multiple File Watchers**: Lists multiple file watchers with different configurations.
4. **Error Handling**: File watcher listing fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock file watcher list: To simulate different file watcher states (running, stopped).

**Integration Tests:**
- Verify list contains correct information about each file watcher.

**Estimated Tests:** 3 unit + 1 integration = 4 total

### Tool: `session_list`

**Priority:** Phase 3 (Advanced)

**Test Cases:**
1. **Happy Path**: Lists all active sessions successfully.
2. **No Sessions**: No active sessions exist, ensure an empty list is returned.
3. **Multiple Sessions**: Lists multiple sessions with different states.
4. **Error Handling**: Session listing fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock session store: To simulate different session states.

**Integration Tests:**
- Verify list contains correct information about each session.

**Estimated Tests:** 3 unit + 1 integration = 4 total

### Tool: `session_read`

**Priority:** Phase 3 (Advanced)

**Test Cases:**
1. **Happy Path**: Reads session data successfully.
2. **Invalid Session ID**: Attempts to read a non-existent session, expecting an error.
3. **Error Handling**: Session read fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock session store: To simulate session data.

**Integration Tests:**
- Verify correct session data is retrieved.

**Estimated Tests:** 3 unit + 1 integration = 4 total

### Tool: `session_search`

**Priority:** Phase 3 (Advanced)

**Test Cases:**
1. **Happy Path**: Searches for sessions based on criteria successfully.
2. **Invalid Search Criteria**: Attempts to search with invalid criteria, expecting an error.
3. **No Matching Sessions**: No sessions match the criteria, ensure an empty list is returned.
4. **Error Handling**: Session search fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock session store: To simulate different session data for search.

**Integration Tests:**
- Verify search returns the correct sessions.

**Estimated Tests:** 3 unit + 1 integration = 4 total

### Tool: `skill_list`

**Priority:** Phase 3 (Advanced)

**Test Cases:**
1. **Happy Path**: Lists all available skills successfully.
2. **No Skills**: No skills are available, ensure an empty list is returned.
3. **Error Handling**: Skill listing fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock skill registry: To simulate available skills.

**Integration Tests:**
- Verify list contains correct information about each skill.

**Estimated Tests:** 3 unit + 1 integration = 4 total

### Tool: `skill_get`

**Priority:** Phase 3 (Advanced)

**Test Cases:**
1. **Happy Path**: Retrieves skill details successfully.
2. **Invalid Skill ID**: Attempts to retrieve a non-existent skill, expecting an error.
3. **Error Handling**: Skill retrieval fails due to internal error, ensure proper error reporting.

**Required Fixtures:**
- `mcp_server`: Provides a running MCP server instance.

**Mocks Needed:**
- Mock skill registry: To simulate skill details.

**Integration Tests:**
- Verify correct skill details are retrieved.

**Estimated Tests:** 3 unit + 1 integration = 4 total
