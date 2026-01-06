import os
import sys
import json
from pathlib import Path

def main():
    try:
        data = json.load(sys.stdin)
        prompt = data.get("prompt", "")
    except Exception:
        return

    cwd = Path(os.environ.get("CLAUDE_CWD", "."))
    
    # Files to look for
    context_files = ["AGENTS.md", "README.md", "CLAUDE.md"]
    found_context = ""

    for f in context_files:
        path = cwd / f
        if path.exists():
            try:
                content = path.read_text()
                found_context += f"\n\n--- LOCAL CONTEXT: {f} ---\n{content}\n"
                break # Only use one for brevity
            except Exception:
                pass

    if found_context:
        # Prepend context to prompt
        # We wrap the user prompt to distinguish it
        new_prompt = f"{found_context}\n\n[USER PROMPT]\n{prompt}"
        print(new_prompt)
    else:
        print(prompt)

if __name__ == "__main__":
    main()
