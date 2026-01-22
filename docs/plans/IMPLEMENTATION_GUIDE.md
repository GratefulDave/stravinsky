# 7-Phase Orchestrator Implementation Guide

**STATUS**: Core state machine complete. This guide covers implementation details for the 7-phase orchestrator workflow.

## Overview

The Stravinsky orchestrator uses a formal state machine with 8 phases (commonly called the "7-phase workflow" with verification as the 8th phase). This guide provides implementation details for integrating with the state machine, creating TaskGraphs, and enforcing parallel execution.

## Quick Reference

### Source Files

| File | Purpose |
|------|---------|
| `mcp_bridge/orchestrator/state.py` | OrchestratorState, PHASE_REQUIREMENTS, VALID_TRANSITIONS |
| `mcp_bridge/orchestrator/enums.py` | OrchestrationPhase enum |
| `mcp_bridge/orchestrator/task_graph.py` | TaskGraph, DelegationEnforcer, ParallelExecutionError |

### Phase Sequence

```
CLASSIFY -> CONTEXT -> WISDOM (optional) -> PLAN <-> VALIDATE -> DELEGATE -> EXECUTE -> VERIFY
```

### Required Artifacts by Phase

| Phase | Required to Enter | Produced |
|-------|-------------------|----------|
| CLASSIFY | - | `query_classification` |
| CONTEXT | `query_classification` | `context_summary` |
| WISDOM | `context_summary` | (wisdom context) |
| PLAN | - | `plan.md` |
| VALIDATE | `plan.md` | `validation_result` |
| DELEGATE | `validation_result` | `delegation_targets`, `task_graph` |
| EXECUTE | `delegation_targets`, `task_graph` | `execution_result` |
| VERIFY | `execution_result` | (final output) |

---

## Part 1: Using OrchestratorState

### Basic Usage

```python
from mcp_bridge.orchestrator.state import OrchestratorState
from mcp_bridge.orchestrator.enums import OrchestrationPhase

# Create state machine
state = OrchestratorState()

# Register an artifact
state.register_artifact("query_classification", "implementation:auth-refactor")

# Transition to next phase
state.transition_to(OrchestrationPhase.CONTEXT)

# Check current phase
print(state.get_phase_display())  # "[Phase 2/8] Gathering codebase context"

# Get state summary
summary = state.get_summary()
```

### Configuration Options

```python
state = OrchestratorState(
    strict_mode=True,       # Enforce artifact requirements (default: True)
    enable_phase_gates=False,  # Require approval for transitions (default: False)
    max_critiques=3,        # Max PLAN/VALIDATE iterations (default: 3)
)
```

### Phase Gates (Interactive Mode)

```python
def get_user_approval():
    response = input("Proceed to next phase? (y/n): ")
    return response.lower() == "y"

state = OrchestratorState(
    enable_phase_gates=True,
    approver=get_user_approval
)

# Now transitions require approval
state.transition_to(OrchestrationPhase.CONTEXT)  # Prompts user
```

### Checking Transition Validity

```python
# Check without transitioning
can_go, error_msg = state.can_transition_to(OrchestrationPhase.CONTEXT)
if not can_go:
    print(f"Cannot transition: {error_msg}")

# Get missing artifacts
missing = state.get_missing_artifacts(OrchestrationPhase.CONTEXT)
print(f"Need to register: {missing}")
```

### Handling the Critique Loop

```python
# PLAN -> VALIDATE -> PLAN (critique) -> VALIDATE -> DELEGATE
while state.current_phase in [OrchestrationPhase.PLAN, OrchestrationPhase.VALIDATE]:
    if state.current_phase == OrchestrationPhase.PLAN:
        plan = generate_plan()
        state.register_artifact("plan.md", plan)
        state.transition_to(OrchestrationPhase.VALIDATE)
    else:
        validation = validate_plan(state.get_artifact("plan.md"))
        if validation.passed:
            state.register_artifact("validation_result", validation.summary)
            state.transition_to(OrchestrationPhase.DELEGATE)
        else:
            # Return to PLAN for revision (max 3 times)
            state.transition_to(OrchestrationPhase.PLAN)
```

---

## Part 2: Creating TaskGraphs

### Basic TaskGraph

```python
from mcp_bridge.orchestrator.task_graph import TaskGraph, Task, TaskStatus

# Create empty graph
graph = TaskGraph()

# Add tasks
graph.add_task(
    task_id="find_auth",
    description="Find authentication implementations in codebase",
    agent_type="explore",
    dependencies=[]  # No dependencies = Wave 1
)

graph.add_task(
    task_id="find_tests",
    description="Find related test files",
    agent_type="explore",
    dependencies=[]  # No dependencies = Wave 1
)

graph.add_task(
    task_id="analyze",
    description="Analyze test coverage for auth module",
    agent_type="dewey",
    dependencies=["find_auth", "find_tests"]  # Depends on Wave 1 = Wave 2
)
```

