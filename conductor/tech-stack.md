# Technology Stack

## Core Language & Runtime
- **Python 3.12+**: The primary programming language for the bridge and server components.
- **Rust (2021 edition)**: Used for performance-critical utilities including search, AST-aware chunking, and file watching.

## Package & Environment Management
- **uv**: Fast Python package installer and resolver used for dependency management and environment isolation.

## Core Frameworks & Libraries
- **Model Context Protocol (MCP) SDK**: The foundation for building the bridge, facilitating communication between LLMs and local tools.
- **FastAPI / Uvicorn**: Used to build and serve the high-performance asynchronous API for the MCP bridge.
- **Pydantic**: Provides data validation and settings management using Python type annotations.

## Native Integration
- **PyO3 / Maturin**: Facilitates seamless Python-Rust bindings, allowing high-performance native code to be called directly from Python.
- **Tree-sitter**: High-performance AST parsing for code chunking.
- **Notify**: Efficient, native file system watching.

## Development & Testing
- **Pytest**: The primary testing framework for unit and integration tests.
- **Ruff**: Fast Python linter and code formatter.
- **MyPy**: Static type checker for Python.

## Architecture
- **MCP Bridge Server**: A local-first architecture designed to bridge the gap between AI models and local development environments.
