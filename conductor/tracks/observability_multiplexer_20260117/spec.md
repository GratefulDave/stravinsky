# Track Specification: Observability Multiplexer

## Overview
Implement a high-performance, concurrent **Log & Stream Multiplexer** in Go (`stravinsky-mux`). This sidecar process solves the "UI Freeze" problem by decoupling agent I/O from the main Python process. It acts as a central hub that captures `stdout/stderr` from all running agents and broadcasts them to a real-time dashboard.

## Objectives
1.  **Non-Blocking I/O:** Move heavy I/O handling (parsing JSON logs, streaming tokens) out of the main Python `asyncio` loop.
2.  **Real-Time Visibility:** Provide a WebSocket endpoint that a TUI or Web Dashboard can subscribe to for live agent status.
3.  **Simplicity:** Use Go's standard library (`net`, `net/http`) to keep the codebase small and maintenance-free.

## Scope
-   **In Scope:**
    -   `go_sidecar/` directory setup.
    -   `stravinsky-mux` binary implementation (Unix Domain Socket listener + WebSocket broadcaster).
    -   Python client (`mcp_bridge/tools/mux_client.py`) to pipe agent output to the mux.
    -   Integration with `agent_manager.py` to start the sidecar automatically.
-   **Out of Scope:**
    -   Complex log retention/database storage (logs are transient or file-based).
    -   Full-blown Web UI (this track builds the *backend* for the UI).