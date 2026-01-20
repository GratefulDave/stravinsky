# Ralph Loop Implementation

## Objective
Implement an iterative, self-correcting development loop ("Ralph Loop") that allows agents to:
1.  Attempt a task.
2.  Verify the result (run tests/linter).
3.  Analyze errors.
4.  Retry/Fix automatically.
5.  Repeat until success or max iterations.

## Components

### 1. `ralph_loop.py` (Tool/Script)
- **Input**: `task`, `verification_command`, `max_iterations`.
- **Logic**:
    ```python
    while iteration < max_iterations:
        # 1. Execute (or Fix)
        agent_spawn(prompt=current_prompt)
        
        # 2. Verify
        result = run_shell_command(verification_command)
        
        # 3. Check
        if result.exit_code == 0:
            return "Success"
            
        # 4. Refine
        current_prompt = f"Previous attempt failed with:\n{result.stderr}\n\nFix the code."
    ```

### 2. `/ralph` Command
- Hook into `.claude/commands/ralph.md`.
- trigger: `ralph_loop(task="...", verify="...")`.

### 3. State Management
- Persist loop state to `.stravinsky/ralph_state.json` to survive session crashes.

## Integration
- Use `agent_manager.spawn_async` for execution.
- Use `run_shell_command` for verification.

## Success Criteria
- User runs `/ralph "Fix bug X" --verify "pytest test_bug.py"`
- System loops 3 times, fixes bug, returns success.