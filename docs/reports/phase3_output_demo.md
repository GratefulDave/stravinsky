# Phase 3 - Clean Output Formatting Demo

## Overview
This document demonstrates the new clean output formatting for agent spawn operations.

## Output Modes

### 1. CLEAN Mode (Default)
**Environment**: `STRAVINSKY_OUTPUT_MODE=clean` (or unset)

**Spawn Output**:
```
✓ explore:gemini-3-flash → agent_abc123
```

**Progress Updates** (every 10s to stderr):
```
⏳ agent_abc123 running (15s)...
⏳ agent_abc123 running (25s)...
⏳ agent_abc123 running (35s)...
```

**Completion Notification** (to stderr):
```
✅ agent_abc123 (42s) - Found authentication logic in src/auth/handlers.py
```

**Failure Notification** (to stderr):
```
❌ agent_abc123 (15s) - FileNotFoundError: auth.py not found
```

**Benefits**:
- Single line output (under 100 chars)
- Easy to parse programmatically
- Minimal visual clutter
- Progress updates don't block main thread

---

### 2. VERBOSE Mode
**Environment**: `STRAVINSKY_OUTPUT_MODE=verbose`

**Spawn Output**:
```
🟢 explore:gemini-3-flash('Find authentication logic') ⏳
task_id=agent_abc123
```

**Progress Updates**: Same as CLEAN mode

**Completion Notification**:
```
🟢 ✅ Agent Task Completed

**Task ID**: agent_abc123
**Agent**: explore:gemini-3-flash('Find authentication logic')
**Duration**: 42s

**Result**:
Found authentication logic in src/auth/handlers.py at line 45.
The UserAuthHandler class implements JWT validation.
```

**Benefits**:
- Full context in spawn message
- Detailed completion output
- Useful for debugging
- Shows task description

---

### 3. SILENT Mode
**Environment**: `STRAVINSKY_OUTPUT_MODE=silent`

**Spawn Output**: (empty)

**Progress Updates**: None

**Completion Notification**: None (only in logs)

**Benefits**:
- No stdout/stderr pollution
- Ideal for automated scripts
- Reduces noise in CI/CD
- All info still in logs

---

## Color Scheme

### Agent Types
- 🟢 **Green**: Cheap models (explore, dewey, document_writer, haiku agents)
- 🔵 **Blue**: Medium cost (frontend with gemini-3-pro-high)
- 🟣 **Purple**: Expensive models (delphi with gpt-5.2, opus)

### Status Indicators
- ✓ **Green checkmark**: Successful spawn
- ⏳ **Yellow hourglass**: Running/in progress
- ✅ **Green check**: Completed successfully
- ❌ **Red X**: Failed
- ⚠️ **Yellow warning**: Cancelled

### Text Colors
- **Cyan**: Agent types and task IDs
- **Yellow**: Model names
- **Bold**: Descriptions and summaries
- **Dim**: Secondary info (PIDs, timestamps)

---

## Usage Examples

### Example 1: Spawning in Default Mode
```python
# No environment variable set (defaults to CLEAN)
task_id = await agent_spawn(
    prompt="Find authentication logic in the codebase",
    agent_type="explore",
    description="Find auth code"
)
# Output: ✓ explore:gemini-3-flash → agent_abc123
```

### Example 2: Spawning in Verbose Mode
```bash
export STRAVINSKY_OUTPUT_MODE=verbose
```
```python
task_id = await agent_spawn(
    prompt="Find authentication logic in the codebase",
    agent_type="explore",
    description="Find auth code"
)
# Output: 🟢 explore:gemini-3-flash('Find auth code') ⏳
#         task_id=agent_abc123
```

### Example 3: Spawning in Silent Mode
```bash
export STRAVINSKY_OUTPUT_MODE=silent
```
```python
task_id = await agent_spawn(
    prompt="Find authentication logic in the codebase",
    agent_type="explore",
    description="Find auth code"
)
# Output: (empty - no stdout/stderr)
```

### Example 4: Getting Output
```python
result = await agent_output(task_id="agent_abc123", block=True)
# Stderr notification: ✅ agent_abc123 (42s) - Found authentication logic...
# Returns full task details with result
```

---

## Implementation Notes

### Progress Monitor
- Runs in background daemon thread
- Updates every 10 seconds
- Writes to stderr (doesn't interfere with stdout)
- Automatically stops when task completes
- Format: `⏳ agent_abc123 running (Xs)...`

### Completion/Failure Notifications
- Triggered by `agent_output()` when retrieving results
- Written to stderr for visibility
- Includes duration and one-sentence summary
- Format:
  - Success: `✅ task_id (duration) - summary`
  - Failure: `❌ task_id (duration) - error`

### Thread Safety
- All progress monitors use daemon threads
- Proper cleanup in `_execute_agent()` finally block
- `_stop_monitors` event flag for coordinated shutdown
- No blocking of main thread

---

## Performance

### CLEAN Mode
- Spawn output: ~75 chars (under 100 char target)
- Progress updates: Every 10s to stderr
- Completion: Single line to stderr
- **Recommended for production use**

### VERBOSE Mode
- Spawn output: ~150 chars (multi-line)
- Progress updates: Every 10s to stderr
- Completion: Full details (multi-line)
- **Recommended for debugging**

### SILENT Mode
- Spawn output: 0 chars
- Progress updates: None (logs only)
- Completion: None (logs only)
- **Recommended for CI/CD pipelines**

---

## Backwards Compatibility

✅ **All existing `agent_spawn()` calls remain compatible**
- No API changes
- Default behavior is CLEAN mode
- Existing code works without modification
- Environment variable is optional

---

## Future Enhancements

Potential improvements for Phase 4+:
1. Configurable progress update interval (currently 10s)
2. Rich progress bars using `rich` library
3. JSON-formatted output mode for machine parsing
4. Progress percentage based on timeout estimate
5. Notification webhooks for remote monitoring
