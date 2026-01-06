# Verify - Post-Implementation Verification

Run comprehensive verification after code changes to ensure quality.

## Usage

```
/verify [files or scope]
```

## Verification Steps

Execute these checks in order:

### 1. Get Modified Files
```bash
git diff --name-only HEAD
git diff --name-only --cached
```

### 2. Run LSP Diagnostics
For each modified Python/TypeScript file, check for errors:
- Use `lsp_diagnostics` tool on each file
- Report any errors or warnings

### 3. Run Tests (if applicable)
```bash
# Python
python -m pytest --tb=short -q

# Node/TypeScript
npm test || yarn test || pnpm test
```

### 4. Run Build/Lint (if applicable)
```bash
# Python
ruff check . || python -m flake8

# TypeScript
npm run build || tsc --noEmit
npm run lint || eslint .
```

### 5. Verify Todo Completion
Check that all todos from the current session are marked complete.

## Instructions

Run verification on recent changes:

1. Get list of modified files from git
2. Run lsp_diagnostics on each modified file
3. If tests exist, run them
4. If build/lint configured, run them
5. Report results with pass/fail status

If any step fails, report the specific errors and suggest fixes.

$ARGUMENTS
