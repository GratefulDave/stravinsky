#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""
Project-local Stop Hook - Executes metrics collection.
Can be called directly or via the global shim.
"""

import os
import sys
import subprocess
from pathlib import Path

def send_stravinsky_metrics(session_id: str, hooks_dir: Path) -> bool:
    """Call stravinsky_metrics.py to query and send metrics to dashboard."""
    script_path = hooks_dir / "stravinsky_metrics.py"

    if not script_path.exists():
        print(f"Error: stravinsky_metrics.py not found at {script_path}", file=sys.stderr)
        return False

    try:
        # Build command
        # We use uv run python to ensure the environment is correctly set up
        cmd = [
            "uv",
            "run",
            "python",
            str(script_path),
            "--session-id",
            session_id,
        ]

        # Inject project root into PYTHONPATH for mcp_bridge resolution
        project_root = hooks_dir.parent.parent
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")

        # Run command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False, env=env)

        if result.returncode != 0:
            print(
                f"Error: stravinsky_metrics.py failed with exit code {result.returncode}",
                file=sys.stderr,
            )
            print(f"stderr: {result.stderr}", file=sys.stderr)
            return False

        return True

    except subprocess.TimeoutExpired:
        print(f"Error: stravinsky_metrics.py timed out after 15 seconds", file=sys.stderr)
        return False

    except Exception as e:
        print(f"Error: stravinsky_metrics.py execution failed: {e}", file=sys.stderr)
        return False


def main():
    # Detect if we are being called via the shim
    is_delegated = os.environ.get("STRAVINSKY_HOOK_DELEGATED") == "1"
    
    # Get session_id from environment or use default
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")

    hooks_dir = Path(__file__).parent.absolute()
    
    # Send metrics to dashboard
    success = send_stravinsky_metrics(session_id, hooks_dir)

    if not success:
        sys.exit(1)

    if is_delegated:
        print(
            f"✓ (Delegated) Successfully sent Stravinsky metrics for session {session_id} to dashboard",
            file=sys.stderr,
        )
    else:
        print(
            f"✓ Successfully sent Stravinsky metrics for session {session_id} to dashboard",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
