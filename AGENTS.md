# AGENTS.md

## Scope

This file applies to the entire repository.

## Sources

- `README.md`
- `INSTALL.md`
- `docs/guides/INSTALL.md`
- `tests/README.md`
- `tests/README_LSP_TESTS.md`
- `tests/README_AUTO_INDEXING_TESTS.md`
- `tests/README_QUERY_CLASSIFICATION.md`
- `pyproject.toml`
- `CLAUDE.md`

## Repository Summary

Stravinsky is an MCP bridge for Claude Code that orchestrates multi-model
requests (Gemini, OpenAI) with OAuth authentication, tool routing, and a set of
specialized agents. The primary Python package lives in `mcp_bridge/` with
tests in `tests/`.

## Tooling and Environment

- Supported Python versions: 3.11–3.13 (`requires-python = ">=3.11,<3.14"`).
- Use `uv` for installs and execution.
- Use `uv pip` for installing packages and editable installs.
- Use `uv add` when adding new dependencies.
- Use `uv run` when running Python scripts or pytest.

## Setup and Install

- User-level MCP install (recommended):
  - `claude mcp add --scope user stravinsky -- uvx --python python3.13 stravinsky@latest`
- Quick start in docs (same flow, without explicit Python pin):
  - `claude mcp add --scope user stravinsky -- uvx stravinsky@latest`
- Global tool install (alternative from INSTALL.md):
  - `uv tool install stravinsky`
  - `claude mcp add --scope user stravinsky -- stravinsky`
- Development install (repo-local):
  - `uv pip install -e .`
- Alternative dev install used in docs:
  - `uv tool install --editable . --force`

## Verification

- Check MCP registration:
  - `claude mcp list`
- Check CLI version:
  - `stravinsky --version`

## Authentication

- Login:
  - `stravinsky-auth login gemini`
  - `stravinsky-auth login openai`
- Status:
  - `stravinsky-auth status`
- Logout:
  - `stravinsky-auth logout gemini`
  - `stravinsky-auth logout openai`
- API key fallback via `.env`:
  - `GEMINI_API_KEY=...` or `GOOGLE_API_KEY=...`

## Running

- Start the MCP server:
  - `stravinsky`
- Optional proxy mode:
  - `stravinsky-proxy`
  - `STRAVINSKY_USE_PROXY=true`

## Build

- Package build (Hatchling backend):
  - `uv build`

## Linting and Type Checking

- Ruff lint:
  - `uv run ruff check .`
- Ruff lint with autofix:
  - `uv run ruff check . --fix`
- Mypy (strict):
  - `uv run mypy mcp_bridge`

## Test Commands

### Core Suites

- Run all tests:
  - `uv run pytest tests/`
- File watcher no-index regression test:
  - `uv run python tests/test_file_watcher_no_index.py`

### LSP Tooling Tests

- Full LSP test suite:
  - `uv run pytest tests/test_lsp_tools.py -v`
- Single LSP test:
  - `uv run pytest tests/test_lsp_tools.py::test_lsp_hover_success -v`
- LSP coverage report:
  - `uv run pytest tests/test_lsp_tools.py --cov=mcp_bridge.tools.lsp --cov-report=html`
- Filter LSP error handling tests:
  - `uv run pytest tests/test_lsp_tools.py -k "invalid or error or timeout" -v`

### Auto-Indexing Tests

- Manual end-to-end test:
  - `uv run python tests/manual_test_auto_indexing.py`
- Unit tests:
  - `uv run pytest tests/test_auto_indexing.py -v`
  - `uv run pytest tests/test_file_watcher.py -v`
- All tests plus manual script (docs example):
  - `uv run pytest tests/`
  - `uv run python tests/manual_test_auto_indexing.py`

### Query Classification Tests

- Install pytest if needed:
  - `uv pip install pytest`
- Query classification test suite:
  - `uv run pytest tests/test_query_classification.py -v`

## Test Prerequisites

- Auto-indexing and semantic tests require Ollama:
  - `ollama serve`
  - `ollama pull nomic-embed-text`

## Semantic Search Notes

- Run `semantic_index(project_path=".")` before `start_file_watcher()`.
- Default vector store location: `~/.stravinsky/vectordb/<project>_<provider>/`.

## Code Style and Quality Settings

- Ruff:
  - Line length: 100
  - Target version: Python 3.11 (`py311`)
  - Lint rules: `E`, `F`, `I`, `UP`, `B`, `SIM`
  - Ignored rules: `E501`
- Mypy:
  - `strict = true`
  - `python_version = 3.11`
  - `warn_return_any = true`
  - `warn_unused_ignores = true`

## Cursor and Copilot Rules

No `.cursorrules`, `.cursor/rules*`, or `.github/copilot-instructions.md` files
were found in this repository.
