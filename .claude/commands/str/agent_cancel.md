---
description: Cancel a running background agent
allowed-tools: mcp__stravinsky__agent_cancel
---

# Cancel Background Agent

Stop a running background agent immediately.

## What This Does

Terminates a running agent and cleans up resources. The agent's status will change to "cancelled" and no further work will be done.

## Usage

```python
# Cancel a specific agent
agent_cancel(task_id="task_001")
```

## Parameters

- `task_id`: The task ID from `agent_spawn`

## When to Cancel

- **Agent stuck**: Agent is taking too long or appears hung
- **Wrong task**: Accidentally spawned wrong agent or wrong prompt
- **Task no longer needed**: Requirements changed, agent work is obsolete
- **Resource management**: Too many agents running, need to free up slots

## Example Workflow

```python
# 1. Spawn multiple agents
task_1 = agent_spawn(agent_type="explore", prompt="Find X", description="Task 1")
task_2 = agent_spawn(agent_type="dewey", prompt="Research Y", description="Task 2")
task_3 = agent_spawn(agent_type="delphi", prompt="Review Z", description="Task 3")

# 2. Check progress
agent_list(show_all=False)

# 3. Cancel slow/stuck agent
agent_cancel(task_id=task_1["task_id"])

# 4. Wait for remaining agents
result_2 = agent_output(task_id=task_2["task_id"], block=True)
result_3 = agent_output(task_id=task_3["task_id"], block=True)
```

## Output

```
✅ Cancelled agent task_001 (explore - Find X)
Agent stopped gracefully
```

## Notes

- **Graceful shutdown**: Agent completes current tool call before stopping
- **No partial results**: Cancelled agents don't return partial work
- **Safe operation**: No data loss or corruption
- **Cannot uncancelled**: Once cancelled, use `agent_retry` to restart with same prompt

## Related Commands

- `/str:agent_list` - List all agents
- `/str:agent_retry` - Retry cancelled/failed agent
- `/str:agent_progress` - Monitor agent before cancelling
- `/str:agent_output` - Get results from completed agents
