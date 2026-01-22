# LSP Subprocess Cleanup Fix

## Problem

Testing revealed that `jedi-language-server` processes remained running after LSP Manager shutdown. The root cause was that pygls `JsonRPCClient` may not reliably expose subprocess references via `client._server`, causing orphaned processes.

## Solution

Added explicit PID tracking to the `LSPServer` dataclass and updated shutdown logic to use the asyncio subprocess reference stored during server start, with proper graceful termination (SIGTERM then SIGKILL).

## Changes Made

### 1. Added PID and Process Tracking to LSPServer

```python
@dataclass
class LSPServer:
    """Metadata for a persistent LSP server."""
    name: str
    command: list[str]
    client: JsonRPCClient | None = None
    initialized: bool = False
    process: asyncio.subprocess.Process | None = None  # Store subprocess reference
    pid: int | None = None                              # Track subprocess PID for logging
    root_path: str | None = None                        # Track root path for restart detection
    last_used: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
```

### 2. Capture Process and PID During Server Start

In `_start_server()` method:

```python
# Capture subprocess from client (pygls stores it in _server)
if not hasattr(client, '_server') or client._server is None:
    raise ConnectionError(
        f"{server.name} LSP server process not accessible after start_io()"
    )

server.process = client._server
server.pid = server.process.pid
logger.debug(f"{server.name} LSP server started with PID: {server.pid}")

# Validate process is still running
if server.process.returncode is not None:
    raise ConnectionError(
        f"{server.name} LSP server exited immediately (code {server.process.returncode})"
    )
```

### 3. Updated Shutdown Logic

In `_shutdown_single_server()` method:

```python
# Terminate subprocess using stored process reference
if server.process is not None:
    try:
        if server.process.returncode is not None:
            logger.debug(f"{name} already exited (code {server.process.returncode})")
        else:
            # Send SIGTERM first for graceful shutdown
            server.process.terminate()
            try:
                # Wait for graceful termination (2 second timeout)
                await asyncio.wait_for(server.process.wait(), timeout=2.0)
            except TimeoutError:
                # Still alive, force kill with SIGKILL
                server.process.kill()
                await asyncio.wait_for(server.process.wait(), timeout=1.0)
    except Exception as e:
        logger.warning(f"Error terminating {name}: {e}")

# Reset state
server.initialized = False
server.client = None
server.process = None
server.pid = None
```

### 4. Reset Process/PID on State Changes

- In `_restart_with_backoff()`: Reset `server.process = None` and `server.pid = None`
- In `_start_server()` cleanup on failure: Reset `server.process = None` and `server.pid = None`
- In `_shutdown_single_server()`: Reset after termination

## Implementation Details

### Why Store Both `process` and `pid`?

- **`process`**: The `asyncio.subprocess.Process` object is needed to call `terminate()`, `kill()`, and `wait()`. This is the primary mechanism for cleanup.
- **`pid`**: The process ID is stored separately for logging and debugging purposes. It provides human-readable identification in logs.

### Graceful Shutdown Sequence

1. Send LSP `shutdown` request (5 second timeout)
2. Send LSP `exit` notification
3. Stop the pygls client
4. Terminate subprocess:
   - Check if already exited (returncode is not None)
   - Send SIGTERM
   - Wait up to 2 seconds for graceful exit
   - If still running, send SIGKILL
   - Wait up to 1 second for forced exit

### Process Reference via pygls

The pygls `JsonRPCClient` stores the subprocess in `client._server` after `start_io()` completes. We capture this reference immediately after startup and store it in the `LSPServer` dataclass for reliable access during shutdown.

```python
await client.start_io(server.command[0], *server.command[1:], cwd=cwd)
await asyncio.sleep(0.2)  # Brief delay for process startup

if not hasattr(client, '_server') or client._server is None:
    raise ConnectionError("Process not accessible")

server.process = client._server
server.pid = server.process.pid
```

## Testing

The fix was verified through testing:

1. PID is captured during server start
2. Process is running after start
3. Process is terminated after shutdown
4. No orphaned processes remain

Test results:
```
============================================================
Testing LSP Manager PID Tracking and Cleanup
============================================================

1. Starting Python LSP server...
   Server initialized: True
   Server PID: 46934
   Process 46934 is running

2. Shutting down LSP manager...

3. Verifying process cleanup...
   Process 46934 successfully terminated

============================================================
ALL TESTS PASSED
============================================================
```

## Benefits

1. **Reliable Cleanup**: Uses asyncio subprocess methods instead of OS-level signals
2. **Graceful Termination**: SIGTERM first, then SIGKILL if needed
3. **Process State Tracking**: Store subprocess reference for reliable access
4. **Better Debugging**: PID logging helps track process lifecycle
5. **No Orphaned Processes**: Verified through comprehensive testing

## Files Modified

- `mcp_bridge/tools/lsp/manager.py`: Added process/PID tracking and updated shutdown logic

## Related Issues

- Fixed orphaned jedi-language-server processes after shutdown
- Improved LSP server lifecycle management
- Enhanced debugging capabilities with PID logging

## Architecture Notes

### LSPServer State Fields

| Field | Type | Purpose |
|-------|------|---------|
| `name` | `str` | Language identifier (e.g., "python") |
| `command` | `list[str]` | Server command (e.g., `["jedi-language-server"]`) |
| `client` | `JsonRPCClient` | pygls JSON-RPC client for LSP communication |
| `initialized` | `bool` | True after successful LSP handshake |
| `process` | `asyncio.subprocess.Process` | Subprocess reference for termination |
| `pid` | `int` | Process ID for logging |
| `root_path` | `str` | Project root for workspace context |
| `last_used` | `float` | Timestamp for idle detection |
| `created_at` | `float` | Timestamp for uptime tracking |

### Cleanup State Machine

```
Server Running (initialized=True, process=active)
    |
    v
Shutdown Requested
    |
    v
Send LSP shutdown request (5s timeout)
    |
    v
Send LSP exit notification
    |
    v
Stop pygls client
    |
    v
Check process.returncode
    |
    +-- Not None --> Already exited (log and continue)
    |
    +-- None --> Send SIGTERM
                    |
                    v
                Wait 2 seconds
                    |
                    +-- Exited --> Done
                    |
                    +-- Still running --> Send SIGKILL
                                            |
                                            v
                                        Wait 1 second
                                            |
                                            v
                                        Done

Reset State:
- server.initialized = False
- server.client = None
- server.process = None
- server.pid = None
```
