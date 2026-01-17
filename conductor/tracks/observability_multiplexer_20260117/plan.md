# Implementation Plan - Observability Multiplexer

## Phase 1: Inception
- [x] Task: Initialize track structure.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Inception' (Protocol in workflow.md)

## Phase 2: The Go Sidecar
- [x] Task: Initialize Go module in `go_sidecar/`.
- [x] Task: Implement `mux/main.go`:
    -   Listen on Unix Socket (`/tmp/stravinsky.sock`).
    -   Parse incoming JSON messages (Agent ID, Stream Type, Content).
    -   Broadcast to WebSocket clients (`ws://localhost:42000`).
- [x] Task: Implement simple "heartbeat" to ensure sidecar dies if parent dies.
- [x] Task: Conductor - User Manual Verification 'Phase 2: The Go Sidecar' (Protocol in workflow.md)

## Phase 3: Python Integration
- [x] Task: Create `mcp_bridge/tools/mux_client.py`:
    -   Async client that connects to the Unix socket.
    -   Functions to push `stdout`, `stderr`, and `lifecycle_events`.
- [x] Task: Modify `agent_manager.py`:
    -   Start `stravinsky-mux` on initialization.
    -   Redirect agent `subprocess` output to `mux_client`.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Python Integration' (Protocol in workflow.md)