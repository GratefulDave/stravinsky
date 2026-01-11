---
description: Get output from a background agent (block until complete or return immediately)
allowed-tools: mcp__stravinsky__agent_output
---

# Get Agent Output

Retrieve the final output from a background agent spawned with `agent_spawn`.

## What This Does

Returns the agent's final response. Can either:
- **Block**: Wait for agent to finish and return result
- **Non-blocking**: Return immediately with current status

## Usage

```python
# Block until agent completes (RECOMMENDED for collecting results)
agent_output(task_id="task_001", block=True)

# Check status without blocking
agent_output(task_id="task_001", block=False)
```

## Parameters

- `task_id`: The task ID from `agent_spawn` (e.g., "task_001")
- `block`: Whether to wait for completion (default: False)

## Example Workflow

```python
# 1. Spawn agents in parallel
task_1 = agent_spawn(
    agent_type="explore",
    prompt="Find authentication code",
    description="Auth search"
)

task_2 = agent_spawn(
    agent_type="dewey",
    prompt="Research JWT best practices",
    description="JWT research"
)

# 2. Collect results (blocks until both complete)
result_1 = agent_output(task_id=task_1["task_id"], block=True)
result_2 = agent_output(task_id=task_2["task_id"], block=True)

# 3. Process results
print(result_1)
print(result_2)
```

## Output Format

### Running Agent (block=False)
```
Agent task_001 is still running (2m 15s elapsed)
Use agent_progress(task_id="task_001") to monitor logs
```

### Completed Agent
```
[Agent Response]
Found authentication code in the following files:
- mcp_bridge/auth/oauth.py
- mcp_bridge/auth/token_store.py
...
```

### Failed Agent
```
Agent task_003 failed with error:
Error: Connection timeout to GPT API
Use agent_retry(task_id="task_003") to retry
```

## Use Cases

- **Parallel collection**: Block on multiple agents to collect all results
- **Status polling**: Check agent status without blocking
- **Error handling**: Get error messages from failed agents
- **Result synthesis**: Combine outputs from multiple agents

## Related Commands

- `/str:agent_list` - List all agents
- `/str:agent_progress` - Monitor real-time logs
- `/str:agent_retry` - Retry failed agent
- `/str:agent_cancel` - Stop running agent
