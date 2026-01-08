# Continuation Loop Guide

## Overview

The **ralph-wiggum continuation loop** allows Claude to automatically continue working on a task until a goal is reached or a maximum number of iterations is hit. This is implemented via the Stop hook (`.claude/hooks/stop_hook.py`).

## How It Works

1. **Activation**: Create a state file at `.stravinsky/continuation-loop.md`
2. **Loop Execution**: Every time Claude finishes a response, the Stop hook checks if it should continue
3. **Termination**: Loop stops when:
   - Max iterations reached (default: 10)
   - Completion promise text detected in response
   - `active: false` set in state file

## State File Format

Create `.stravinsky/continuation-loop.md` with YAML frontmatter:

```markdown
---
iteration_count: 1
max_iterations: 10
completion_promise: "All tests passing"
active: true
---

Optional context or notes about the loop goal.
```

### State Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `iteration_count` | integer | Yes | Current iteration (auto-incremented by hook) |
| `max_iterations` | integer | Yes | Maximum iterations before force stop (default: 10) |
| `completion_promise` | string | Yes | Text to detect in response that signals completion |
| `active` | boolean | Yes | Whether loop is active (set false to stop) |

## Usage Examples

### Example 1: Run Tests Until Passing

```markdown
---
iteration_count: 1
max_iterations: 15
completion_promise: "✅ All tests passing"
active: true
---

Goal: Fix failing tests in test_auth.py
- Run pytest
- Analyze failures
- Fix issues
- Repeat until all tests pass
```

**Completion**: When Claude's response contains "✅ All tests passing", loop stops automatically.

### Example 2: Implement Feature with Checkpoints

```markdown
---
iteration_count: 1
max_iterations: 20
completion_promise: "Feature complete and tested"
active: true
---

Goal: Implement OAuth refresh token flow
1. Add refresh endpoint
2. Update token storage
3. Implement auto-refresh logic
4. Add tests
5. Update documentation
```

### Example 3: Debug Complex Issue

```markdown
---
iteration_count: 1
max_iterations: 12
completion_promise: "Root cause identified and fixed"
active: true
---

Goal: Fix memory leak in semantic search indexer
- Profile memory usage
- Identify leak source
- Implement fix
- Verify with stress test
```

## Hook Behavior

### Stop Hook Flow

1. **Read State**: Parse `.stravinsky/continuation-loop.md`
2. **Extract Response**: Get Claude's last response text
3. **Increment Counter**: `iteration_count += 1`
4. **Check Conditions**:
   - If `iteration_count >= max_iterations` → Stop (exit 0)
   - If `completion_promise` in response → Stop (exit 0)
   - If `active == false` → Stop (exit 0)
   - Otherwise → Continue (exit 2)
5. **Update State**: Write incremented counter to state file
6. **Inject Prompt**: Add continuation reminder to trigger next iteration

### Exit Codes

- **Exit 0**: Stop loop, allow normal completion
- **Exit 2**: Continue loop, inject continuation prompt, block completion

### Continuation Prompt

When continuing, the hook injects:

```
[SYSTEM REMINDER - CONTINUATION LOOP ACTIVE]
This is an automated continuation loop. Review your progress:
- Check what has been completed
- Continue working towards the goal
- If complete, explicitly state the completion promise
- If blocked, explain the issue
```

## Integration with TODO System

The continuation loop **coexists peacefully** with the TODO continuation system:

- **todo_continuation.py**: UserPromptSubmit hook (runs BEFORE processing)
  - Reminds about incomplete TODOs
  - Message format: `[SYSTEM REMINDER - TODO CONTINUATION]`

- **stop_hook.py**: Stop hook (runs AFTER response)
  - Manages continuation loop
  - Message format: `[SYSTEM REMINDER - CONTINUATION LOOP ACTIVE]`

Both systems can run simultaneously without conflicts.

## Manual Control

### Start Loop

```bash
cat > .stravinsky/continuation-loop.md << 'EOF'
---
iteration_count: 1
max_iterations: 10
completion_promise: "Goal achieved"
active: true
---

Your goal description here.
EOF
```

### Stop Loop

Option 1: Set `active: false` in state file
Option 2: Delete `.stravinsky/continuation-loop.md`
Option 3: Include completion promise text in response

