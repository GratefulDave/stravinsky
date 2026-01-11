---
description: List all background agents (running, completed, failed)
allowed-tools: mcp__stravinsky__agent_list
---

# List Background Agents

Show overview of all background agents spawned with `agent_spawn`, including their status, task IDs, and descriptions.

## What This Does

Returns a formatted table showing:
- **Task ID**: Unique identifier for each agent
- **Agent Type**: explore, dewey, frontend, delphi, etc.
- **Status**: running, completed, failed
- **Description**: Short description of the task
- **Model**: Which model the agent is using
- **Duration**: How long the agent has been running/ran

## Usage

```python
# Show all agents (default)
agent_list(show_all=True)

# Show only running agents
agent_list(show_all=False)
```

## Example Output

```
Background Agents (3 total, 1 running):

┌──────────┬─────────┬───────────┬──────────────────────┬────────┬──────────┐
│ Task ID  │ Type    │ Status    │ Description          │ Model  │ Duration │
├──────────┼─────────┼───────────┼──────────────────────┼────────┼──────────┤
│ task_001 │ explore │ running   │ Find auth code       │ Gemini │ 2m 15s   │
│ task_002 │ dewey   │ completed │ Research JWT docs    │ Gemini │ 1m 30s   │
│ task_003 │ delphi  │ failed    │ Architecture review  │ GPT-5  │ 3m 45s   │
└──────────┴─────────┴───────────┴──────────────────────┴────────┴──────────┘
```

## Use Cases

- **Monitor parallel agents**: Check progress of multiple spawned agents
- **Debugging**: Find failed agents and retry
- **Status check**: See what's currently running
- **Task tracking**: Get task IDs for `agent_output` and `agent_progress`

## Related Commands

- `/str:agent_progress` - Monitor real-time agent logs
- `/str:agent_output` - Get agent results
- `/str:agent_cancel` - Stop running agent
- `/str:agent_retry` - Retry failed agent
