# MCP Tool Invocation Flow

This document details how tools are registered, invoked, and processed in Stravinsky's MCP server.

## Overview

Stravinsky implements 54 MCP tools across 10 categories. Each tool follows a consistent invocation pattern with hooks for pre/post processing.

```mermaid
flowchart TB
    subgraph "Claude Code"
        CC[Claude Code]
    end

    subgraph "MCP Protocol"
        LT[list_tools]
        CT[call_tool]
    end

    subgraph "Stravinsky Server"
        TD[Tool Definitions<br/>server_tools.py]
        TH[Tool Handlers<br/>server.py]
        HM[Hook Manager]

        subgraph "Tool Implementations"
            MI[model_invoke.py]
            AM[agent_manager.py]
            CS[code_search.py]
            FC[find_code.py]
            SS[semantic_search.py]
            LSP[lsp/tools.py]
            SE[search_enhancements.py]
        end
    end

    CC -->|MCP| LT
    CC -->|MCP| CT
    LT --> TD
    CT --> TH
    TH --> HM
    HM --> MI
    HM --> AM
    HM --> CS
    HM --> FC
    HM --> SS
    HM --> LSP
    HM --> SE
```

## Tool Registration

### Tool Metadata Structure

Each tool is defined in `server_tools.py` with JSON Schema validation:

```python
Tool(
    name="invoke_gemini",
    description="Invoke a Gemini model with the given prompt...",
    inputSchema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "The prompt to send"},
            "model": {"type": "string", "default": "gemini-3-flash"},
            "max_tokens": {"type": "integer", "default": 8192},
            "temperature": {"type": "number", "default": 0.7},
            "agent_context": {
                "type": "object",
                "properties": {
                    "agent_type": {"type": "string"},
                    "task_id": {"type": "string"},
                    "description": {"type": "string"}
                }
            }
        },
        "required": ["prompt"]
    }
)
```

### Tool Categories

```mermaid
graph LR
    subgraph "Tool Categories (54 total)"
        MI[Model Invoke<br/>3 tools]
        ENV[Environment<br/>2 tools]
        AG[Agents<br/>7 tools]
        CS[Code Search<br/>5 tools]
        SS[Semantic Search<br/>11 tools]
        LSP[LSP<br/>12 tools]
        FW[File Watcher<br/>3 tools]
        SESS[Sessions<br/>3 tools]
        SK[Skills<br/>2 tools]
        FILE[File Ops<br/>6 tools]
    end
```

## Invocation Flow

### Complete Request Lifecycle

```mermaid
sequenceDiagram
    participant CC as Claude Code
    participant MCP as MCP Server
    participant HM as Hook Manager
    participant Tool as Tool Handler
    participant Ext as External Service

    CC->>MCP: call_tool(name, arguments)

    rect rgb(200, 230, 255)
        Note over MCP,HM: Pre-Tool Processing
        MCP->>HM: execute_pre_tool_call(name, args)
        HM->>HM: Run pre-tool hooks
        HM-->>MCP: Modified arguments
    end

    rect rgb(200, 255, 200)
        Note over MCP,Ext: Tool Execution
        MCP->>Tool: dispatch(name, arguments)

        alt Model Invoke Tool
            Tool->>HM: execute_pre_model_invoke(params)
            Tool->>Ext: HTTP Request (Gemini/OpenAI)
            Ext-->>Tool: Response
            Tool->>HM: execute_post_model_invoke(result)
        else Agent Tool
            Tool->>Tool: Validate with DelegationEnforcer
            Tool->>Tool: Spawn subprocess
            Tool-->>Tool: Background execution
        else LSP Tool
            Tool->>Tool: Get persistent server
            Tool->>Tool: LSP protocol request
        else Standard Tool
            Tool->>Tool: Direct execution
        end

        Tool-->>MCP: result_content
    end

    rect rgb(255, 230, 200)
        Note over MCP,HM: Post-Tool Processing
        MCP->>HM: execute_post_tool_call(name, result)
        HM->>HM: Run post-tool hooks
        HM-->>MCP: Processed result
    end

    MCP-->>CC: TextContent[]
```

### Dispatch Logic

```python
# server.py call_tool() dispatch pattern
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    hook_manager = get_hook_manager_lazy()

    # Pre-tool hooks
    arguments = await hook_manager.execute_pre_tool_call(name, arguments)

    # Dispatch by name
    if name == "invoke_gemini":
        from .tools.model_invoke import invoke_gemini
        result = await invoke_gemini(
            prompt=arguments["prompt"],
            model=arguments.get("model", "gemini-3-flash"),
            # ... other params
        )
    elif name == "agent_spawn":
        from .tools.agent_manager import agent_spawn
        result = await agent_spawn(
            prompt=arguments["prompt"],
            agent_type=arguments.get("agent_type", "explore"),
            task_graph_id=arguments.get("task_graph_id"),  # NEW: parallel enforcement
            # ... other params
        )
    elif name.startswith("lsp_"):
        from .tools.lsp import get_lsp_tool
        tool_fn = get_lsp_tool(name)
        result = await tool_fn(**arguments)
    # ... more tools

    # Post-tool hooks
    result = await hook_manager.execute_post_tool_call(name, result)

    return [TextContent(type="text", text=result)]
```

