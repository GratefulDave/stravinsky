# Product Guide: Stravinsky (Phase 3 - "Opencode Alignment")

## Initial Concept
Stravinsky is an avant-garde MCP bridge for Claude Code, evolving into a sophisticated orchestration layer that mirrors the power and granularity of `oh-my-opencode`. It provides multi-model access (Gemini, GPT) through secure OAuth, now enhanced with advanced agentic workflows and architectural patterns inspired by the best-in-class orchestration logic of `oh-my-opencode`.

## Vision & Goals
The goal is to transform Stravinsky from a model-invocation bridge into a comprehensive AI development platform. We will adopt the "Opencode" philosophy—granular, specialized agents and robust hook-based orchestration—while maintaining Stravinsky's identity as the primary multi-model gateway for Claude Code.

## Key Focus Areas

### 1. Granular Agent Roles (Inspired by oh-my-opencode)
*   **Specialization:** Expand beyond generic agents to include highly specific roles (e.g., dedicated Architect, QA, and Refactoring agents).
*   **System Prompts:** Adopt the prompt engineering structure and specific instruction sets from `oh-my-opencode` to ensure high-fidelity task execution.
*   **Inter-Agent Communication:** Implement sophisticated hand-off protocols and inter-agent messaging to enable complex, multi-step collaboration.

### 2. Hybrid Hook Architecture
*   **Architectural Adaptation:** Adapt the core orchestration logic of `oh-my-opencode` hooks (e.g., delegation triggers, lifecycle management) to control Stravinsky's specialist agents.
*   **Pre-Tool Use Enforcement:** Strengthen the boundary between the orchestrator and specialists using advanced hook patterns to prevent redundant or out-of-scope work.
*   **Selective Porting:** Identify and implement high-value hooks from `oh-my-opencode` that enhance session awareness and task persistence.

### 3. Toolset Expansion & Integration
*   **Gap Analysis:** Conduct a thorough analysis of tools in `oh-my-opencode` (specifically around file manipulation and system introspection) and port those that fill functional gaps.
*   **Native Integration:** Ensure all new tools are seamlessly integrated into Stravinsky's multi-model backbone, leveraging Gemini or GPT-4o as needed for high-complexity operations.

### 4. Configuration & Standards
*   **Unified Settings:** Move towards a standardized configuration structure (e.g., `settings.json` and agent manifests) that aligns with modern Claude Code orchestration conventions.
*   **OAuth Backbone:** Maintain and further stabilize Stravinsky's secure OAuth flow and token management as the underlying infrastructure for all external model interactions.

## Target User
Senior software engineers and AI enthusiasts using Claude Code who require a powerful, extensible, and multi-model orchestration environment that rivals the depth of specialized open-source tools.
