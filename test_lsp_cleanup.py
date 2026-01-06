#!/usr/bin/env python3
"""
Test LSP Manager PID tracking and cleanup.

This script:
1. Starts a Python LSP server
2. Verifies PID is captured
3. Shuts down the server
4. Verifies process is terminated
"""

import asyncio
import os
import signal
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_bridge.tools.lsp.manager import get_lsp_manager


async def test_pid_tracking():
    """Test that PIDs are captured and processes are properly terminated."""
    print("=" * 60)
    print("Testing LSP Manager PID Tracking and Cleanup")
    print("=" * 60)

    manager = get_lsp_manager()

    # Start Python LSP server
    print("\n1. Starting Python LSP server...")
    client = await manager.get_server("python")

    if not client:
        print("❌ Failed to start LSP server")
        return False

    # Check if PID was captured
    server = manager._servers["python"]
    print(f"   Server initialized: {server.initialized}")
    print(f"   Server PID: {server.pid}")

    if not server.pid:
        print("❌ PID was not captured!")
        return False

    # Verify process is running
    captured_pid = server.pid  # Capture before shutdown resets it
    try:
        os.kill(captured_pid, 0)
        print(f"✅ Process {captured_pid} is running")
    except ProcessLookupError:
        print(f"❌ Process {captured_pid} not found!")
        return False

    # Shutdown the manager
    print("\n2. Shutting down LSP manager...")
    await manager.shutdown()

    # Wait a moment for cleanup
    await asyncio.sleep(1.0)

    # Verify process is terminated
    print("\n3. Verifying process cleanup...")
    try:
        os.kill(captured_pid, 0)
        print(f"❌ Process {captured_pid} still running!")

        # List all jedi-language-server processes
        import subprocess
        result = subprocess.run(
            ["pgrep", "-fl", "jedi-language-server"],
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(f"   Orphaned processes:\n{result.stdout}")
        return False
    except ProcessLookupError:
        print(f"✅ Process {captured_pid} successfully terminated")
        return True


async def main():
    """Run the test."""
    success = await test_pid_tracking()

    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("❌ TEST FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
