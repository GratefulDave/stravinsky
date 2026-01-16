# Stravinsky Architecture

This document provides a comprehensive view of Stravinsky's architecture with detailed flow diagrams.

## System Overview

Stravinsky is an MCP (Model Context Protocol) server that extends Claude Code with multi-model orchestration, OAuth authentication, and specialized tooling.

```mermaid
graph TB
    subgraph "Claude Code"
        CC[Claude Code CLI]
        HC[Hook System]
        TS[Task System]
    end

    subgraph "Stravinsky MCP Server"
        MCP[MCP Server<br/>server.py]

        subgraph "Tools Layer"
            MI[Model Invoke<br/>invoke_gemini/openai]
            AG[Agent Tools<br/>agent_spawn/output]
            CS[Code Search<br/>ast_grep/grep/glob]
            SS[Semantic Search<br/>vector embeddings]
            LSP[LSP Tools<br/>12 refactoring tools]
        end

        subgraph "Auth Layer"
            OAuth[OAuth Manager]
            TK[Token Store<br/>keyring + encrypted files]
        end

        subgraph "Execution Layer"
            AM[Agent Manager<br/>background processes]
            LM[LSP Manager<br/>persistent servers]
            VS[Vector Store<br/>ChromaDB]
        end
    end

    subgraph "External Models"
        GM[Gemini API<br/>Antigravity + Direct]
        OA[OpenAI API<br/>ChatGPT Backend]
    end

    CC -->|MCP Protocol| MCP
    HC -->|Hook Events| CC
    TS -->|Task Delegation| CC

    MCP --> MI
    MCP --> AG
    MCP --> CS
    MCP --> SS
    MCP --> LSP

    MI --> OAuth
    OAuth --> TK
    OAuth --> GM
    OAuth --> OA

    AG --> AM
    LSP --> LM
    SS --> VS
```

## Component Architecture

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **MCP Server** | `mcp_bridge/server.py` | Entry point, tool dispatch |
| **Tool Definitions** | `mcp_bridge/server_tools.py` | Tool metadata (47 tools) |
| **Model Invoke** | `mcp_bridge/tools/model_invoke.py` | Gemini/OpenAI integration |
| **Agent Manager** | `mcp_bridge/tools/agents/` | Background agent spawning |
| **LSP Manager** | `mcp_bridge/tools/lsp/manager.py` | Persistent LSP servers |
| **Semantic Search** | `mcp_bridge/tools/semantic_search/` | Vector embeddings |
| **OAuth** | `mcp_bridge/auth/` | Token management |

### Tool Categories (47 Total)

```mermaid
pie title Stravinsky Tool Distribution
    "Model Invoke" : 3
    "Environment" : 6
    "Background Tasks" : 3
    "Agents" : 6
    "Code Search" : 4
    "Semantic Search" : 12
    "LSP" : 12
    "Sessions" : 3
    "Skills" : 2
```

## Key Architectural Flows

### 1. MCP Tool Invocation Flow

```mermaid
sequenceDiagram
    participant CC as Claude Code
    participant MCP as MCP Server
    participant HM as Hook Manager
    participant Tool as Tool Implementation
    participant Ext as External API

    CC->>MCP: call_tool(name, arguments)
    MCP->>HM: execute_pre_tool_call()
    HM-->>MCP: modified arguments

    alt Model Invoke Tool
        MCP->>Tool: invoke_gemini/openai()
        Tool->>HM: execute_pre_model_invoke()
        Tool->>Ext: HTTP Request
        Ext-->>Tool: Response
        Tool->>HM: execute_post_model_invoke()
    else Standard Tool
        MCP->>Tool: tool_function()
    end

    Tool-->>MCP: result
    MCP->>HM: execute_post_tool_call()
    MCP-->>CC: TextContent[]
```

### 2. OAuth Authentication Flow

```mermaid
stateDiagram-v2
    [*] --> CheckOAuth: Tool Request

    CheckOAuth --> TryOAuth: OAuth Configured
    CheckOAuth --> UseAPIKey: API Key Only

    TryOAuth --> Success: Token Valid
    TryOAuth --> RefreshToken: Token Expired
    TryOAuth --> RateLimited: 429 Response

    RefreshToken --> Success: Refresh OK
    RefreshToken --> ReAuthenticate: Refresh Failed

    RateLimited --> APIKeyFallback: Has API Key
    RateLimited --> WaitCooldown: No API Key

    APIKeyFallback --> Success: 5-min Cooldown
    WaitCooldown --> TryOAuth: After 5 min

    UseAPIKey --> Success: Direct API
    ReAuthenticate --> [*]: User Action Required

    Success --> [*]: Return Response
```

### 3. Agent Orchestration Flow

```mermaid
flowchart TB
    subgraph "Orchestrator (Claude Sonnet)"
        O[Stravinsky Orchestrator]
        TODO[TodoWrite]
        SPAWN[agent_spawn x N]
    end

    subgraph "Parallel Agents"
        E1[explore:gemini-3-flash]
        E2[explore:gemini-3-flash]
        D[dewey:gemini-3-flash]
    end

    subgraph "Blocking Agents"
        F[frontend:gemini-3-pro]
        DEL[delphi:gpt-5.2]
    end

    O -->|1. Create tasks| TODO
    TODO -->|2. Immediate fan-out| SPAWN
    SPAWN -->|async| E1
    SPAWN -->|async| E2
    SPAWN -->|async| D

    E1 -->|results| O
    E2 -->|results| O
    D -->|results| O

    O -->|blocking| F
    F -->|complete| O

    O -->|blocking| DEL
    DEL -->|complete| O
```