### Creating from Dictionary

```python
task_dict = {
    "search_imports": {
        "description": "Search for import statements",
        "agent_type": "explore",
        "depends_on": []
    },
    "search_usages": {
        "description": "Find function usages",
        "agent_type": "explore",
        "depends_on": []
    },
    "summarize": {
        "description": "Summarize findings",
        "agent_type": "dewey",
        "depends_on": ["search_imports", "search_usages"]
    }
}

graph = TaskGraph.from_dict(task_dict)
```

### Getting Execution Waves

```python
# Get groups of tasks that can run in parallel
waves = graph.get_independent_groups()

for i, wave in enumerate(waves):
    print(f"Wave {i + 1}:")
    for task in wave:
        print(f"  - {task.id}: {task.description} ({task.agent_type})")

# Output:
# Wave 1:
#   - search_imports: Search for import statements (explore)
#   - search_usages: Find function usages (explore)
# Wave 2:
#   - summarize: Summarize findings (dewey)
```

### Task Status Management

```python
# Mark task as spawned (with agent task ID)
graph.mark_spawned("search_imports", "agent_task_abc123")

# Mark task as completed
graph.mark_completed("search_imports")

# Mark task as failed
graph.mark_failed("search_imports")

# Get ready tasks (pending with satisfied dependencies)
ready = graph.get_ready_tasks()
```

---

## Part 3: Enforcing Parallel Execution

### Using DelegationEnforcer

```python
from mcp_bridge.orchestrator.task_graph import (
    TaskGraph, DelegationEnforcer, ParallelExecutionError
)

# Create graph and enforcer
graph = TaskGraph.from_dict(task_dict)
enforcer = DelegationEnforcer(
    task_graph=graph,
    parallel_window_ms=500,  # Tasks must spawn within 500ms
    strict=True              # Raise errors on violations
)

# Get current wave tasks
current_wave = enforcer.get_current_wave()
print(f"Must spawn these tasks in parallel: {[t.id for t in current_wave]}")
```

### Recording Task Spawns

```python
import time

# Spawn tasks and record them
for task in current_wave:
    # Validate spawn is allowed
    is_valid, error = enforcer.validate_spawn(task.id)
    if not is_valid:
        raise ValueError(error)

    # Actually spawn the agent (your implementation)
    agent_task_id = spawn_agent(task.agent_type, task.description)

    # Record the spawn
    enforcer.record_spawn(task.id, agent_task_id)

# Check parallel compliance (will raise if tasks weren't spawned together)
is_compliant, error = enforcer.check_parallel_compliance()
if not is_compliant:
    print(f"WARNING: {error}")
```

### Advancing Waves

```python
# After all tasks in wave complete, advance to next wave
enforcer.mark_task_completed("search_imports")
enforcer.mark_task_completed("search_usages")

# This automatically advances to Wave 2 when all Wave 1 tasks complete
# Get new current wave
next_wave = enforcer.get_current_wave()
```

### Getting Enforcement Status

```python
status = enforcer.get_enforcement_status()
print(status)
# {
#     "current_wave": 1,
#     "total_waves": 2,
#     "current_wave_tasks": ["search_imports", "search_usages"],
#     "spawn_batch": [("search_imports", 1705954321.123), ("search_usages", 1705954321.145)],
#     "task_statuses": {
#         "search_imports": "spawned",
#         "search_usages": "spawned",
#         "summarize": "pending"
#     }
# }
```

### Handling ParallelExecutionError

```python
try:
    enforcer.advance_wave()
except ParallelExecutionError as e:
    # Tasks were not spawned in parallel (time spread > 500ms)
    print(f"Parallel violation: {e}")
    # Options:
    # 1. Log warning and continue (non-strict mode)
    # 2. Abort and retry the wave
    # 3. Report to orchestrator for human review
```

---

## Part 4: Complete Workflow Example

