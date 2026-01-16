# Track Specification: Implement Hard Enforcement and Advanced Capabilities

## Overview
This track focuses on the long-term strategic goals for Stravinsky, moving from advisory patterns to strict enforcement of architectural standards (Hard Parallel Enforcement) and introducing advanced capabilities that enhance reasoning, isolation, search, and observability.

## Objectives
1.  **Strict Orchestration**: Implement opt-in hard enforcement for parallel delegation to ensure the orchestrator always leverages multi-model capabilities.
2.  **Advanced Reasoning**: Integrate extended thinking budgets for supported models.
3.  **Enhanced Reliability**: Finalize agent session isolation to prevent state leakage.
4.  **Intelligent Search**: Implement advanced semantic search strategies (Hybrid, Multi-query, Decomposed).
5.  **Observability**: Create visual tool outputs and a cost tracking dashboard.

## Scope
-   **In Scope:**
    -   `post_tool/parallel_validation.py` and `pre_tool/agent_spawn_validator.py`.
    -   Extended thinking configuration in agent YAMLs.
    -   Semantic search tool enhancements (`hybrid_search`, etc.).
    -   Cost tracking and visualization logic.
-   **Out of Scope:**
    -   Changes to the core MCP protocol.
    -   Non-Python client library support.

## Technical Requirements
-   **Hard Enforcement:**
    -   State tracking for `TodoWrite`.
    -   Validation hook that blocks subsequent non-delegation tools if multiple tasks are pending.
    -   `STRAVINSKY_ALLOW_SEQUENTIAL` escape hatch.
-   **Advanced Search:**
    -   Integration of BM25 with ChromaDB for hybrid results.
    -   LLM-based query expansion for multi-query search.
-   **Cost Tracking:**
    -   Hook-based token collection per agent/session.
    -   Rich-based terminal dashboard or FastAPI web view.

## Success Criteria
-   Parallel delegation rate >80% when hard enforcement is enabled.
-   Advanced search tools are fully documented and verified.
-   Agent sessions are verifiably isolated in E2E tests.
-   Real-time cost tracking is functional.
