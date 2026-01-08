# /strav:loop - Continuation Loop

Start a Ralph Wiggum continuation loop for iterative task execution.

## What This Does

Creates a continuation loop that:
1. Initializes `.stravinsky/continuation-loop.md` with YAML frontmatter
2. Tracks iteration count, max iterations, and completion state
3. Provides a mechanism for iterative refinement and self-improvement
4. Requires a Stop hook in `.claude/settings.json` to interrupt

## Prerequisites

None. The command creates necessary files automatically.

## Usage

```
/strav:loop prompt="Your iterative task here" max_iterations=10 completion_promise="TASK_COMPLETE"
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | required | The task description or goal for the loop |
| `max_iterations` | int | 10 | Maximum number of iterations before auto-stop |
| `completion_promise` | string | "TASK_COMPLETE" | Signal string that terminates the loop when encountered |

## How It Works

### 1. Loop Initialization

The command creates `.stravinsky/continuation-loop.md` with YAML frontmatter:

```yaml
---
iteration_count: 0
max_iterations: 10
completion_promise: "TASK_COMPLETE"
active: true
started_at: 2026-01-08T12:34:56Z
---
Your original prompt here...
```

### 2. Iteration Tracking

During execution:
- Increment `iteration_count` after each cycle
- Check if `iteration_count >= max_iterations` → auto-stop
- Check if response contains `completion_promise` → auto-stop
- Continue execution while `active: true` and limits not exceeded

### 3. Stop Hook Configuration

The stop hook is automatically installed at `~/.claude/hooks/stop_hook.py`.

Add this to `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/stop_hook.py"
          }
        ]
      }
    ]
  }
}
```

When you click "Stop" in Claude Code, the hook sets `active: false` in the continuation loop state file.

## Example Usage

### Simple Iterative Refinement

```
/strav:loop prompt="Refine error messages in auth module until all validation errors are clear and actionable"
```

This will:
1. Create continuation loop
2. Run iteratively, improving error messages
3. Stop when "TASK_COMPLETE" is detected or after 10 iterations

### Multi-Step Feature Development

```
/strav:loop 
  prompt="Implement Redis caching layer: (1) Add RedisClient, (2) Implement cache decorators, (3) Add cache invalidation, (4) Add tests"
  max_iterations=20
  completion_promise="ALL_FEATURES_IMPLEMENTED"
```

### Performance Optimization Loop

```
/strav:loop
  prompt="Optimize database queries in reports module. Profile queries, identify N+1 problems, add indexes, verify improvement."
  max_iterations=15
```

## Loop State File

The loop maintains state in `.stravinsky/continuation-loop.md`:

```yaml
---
iteration_count: 3
max_iterations: 10
completion_promise: "TASK_COMPLETE"
active: true
started_at: 2026-01-08T12:34:56Z
last_updated: 2026-01-08T12:35:22Z
---
Original prompt...

## Iteration 1
[Work performed]

## Iteration 2
[Work performed]

## Iteration 3
[Work performed]
```

## Stopping the Loop

### Manual Stop

1. Run `/strav:stop` command, OR
2. User interrupt (Claude "Stop" button) triggers hook, OR
3. Set `active: false` in `.stravinsky/continuation-loop.md`

### Automatic Stop

- `iteration_count >= max_iterations`, OR
- Response contains `completion_promise` string

## When to Use

- Iterative refinement and improvement
- Multi-phase feature development
- Optimization and performance tuning
- Incremental testing and validation
- Self-correcting algorithms or processes
- Complex tasks with multiple success criteria

## When NOT to Use

- Single-pass tasks (use `/strav` orchestrator instead)
- Tasks with unclear stopping criteria
- Emergency fixes or time-critical work
- One-off changes

## Related Commands

- `/strav` - Stravinsky Orchestrator (standard task execution)
- `/strav:stop` - Stop active continuation loop
- `/delphi` - Strategic architecture advice
- `/dewey` - Research and implementation examples

## Tips

1. **Clear completion promise**: Use specific, detectable strings
   - Good: "ALL_TESTS_PASSING", "PERFORMANCE_TARGET_MET"
   - Less effective: "done", "finished"

2. **Reasonable iteration limit**: Balance between thoroughness and time
   - 10 iterations: Quick refinement tasks
   - 15-20 iterations: Complex multi-step features
   - 25+ iterations: Only for optimization/tuning with clear metrics

3. **Document progress**: Each iteration should log what was done
   - Makes debugging easier
   - Shows progress to user
   - Helps identify stuck loops

4. **Monitor iteration count**: Check `.stravinsky/continuation-loop.md` to see progress

5. **Use specific metrics**: Include success criteria in prompt
   - Bad: "Improve performance"
   - Good: "Improve query response time from 500ms to <100ms"
