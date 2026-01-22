# Track Specification: 7-Phase Orchestrator & Output Hygiene

## Overview
Implement a rigorous 7-phase orchestration lifecycle for Stravinsky agents to enforce high-quality results, mirroring OMO's best practices. This includes "Model Variant" routing (Smart vs. Fast models), strict phase gates (Plan before Code), and a native Rust-based output compaction system to maintain context hygiene.

## Core Objectives
1.  **7-Phase Workflow:** Enforce the following lifecycle for complex tasks:
    1.  **Classify & Scope**
    2.  **Context Gathering**
    3.  **Wisdom Injection** (Read `wisdom.md`)
    4.  **Strategic Planning** (Critique Loop included)
    5.  **Validation** (Check plan against rules)
    6.  **Delegation/Execution** (Model Variant routing)
    7.  **Synthesis & Verification**
2.  **Model Variants:** Route "Thinking" phases (Plan, Validate) to high-reasoning models (e.g., Claude 3.5 Sonnet/Opus) and "Execution" phases to faster models.
3.  **Output Hygiene (Native Rust):** Implement high-performance output truncation and compaction in Rust:
    *   **Logs/Streams:** Auto-tail (Head + Tail).
    *   **Search/Lists:** Smart summarization.
    *   **File Reads:** Truncate with offset/limit support.
4.  **UX:** Autonomous execution with clear phase visualization (`[Phase X/7]`).
5.  **Intelligent Query Routing:** Implement the classification logic defined in `QUERY_CLASSIFICATION_GUIDE.md`, prioritizing **Semantic Search** for conceptual/hybrid queries while maintaining GREP/AST for structural/exact matches.
6.  **Robust Parallel Delegation:** Implement "State-Based Reinforcement" (Option C from Gap Analysis) to maintain parallel execution capabilities throughout extended sessions.

## Functional Requirements
*   **Orchestrator Class:** A central state machine managing the current phase and ensuring phase artifacts (e.g., `plan.md`) exist before transitioning.
*   **Wisdom Integration:** System must check for and read `.stravinsky/wisdom.md` into the context window at the start of the Planning phase.
*   **Critique Step:** The Planning phase must include a self-reflection prompt: "List 3 ways this plan could fail."
*   **Native Truncator:** A Rust FFI function `compact_output(content, type)` that handles text processing efficiently.
*   **Manual Phase Gates:** Optional configuration toggle `enable_phase_gates` to require user confirmation between phases.
*   **Query Classifier:** Implementation of `QUERY_CLASSIFICATION_GUIDE.md` logic (Exact vs Structural vs Semantic) to drive the **Context Gathering** phase.
*   **Delegation State Tracker:** Persistent tracking of task dependencies and tool usage to enforce parallel execution as per `GAP_ANALYSIS_PARALLEL_DELEGATION.md`.

## Non-Functional Requirements
*   **Performance:** Truncation must happen in <1ms overhead (Rust).
*   **Autonomy:** Default to full autonomy; pause only on critical errors.
*   **Reuse:** Leverage existing `LSPManager` and `ModelProxy` where applicable.

## Out of Scope
*   Interactive TUI (Dashboard) - Handled in a separate track.
*   Persistent state between reboots (Phase 1 focus).
