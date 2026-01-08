# Continuation Loop - Ralph Wiggum Implementation

## Overview

The **ralph-wiggum continuation loop** is implemented via the Stop hook system. It allows Claude to automatically continue working on a task until completion or max iterations.

## Implementation Status

✅ **COMPLETE** - All requirements implemented and tested

### Components

1. **Stop Hook** (`.claude/hooks/stop_hook.py`)
   - Runs after every assistant response
   - Checks continuation state file
   - Decides whether to continue or stop
   - Auto-increments iteration counter
   - Detects completion promises

2. **State File** (`.stravinsky/continuation-loop.md`)
   - YAML frontmatter format
   - Stores iteration count, max iterations, completion promise, active flag
   - Auto-created/updated by hook
   - Auto-deleted on loop completion

3. **Documentation** (`.stravinsky/CONTINUATION_LOOP_GUIDE.md`)
   - Complete user guide
   - Usage examples
   - Best practices
   - Troubleshooting

4. **Tests** (`.stravinsky/test_continuation_loop.py`)
   - Comprehensive test suite
   - All tests passing ✅
   - Covers all critical paths

## Key Features

### ✅ Default max_iterations = 10
Set in `stop_hook.py` line 42:
```python
DEFAULT_MAX_ITERATIONS = 10
```

### ✅ No Conflicts with todo_continuation.py
The two hooks operate at different lifecycle points:
- **todo_continuation.py**: UserPromptSubmit hook (BEFORE processing)
- **stop_hook.py**: Stop hook (AFTER response)

Different message formats ensure no collisions:
- TODO: `[SYSTEM REMINDER - TODO CONTINUATION]`
- Loop: `[SYSTEM REMINDER - CONTINUATION LOOP ACTIVE]`

### ✅ Completion Promise Detection
Case-insensitive substring matching (lines 167-169):
```python
completion_promise = state.get('completion_promise', '')
if completion_promise and completion_promise.lower() in response.lower():
    return False  # Stop loop
```

### ✅ State File Format
YAML frontmatter in `.stravinsky/continuation-loop.md`:
```markdown
---
iteration_count: 1
max_iterations: 10
completion_promise: "Goal completed"
active: true
---

Optional context about the loop goal
```

## Quick Start

### 1. Create State File

```bash
cat > .stravinsky/continuation-loop.md << 'EOF'
---
iteration_count: 1
max_iterations: 10
completion_promise: "All tests passing"
active: true
---

Goal: Fix all failing tests in test_auth.py
EOF
```

### 2. Start Working

The loop activates automatically. Claude will:
1. Work on the task
2. Stop hook checks state after each response
3. Auto-continues if conditions not met
4. Stops when completion promise detected or max iterations reached

### 3. Monitor Progress

```bash
# Check current state
cat .stravinsky/continuation-loop.md

# Stop manually if needed
rm .stravinsky/continuation-loop.md
```

## Hook Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ Claude generates response                                        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stop hook fires                                                  │
│ 1. Read .stravinsky/continuation-loop.md                        │
│ 2. Parse YAML frontmatter                                       │
│ 3. increment iteration_count                                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │ Check conditions:           │
         │ - iteration >= max?         │
         │ - completion promise found? │
         │ - active == false?          │
         └─────┬──────────────┬────────┘
               │              │
          Yes  │              │ No
               ▼              ▼
       ┌───────────────┐  ┌──────────────────────┐
       │ STOP (exit 0) │  │ CONTINUE (exit 2)    │
       │ - Delete state│  │ - Update state file  │
       │ - Log reason  │  │ - Inject prompt      │
       └───────────────┘  │ - Block completion   │
                          └──────────┬───────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │ Claude continues...  │
                          └──────────────────────┘
```

## Test Results

All 6 tests passing:

```
✅ Test 1: Loop activation with valid state file
✅ Test 2: Max iterations termination
✅ Test 3: Completion promise detection
✅ Test 4: Active flag control
✅ Test 5: No state file (normal operation)
✅ Test 6: Case-insensitive completion promise
```

Run tests:
```bash
python3 .stravinsky/test_continuation_loop.py
```

## Integration with TODO System

The continuation loop **coexists peacefully** with todo_continuation.py:

| Hook | Lifecycle Point | Message Format | Purpose |
|------|----------------|----------------|---------|
| `todo_continuation.py` | UserPromptSubmit | `[TODO CONTINUATION]` | Remind about incomplete TODOs |
| `stop_hook.py` | Stop | `[CONTINUATION LOOP ACTIVE]` | Auto-continue toward goal |

Both can run simultaneously without conflicts.

## Usage Examples

### Example 1: Test-Driven Loop
```markdown
---
iteration_count: 1
max_iterations: 15
completion_promise: "✅ All tests passing"
active: true
---

