# /strav:cancel-loop - Cancel Continuation Loop

Cancel an active Ralph Wiggum continuation loop.

## What This Does

Cancels the currently active continuation loop by:
1. Checking if `.stravinsky/continuation-loop.md` exists
2. If active: Reading the current iteration count and original prompt
3. Deleting the state file to stop the loop
4. Displaying a summary of work completed
5. Providing instructions to clean up hooks if desired

## Prerequisites

An active continuation loop (started with `/strav:loop`).

## Usage

```
/strav:cancel-loop
```

No parameters required.

## How It Works

### 1. Check Loop Status

The command first checks if `.stravinsky/continuation-loop.md` exists:

- **Found**: Parse the YAML frontmatter to extract iteration count, max iterations, and completion promise
- **Not Found**: Display "No active loop" message

### 2. Display Loop Summary

If active, shows:
- Current iteration number
- Maximum iterations configured
- Completion promise target
- Original prompt/task description
- Time elapsed since loop started

### 3. Clean Up State

Removes the `.stravinsky/continuation-loop.md` file to stop the continuation hook from intercepting exits.

### 4. Stop Hook Remains Active

The Stop hook at `~/.claude/hooks/stop_hook.py` remains configured in `.claude/settings.json` for future loops.

To remove it, delete the "Stop" section from `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [...]  // Delete this entire section
  }
}
```

## Example Output

```
Cancelling active continuation loop...

Loop Summary:
- Status: ACTIVE
- Iteration: 7 of 15
- Completion Promise: "ALL_TESTS_PASSING"
- Started: 2026-01-08 12:34:56 UTC
- Elapsed: 18 minutes

Original Task:
"Implement Redis caching layer with proper invalidation"

✅ State file removed: .stravinsky/continuation-loop.md
Loop cancelled successfully.

To remove the Stop hook from .claude/settings.json, delete the "Stop" section.
```

## Output Messages

### Active Loop Cancelled

```
✅ Cancelled continuation loop at iteration 7/15

Original task: Implement Redis caching layer...
Completion promise: "ALL_TESTS_PASSING"

Work completed: 7 iterations, 18 minutes
```

### No Active Loop

```
ℹ No active continuation loop found.

Use /strav:loop to start a new loop.
```

## Related Commands

- `/strav:loop` - Start a new continuation loop
- `/strav` - Stravinsky Orchestrator (standard task execution)

## Tips

1. **Before cancelling**: Review `.stravinsky/continuation-loop.md` to see how many iterations completed
2. **Save work**: Cancelling stops the loop but doesn't affect files created during iterations
3. **Re-enable loop**: Run `/strav:loop` again with a new prompt if you need to restart
4. **Clean hooks**: If you no longer want continuation loops, remove the Stop hook from settings

## Workflow

```
/strav:loop prompt="Task..." max_iterations=20
    ↓
[Claude works iteratively, refeding prompt]
    ↓
/strav:cancel-loop  ← You are here
    ↓
[Loop stops, state cleaned up]
    ↓
Continue with next task
```
