# /str:search - Semantic Code Search

Search your indexed project using natural language queries with the `semantic_search()` MCP tool.

## What This Does

Performs semantic code search using pre-computed vector embeddings to find code matching your natural language description:

Examples:
- "find authentication logic"
- "error handling in API endpoints"
- "database connection pooling"
- "logging and monitoring"
- "configuration management"
- "HTTP request processing"

## Prerequisites

This command requires the project to be indexed first. **Run `/str:index` before using `/str:search`.**

## Usage

Invoke the `semantic_search()` MCP tool directly with your natural language query:

```
semantic_search(
  query="your search description here",
  project_path=".",
  n_results=10,
  provider="ollama",
  language=None,
  node_type=None
)
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Natural language search description |
| `project_path` | string | "." | Project root directory |
| `n_results` | int | 10 | Number of results to return |
| `provider` | string | "ollama" | Embedding provider: ollama, gemini, openai, huggingface |
| `language` | string | None | Optional language filter (py, ts, js, java, go, etc.) |
| `node_type` | string | None | Optional node type filter (function, class, method, import, etc.) |

## Example Queries

### Architectural/Design Questions

```
semantic_search(query="authentication and authorization implementation")
semantic_search(query="error handling and exception recovery patterns", n_results=15)
semantic_search(query="caching and performance optimization strategies")
semantic_search(query="database connection pooling and persistence")
semantic_search(query="configuration loading and environment settings")
```

### Feature Discovery

```
semantic_search(query="logging instrumentation and monitoring")
semantic_search(query="HTTP request processing and routing")
semantic_search(query="input validation and data sanitization")
semantic_search(query="background job processing and scheduling")
semantic_search(query="rate limiting and throttling mechanisms")
```

### Code Organization

```
semantic_search(query="testing framework and test utilities")
semantic_search(query="deployment pipeline and release management")
semantic_search(query="security encryption and cryptographic operations")
semantic_search(query="transaction handling and atomicity guarantees")
```

### Filtered Search

```
semantic_search(query="error handling patterns", language="py")
semantic_search(query="authentication logic", node_type="class")
semantic_search(query="API handlers", language="py", node_type="function")
```

## Provider Options

### Ollama (Default - Recommended for Development)

Free, local, private embeddings:
- No setup required if ollama is running
- Model: nomic-embed-text (embeddings) or similar
- Speed: Fast
- Cost: Free

**Setup:**
```bash
# Install ollama (if not already installed)
brew install ollama  # macOS

# Start ollama server
ollama serve

# In another terminal, pull the embedding model
ollama pull nomic-embed-text
```

### Gemini (Cloud - Recommended for Production)

Google's embeddings service:
- **Setup:** `stravinsky-auth login gemini`
- **Speed:** Fast
- **Cost:** Low (~$0.075/1M tokens)
- **Quality:** Excellent

### OpenAI

OpenAI's embeddings API:
- **Setup:** `stravinsky-auth login openai`
- **Speed:** Medium
- **Cost:** Medium (~$0.10/1M tokens)
- **Quality:** Excellent

### HuggingFace

Free cloud embeddings (no auth required):
- **Speed:** Slower (can be slow for large codebases)
- **Cost:** Free
- **Quality:** Good

## Tips

1. **Be specific and conversational** in your queries
   - Good: "How is authentication and authorization implemented?"
   - Less effective: "auth"

2. **Use filters to narrow results**
   - Language filter: `language="py"` for Python-only results
   - Node type filter: `node_type="function"` for function definitions only

3. **Adjust result count based on codebase size**
   - Small projects: `n_results=5`
   - Medium projects: `n_results=10` (default)
   - Large projects: `n_results=15-20`

4. **Rebuild index if results are stale**
   - Run `/str:index force=true` to reindex the entire project

5. **Check index status**
   - Run `semantic_stats()` to view index statistics and provider information

## Switching Providers

```
# Default (local ollama - free)
semantic_search(query="your query")

# Cloud providers
semantic_search(query="your query", provider="gemini")
semantic_search(query="your query", provider="openai")
semantic_search(query="your query", provider="huggingface")
```

First-time setup for cloud providers:

```bash
# Gemini OAuth
stravinsky-auth login gemini

# OpenAI OAuth
stravinsky-auth login openai
```

## Common Search Patterns

### Finding Implementation Details

```
semantic_search(query="where is X implemented")
semantic_search(query="how does Y work")
semantic_search(query="what components make up Z")
```

### Quality/Best Practices

```
semantic_search(query="error handling patterns in the codebase")
semantic_search(query="security checks and validation logic")
semantic_search(query="performance optimization strategies")
```

### Integration Points

```
semantic_search(query="external API integration and client libraries")
semantic_search(query="database queries and ORM usage")
semantic_search(query="message queue and event processing")
```

## Related Commands

- `/str:index` - Index the project for semantic search
- `/explore` - Run explore agent for code discovery
- `/delphi` - Ask architecture and design questions
- `/dewey` - Research implementation patterns
