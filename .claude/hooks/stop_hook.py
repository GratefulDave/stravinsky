#!/usr/bin/env python3
"""
Stop Hook: Continuation Loop Handler for Stravinsky.

Fires when the assistant stops generating to:
1. Check if a continuation loop is active (.stravinsky/continuation-loop.md)
2. Parse YAML frontmatter with iteration_count, max_iterations, completion_promise, active
3. Decide whether to continue the loop or exit
4. Inject continuation prompt if needed

Exit codes:
  0 = Stop loop (allow normal completion)
  2 = Continue loop (inject continuation prompt, block completion)

State File Format (.stravinsky/continuation-loop.md):
---
iteration_count: 1
max_iterations: 10
completion_promise: "Goal completed: All tests passing"
active: true
---
<optional loop context or notes>

The hook will:
1. Read stdin for assistant's last response
2. Check if continuation-loop.md exists
3. Parse YAML frontmatter to get state
4. Increment iteration_count
5. Check if max_iterations reached OR completion_promise found in response
6. If continue: update state file, exit 2, print continuation prompt
7. If stop: delete state file, exit 0
"""

import json
import sys
import re
from pathlib import Path
from typing import Optional, Tuple, Dict


CONTINUATION_LOOP_FILE = Path.cwd() / ".stravinsky" / "continuation-loop.md"
DEFAULT_MAX_ITERATIONS = 10


def parse_yaml_frontmatter(content: str) -> Tuple[Dict[str, any], str]:
    """
    Parse YAML frontmatter from a markdown file.
    
    Returns: (parsed_dict, remaining_content)
    """
    # Match frontmatter: --- YAML --- content
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    
    if not match:
        return {}, content
    
    yaml_block = match.group(1)
    remaining = match.group(2)
    
    # Simple YAML parser for our format
    state = {}
    for line in yaml_block.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # Parse value types
            if value.lower() == 'true':
                state[key] = True
            elif value.lower() == 'false':
                state[key] = False
            elif value.isdigit():
                state[key] = int(value)
            else:
                # Remove quotes if present
                state[key] = value.strip('\'"')
    
    return state, remaining


def read_continuation_state() -> Optional[Dict[str, any]]:
    """Read and parse continuation loop state file."""
    if not CONTINUATION_LOOP_FILE.exists():
        return None
    
    try:
        content = CONTINUATION_LOOP_FILE.read_text()
        state, _ = parse_yaml_frontmatter(content)
        return state if state else None
    except Exception:
        return None


def write_continuation_state(state: Dict[str, any], context: str = "") -> None:
    """Write continuation loop state to file in YAML frontmatter format."""
    CONTINUATION_LOOP_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Build YAML frontmatter
    yaml_lines = ["---"]
    yaml_lines.append(f"iteration_count: {state.get('iteration_count', 1)}")
    yaml_lines.append(f"max_iterations: {state.get('max_iterations', DEFAULT_MAX_ITERATIONS)}")
    yaml_lines.append(f"completion_promise: \"{state.get('completion_promise', '')}\"")
    yaml_lines.append(f"active: {str(state.get('active', True)).lower()}")
    yaml_lines.append("---")
    
    content = "\n".join(yaml_lines)
    if context:
        content += f"\n\n{context}"
    
    CONTINUATION_LOOP_FILE.write_text(content)


def extract_assistant_response(hook_input: dict) -> str:
    """Extract assistant's last response from hook input."""
    # Try multiple possible locations for the response
    response = ""
    
    if isinstance(hook_input, dict):
        # Could be in 'response', 'content', 'message', etc.
        for key in ['response', 'content', 'message', 'text', 'assistant_response']:
            if key in hook_input:
                value = hook_input[key]
                if isinstance(value, str):
                    response = value
                    break
                elif isinstance(value, list):
                    # Could be a list of message objects
                    response = " ".join(str(v) for v in value)
                    break
                elif isinstance(value, dict):
                    # Could have 'text' key
                    response = value.get('text', str(value))
                    break
    
    return response


def should_continue_loop(state: Dict[str, any], response: str) -> bool:
    """
    Determine if loop should continue.
    
    Continue if:
    - active is true AND
    - iteration_count < max_iterations AND
    - completion_promise NOT found in response
    
    Stop if:
    - iteration_count >= max_iterations OR
    - completion_promise text found in response
    """
    if not state.get('active', True):
        return False
    
    max_iterations = state.get('max_iterations', DEFAULT_MAX_ITERATIONS)
    iteration_count = state.get('iteration_count', 0)
    
    # Check max iterations
    if iteration_count >= max_iterations:
        return False
    
    # Check completion promise
    completion_promise = state.get('completion_promise', '')
    if completion_promise and completion_promise.lower() in response.lower():
        return False
    
    return True


def format_continuation_prompt() -> str:
    """Format a reminder prompt for continuation."""
    return (
        "\n\n[SYSTEM REMINDER - CONTINUATION LOOP ACTIVE]\n"
        "This is an automated continuation loop. Review your progress:\n"
        "- Check what has been completed\n"
        "- Continue working towards the goal\n"
        "- If complete, explicitly state the completion promise\n"
        "- If blocked, explain the issue\n"
    )


def main():
    """Main hook entry point."""
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0
    
    # Check if continuation loop is active
    state = read_continuation_state()
    if state is None:
        # No continuation loop active, allow normal completion
        return 0
    
    # Extract assistant response
    response = extract_assistant_response(hook_input)
    
    # Increment iteration count
    state['iteration_count'] = state.get('iteration_count', 1) + 1
    
    # Determine if we should continue
    if should_continue_loop(state, response):
        # Update state file with incremented iteration
        write_continuation_state(state, f"Iteration {state['iteration_count']} in progress")
        
        # Print continuation prompt
        print(format_continuation_prompt(), file=sys.stderr)
        
        # Exit with code 2 to signal continuation
        return 2
    else:
        # Loop complete, clean up state file
        CONTINUATION_LOOP_FILE.unlink(missing_ok=True)
        
        if state.get('iteration_count', 0) >= state.get('max_iterations', DEFAULT_MAX_ITERATIONS):
            print(
                f"[CONTINUATION LOOP] Max iterations ({state.get('max_iterations', DEFAULT_MAX_ITERATIONS)}) reached. Loop stopped.",
                file=sys.stderr
            )
        else:
            print(
                f"[CONTINUATION LOOP] Completion promise detected. Loop stopped successfully.",
                file=sys.stderr
            )
        
        return 0


if __name__ == "__main__":
    sys.exit(main())
