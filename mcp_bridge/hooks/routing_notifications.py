#!/usr/bin/env python3
"""
PostToolUse hook for routing fallback notifications.

Monitors provider state changes and notifies users when routing decisions
are made due to rate limits or provider unavailability.
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from routing import get_provider_tracker
except ImportError:
    get_provider_tracker = None  # type: ignore


logger = logging.getLogger(__name__)


def format_cooldown_time(seconds: float) -> str:
    """Format cooldown duration for user display."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds / 60)
    remaining_seconds = int(seconds % 60)
    if remaining_seconds == 0:
        return f"{minutes}m"
    return f"{minutes}m {remaining_seconds}s"


def check_and_notify_routing_state() -> None:
    """Check current routing state and notify if providers are unavailable."""
    if not get_provider_tracker or not callable(get_provider_tracker):
        return

    tracker = get_provider_tracker()
    if not tracker:
        return

    status = tracker.get_status()

    unavailable_providers = []
    for provider_name, provider_status in status.items():
        if not provider_status["available"] and provider_status["cooldown_remaining"]:
            cooldown_str = format_cooldown_time(provider_status["cooldown_remaining"])
            unavailable_providers.append((provider_name, cooldown_str))

    if unavailable_providers:
        print("\n📊 Provider Status:", file=sys.stderr)
        for provider, cooldown in unavailable_providers:
            print(f"  ⏳ {provider.title()}: Cooldown ({cooldown} remaining)", file=sys.stderr)


def main() -> None:
    """Process PostToolUse hook event."""
    try:
        hook_input = json.loads(sys.stdin.read())

        tool_name = hook_input.get("tool_name", "")

        if "invoke" in tool_name.lower() or "agent_spawn" in tool_name.lower():
            check_and_notify_routing_state()

        sys.exit(0)

    except Exception as e:
        logger.error(f"[RoutingNotifications] Error: {e}", exc_info=True)
        sys.exit(0)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    main()
