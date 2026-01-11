#!/usr/bin/env python3
"""
PreCompact hook: Context preservation before compaction.

Fires before Claude Code compacts conversation context to:
1. Preserve critical context patterns
2. Maintain stravinsky mode state
3. Warn about information loss
4. Save state for recovery

Cannot block compaction (exit 2 only shows error).
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


STRAVINSKY_MODE_FILE = Path.home() / ".stravinsky_mode"
STATE_DIR = Path.home() / ".claude" / "state"
COMPACTION_LOG = STATE_DIR / "compaction.jsonl"

# Patterns to preserve
PRESERVE_PATTERNS = [
    "ARCHITECTURE:",
    "DESIGN DECISION:",
    "CONSTRAINT:",
    "REQUIREMENT:",
    "MUST NOT:",
    "NEVER:",
    "CRITICAL ERROR:",
    "CURRENT TASK:",
    "BLOCKED BY:",
    "[STRAVINSKY MODE]",
    "PARALLEL_DELEGATION:",
]


def ensure_state_dir():
    """Ensure state directory exists."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_stravinsky_mode_state() -> Dict[str, Any]:
    """Read stravinsky mode state."""
    if not STRAVINSKY_MODE_FILE.exists():
        return {"active": False}
    try:
        content = STRAVINSKY_MODE_FILE.read_text().strip()
        return json.loads(content) if content else {"active": True}
    except (json.JSONDecodeError, IOError):
        return {"active": True}


def extract_preserved_context(prompt: str) -> List[str]:
    """Extract context matching preservation patterns."""
    preserved = []
    lines = prompt.split("\n")

    for i, line in enumerate(lines):
        for pattern in PRESERVE_PATTERNS:
            if pattern in line:
                # Capture line + 2 more for context
                context = "\n".join(lines[i:min(i+3, len(lines))])
                preserved.append(context)
                break

    return preserved[:15]  # Max 15 items


def log_compaction(preserved: List[str], stravinsky_active: bool):
    """Log compaction event for audit."""
    ensure_state_dir()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "preserved_count": len(preserved),
        "stravinsky_mode": stravinsky_active,
        "preview": [p[:50] for p in preserved[:3]],
    }

    try:
        with COMPACTION_LOG.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except IOError:
        pass


def main():
    """Main hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    prompt = hook_input.get("prompt", "")
    trigger = hook_input.get("trigger", "auto")

    # Get stravinsky mode state
    strav_state = get_stravinsky_mode_state()
    stravinsky_active = strav_state.get("active", False)

    # Extract preserved context
    preserved = extract_preserved_context(prompt)

    # Log compaction event
    log_compaction(preserved, stravinsky_active)

    # Output preservation warning
    if preserved or stravinsky_active:
        print(f"\n[PreCompact] Context compaction triggered ({trigger})", file=sys.stderr)
        print(f"  Preserved items: {len(preserved)}", file=sys.stderr)
        if stravinsky_active:
            print("  [STRAVINSKY MODE ACTIVE] - State will persist", file=sys.stderr)
        print("  Audit log: ~/.claude/state/compaction.jsonl", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