Fix failing tests in test_semantic_search.py
- Run pytest
- Analyze failures
- Fix issues
- Repeat until passing
```

### Example 2: Feature Implementation
```markdown
---
iteration_count: 1
max_iterations: 20
completion_promise: "Feature complete and tested"
active: true
---

Implement OAuth refresh token flow
1. Add refresh endpoint
2. Update token storage
3. Add auto-refresh logic
4. Write tests
5. Update docs
```

### Example 3: Debug Session
```markdown
---
iteration_count: 1
max_iterations: 12
completion_promise: "Bug fixed and verified"
active: true
---

Fix memory leak in LSP manager
- Profile memory usage
- Identify leak source
- Implement fix
- Verify with stress test
```

## Manual Control

### Start Loop
```bash
cp .stravinsky/continuation-loop.template.md .stravinsky/continuation-loop.md
# Edit with your goal and parameters
```

### Stop Loop
```bash
# Option 1: Delete state file
rm .stravinsky/continuation-loop.md

# Option 2: Set active flag
sed -i '' 's/active: true/active: false/' .stravinsky/continuation-loop.md

# Option 3: Include completion promise in response
# (Claude will detect it automatically)
```

### Adjust Max Iterations
```bash
# Increase if task is taking longer
sed -i '' 's/max_iterations: 10/max_iterations: 20/' .stravinsky/continuation-loop.md
```

## Architecture Details

### File Locations
- **Hook**: `.claude/hooks/stop_hook.py` (235 lines)
- **State**: `.stravinsky/continuation-loop.md` (YAML frontmatter)
- **Guide**: `.stravinsky/CONTINUATION_LOOP_GUIDE.md` (comprehensive docs)
- **Template**: `.stravinsky/continuation-loop.template.md` (quick start)
- **Tests**: `.stravinsky/test_continuation_loop.py` (6 test cases)

### Exit Codes
- **0**: Stop loop (normal completion)
- **2**: Continue loop (inject prompt, block completion)

### State Parsing
Simple YAML parser supports:
- Integers: `iteration_count: 5`
- Booleans: `active: true`
- Strings: `completion_promise: "text"`
- Comments: `# This is a comment`

### Constants
```python
CONTINUATION_LOOP_FILE = Path.cwd() / ".stravinsky" / "continuation-loop.md"
DEFAULT_MAX_ITERATIONS = 10
```

## Success Criteria

All requirements met:

- ✅ Create .claude/hooks/stop_hook.py with continuation logic
- ✅ Implement state file at .stravinsky/continuation-loop.md
- ✅ Set default max_iterations to 10
- ✅ Check existing todo_continuation.py to avoid conflicts
- ✅ Ensure Stop hook doesn't interfere with todo reminders
- ✅ Add completion promise detection
- ✅ No conflicts with todo_continuation.py (lines 74-82)
- ✅ No infinite loops (max_iterations enforced)
- ✅ No override of todo continuation messages

## Future Enhancements

Potential improvements (not yet implemented):

1. **Multiple Completion Conditions** - OR logic for promises
2. **Iteration Timeout** - Max time per iteration
3. **Progress Callbacks** - Notify on milestones
4. **Loop Templates** - Common task patterns
5. **TODO Integration** - Auto-create from pending todos
6. **Loop History** - Save completed loops for analysis

## Troubleshooting

### Loop Won't Start
- Verify state file exists: `ls -la .stravinsky/continuation-loop.md`
- Check YAML syntax (must have `---` delimiters)
- Ensure `active: true`

### Loop Stops Prematurely
- Check if completion promise appears in response
- Verify max_iterations is high enough
- Check if active changed to false

### Loop Won't Stop
- Verify completion promise text matches exactly
- Set `active: false` to force stop
- Delete state file as last resort

## References

- Stop hook implementation: `.claude/hooks/stop_hook.py`
- TODO continuation hook: `.claude/hooks/todo_continuation.py`
- User guide: `.stravinsky/CONTINUATION_LOOP_GUIDE.md`
- Template: `.stravinsky/continuation-loop.template.md`
- Tests: `.stravinsky/test_continuation_loop.py`

## Maintenance

**No maintenance required** - the implementation is complete and tested.

Future updates should:
1. Run test suite after changes: `python3 .stravinsky/test_continuation_loop.py`
2. Update this README with new features
3. Keep CONTINUATION_LOOP_GUIDE.md synchronized
4. Maintain backward compatibility with state file format
