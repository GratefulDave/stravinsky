"""
Persistent LSP Server Manager

Manages persistent Language Server Protocol (LSP) servers for improved performance.
Implements lazy initialization, JSON-RPC communication, and graceful shutdown.

Architecture:
- Servers start on first use (lazy initialization)
- JSON-RPC over stdio using pygls BaseLanguageClient
- Supports Python (jedi-language-server) and TypeScript (typescript-language-server)
- Graceful shutdown on MCP server exit
"""

import asyncio
import json
import logging
import os
import shlex
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from pygls.client import JsonRPCClient
from lsprotocol.types import (
    InitializeParams,
    InitializedParams,
    ClientCapabilities,
    WorkspaceFolder,
)

logger = logging.getLogger(__name__)


@dataclass
class LSPServer:
    """Metadata for a persistent LSP server."""

    name: str
    command: list[str]
    client: Optional[JsonRPCClient] = None
    initialized: bool = False
    pid: Optional[int] = None  # Track subprocess PID for explicit cleanup


class LSPManager:
    """
    Singleton manager for persistent LSP servers.

    Implements:
    - Lazy server initialization (start on first use)
    - Process lifecycle management with GC protection
    - Exponential backoff for crash recovery
    - Graceful shutdown with signal handling
    """

    _instance: Optional["LSPManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._servers: dict[str, LSPServer] = {}
        self._lock = asyncio.Lock()
        self._restart_attempts: dict[str, int] = {}

        # Register available LSP servers
        self._register_servers()

    def _register_servers(self):
        """Register available LSP server configurations."""
        self._servers["python"] = LSPServer(name="python", command=["jedi-language-server"])
        self._servers["typescript"] = LSPServer(
            name="typescript", command=["typescript-language-server", "--stdio"]
        )

    async def get_server(self, language: str) -> Optional[JsonRPCClient]:
        """
        Get or start a persistent LSP server for the given language.

        Args:
            language: Language identifier (e.g., "python", "typescript")

        Returns:
            JsonRPCClient instance or None if server unavailable
        """
        if language not in self._servers:
            logger.warning(f"No LSP server configured for language: {language}")
            return None

        server = self._servers[language]

        # Return existing initialized server
        if server.initialized and server.client:
            return server.client

        # Start server with lock to prevent race conditions
        async with self._lock:
            # Double-check after acquiring lock
            if server.initialized and server.client:
                return server.client

            try:
                await self._start_server(server)
                return server.client
            except Exception as e:
                logger.error(f"Failed to start {language} LSP server: {e}")
                return None

    async def _start_server(self, server: LSPServer):
        """
        Start a persistent LSP server process.

        Implements:
        - Process health validation after start
        - LSP initialization handshake
        - GC protection via persistent reference

        Args:
            server: LSPServer metadata object
        """
        try:
            # Create pygls client
            client = JsonRPCClient()

            logger.info(f"Starting {server.name} LSP server: {' '.join(server.command)}")

            # Start server process (start_io expects cmd as first arg, then *args)
            await client.start_io(server.command[0], *server.command[1:])

            # Brief delay for process startup
            await asyncio.sleep(0.2)

            # Capture PID for explicit cleanup
            server_proc = getattr(client, "_server", None)
            if server_proc and hasattr(server_proc, "pid"):
                server.pid = server_proc.pid
                logger.debug(f"{server.name} LSP server PID: {server.pid}")
            else:
                logger.warning(f"{server.name} LSP server PID not accessible")

            # Validate process is running
            if server_proc and getattr(server_proc, "returncode", None) is not None:
                raise ConnectionError(
                    f"{server.name} LSP server exited immediately (code {server_proc.returncode})"
                )

            # Perform LSP initialization handshake
            init_params = InitializeParams(
                process_id=None, root_uri=None, capabilities=ClientCapabilities()
            )

            try:
                # Send initialize request via protocol
                response = await asyncio.wait_for(
                    client.protocol.send_request_async("initialize", init_params), timeout=10.0
                )

                # Send initialized notification
                client.protocol.notify("initialized", InitializedParams())

                logger.info(f"{server.name} LSP server initialized: {response}")

            except asyncio.TimeoutError:
                raise ConnectionError(f"{server.name} LSP server initialization timed out")

            # Store client reference (GC protection)
            server.client = client
            server.initialized = True

            # Reset restart attempts on successful start
            self._restart_attempts[server.name] = 0

            logger.info(f"{server.name} LSP server started successfully")

        except Exception as e:
            logger.error(f"Failed to start {server.name} LSP server: {e}", exc_info=True)
            # Cleanup on failure
            if server.client:
                try:
                    await server.client.stop()
                except:
                    pass
            server.client = None
            server.initialized = False
            server.pid = None
            raise

    async def _restart_with_backoff(self, server: LSPServer):
        """
        Restart a crashed LSP server with exponential backoff.

        Strategy: delay = 2^attempt + jitter (max 60s)

        Args:
            server: LSPServer to restart
        """
        import random

        attempt = self._restart_attempts.get(server.name, 0)
        self._restart_attempts[server.name] = attempt + 1

        # Exponential backoff with jitter (max 60s)
        delay = min(60, (2**attempt) + random.uniform(0, 1))

        logger.warning(
            f"{server.name} LSP server crashed. Restarting in {delay:.2f}s (attempt {attempt + 1})"
        )
        await asyncio.sleep(delay)

        # Reset state before restart
        server.initialized = False
        server.client = None
        server.pid = None

        try:
            await self._start_server(server)
        except Exception as e:
            logger.error(f"Restart failed for {server.name}: {e}")

    def get_status(self) -> dict:
        """Get status of managed servers."""
        status = {}
        for name, server in self._servers.items():
            status[name] = {
                "running": server.initialized and server.client is not None,
                "pid": server.pid,
                "command": " ".join(server.command),
                "restarts": self._restart_attempts.get(name, 0),
            }
        return status

    async def shutdown(self):
        """
        Gracefully shutdown all LSP servers.

        Implements:
        - LSP protocol shutdown (shutdown request + exit notification)
        - Pending task cancellation
        - Process cleanup with timeout
        """
        logger.info("Shutting down LSP manager...")

        async with self._lock:
            for name, server in self._servers.items():
                if not server.initialized or not server.client:
                    continue

                try:
                    logger.info(f"Shutting down {name} LSP server")

                    # LSP protocol shutdown request
                    try:
                        await asyncio.wait_for(
                            server.client.protocol.send_request_async("shutdown", None), timeout=5.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"{name} LSP server shutdown request timed out")

                    # Send exit notification
                    server.client.protocol.notify("exit", None)

                    # Stop the client
                    await server.client.stop()

                    # Explicitly terminate subprocess using tracked PID
                    if server.pid:
                        try:
                            # Check if process still exists
                            os.kill(server.pid, 0)  # Signal 0 just checks existence
                            logger.debug(
                                f"{name} LSP server (PID {server.pid}) still running, terminating"
                            )

                            # Send SIGTERM first
                            os.kill(server.pid, signal.SIGTERM)

                            # Wait for graceful termination
                            await asyncio.sleep(2.0)

                            # Check if still alive
                            try:
                                os.kill(server.pid, 0)
                                # Still alive, force kill
                                logger.warning(
                                    f"{name} LSP server (PID {server.pid}) didn't terminate, force killing"
                                )
                                os.kill(server.pid, signal.SIGKILL)
                                await asyncio.sleep(0.5)
                            except ProcessLookupError:
                                # Process terminated successfully
                                logger.debug(
                                    f"{name} LSP server (PID {server.pid}) terminated gracefully"
                                )

                        except ProcessLookupError:
                            # Process already dead
                            logger.debug(f"{name} LSP server (PID {server.pid}) already terminated")
                        except Exception as e:
                            logger.warning(
                                f"Error killing {name} LSP server (PID {server.pid}): {e}"
                            )

                    # Fallback: also try client._server if PID tracking failed
                    elif hasattr(server.client, "_server") and server.client._server:
                        proc = server.client._server
                        if proc.returncode is None:
                            try:
                                proc.terminate()
                                await asyncio.wait_for(proc.wait(), timeout=2.0)
                            except asyncio.TimeoutError:
                                logger.warning(
                                    f"{name} LSP server process didn't terminate, force killing"
                                )
                                proc.kill()
                                await proc.wait()

                    # Mark as uninitialized
                    server.initialized = False
                    server.client = None
                    server.pid = None

                except Exception as e:
                    logger.error(f"Error shutting down {name} LSP server: {e}")

        logger.info("LSP manager shutdown complete")


# Singleton accessor
_manager_instance: Optional[LSPManager] = None


def get_lsp_manager() -> LSPManager:
    """Get the global LSP manager singleton."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = LSPManager()
    return _manager_instance