```python
from mcp_bridge.orchestrator.state import OrchestratorState
from mcp_bridge.orchestrator.enums import OrchestrationPhase
from mcp_bridge.orchestrator.task_graph import (
    TaskGraph, DelegationEnforcer, ParallelExecutionError
)

def run_orchestration(user_query: str):
    # Initialize state machine
    state = OrchestratorState(strict_mode=True)

    # Phase 1: CLASSIFY
    classification = classify_query(user_query)
    state.register_artifact("query_classification", classification)
    state.transition_to(OrchestrationPhase.CONTEXT)

    # Phase 2: CONTEXT
    context = gather_context(classification)
    state.register_artifact("context_summary", context)
    state.transition_to(OrchestrationPhase.WISDOM)

    # Phase 3: WISDOM (optional - may skip if no wisdom file)
    try:
        wisdom = load_wisdom()
        state.transition_to(OrchestrationPhase.PLAN)
    except FileNotFoundError:
        # Skip wisdom, go directly to PLAN
        state.transition_to(OrchestrationPhase.PLAN)

    # Phase 4-5: PLAN/VALIDATE loop
    while state.critique_count < state.max_critiques:
        # Phase 4: PLAN
        plan = create_plan(classification, context, wisdom)
        state.register_artifact("plan.md", plan)
        state.transition_to(OrchestrationPhase.VALIDATE)

        # Phase 5: VALIDATE
        validation = validate_plan(plan)
        if validation.passed:
            state.register_artifact("validation_result", validation.summary)
            break
        else:
            state.transition_to(OrchestrationPhase.PLAN)  # Critique loop

    # Phase 6: DELEGATE
    state.transition_to(OrchestrationPhase.DELEGATE)
    task_dict = plan_to_tasks(state.get_artifact("plan.md"))
    graph = TaskGraph.from_dict(task_dict)
    state.register_artifact("delegation_targets", str(list(task_dict.keys())))
    state.register_artifact("task_graph", graph.to_dict())

    # Phase 7: EXECUTE with parallel enforcement
    state.transition_to(OrchestrationPhase.EXECUTE)
    enforcer = DelegationEnforcer(task_graph=graph, strict=True)

    results = {}
    while True:
        current_wave = enforcer.get_current_wave()
        if not current_wave:
            break  # All waves complete

        # Spawn all tasks in wave (must be parallel)
        for task in current_wave:
            agent_id = spawn_agent(task.agent_type, task.description)
            enforcer.record_spawn(task.id, agent_id)

        # Wait for wave completion
        for task in current_wave:
            result = wait_for_agent(task.task_id)
            results[task.id] = result
            enforcer.mark_task_completed(task.id)

    state.register_artifact("execution_result", str(results))

    # Phase 8: VERIFY
    state.transition_to(OrchestrationPhase.VERIFY)
    final_output = synthesize_results(results)

    return final_output
```

---

## Part 5: Hook Integration

### Hook Files for State Machine Integration

The state machine integrates with Claude Code hooks at key points:

#### UserPromptSubmit Hook (CLASSIFY Phase)

```python
#!/usr/bin/env python3
# hooks/classify_intent.py
import json
import sys
from mcp_bridge.orchestrator.state import OrchestratorState
from mcp_bridge.orchestrator.enums import OrchestrationPhase

def main():
    hook_input = json.load(sys.stdin)
    prompt = hook_input.get("prompt", "")

    # Create or load state
    state = load_or_create_state()

    # Classify the query
    if "implement" in prompt.lower() or "build" in prompt.lower():
        classification = "implementation"
    elif "debug" in prompt.lower() or "fix" in prompt.lower():
        classification = "debugging"
    else:
        classification = "research"

    state.register_artifact("query_classification", classification)
    save_state(state)

    # Inject phase context into prompt
    augmented = f"[{state.get_phase_display()}]\n\n{prompt}"
    print(augmented)
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

#### PreToolUse Hook (EXECUTE Phase Enforcement)

```python
#!/usr/bin/env python3
# hooks/enforce_delegation.py
import json
import sys
from pathlib import Path

STRAVINSKY_MODE = Path.home() / ".stravinsky_mode"
BLOCKED_TOOLS = ["Read", "Grep", "Bash", "Edit", "Write"]

def main():
    hook_input = json.load(sys.stdin)
    tool_name = hook_input.get("tool_name", "")

    if not STRAVINSKY_MODE.exists():
        return 0  # Not in stravinsky mode

    if tool_name in BLOCKED_TOOLS:
        print(json.dumps({
            "decision": "block",
            "message": f"Tool '{tool_name}' blocked in EXECUTE phase. Use agent_spawn for delegation."
        }))
        return 2  # Hard block

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

#### PostToolUse Hook (VERIFY Phase)