## Model Invocation Details

### invoke_gemini Flow

```mermaid
flowchart TD
    REQ[invoke_gemini Request] --> HOOKS1[Pre-Model Hooks]
    HOOKS1 --> CTX[Extract agent_context]
    CTX --> AUTH{Auth Mode?}

    AUTH -->|OAuth| OAUTH[Get OAuth Token]
    AUTH -->|API Key| APIKEY[Get API Key]

    OAUTH --> SEM[Acquire Semaphore<br/>Rate Limiting]
    APIKEY --> SEM

    SEM --> HTTP[HTTP POST Request]

    HTTP --> RESP{Response Code}

    RESP -->|200| PARSE[Parse Response]
    RESP -->|429| RL[Rate Limit Handler]
    RESP -->|5xx| RETRY[Retry with Backoff]
    RESP -->|4xx| ERROR[Return Error]

    RL -->|Has API Key| FALLBACK[Switch to API Key Mode]
    FALLBACK --> HTTP

    RETRY -->|Max 2 attempts| HTTP
    RETRY -->|Exhausted| ERROR

    PARSE --> HOOKS2[Post-Model Hooks]
    HOOKS2 --> RETURN[Return Result]
```

### Agent Context Propagation

```mermaid
flowchart LR
    subgraph "Context Flow"
        C1[Tool Arguments<br/>agent_context dict]
        C2[Pre-Model Hook<br/>params modification]
        C3[Logging<br/>stderr + logger]
        C4[Fallback Logic<br/>agent-specific behavior]
    end

    C1 --> C2 --> C3 --> C4
```

Example context usage:
```python
await invoke_gemini(
    prompt="Find authentication code",
    agent_context={
        "agent_type": "explore",
        "task_id": "agent_abc123",
        "description": "Search for auth patterns"
    }
)

# Logged as:
# [explore] -> gemini-3-flash: Find authentication code...
```

## Parallel Execution Enforcement

### DelegationEnforcer Integration

The `agent_spawn` tool now integrates with `DelegationEnforcer` for parallel execution validation:

```mermaid
flowchart TD
    REQ[agent_spawn Request] --> CHECK{task_graph_id<br/>provided?}

    CHECK -->|No| SPAWN[Normal spawn]
    CHECK -->|Yes| VALIDATE[DelegationEnforcer.validate_spawn]

    VALIDATE --> VALID{Is spawn<br/>allowed?}

    VALID -->|Yes| RECORD[Record spawn]
    VALID -->|No| ERROR[ParallelExecutionError]

    RECORD --> SPAWN
    SPAWN --> RESULT[Return task_id]
```

Usage with parallel enforcement:
```python
# During DELEGATE phase, orchestrator sets enforcer
from mcp_bridge.tools.agent_manager import set_delegation_enforcer
set_delegation_enforcer(enforcer)

# Subsequent spawns are validated
await agent_spawn(
    prompt="Search for auth patterns",
    agent_type="explore",
    task_graph_id="task_001",  # Links to TaskGraph node
)

# Independent tasks MUST be spawned together or error is raised
```

## Rate Limiting Architecture

### Concurrency Control

```mermaid
flowchart TB
    subgraph "Per-Model Semaphores"
        S1[gemini-3-flash<br/>Semaphore(10)]
        S2[gemini-3-pro<br/>Semaphore(5)]
        S3[gemini-3-pro-high<br/>Semaphore(3)]
    end

    subgraph "Time-Window Limiter"
        TL[30 requests/minute<br/>global limit]
    end

    REQ1[Request 1] --> S1
    REQ2[Request 2] --> S1
    REQ3[Request 3] --> S2

    S1 --> TL
    S2 --> TL
    S3 --> TL

    TL --> OUT[HTTP Request]
```

### Rate Limit Configuration

```python
# Default semaphore limits
SEMAPHORE_LIMITS = {
    "gemini-3-flash": 10,
    "gemini-3-pro": 5,
    "gemini-3-pro-high": 3,
    "gpt-5.2": 3,
}

# Time-window limit
REQUESTS_PER_MINUTE = 30
```

## Error Handling

### Retry Strategy

```mermaid
stateDiagram-v2
    [*] --> Try: Request

    Try --> Success: 2xx Response
    Try --> Retry: 5xx Error

    Retry --> Wait: Attempt < 2
    Wait --> Try: Exponential Backoff

    Retry --> Fail: Max Attempts

    Try --> RateLimit: 429 Error
    RateLimit --> Fallback: Has API Key
    RateLimit --> Fail: No Fallback

    Fallback --> Try: Retry with API Key

    Try --> Fail: 4xx Error

    Success --> [*]
    Fail --> [*]
```

