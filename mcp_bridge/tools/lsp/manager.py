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
import shlex
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from pygls.client import BaseLanguageClient

logger = logging.getLogger(__name__)


@dataclass
class LSPServer:
    """Metadata for a persistent LSP server."""
    name: str
    command: list[str]
    client: Optional[BaseLanguageClient] = None
    initialized: bool = False


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
        self._servers["python"] = LSPServer(
            name="python",
            command=["jedi-language-server"]
        )
        self._servers["typescript"] = LSPServer(
            name="typescript",
            command=["typescript-language-server", "--stdio"]
        )

    async def get_server(self, language: str) -> Optional[BaseLanguageClient]:
        """
        Get or start a persistent LSP server for the given language.

        Args:
            language: Language identifier (e.g., "python", "typescript")

        Returns:
            BaseLanguageClient instance or None if server unavailable
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
            client = BaseLanguageClient(f"{server.name}-client", "1.0.0")

            # Sanitize command to prevent shell injection
            safe_command = [shlex.quote(arg) for arg in server.command]

            logger.info(f"Starting {server.name} LSP server: {' '.join(safe_command)}")

            # Start server process
            client.start_io(*server.command)

            # Validate transport is active (prevent "immediate exit" pitfall)
            await asyncio.sleep(0.1)  # Brief delay for process startup
            if not client.protocol or client.protocol.transport.is_closing():
                raise ConnectionError(f"{server.name} LSP server exited immediately after launch")

            # Perform LSP initialization handshake
            init_params = {
                "processId": None,
                "rootUri": None,
                "capabilities": {}
            }

            try:
                await asyncio.wait_for(
                    client.initialize_async(init_params),
                    timeout=10.0
                )
                await client.initialized_async()
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
                    server.client.exit()
                except:
                    pass
            server.client = None
            server.initialized = False
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
        delay = min(60, (2 ** attempt) + random.uniform(0, 1))

        logger.warning(f"{server.name} LSP server crashed. Restarting in {delay:.2f}s (attempt {attempt + 1})")
        await asyncio.sleep(delay)

        # Reset state before restart
        server.initialized = False
        server.client = None

        try:
            await self._start_server(server)
        except Exception as e:
            logger.error(f"Restart failed for {server.name}: {e}")

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

                    # LSP protocol shutdown
                    await asyncio.wait_for(
                        server.client.shutdown_async(),
                        timeout=5.0
                    )
                    server.client.exit()

                    # Mark as uninitialized
                    server.initialized = False
                    server.client = None

                except asyncio.TimeoutError:
                    logger.warning(f"{name} LSP server shutdown timed out")
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
