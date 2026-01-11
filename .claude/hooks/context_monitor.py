#!/usr/bin/env python3
"""
Context Monitor Hook - Pre-emptive Compact at 70%

Fires on UserPromptSubmit to monitor context usage.
At 70%: Generates a pre-emptive compact summary.
At 85%: Critical warning.

This hook provides PROACTIVE context management, not reactive.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Context estimation constants
MAX_CONTEXT_TOKENS = 200000
CHARS_PER_TOKEN = 4
PREEMPTIVE_THRESHOLD = 0.70  # 70%
CRITICAL_THRESHOLD = 0.85    # 85%

# State tracking
STATE_DIR = Path.home() / ".claude" / "state"
CONTEXT_STATE_FILE = STATE_DIR / "context_monitor.json"


def estimate_tokens(text: str) -> int:
    """Estimate token count from character count."""
    return len(text) // CHARS_PER_TOKEN


def get_usage_percentage(text: str) -> float:
    """Calculate context window usage as percentage."""
    tokens = estimate_tokens(text)
    return tokens / MAX_CONTEXT_TOKENS


def ensure_state_dir():
    """Ensure state directory exists."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_last_compact_tokens() -> int:
    """Get token count at last compact recommendation."""
    try:
        if CONTEXT_STATE_FILE.exists():
            state = json.loads(CONTEXT_STATE_FILE.read_text())
            return state.get("last_compact_tokens", 0)
    except (json.JSONDecodeError, IOError):
        pass
    return 0


def set_last_compact_tokens(tokens: int):
    """Record token count at compact recommendation."""
    ensure_state_dir()
    try:
        state = {"last_compact_tokens": tokens, "timestamp": datetime.now(timezone.utc).isoformat()}
        CONTEXT_STATE_FILE.write_text(json.dumps(state))
    except IOError:
        pass


def generate_compact_summary_prompt(conversation: str, usage_pct: float) -> str:
    """Generate the summary request to inject into response."""
    return f"""
<system-reminder>
**[PRE-EMPTIVE CONTEXT OPTIMIZATION - {usage_pct:.1%} USAGE]**

Context window at {usage_pct:.1%} capacity. To prevent forced truncation, generate a summary NOW.

REQUIRED: Before continuing, output a structured summary:

```
## Context Summary (Pre-emptive Compact)

### Current Task
[What are we working on right now?]

### Key Decisions Made
- [Decision 1]
- [Decision 2]

### Files Modified/Created
- [file1.py]: [what changed]
- [file2.py]: [what changed]

### Critical Constraints
- [Any MUST NOT or NEVER rules]
- [Architectural decisions]

### Next Steps
1. [Immediate next action]
2. [Following action]
```

This summary will be preserved when automatic compaction occurs.
</system-reminder>
"""


def main():
    """Main hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    # Get the full conversation/prompt
    conversation = hook_input.get("prompt", "")
    if not conversation:
        return 0

    # Calculate usage
    tokens = estimate_tokens(conversation)
    usage = get_usage_percentage(conversation)

    # Check if we already triggered at this token level (avoid spam)
    last_compact = get_last_compact_tokens()

    # Only trigger once per ~10% increase
    token_threshold = int(MAX_CONTEXT_TOKENS * 0.10)  # ~20k tokens
    already_triggered = (tokens - last_compact) < token_threshold

    if usage >= CRITICAL_THRESHOLD:
        # Critical warning - always show
        print(f"\n⚠️ **CRITICAL: Context at {usage:.1%}** - Forced compaction imminent!", file=sys.stderr)
        print("  Generate summary NOW or context will be truncated.", file=sys.stderr)

        if not already_triggered:
            set_last_compact_tokens(tokens)
            # Inject summary request
            summary_prompt = generate_compact_summary_prompt(conversation, usage)
            print(summary_prompt, file=sys.stderr)

    elif usage >= PREEMPTIVE_THRESHOLD:
        # Pre-emptive optimization
        if not already_triggered:
            print(f"\n📊 **Context at {usage:.1%}** - Pre-emptive optimization recommended", file=sys.stderr)
            print(f"  Estimated tokens: {tokens:,} / {MAX_CONTEXT_TOKENS:,}", file=sys.stderr)
            print("  Headroom remaining: ~{:.0f}%".format((1 - usage) * 100), file=sys.stderr)

            set_last_compact_tokens(tokens)
            # Inject summary request
            summary_prompt = generate_compact_summary_prompt(conversation, usage)
            print(summary_prompt, file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