### Backoff Timing

```python
# Retry configuration
retry = tenacity.retry(
    stop=stop_after_attempt(2),           # Max 2 attempts
    wait=wait_exponential(multiplier=10), # 10s -> 20s -> 40s
    retry=retry_if_result(is_retryable),  # Only 5xx errors
)
```

## Tool Categories Reference

### Model Invoke (3 tools)

| Tool | Model | Purpose |
|------|-------|---------|
| `invoke_gemini` | Gemini 3 Flash/Pro | General text generation |
| `invoke_gemini_agentic` | Gemini 3 Flash | Agentic loop with tools |
| `invoke_openai` | GPT-5.2 | Complex reasoning |

### Agent Tools (7 tools)

| Tool | Purpose |
|------|---------|
| `agent_spawn` | Launch background agent with optional task_graph_id for parallel enforcement |
| `agent_output` | Get agent results (block=true to wait) |
| `agent_progress` | Real-time progress monitoring |
| `agent_cancel` | Cancel running agent |
| `agent_list` | List all agents |
| `agent_retry` | Retry failed agent |
| `agent_cleanup` | Remove old completed/failed agents |

### Code Search (5 tools)

| Tool | Purpose |
|------|---------|
| `ast_grep_search` | AST-aware structural pattern search |
| `ast_grep_replace` | AST-aware code replacement |
| `grep_search` | Fast text/regex search (ripgrep) |
| `glob_files` | Find files by pattern |
| `find_code` | Smart routing to optimal search strategy |

### LSP Tools (12 tools)

| Tool | LSP Method | Purpose |
|------|-----------|---------|
| `lsp_hover` | `textDocument/hover` | Type info at position |
| `lsp_goto_definition` | `textDocument/definition` | Jump to definition |
| `lsp_find_references` | `textDocument/references` | Find all usages |
| `lsp_document_symbols` | `textDocument/documentSymbol` | File outline |
| `lsp_workspace_symbols` | `workspace/symbol` | Search symbols |
| `lsp_prepare_rename` | `textDocument/prepareRename` | Validate rename |
| `lsp_rename` | `textDocument/rename` | Rename symbol |
| `lsp_code_actions` | `textDocument/codeAction` | Quick fixes |
| `lsp_code_action_resolve` | N/A (ruff) | Apply fix |
| `lsp_extract_refactor` | N/A (jedi) | Extract function |
| `lsp_servers` | N/A | List servers |
| `lsp_diagnostics` | N/A (ruff/tsc) | File diagnostics |

### Semantic Search (11 tools)

| Tool | Purpose |
|------|---------|
| `semantic_search` | Natural language code search |
| `hybrid_search` | Semantic + AST combined search |
| `semantic_index` | Index codebase for search |
| `semantic_stats` | Index statistics |
| `multi_query_search` | LLM-expanded query variations |
| `decomposed_search` | Break complex queries into sub-searches |
| `enhanced_search` | Auto-select best strategy |
| `start_file_watcher` | Auto-reindex on file changes |
| `stop_file_watcher` | Stop watching |
| `list_file_watchers` | List active watchers |
| `cancel_indexing` | Cancel ongoing indexing |
| `delete_index` | Remove search index |

### File Operations (6 tools)

| Tool | Purpose |
|------|---------|
| `list_directory` | List files in directory |
| `read_file` | Read file contents with smart truncation |
| `write_file` | Write content to file |
| `replace` | Replace text in file |
| `run_shell_command` | Execute shell command |
| `tool_search` | Search for tools by name/category |

### Environment (2 tools)

| Tool | Purpose |
|------|---------|
| `get_project_context` | Git status, rules, todos |
| `get_system_health` | Dependencies and auth status |

### Sessions (3 tools)

| Tool | Purpose |
|------|---------|
| `session_list` | List Claude Code sessions |
| `session_read` | Read session messages |
| `session_search` | Search session content |

### Skills (2 tools)

| Tool | Purpose |
|------|---------|
| `skill_list` | List available commands |
| `skill_get` | Get command content |

## Lazy Loading Pattern

All tool implementations use lazy imports to minimize startup time:

```python
# Instead of top-level imports
# from .tools.model_invoke import invoke_gemini  # Wrong

# Tools are imported only when called
if name == "invoke_gemini":
    from .tools.model_invoke import invoke_gemini  # Correct
    result = await invoke_gemini(...)
```

This reduces initial memory footprint and speeds up MCP server startup.

## Related Documentation

- [Architecture Overview](ARCHITECTURE.md)
- [OAuth Flow](OAUTH_FLOW.md)
- [Agent Orchestration](AGENT_ORCHESTRATION.md)
- [LSP Architecture](LSP_ARCHITECTURE.md)
- [Injection Points](../implementation/MCP_TOOL_CALL_INJECTION_POINTS.md)
