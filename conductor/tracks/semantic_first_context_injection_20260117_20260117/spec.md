# Semantic First Context Injection

## Objective
Reduce token usage and latency by automatically injecting relevant code context into agents at spawn time, eliminating the need for initial "discovery" steps (grep/read).

## Implementation Details

### 1. `AgentManager.spawn_async` Update
- Add `semantic_first: bool = False` parameter.
- If `True`:
  - Call `mcp_bridge.tools.semantic_search.search(prompt, n_results=5)`.
  - Format results:
    ```
    [Context 1] path/to/file.py
    def relevant_function():
        ...
    ```
  - Prepend to agent prompt.

### 2. `agent_spawn` Tool Update
- Expose `semantic_first` argument in the tool definition.
- Default to `True` for `explore` and `delphi` agents? Or let user specify?
- **Decision**: Default to `True` when `ULTRAWORK` mode is detected (handled by orchestrator prompt), but expose as optional arg.

### 3. "Smart Context" Logic
- Use `mcp_bridge.tools.search_enhancements.smart_search` (if available) or standard `semantic_search`.
- Filter out low-relevance results (score threshold).

## Success Criteria
- Agent receives prompt WITH code context.
- Agent successfully answers "what does X do?" WITHOUT calling `grep` or `read_file` first.
- Reduced token count for simple queries.