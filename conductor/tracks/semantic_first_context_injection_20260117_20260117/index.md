# Semantic First Context Injection

## Status: Completed

## Implementation
- Added `semantic_first` parameter to `AgentManager.spawn_async`.
- Updated `agent_spawn` tool to support `semantic_first`.
- Auto-injects top 5 semantic search results into the agent's prompt.
- Handled async threading to avoid blocking the event loop.

## Tests
- Added `test_spawn_with_semantic_first` to `tests/test_agent_manager.py`.
- Verified passing.

## Deployment
- Code changes merged to `main`.
- Requires release `v0.4.65` (or next).