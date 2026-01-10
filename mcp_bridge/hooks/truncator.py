import json
import sys

MAX_CHARS = 30000

def main():
    try:
        data = json.load(sys.stdin)
        tool_response = data.get("tool_response", "")
    except Exception:
        return

    if len(tool_response) > MAX_CHARS:
        header = f"[TRUNCATED - {len(tool_response)} chars reduced to {MAX_CHARS}]\n"
        footer = "\n...[TRUNCATED]"
        truncated = tool_response[:MAX_CHARS]
        print(header + truncated + footer)
    else:
        print(tool_response)

if __name__ == "__main__":
    main()