```python
#!/usr/bin/env python3
# hooks/collect_results.py
import json
import sys

def main():
    hook_input = json.load(sys.stdin)
    tool_name = hook_input.get("tool_name", "")
    tool_result = hook_input.get("tool_result", {})

    if tool_name == "agent_output":
        # Collect agent results for VERIFY phase
        task_id = tool_result.get("task_id")
        output = tool_result.get("output")

        # Store for later synthesis
        store_agent_result(task_id, output)

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## Part 6: Troubleshooting

### Common Errors

#### "Missing artifacts for X phase"

**Cause**: Attempting to transition without required artifacts.

**Solution**: Register the required artifacts before transitioning.

```python
# Check what's missing
missing = state.get_missing_artifacts(OrchestrationPhase.CONTEXT)
print(f"Need to register: {missing}")

# Register the missing artifact
state.register_artifact("query_classification", "implementation")
```

#### "Invalid transition: X -> Y"

**Cause**: Attempting an invalid phase transition.

**Solution**: Follow the valid transition paths.

```python
# Check valid transitions from current phase
from mcp_bridge.orchestrator.state import VALID_TRANSITIONS
valid = VALID_TRANSITIONS[state.current_phase]
print(f"Can transition to: {[p.value for p in valid]}")
```

#### "Max critique iterations reached"

**Cause**: PLAN/VALIDATE loop exceeded 3 iterations.

**Solution**: The plan must proceed to DELEGATE. Improve validation criteria or accept current plan.

```python
# Check critique count
print(f"Critique count: {state.critique_count}/{state.max_critiques}")

# Force proceed (validation must pass or be accepted)
state.register_artifact("validation_result", "accepted_with_warnings")
state.transition_to(OrchestrationPhase.DELEGATE)
```

#### ParallelExecutionError

**Cause**: Independent tasks were not spawned within the 500ms window.

**Solution**: Spawn all tasks in a wave together, not sequentially.

```python
# WRONG: Sequential spawning
for task in wave:
    spawn_agent(task)  # Each spawn takes time
    time.sleep(1)      # Definitely violates window

# CORRECT: Parallel spawning
import asyncio

async def spawn_wave(wave):
    tasks = [spawn_agent_async(t) for t in wave]
    return await asyncio.gather(*tasks)
```

---

## Part 7: Testing

### Unit Testing State Transitions

```python
import pytest
from mcp_bridge.orchestrator.state import OrchestratorState
from mcp_bridge.orchestrator.enums import OrchestrationPhase

def test_valid_transition():
    state = OrchestratorState()
    state.register_artifact("query_classification", "test")
    state.transition_to(OrchestrationPhase.CONTEXT)
    assert state.current_phase == OrchestrationPhase.CONTEXT

def test_invalid_transition():
    state = OrchestratorState()
    with pytest.raises(ValueError, match="Invalid transition"):
        state.transition_to(OrchestrationPhase.EXECUTE)

def test_missing_artifact():
    state = OrchestratorState()
    with pytest.raises(ValueError, match="Missing artifacts"):
        state.transition_to(OrchestrationPhase.CONTEXT)
```

### Testing Parallel Enforcement

```python
import time
from mcp_bridge.orchestrator.task_graph import (
    TaskGraph, DelegationEnforcer, ParallelExecutionError
)

def test_parallel_compliance():
    graph = TaskGraph()
    graph.add_task("a", "Task A", "explore")
    graph.add_task("b", "Task B", "explore")

    enforcer = DelegationEnforcer(
        task_graph=graph,
        parallel_window_ms=100,
        strict=True
    )

    # Spawn both quickly (within window)
    enforcer.record_spawn("a", "agent_a")
    enforcer.record_spawn("b", "agent_b")

    is_compliant, _ = enforcer.check_parallel_compliance()
    assert is_compliant

def test_parallel_violation():
    graph = TaskGraph()
    graph.add_task("a", "Task A", "explore")
    graph.add_task("b", "Task B", "explore")

    enforcer = DelegationEnforcer(
        task_graph=graph,
        parallel_window_ms=100,
        strict=True
    )

    # Spawn with delay (exceeds window)
    enforcer.record_spawn("a", "agent_a")
    time.sleep(0.2)  # 200ms > 100ms window
    enforcer.record_spawn("b", "agent_b")

    with pytest.raises(ParallelExecutionError):
        enforcer.advance_wave()
```

---

## Summary

The 7-phase orchestrator provides:

1. **Formal State Machine**: Strict phase transitions with artifact requirements
2. **TaskGraph**: DAG-based task dependency management
3. **DelegationEnforcer**: Hard enforcement of parallel execution
4. **Hook Integration**: Seamless integration with Claude Code hooks
5. **Critique Loop**: Built-in plan refinement with iteration limits

For architecture overview, see [architecture_workflow.md](../architecture/architecture_workflow.md).
