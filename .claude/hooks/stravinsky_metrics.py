#!/usr/bin/env python3
"""
Stravinsky Metrics Hook Script

Queries Stravinsky's internal metrics and sends them to the observability dashboard.
This hook is triggered on Stop/SubagentStop events.

Usage:
    stravinsky_metrics.py --session-id <session_id>

Environment Variables:
    CLAUDE_SESSION_ID: Fallback session ID if --session-id not provided

Output:
    Sends StravinskyMetrics event to dashboard via send_event.py

Metrics Collected:
    - Total session cost (USD)
    - Total tokens used
    - Per-agent cost and token breakdown
    - Per-model cost and token breakdown (TODO)
    - Agent count (active/total) (TODO)

Error Handling:
    Returns non-zero exit code on error to prevent blocking Claude Code operations.
"""

import sys
import os
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def load_usage_data(session_id: str) -> Dict[str, Any]:
    """
    Load usage data from Stravinsky's metrics storage.

    TODO: Replace this with actual integration using CostTracker.get_session_summary()
    Currently reads directly from ~/.stravinsky/usage.jsonl as a placeholder.

    Args:
        session_id: Claude Code session ID

    Returns:
        Dictionary with metrics data
    """
    usage_file = Path.home() / ".stravinsky" / "usage.jsonl"

    if not usage_file.exists():
        return {"total_cost": 0.0, "total_tokens": 0, "by_agent": {}, "by_model": {}}

    total_cost = 0.0
    total_tokens = 0
    by_agent = {}
    by_model = {}

    try:
        with open(usage_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)

                    if record.get("session_id") != session_id:
                        continue

                    cost = record.get("cost", 0.0)
                    tokens = record.get("input_tokens", 0) + record.get("output_tokens", 0)
                    agent_type = record.get("agent_type", "unknown")
                    model = record.get("model", "unknown")

                    total_cost += cost
                    total_tokens += tokens

                    if agent_type not in by_agent:
                        by_agent[agent_type] = {"cost": 0.0, "tokens": 0}
                    by_agent[agent_type]["cost"] += cost
                    by_agent[agent_type]["tokens"] += tokens

                    if model not in by_model:
                        by_model[model] = {"cost": 0.0, "tokens": 0}
                    by_model[model]["cost"] += cost
                    by_model[model]["tokens"] += tokens

                except json.JSONDecodeError:
                    continue

    except Exception as e:
        print(f"Error reading usage file: {e}", file=sys.stderr)
        return None

    return {
        "total_cost": round(total_cost, 6),
        "total_tokens": total_tokens,
        "by_agent": by_agent,
        "by_model": by_model,
    }


def send_metrics_event(session_id: str, metrics: Dict[str, Any]) -> bool:
    """
    Send metrics event to observability dashboard via send_event.py.

    Args:
        session_id: Claude Code session ID
        metrics: Metrics data dictionary

    Returns:
        True if successful, False otherwise
    """
    hook_dir = Path(__file__).parent
    send_event_script = hook_dir / "send_event.py"

    if not send_event_script.exists():
        print(f"Error: send_event.py not found at {send_event_script}", file=sys.stderr)
        return False

    event_data = {
        "session_id": session_id,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat(),
    }

    cmd = [
        "uv",
        "run",
        str(send_event_script),
        "--source-app",
        "stravinsky",
        "--event-type",
        "StravinskyMetrics",
        "--summarize",
    ]

    try:
        result = subprocess.run(
            cmd, input=json.dumps(event_data), capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            print(f"Error from send_event.py: {result.stderr}", file=sys.stderr)
            return False

        return True

    except subprocess.TimeoutExpired:
        print("Error: send_event.py timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error running send_event.py: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Query Stravinsky metrics and send to dashboard")
    parser.add_argument(
        "--session-id", help="Claude Code session ID (falls back to CLAUDE_SESSION_ID env var)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print metrics without sending to dashboard (for testing)",
    )

    args = parser.parse_args()

    session_id = args.session_id or os.environ.get("CLAUDE_SESSION_ID", "default")

    if not session_id or session_id == "default":
        print("Warning: No session ID provided, using 'default'", file=sys.stderr)

    metrics = load_usage_data(session_id)

    if metrics is None:
        print("Error: Failed to load metrics", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(json.dumps(metrics, indent=2))
        sys.exit(0)

    print(f"Stravinsky Metrics for session {session_id}:", file=sys.stderr)
    print(f"  Total Cost: ${metrics['total_cost']:.6f}", file=sys.stderr)
    print(f"  Total Tokens: {metrics['total_tokens']:,}", file=sys.stderr)
    print(f"  Agents: {len(metrics['by_agent'])}", file=sys.stderr)

    success = send_metrics_event(session_id, metrics)

    if success:
        print("Metrics sent to dashboard successfully", file=sys.stderr)
        sys.exit(0)
    else:
        print("Failed to send metrics to dashboard", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
