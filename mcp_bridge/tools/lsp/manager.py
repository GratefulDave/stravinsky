"""
Persistent LSP Server Manager

Manages persistent Language Server Protocol (LSP) servers for improved performance.
Implements lazy initialization, JSON-RPC communication, and graceful shutdown.

Architecture:
- Servers start on first use (lazy initialization)
- JSON-RPC over stdio using pygls BaseLanguageClient
- Supports Python (jedi-language-server) and TypeScript (typescript-language-server)
- Graceful shutdown on MCP server exit
- Health checks and idle timeout management
"""

import asyncio
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from lsprotocol.types import (
    ClientCapabilities,
    InitializedParams,
    InitializeParams,
)
from pygls.client import JsonRPCClient

logger = logging.getLogger(__name__)

# Configuration for LSP server lifecycle management
LSP_CONFIG = {
    "idle_timeout": 1800,  # 30 minutes
    "health_check_interval": 300,  # 5 minutes
    "health_check_timeout": 5.0,
}


@dataclass
class LSPServer:
    """Metadata for a persistent LSP server."""

    name: str
    command: list[str]
    client: JsonRPCClient | None = None
    initialized: bool = False
    process: asyncio.subprocess.Process | None = None
    pid: int | None = None  # Track subprocess PID for explicit cleanup
    root_path: str | None = None  # Track root path server was started with
    last_used: float = field(default_factory=time.time)  # Timestamp of last usage
    created_at: float = field(default_factory=time.time)  # Timestamp of server creation


