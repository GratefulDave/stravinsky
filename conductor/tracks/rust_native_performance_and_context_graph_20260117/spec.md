# Track Specification: Rust Native Performance and Context Graph

## Overview
Implement a high-performance, robust "Hot Path" Context Graph in Rust. This system improves agent context retrieval by predicting related files. It combines **Temporal Coupling** (files that change together in Git) with **Static Analysis** (files that explicitly import each other) to filter out noise from "lazy commits."

## Objectives
1.  **High-Fidelity Context:** Provide agents with instantly relevant files (e.g., test files, utilities) when they focus on a module.
2.  **Noise Reduction:** Use Static Import Analysis (via `tree-sitter`) to verify Git temporal signals, preventing false positives from unrelated files committed together.
3.  **Safety & Control:** Implement a strict configuration toggle to completely disable the feature if it behaves unexpectedly.

## Scope
-   **In Scope:**
    -   `rust_native` extension enhancements.
    -   `tree-sitter` based import extraction for Python and TypeScript/JavaScript.
    -   Hybrid scoring algorithm (Git frequency + Static Import validation).
    -   Configuration management in `.stravinsky/model_config.yaml`.
    -   Integration with `find_code` tool.
-   **Out of Scope:**
    -   Full language support for C++/Go/Rust (initial focus on Py/TS).
    -   Persistent caching of the graph (initially computed on-demand or in-memory for the session).