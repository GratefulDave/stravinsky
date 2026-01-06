# Stravinsky Workflow Architecture: Hooks & Agents

This document outlines the high-level architecture of Stravinsky's orchestration system, focusing on how Claude Code hooks and specialized agents interact to achieve parallel execution and rigorous delegation.

## Overview

Stravinsky implements an "Enforced Parallelism" pattern inspired by **oh-my-opencode**. It leverages Claude Code's native hook system to gate tools and enforce delegation to specialized sub-agents.

## Core Components

### 1. Specialized Agents (The Workers)
Specialized agents are configured in `.claude/agents/` and use specialized models via MCP tools (`invoke_gemini`, `invoke_openai`).
- **explore**: Code search specialist (Gemini 3 Flash, always async).
- **dewey**: Documentation research (Gemini 3 Flash, always async).
- **frontend**: UI/UX implementer (Gemini 3 Pro High, blocking).
- **delphi**: Strategic advisor (GPT-5.2 Medium, blocking).
- **stravinsky**: The primary orchestrator (Sonnet 4.5).

### 2. Native Hooks (The Enforcers)
Hooks in `.claude/hooks/` gate execution and enforce workflow rules.

#### A. UserPromptSubmit (Pre-emptive)
- **`parallel_execution.py`**: Detects implementation intent and injects "Parallel Execution Mode" instructions into the user prompt. This ensures the assistant is aware of delegation rules before it starts reasoning.
- **`context.py`**: Injects situational awareness (Git status, active TODOs).

#### B. PreToolUse (Gating)
- **`stravinsky_mode.py`**: Checks for the `~/.stravinsky_mode` marker. If active, it blocks direct file operations (Read, Grep, Bash, Edit) with exit code 2, forcing delegation to `Task` agents.
- **`task_validator.py`**: Ensures `Task` calls follow the correct parallel-first pattern.

#### C. PostToolUse (Verification & Continuation)
- **`todo_delegation.py`**: Fires after `TodoWrite`. If multiple independent TODOs are created, it enforces immediate fan-out to parallel agents by failing with exit code 2.
- **`todo_continuation.py`**: Re-injects pending TODOs into the prompt to ensure continuity.

### 3. State Management
- **Marker File**: `~/.stravinsky_mode` indicates that the orchestrator is in control.
- **TODO List**: Maintained via `TodoWrite` to track progress across turns.

---

## Workflow Lifecycle

### Phase 1: Intent Detection
1. User provides a complex prompt.
2. `UserPromptSubmit` hook detects "Implementation" intent.
3. Hook injects parallel execution rules and activates Stravinsky mode.

### Phase 2: Planning & Fan-Out
1. Orchestrator receives prompt + injected rules.
2. Orchestrator creates a detailed plan using `TodoWrite`.
3. `PostToolUse` (after `TodoWrite`) checks if parallel delegation is required.
4. If yes, it enforces immediate spawning of parallel agents.
5. Orchestrator spawns multiple agents in a single turn.

### Phase 3: Execution (Parallel)
1. Specialists (explore, dewey) run asynchronously.
2. Orchestrator continues to manage the high-level loop.
3. `PreToolUse` blocks the orchestrator from doing "low-level" work directly.

### Phase 4: Synthesis & Implementation
1. Orchestrator collects results from specialists.
2. If architecture is complex, it consults `delphi`.
3. Implementation tasks are delegated to specific specialists (e.g., `frontend` for UI).
4. Orchestrator verifies results and marks TODOs as complete.

---

## Technical Constraints & Design Choices

### Native `Task` vs. MCP `agent_spawn`
- **Native `Task`**: Preferred for standard delegation. Note: True parallelism in native tasks requires `run_in_background: true` (verify support in current Claude Code version).
- **MCP `agent_spawn`**: Used for true asynchronous background work that outlasts a single turn, or when deep nesting is required.

### The "Exit Code 2" Strategy
- Exit code 2 is used to signal a **Hard Block**. It forces Claude to reconsider its last action and follow the enforced pattern (e.g., "Don't just write code, delegate first").

### Async vs. Background
- **Async (Task + background)**: Used for discovery/research where the orchestrator can keep working.
- **Background (MCP agent_spawn)**: Used for long-running verification or independent sub-tasks.
- **Blocking**: Used for tasks that gate the next step (e.g., a critical architecture decision from Delphi).