### 4. LSP Persistence Architecture

```mermaid
flowchart LR
    subgraph "First Request (Cold Start)"
        R1[Tool Request] --> M1[LSPManager]
        M1 -->|spawn| P1[jedi-language-server]
        P1 -->|initialize| I1[LSP Init]
        I1 -->|index| X1[Codebase Index<br/>~2-5s]
        X1 -->|respond| R1
    end

    subgraph "Subsequent Requests (Warm)"
        R2[Tool Request] --> M2[LSPManager]
        M2 -->|reuse| P2[Existing Server]
        P2 -->|immediate| R2
    end

    M1 -.->|singleton| M2
    P1 -.->|persistent| P2

    style X1 fill:#ff9999
    style P2 fill:#99ff99
```

### 5. Semantic Search Pipeline

```mermaid
flowchart TB
    subgraph "Indexing Pipeline"
        F[Source Files] --> CH[Chunker]
        CH -->|Python| AST[AST Parser<br/>functions/classes]
        CH -->|Other| LN[Line Chunker<br/>512 lines]
        AST --> EMB[Embedding Provider]
        LN --> EMB
        EMB -->|vectors| DB[(ChromaDB)]
    end

    subgraph "Search Pipeline"
        Q[Natural Language Query]
        Q --> QE[Query Embedding]
        QE --> VS[Vector Search]
        DB --> VS
        VS --> RES[Ranked Results]
    end

    subgraph "Embedding Providers"
        OL[Ollama<br/>nomic-embed-text]
        GE[Gemini<br/>gemini-embedding-001]
        OP[OpenAI<br/>text-embedding-3-small]
        HF[HuggingFace<br/>all-mpnet]
    end

    EMB -.-> OL
    EMB -.-> GE
    EMB -.-> OP
    EMB -.-> HF
    QE -.-> OL
```

## Performance Characteristics

### LSP 35x Speedup

| Metric | Cold Start | Warm Start | Improvement |
|--------|-----------|------------|-------------|
| Process startup | 100-200ms | 0ms | Eliminated |
| LSP initialization | 50-100ms | 0ms | Eliminated |
| Codebase indexing | 1-5s | 0ms | Eliminated |
| Request processing | 5-50ms | 5-50ms | Same |
| **Total** | **2-5s** | **5-50ms** | **35-400x** |

### Agent Cost Optimization

| Agent | Wrapper Model | External Model | Use Case |
|-------|---------------|----------------|----------|
| `explore` | Haiku | gemini-3-flash | Code search |
| `dewey` | Haiku | gemini-3-flash | Documentation |
| `frontend` | Haiku | gemini-3-pro | UI/UX |
| `delphi` | Haiku | gpt-5.2-medium | Architecture |

## State Management

```mermaid
stateDiagram-v2
    [*] --> Idle: MCP Server Start

    Idle --> Processing: Tool Call
    Processing --> Idle: Complete

    state Processing {
        [*] --> PreHooks
        PreHooks --> Execute
        Execute --> PostHooks
        PostHooks --> [*]
    }

    state "Background State" as BG {
        LSPServers: LSP Servers (persistent)
        Agents: Agent Processes
        FileWatcher: File Watcher
        VectorDB: ChromaDB
    }

    Idle --> BG: Managed Resources
```

## Error Handling Strategy

```mermaid
flowchart TD
    REQ[Request] --> TRY{Try Primary}

    TRY -->|Success| OK[Return Result]
    TRY -->|5xx Error| RETRY[Retry with Backoff<br/>10s → 20s → 40s]
    TRY -->|429 Rate Limit| FALLBACK[Switch to Fallback]
    TRY -->|4xx Error| FAIL[Return Error]

    RETRY -->|Max 2 attempts| TRY
    RETRY -->|Exhausted| FAIL

    FALLBACK -->|Has API Key| API[Use API Key<br/>5-min cooldown]
    FALLBACK -->|No API Key| WAIT[Wait for Cooldown]

    API --> OK
    WAIT -->|5 min| TRY
```

## Security Architecture

### Token Storage

```mermaid
flowchart TB
    subgraph "Primary: System Keyring"
        KC[macOS Keychain]
        KL[Linux Secret Service]
        KW[Windows Credential Locker]
    end

    subgraph "Fallback: Encrypted Files"
        EF[~/.stravinsky/tokens/]
        KEY[.key file<br/>AES-128 key]
        TF[token files<br/>Fernet encrypted]
    end

    AUTH[OAuth Flow] -->|try| KC
    AUTH -->|try| KL
    AUTH -->|try| KW
    KC -->|fail| EF
    KL -->|fail| EF
    KW -->|fail| EF

    KEY -->|encrypts| TF
    TF -->|0o600| PERMS[File Permissions]
```

## Related Documentation

- [OAuth Flow Details](OAUTH_FLOW.md)
- [MCP Tool Flow](MCP_TOOL_FLOW.md)
- [Agent Orchestration](AGENT_ORCHESTRATION.md)
- [LSP Architecture](LSP_ARCHITECTURE.md)
- [Semantic Search](SEMANTIC_SEARCH_QUICK_START.md)
- [Hooks System](HOOKS.md)
