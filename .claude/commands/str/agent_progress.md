---
description: Monitor real-time logs from a running background agent
allowed-tools: mcp__stravinsky__agent_progress
---

# Monitor Agent Progress

Stream real-time logs from a running background agent to see what it's doing.

## What This Does

Shows the last N lines of an agent's execution log, including:
- Tool calls being made
- Reasoning/thinking steps
- Error messages
- Current status

## Usage

```python
# Show last 20 lines (default)
agent_progress(task_id="task_001")

# Show last 50 lines
agent_progress(task_id="task_001", lines=50)
```

## Parameters

- `task_id`: The task ID from `agent_spawn`
- `lines`: Number of log lines to show (default: 20)

## Example Output

```
Progress for agent task_001 (explore - Find auth code):
Status: running (2m 15s)

[2026-01-11 04:00:15] Starting agent task_001 (explore)
[2026-01-11 04:00:16] Tool call: semantic_search(query="authentication logic")
[2026-01-11 04:00:18] Found 5 results in semantic search
[2026-01-11 04:00:19] Tool call: read_file(path="mcp_bridge/auth/oauth.py")
[2026-01-11 04:00:20] Analyzing OAuth implementation...
[2026-01-11 04:00:21] Tool call: read_file(path="mcp_bridge/auth/token_store.py")
[2026-01-11 04:00:22] Found keyring storage implementation
[2026-01-11 04:00:23] Synthesizing findings...
[2026-01-11 04:00:24] Agent completed successfully
```

## Use Cases

- **Debug long-running agents**: See what's taking so long
- **Monitor progress**: Check if agent is making progress
- **Spot errors**: Catch errors early before completion
- **Learn patterns**: See what tools agents use and in what order

## Monitoring Multiple Agents

```python
# List all running agents
agent_list(show_all=False)

# Check progress of each
agent_progress(task_id="task_001")
agent_progress(task_id="task_002")
agent_progress(task_id="task_003")
```

## Related Commands

- `/str:agent_list` - List all agents
- `/str:agent_output` - Get final results
- `/str:agent_cancel` - Stop agent
- `/str:agent_retry` - Retry failed agent
