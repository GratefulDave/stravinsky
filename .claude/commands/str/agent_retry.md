---
description: Retry a failed or cancelled background agent with the same prompt
allowed-tools: mcp__stravinsky__agent_retry, mcp__stravinsky__agent_spawn
---

# Retry Background Agent

Retry a failed or cancelled agent with the exact same prompt and configuration.

## What This Does

Creates a new agent task with the same:
- Agent type
- Prompt
- Description
- Model (if specified)

Returns a new task ID for the retried agent.

## Usage

```python
# Retry a failed agent
agent_retry(task_id="task_001")
```

## Parameters

- `task_id`: The task ID of the failed/cancelled agent to retry

## When to Retry

- **Transient failures**: Network timeout, API rate limit, temporary service outage
- **Fixed environment**: Ollama was down, now it's running
- **Cancelled by mistake**: Accidentally cancelled a needed agent
- **Resource contention**: Agent failed due to too many concurrent operations

## Example Workflow

```python
# 1. Spawn agent
task_1 = agent_spawn(
    agent_type="explore",
    prompt="Find authentication code",
    description="Auth search"
)

# 2. Agent fails (e.g., network error)
agent_list()  # Shows task_001: failed

# 3. Fix issue (e.g., restart network)

# 4. Retry with same configuration
retry_result = agent_retry(task_id=task_1["task_id"])
new_task_id = retry_result["task_id"]

# 5. Monitor new agent
agent_progress(task_id=new_task_id)
result = agent_output(task_id=new_task_id, block=True)
```

## Output

```
♻️ Retrying agent task_001 (explore - Auth search)
New task ID: task_004
Agent started with same configuration
```

## Error Handling

```python
# Pattern: Retry on failure
try:
    result = agent_output(task_id="task_001", block=True)
except Exception as e:
    print(f"Agent failed: {e}")
    retry = agent_retry(task_id="task_001")
    result = agent_output(task_id=retry["task_id"], block=True)
```

## Notes

- **New task ID**: Retry creates a new agent, doesn't reuse the old task ID
- **Same configuration**: All parameters are copied from original agent
- **Independent execution**: Retried agent is separate from original
- **No automatic retry**: You must explicitly call `agent_retry`

## Related Commands

- `/str:agent_list` - List failed agents to retry
- `/str:agent_output` - Get results after retry
- `/str:agent_progress` - Monitor retry progress
- `/str:agent_cancel` - Cancel retry if it fails again
