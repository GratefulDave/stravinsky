# Specification: Stravinsky Orchestration & Routing Refactor

## 1. Overview
Refactor the Stravinsky `mcp_bridge` to strictly implement the "Sisyphus" 7-Phase development process. This involves centralizing model routing configuration, enforcing specific model assignments (e.g., Claude 4.5 Opus for orchestration, Gemini 3 Flash for exploration), implementing parallel agent delegation, and standardizing CLI output.

## 2. Functional Requirements

### 2.1 Model Routing & Configuration
*   **Centralization:** Remove all hardcoded model routing from `mcp_bridge/tools/agent_manager.py`.
*   **Config Source:** Ensure `mcp_bridge/routing/config.py` is the single source of truth.
*   **Strict Mappings:** Enforce the following agent-to-model map:
    *   **Orchestrator (`stravinsky`, `planner`):** Claude 4.5 Opus
    *   **Strategy/Oracle (`delphi`):** OpenAI GPT-5.2 High
    *   **Refactor/Debug (`debugger`, `code-reviewer`):** OpenAI GPT-5.2 Codex
    *   **UI/UX (`frontend`):** Gemini 3 Pro
    *   **Explore/Context (`explore`, `dewey`, `document_writer`, `multimodal`, `comment_checker`):** Gemini 3 Flash
    *   **Coordination (`research-lead`, `implementation-lead`, `momus`):** Claude 4.5 Sonnet
    *   **Semantic Search (Tool):** Ollama (nomic-embed-text)

### 2.2 Sisyphus 7-Phase Orchestration
*   Update `mcp_bridge/prompts/stravinsky.py` to enforce this loop:
    1.  **Recon:** Parallel spawning of `explore` agents.
    2.  **Refactor:** Delegation to `debugger` (Codex) using LSP.
    3.  **UI/UX:** Delegation to `frontend` (Gemini Pro).
    4.  **Strategy:** Dual-Model Architecture generation (see 2.3).
    5.  **Subagents:** Recursive spawning for complex tasks.
    6.  **Cleanup:** Automated code hygiene via `comment_checker`.
    7.  **Loop:** Iterative execution until TODO completion.

### 2.3 Dual-Model Architecture Strategy
*   Implement a specific workflow for high-level architecture requests:
    1.  Spawn `planner` (Opus) to generate "Plan A".
    2.  Spawn `delphi` (GPT-5.2 High) to generate "Plan B" (Critique/Alternative).
    3.  `stravinsky` (Opus) synthesizes the final plan from both inputs.

### 2.4 Execution & Parallelism
*   **Parallel Delegation:** Update `agent_spawn` to support non-blocking execution.
*   **Default Behavior:** Independent tasks (especially `explore` and `dewey`) must run in parallel by default.

### 2.5 Logging & Display
*   **Format:** Enforce strict output format: `agent/modelname/task('summary')`.
*   **Cleanup:** Remove existing emojis and verbose status text from `agent_manager.py`.

## 3. Non-Functional Requirements
*   **Infrastructure:** Must retain and use the existing Proxy Gateway, Rust tools (`rust_native`), and Agentic MCPs.
*   **Performance:** Agent spawning must be low-latency.

## 4. Out of Scope
*   Implementation of DeepSeek models (explicitly excluded).