#!/usr/bin/env python3
"""
Test script for LSPManager persistent server implementation.

Tests:
1. LSPManager singleton initialization
2. Python LSP server startup (jedi-language-server)
3. Client initialization handshake
4. Basic LSP operation (textDocument/hover)
5. Graceful shutdown
6. Process cleanup verification
"""

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

# Add mcp_bridge to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_bridge.tools.lsp.manager import get_lsp_manager
from lsprotocol.types import (
    HoverParams,
    Position,
    TextDocumentIdentifier,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResult:
    """Track test results."""
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.details = None

    def success(self, details=None):
        self.passed = True
        self.details = details
        logger.info(f"✅ {self.name}: PASSED")
        if details:
            logger.info(f"   {details}")

    def failure(self, error):
        self.passed = False
        self.error = str(error)
        logger.error(f"❌ {self.name}: FAILED - {error}")


async def test_manager_singleton():
    """Test 1: Verify LSPManager singleton works correctly."""
    test = TestResult("LSPManager Singleton")
    try:
        manager1 = get_lsp_manager()
        manager2 = get_lsp_manager()

        if manager1 is not manager2:
            raise AssertionError("Multiple manager instances created")

        if not hasattr(manager1, '_servers'):
            raise AssertionError("Manager not properly initialized")

        test.success(f"Singleton verified, {len(manager1._servers)} servers registered")
    except Exception as e:
        test.failure(e)

    return test


async def test_server_startup():
    """Test 2: Verify Python LSP server starts successfully."""
    test = TestResult("Server Startup")
    try:
        manager = get_lsp_manager()

        # Check if jedi-language-server is installed
        try:
            result = subprocess.run(
                ["which", "jedi-language-server"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise EnvironmentError(
                    "jedi-language-server not found in PATH. "
                    "Install with: uv pip install jedi-language-server"
                )
        except subprocess.TimeoutExpired:
            raise EnvironmentError("Command 'which jedi-language-server' timed out")

        # Start server
        client = await manager.get_server("python")

        if client is None:
            raise AssertionError("get_server returned None")

        if not manager._servers["python"].initialized:
            raise AssertionError("Server not marked as initialized")

        # Verify process is running (check internal _server attribute)
        if hasattr(client, '_server'):
            if client._server.returncode is not None:
                raise AssertionError(f"Server process exited (returncode: {client._server.returncode})")
        else:
            raise AssertionError("Client has no _server attribute")

        test.success(f"Server started, process running")
    except Exception as e:
        test.failure(e)

    return test


async def test_lsp_hover():
    """Test 3: Test basic LSP operation (textDocument/hover)."""
    test = TestResult("LSP Hover Request")
    try:
        manager = get_lsp_manager()
        client = await manager.get_server("python")

        if client is None:
            raise AssertionError("Client not available")

        # Test with mcp_bridge/server.py as target
        test_file = Path(__file__).parent / "mcp_bridge" / "server.py"
        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found: {test_file}")

        # Read file to find a good test position (import statement)
        content = test_file.read_text()
        lines = content.split('\n')

        # Find a line with "import" to test hover
        test_line = None
        test_char = None
        for i, line in enumerate(lines):
            if "import" in line and not line.strip().startswith("#"):
                test_line = i
                test_char = line.index("import") + 3  # Middle of "import"
                break

        if test_line is None:
            raise AssertionError("Could not find suitable test position in file")

        # Prepare hover request
        params = HoverParams(
            text_document=TextDocumentIdentifier(uri=test_file.as_uri()),
            position=Position(line=test_line, character=test_char)
        )

        # Send hover request via protocol
        logger.info(f"Sending hover request for {test_file}:{test_line}:{test_char}")
        response = await asyncio.wait_for(
            client.protocol.send_request_async("textDocument/hover", params),
            timeout=10.0
        )

        # Validate response
        if response is None:
            logger.warning("Hover returned None (may be expected for some positions)")
            test.success(f"Hover request completed (no hover info at position)")
        else:
            hover_text = str(response.contents)[:100] if response.contents else "empty"
            test.success(f"Hover returned: {hover_text}...")

    except asyncio.TimeoutError:
        test.failure("Hover request timed out after 10s")
    except Exception as e:
        test.failure(e)

    return test


async def test_graceful_shutdown():
    """Test 4: Verify graceful shutdown completes without errors."""
    test = TestResult("Graceful Shutdown")
    try:
        manager = get_lsp_manager()

        # Ensure server is running
        server_meta = manager._servers.get("python")
        if not server_meta or not server_meta.initialized:
            raise AssertionError("Server not running before shutdown")

        # Perform shutdown
        await asyncio.wait_for(
            manager.shutdown(),
            timeout=10.0
        )

        # Verify server is marked as shut down
        if server_meta.initialized:
            raise AssertionError("Server still marked as initialized after shutdown")

        if server_meta.client is not None:
            raise AssertionError("Client reference not cleared after shutdown")

        test.success("Shutdown completed within 10s")
    except asyncio.TimeoutError:
        test.failure("Shutdown timed out after 10s")
    except Exception as e:
        test.failure(e)

    return test


async def test_process_cleanup():
    """Test 5: Verify no zombie processes remain."""
    test = TestResult("Process Cleanup")
    try:
        # Give processes time to fully shutdown
        await asyncio.sleep(1.0)

        # Check for jedi-language-server processes
        # We need to be careful not to match the pgrep command itself
        result = subprocess.run(
            ["pgrep", "-f", "jedi-language-server"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            pids = [p for p in result.stdout.strip().split('\n') if p]
            # Wait a bit more and retry
            await asyncio.sleep(2.0)
            result = subprocess.run(
                ["pgrep", "-f", "jedi-language-server"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                pids = [p for p in result.stdout.strip().split('\n') if p]
                logger.warning(f"Found lingering processes: {pids}")
                # Try to kill them
                for pid in pids:
                    try:
                        subprocess.run(["kill", "-9", pid], timeout=1)
                    except:
                        pass
                raise AssertionError(
                    f"Found {len(pids)} jedi-language-server process(es) still running after shutdown"
                )

        test.success("No zombie processes found")
    except Exception as e:
        test.failure(e)

    return test


async def main():
    """Run all tests and report results."""
    print("\n" + "="*60)
    print("LSPManager Test Suite")
    print("="*60 + "\n")

    tests = []

    # Run tests sequentially
    tests.append(await test_manager_singleton())
    tests.append(await test_server_startup())
    tests.append(await test_lsp_hover())
    tests.append(await test_graceful_shutdown())
    tests.append(await test_process_cleanup())

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    passed = sum(1 for t in tests if t.passed)
    failed = len(tests) - passed

    for test in tests:
        status = "✅ PASS" if test.passed else "❌ FAIL"
        print(f"{status}: {test.name}")
        if test.error:
            print(f"       Error: {test.error}")

    print(f"\nTotal: {passed}/{len(tests)} passed, {failed} failed")

    if failed > 0:
        print("\n❌ TEST SUITE FAILED")
        sys.exit(1)
    else:
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
