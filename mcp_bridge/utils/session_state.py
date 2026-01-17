import json
import os
import time
from pathlib import Path
from typing import Any, Optional

STATE_DIR = Path.home() / ".stravinsky" / "state"


def ensure_state_dir():
    """Ensure the state directory exists."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_session_state_path(session_id: str) -> Path:
    """Get the path to the state file for a given session."""
    ensure_state_dir()
    # Sanitize session_id to avoid path traversal
    safe_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
    return STATE_DIR / f"session_{safe_id}.json"


def get_session_state(session_id: Optional[str] = None) -> dict[str, Any]:
    """Get the state for a session."""
    if session_id is None:
        session_id = get_current_session_id()

    path = get_session_state_path(session_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def update_session_state(updates: dict[str, Any], session_id: Optional[str] = None):
    """Update the state for a session."""
    if session_id is None:
        session_id = get_current_session_id()

    state = get_session_state(session_id)
    state.update(updates)
    state["updated_at"] = time.time()
    path = get_session_state_path(session_id)
    path.write_text(json.dumps(state, indent=2))


def get_current_session_id() -> str:
    """Get the current session ID from environment or default."""
    return os.environ.get("CLAUDE_SESSION_ID", "default")
