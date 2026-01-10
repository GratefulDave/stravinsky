import json
import os
import re
import sys


def main():
    # Claude Code PostToolUse inputs via Environment Variables
    tool_name = os.environ.get("CLAUDE_TOOL_NAME")
    
    # We only care about Edit/MultiEdit
    if tool_name not in ["Edit", "MultiEdit"]:
        return

    # Read from stdin (Claude Code passes the tool response via stdin for some hook types, 
    # but for PostToolUse it's often better to check the environment variable if available.
    # Actually, the summary says input is a JSON payload.
    try:
        data = json.load(sys.stdin)
        tool_response = data.get("tool_response", "")
    except Exception:
        # Fallback to direct string if not JSON
        return

    # Error patterns
    error_patterns = [
        r"oldString not found",
        r"oldString matched multiple times",
        r"line numbers out of range"
    ]

    recovery_needed = any(re.search(p, tool_response, re.IGNORECASE) for p in error_patterns)

    if recovery_needed:
        correction = (
            "\n\n[SYSTEM RECOVERY] It appears the Edit tool failed to find the target string. "
            "Please call 'Read' on the file again to verify the current content, "
            "then ensure your 'oldString' is an EXACT match including all whitespace."
        )
        # For PostToolUse, stdout is captured and appended/replaces output
        print(tool_response + correction)
    else:
        # No change
        print(tool_response)

if __name__ == "__main__":
    main()
