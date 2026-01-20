#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.8"
# dependencies = [
#     "anthropic",
#     "python-dotenv",
# ]

"""
Fix Stop Hook - Calls stravinsky_metrics.py on Stop events.

This hook is triggered by .claude/settings.json on Stop/SubagentStop.
It queries Stravinsky's cost tracker and sends a StravinskyMetrics event to the dashboard.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add hooks directory to path for script imports
hooks_dir = Path(__file__).parent
sys.path.insert(0, str(hooks_dir))


def send_stravinsky_metrics(session_id: str) -> bool:
    """Call stravinsky_metrics.py to query and send metrics to dashboard."""
    script_path = hooks_dir / "stravinsky_metrics.py"

    if not script_path.exists():
        print(f"Error: stravinsky_metrics.py not found at {script_path}", file=sys.stderr)
        return False

    try:
        # Build command
        cmd = [
            "uv",
            "run",
            "--script",
            str(script_path),
            "--session-id",
            session_id,
            "--summarize",  # Generate summary and send as event
        ]

        # Run command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)

        if result.returncode != 0:
            print(
                f"Error: stravinsky_metrics.py failed with exit code {result.returncode}",
                file=sys.stderr,
            )
            print(f"stderr: {result.stderr}", file=sys.stderr)
            return False

        return True

    except subprocess.TimeoutExpired:
        print(f"Error: stravinsky_metrics.py timed out after 10 seconds", file=sys.stderr)
        return False

    except Exception as e:
        print(f"Error: stravinsky_metrics.py execution failed: {e}", file=sys.stderr)
        return False


def main():
    # Get session_id from environment or use default
    session_id = os.environ.get("CLAUDE_SESSION_ID", "default")

    # Determine hook type
    hook_type = os.environ.get("CLAUDE_HOOK_EVENT_TYPE", "Stop")

    # Send metrics to dashboard
    success = send_stravinsky_metrics(session_id)

    if not success:
        sys.exit(1)

    print(
        f"✓ Successfully sent Stravinsky metrics for session {session_id} to dashboard",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
