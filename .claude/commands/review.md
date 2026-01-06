# Review - Code Review Recent Changes

Perform a thorough code review on recent changes before committing.

## Usage

```
/review [scope: staged|unstaged|branch|file]
```

Default: Reviews both staged and unstaged changes.

## Review Checklist

### Security
- [ ] No hardcoded secrets or credentials
- [ ] Input validation on user data
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] No command injection vulnerabilities

### Performance
- [ ] No N+1 query patterns
- [ ] Appropriate use of caching
- [ ] No unnecessary loops or iterations
- [ ] Efficient data structures

### Code Quality
- [ ] Clear, descriptive names
- [ ] Single responsibility principle
- [ ] No code duplication
- [ ] Appropriate error handling
- [ ] No commented-out code

### Testing
- [ ] New code has tests
- [ ] Edge cases covered
- [ ] Tests are meaningful (not just coverage)

## Instructions

Review recent code changes:

1. Get the diff:
```bash
git diff HEAD          # unstaged changes
git diff --cached      # staged changes
```

2. Analyze each changed file for:
   - Security vulnerabilities (OWASP top 10)
   - Performance issues
   - Code style and maintainability
   - Missing error handling
   - Missing tests

3. Provide specific, actionable feedback:
   - File and line number
   - Issue description
   - Suggested fix

4. Categorize issues by severity:
   - CRITICAL: Must fix before merge
   - WARNING: Should fix/m
   - SUGGESTION: Nice to have

$ARGUMENTS