class LSPManager:
    """
    Singleton manager for persistent LSP servers.

    Implements:
    - Lazy server initialization (start on first use)
    - Process lifecycle management with GC protection
    - Exponential backoff for crash recovery
    - Graceful shutdown with signal handling
    - Health checks and idle server shutdown
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
        self._health_monitor_task: asyncio.Task | None = None

        # Register available LSP servers
        self._register_servers()

    def _register_servers(self):
        """Register available LSP server configurations."""
        # Allow overriding commands via environment variables
        python_cmd = os.environ.get("LSP_CMD_PYTHON", "jedi-language-server").split()
        ts_cmd = os.environ.get(
            "LSP_CMD_TYPESCRIPT", "typescript-language-server --stdio"
        ).split()

        self._servers["python"] = LSPServer(name="python", command=python_cmd)
        self._servers["typescript"] = LSPServer(name="typescript", command=ts_cmd)

    async def get_server(
        self, language: str, root_path: str | None = None
    ) -> JsonRPCClient | None:
        """
        Get or start a persistent LSP server for the given language.

        Args:
            language: Language identifier (e.g., "python", "typescript")
            root_path: Project root path (optional, but recommended)

        Returns:
            JsonRPCClient instance or None if server unavailable
        """
        if language not in self._servers:
            logger.warning(f"No LSP server configured for language: {language}")
            return None

        server = self._servers[language]

        # Check if we need to restart due to root path change
        # (Simple implementation: if root_path differs, restart)
        # In multi-root workspaces, this might be too aggressive, but safe for now.
        restart_needed = False
        if root_path and server.root_path and root_path != server.root_path:
            logger.info(
                f"Restarting {language} LSP server: root path changed ({server.root_path} -> {root_path})"
            )
            restart_needed = True

        if restart_needed:
            async with self._lock:
                await self._shutdown_single_server(language, server)

        # Return existing initialized server
        if server.initialized and server.client:
            # Update last_used timestamp
            server.last_used = time.time()
            # Start health monitor on first use
            if self._health_monitor_task is None or self._health_monitor_task.done():
                self._health_monitor_task = asyncio.create_task(self._background_health_monitor())
            return server.client

        # Start server with lock to prevent race conditions
        async with self._lock:
            # Double-check after acquiring lock
            if server.initialized and server.client:
                server.last_used = time.time()
                if self._health_monitor_task is None or self._health_monitor_task.done():
                    self._health_monitor_task = asyncio.create_task(self._background_health_monitor())
                return server.client

            try:
                await self._start_server(server, root_path)
                # Start health monitor on first server creation
                if self._health_monitor_task is None or self._health_monitor_task.done():
                    self._health_monitor_task = asyncio.create_task(self._background_health_monitor())
                return server.client
            except Exception as e:
                logger.error(f"Failed to start {language} LSP server: {e}")
                return None

    async def _start_server(self, server: LSPServer, root_path: str | None = None):
        """
        Start a persistent LSP server process.

        Implements:
        - Process health validation after start
        - LSP initialization handshake
        - GC protection via persistent reference
        - Timestamp tracking for idle detection

        Args:
            server: LSPServer metadata object
            root_path: Project root path
        """
        try:
            # Create pygls client
            client = JsonRPCClient()

            logger.info(f"Starting {server.name} LSP server: {' '.join(server.command)}")

            # Start server process (start_io expects cmd as first arg, then *args)
            # Use cwd=root_path if available to help server find config
            cwd = root_path if root_path and os.path.isdir(root_path) else None
            await client.start_io(server.command[0], *server.command[1:], cwd=cwd)

            # Brief delay for process startup
            await asyncio.sleep(0.2)

            # Capture subprocess from client
            if not hasattr(client, "_server") or client._server is None:
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

            # Perform LSP initialization handshake
            root_uri = f"file://{root_path}" if root_path else None
            init_params = InitializeParams(
                process_id=None, root_uri=root_uri, capabilities=ClientCapabilities()
            )

            try:
                # Send initialize request via protocol
                response = await asyncio.wait_for(
                    client.protocol.send_request_async("initialize", init_params), timeout=10.0
                )

                # Send initialized notification
                client.protocol.notify("initialized", InitializedParams())

                logger.info(f"{server.name} LSP server initialized: {response}")

            except TimeoutError:
                raise ConnectionError(f"{server.name} LSP server initialization timed out")

            # Store client reference (GC protection)
            server.client = client
            server.initialized = True
            server.root_path = root_path
            server.created_at = time.time()
            server.last_used = time.time()

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
            server.process = None
            server.pid = None
            server.root_path = None
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
        server.process = None
        server.pid = None

        try:
            await self._start_server(server)
        except Exception as e:
            logger.error(f"Restart failed for {server.name}: {e}")

    async def _health_check_server(self, server: LSPServer) -> bool:
        """
        Perform health check on an LSP server.

        Args:
            server: LSPServer to check

        Returns:
            True if server is healthy, False otherwise
        """
        if not server.initialized or not server.client:
            return False

        try:
            # Simple health check: send initialize request
            # Most servers respond to repeated initialize calls
            init_params = InitializeParams(
                process_id=None, root_uri=None, capabilities=ClientCapabilities()
            )
            response = await asyncio.wait_for(
                server.client.protocol.send_request_async("initialize", init_params),
                timeout=LSP_CONFIG["health_check_timeout"],
            )
            logger.debug(f"{server.name} LSP server health check passed")
            return True
        except TimeoutError:
            logger.warning(f"{server.name} LSP server health check timed out")
            return False
        except Exception as e:
            logger.warning(f"{server.name} LSP server health check failed: {e}")
            return False

    async def _shutdown_single_server(self, name: str, server: LSPServer):
        """
        Gracefully shutdown a single LSP server.

        Args:
            name: Server name (key)
            server: LSPServer instance
        """
        if not server.initialized or not server.client:
            return

        try:
            logger.info(f"Shutting down {name} LSP server")

            # LSP protocol shutdown request
            try:
                await asyncio.wait_for(
                    server.client.protocol.send_request_async("shutdown", None), timeout=5.0
                )
            except TimeoutError:
                logger.warning(f"{name} LSP server shutdown request timed out")

            # Send exit notification
            server.client.protocol.notify("exit", None)

            # Stop the client
            await server.client.stop()

            # Terminate subprocess using stored process reference
            if server.process is not None:
                try:
                    if server.process.returncode is not None:
                        logger.debug(f"{name} already exited (code {server.process.returncode})")
                    else:
                        server.process.terminate()
                        try:
                            await asyncio.wait_for(server.process.wait(), timeout=2.0)
                        except TimeoutError:
                            server.process.kill()
                            await asyncio.wait_for(server.process.wait(), timeout=1.0)
                except Exception as e:
                    logger.warning(f"Error terminating {name}: {e}")

            # Mark as uninitialized
            server.initialized = False
            server.client = None
            server.process = None
            server.pid = None

        except Exception as e:
            logger.error(f"Error shutting down {name} LSP server: {e}")

    async def _background_health_monitor(self):
        """
        Background task for health checking and idle server shutdown.

        Runs periodically to:
        - Check health of running servers
        - Shutdown idle servers
        - Restart crashed servers
        """
        logger.info("LSP health monitor task started")
        try:
            while True:
                await asyncio.sleep(LSP_CONFIG["health_check_interval"])

                current_time = time.time()
                idle_threshold = current_time - LSP_CONFIG["idle_timeout"]

                async with self._lock:
                    for name, server in self._servers.items():
                        if not server.initialized or not server.client:
                            continue

                        # Check if server is idle
                        if server.last_used < idle_threshold:
                            logger.info(
                                f"{name} LSP server idle for {(current_time - server.last_used) / 60:.1f} minutes, shutting down"
                            )
                            await self._shutdown_single_server(name, server)
                            continue

                        # Health check for active servers
                        is_healthy = await self._health_check_server(server)
                        if not is_healthy:
                            logger.warning(f"{name} LSP server health check failed, restarting")
                            await self._shutdown_single_server(name, server)
                            try:
                                await self._start_server(server)
                            except Exception as e:
                                logger.error(f"Failed to restart {name} LSP server: {e}")

        except asyncio.CancelledError:
            logger.info("LSP health monitor task cancelled")
            raise
        except Exception as e:
            logger.error(f"LSP health monitor task error: {e}", exc_info=True)

    def get_status(self) -> dict:
        """Get status of managed servers including idle information."""
        current_time = time.time()
        status = {}
        for name, server in self._servers.items():
            idle_seconds = current_time - server.last_used
            uptime_seconds = current_time - server.created_at if server.created_at else 0
            status[name] = {
                "running": server.initialized and server.client is not None,
                "pid": server.pid,
                "command": " ".join(server.command),
                "restarts": self._restart_attempts.get(name, 0),
                "idle_seconds": idle_seconds,
                "idle_minutes": idle_seconds / 60.0,
                "uptime_seconds": uptime_seconds,
            }
        return status

    async def shutdown(self):
        """
        Gracefully shutdown all LSP servers.

        Implements:
        - Health monitor cancellation
        - LSP protocol shutdown (shutdown request + exit notification)
        - Pending task cancellation
        - Process cleanup with timeout
        """
        logger.info("Shutting down LSP manager...")

        # Cancel health monitor task
        if self._health_monitor_task and not self._health_monitor_task.done():
            logger.info("Cancelling health monitor task")
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            for name, server in self._servers.items():
                await self._shutdown_single_server(name, server)

        logger.info("LSP manager shutdown complete")


# Singleton accessor
_manager_instance: LSPManager | None = None
_manager_lock = threading.Lock()


def get_lsp_manager() -> LSPManager:
    """Get the global LSP manager singleton."""
    global _manager_instance
    if _manager_instance is None:
        with _manager_lock:
            # Double-check pattern to avoid race condition
            if _manager_instance is None:
                _manager_instance = LSPManager()
    return _manager_instance
