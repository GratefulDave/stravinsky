# Track Specification: Refactor MCP Tools and Documentation for Bridge Alignment

## Overview
This track addresses critical architectural improvements for Stravinsky v0.4.56+, focusing on unifying hook systems, enabling true parallelism via a model proxy, and standardizing the Native Subagent Pattern. The goal is to eliminate configuration conflicts, enforce parallel delegation, and remove performance bottlenecks caused by head-of-line blocking.

## Objectives
1.  **Configuration Alignment**: Eliminate conflicts between slash commands, native subagents, and hooks regarding delegation patterns (Task tool vs. agent_spawn).
2.  **Hook Unification**: Implement a shared event model (`ToolCallEvent`, `HookPolicy`) to reduce duplication between native and MCP hooks.
3.  **Parallelism Optimization**: Implement a local FastAPI Model Proxy to handle model invocations, eliminating MCP stdio blocking.
4.  **Soft Enforcement**: Implement session state tracking and messaging to encourage parallel delegation.
5.  **Documentation Standardization**: Update all documentation to reflect the Native Subagent Pattern as the primary architecture.

## Scope
-   **In Scope:**
    -   Updates to `.claude/commands/`, `.claude/agents/`, and `mcp_bridge/hooks/`.
    -   Creation of `mcp_bridge/hooks/events.py` and `mcp_bridge/proxy/model_server.py`.
    -   Implementation of `HookPolicy` adapters.
    -   Updates to `README.md`, `WARP.md`, and `docs/`.
-   **Out of Scope:**
    -   Hard enforcement of parallel delegation (Phase 5 in roadmap).
    -   Visual tool output enhancements.
    -   Agent cost dashboard.

## Technical Requirements
-   **Hook Unification:**
    -   `ToolCallEvent` dataclass to normalize native/MCP events.
    -   `HookPolicy` abstract base class with `should_block` and `transform_result` methods.
    -   Adapters for `from_native_hook()` and `from_mcp_hook()`.
-   **Model Proxy:**
    -   FastAPI server running on `localhost:8765`.
    -   Endpoints: `/v1/gemini/generate`, `/v1/openai/chat`.
    -   Direct API calls using existing OAuth tokens.
    -   Observability: Trace IDs, circuit breakers.
-   **Documentation:**
    -   Deprecation warnings for legacy slash commands.
    -   Clear "Task vs. agent_spawn" guidelines.

## Success Criteria
-   Zero configuration conflicts regarding delegation instructions.
-   3+ policies migrated to the unified `HookPolicy` interface.
-   Model Proxy handles 20+ concurrent requests with <100ms overhead.
-   Documentation accurately reflects the Native Subagent Pattern.