### Check Status

```bash
cat .stravinsky/continuation-loop.md
```

## Best Practices

1. **Set Realistic Max Iterations**
   - Simple tasks: 5-8 iterations
   - Complex features: 15-20 iterations
   - Debug sessions: 10-15 iterations

2. **Use Clear Completion Promises**
   - ✅ Good: "All tests passing", "Feature complete", "Bug fixed"
   - ❌ Bad: "done", "ok", "finished" (too vague, might trigger early)

3. **Include Context in State File**
   - Add goal description below frontmatter
   - List subtasks or checkpoints
   - Document blockers or dependencies

4. **Monitor Progress**
   - Check `iteration_count` periodically
   - Review Claude's responses for blockers
   - Adjust `max_iterations` if needed

5. **Clean Up After Completion**
   - Hook auto-deletes state file on success
   - Manually delete if loop abandoned

## Troubleshooting

### Loop Won't Start

- Verify state file exists at `.stravinsky/continuation-loop.md`
- Check YAML frontmatter syntax (must have `---` delimiters)
- Ensure `active: true` is set

### Loop Stops Prematurely

- Check if completion promise text appears in response
- Verify `max_iterations` is high enough
- Check if `active` changed to `false`

### Loop Won't Stop

- Verify completion promise text exactly matches
- Matching is case-insensitive
- Set `active: false` to force stop
- Delete state file as last resort

### State File Not Updating

- Check file permissions on `.stravinsky/` directory
- Verify hook has write access
- Check hook execution logs

## Implementation Details

### File Locations

- **Hook**: `.claude/hooks/stop_hook.py`
- **State File**: `.stravinsky/continuation-loop.md`
- **Todo Hook**: `.claude/hooks/todo_continuation.py` (separate, no conflicts)

### Constants

```python
CONTINUATION_LOOP_FILE = Path.cwd() / ".stravinsky" / "continuation-loop.md"
DEFAULT_MAX_ITERATIONS = 10
```

### State Parsing

The hook uses a simple YAML parser that supports:
- Integer values: `iteration_count: 5`
- Boolean values: `active: true` / `active: false`
- String values: `completion_promise: "text"`
- Comments: `# This is a comment`

### Completion Promise Detection

```python
completion_promise = state.get('completion_promise', '')
if completion_promise and completion_promise.lower() in response.lower():
    return False  # Stop loop
```

- Case-insensitive substring matching
- Must be exact text (e.g., "tests passing" won't match "All tests passing")

## Advanced Usage

### Dynamic Max Iterations

Manually update state file during loop:

```bash
# Increase max iterations if task is taking longer
sed -i '' 's/max_iterations: 10/max_iterations: 20/' .stravinsky/continuation-loop.md
```

### Multiple Completion Conditions

Use logical OR in completion promise:

```markdown
completion_promise: "All tests passing|Feature complete|No errors found"
```

Note: Current implementation only supports single string matching. For multiple conditions, you'd need to modify the hook.

### Loop Chaining

Start a new loop after one completes:

```bash
# After loop 1 completes, start loop 2
cat > .stravinsky/continuation-loop.md << 'EOF'
---
iteration_count: 1
max_iterations: 10
completion_promise: "Documentation complete"
active: true
---

Phase 2: Document the new feature
EOF
```

## Security Considerations

1. **State File Validation**
   - Hook validates state file format
   - Invalid YAML is ignored (loop won't start)
   - Missing required fields default to safe values

2. **Infinite Loop Prevention**
   - Hard limit via `max_iterations`
   - Default is conservative (10)
   - Can be increased for complex tasks

3. **Manual Override**
   - User can always stop loop by deleting state file
   - Setting `active: false` provides graceful shutdown

## Future Enhancements

Potential improvements (not yet implemented):

- Multiple completion promise conditions (OR logic)
- Iteration timeout (max time per iteration)
- Progress callbacks (notify on milestones)
- Loop templates for common tasks
- Integration with TODO system (auto-create from pending TODOs)
- Loop history/replay (save completed loops for analysis)

## References

- Stop hook implementation: `.claude/hooks/stop_hook.py`
- TODO continuation hook: `.claude/hooks/todo_continuation.py`
- Hook system documentation: `.claude/hooks/README.md`
