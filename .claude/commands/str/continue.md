---
description: Continue working on pending todos (RALPH loop manual trigger)
allowed-tools: TodoRead
---

# Continue Working on Pending Todos

Manually trigger the RALPH loop (Relentless Autonomous Labor Protocol) to continue working on incomplete todos.

## What This Does

Forces Claude to continue working on incomplete todos instead of stopping. Use this when:
- Claude completes a task but there are still pending todos
- You want to ensure all todos are completed before stopping
- The auto-continuation safety limit was reached

## Usage

Simply run: `/str:continue` or `/continue`

## What Happens

Claude will:
1. Check for incomplete todos (in_progress or pending)
2. Resume work on the next todo
3. Continue until all todos are complete or safety limit reached

## Safety Limits

- Maximum 10 auto-continuations per hour
- Resets after 1 hour of inactivity
- Manual `/continue` bypasses the limit

## Related Commands

- `/str:clean` - Delete semantic search indexes
- `/str:watch` - Start file watcher
- `/str:unwatch` - Stop file watcher
