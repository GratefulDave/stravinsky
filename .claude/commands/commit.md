# Git Master - Intelligent Commit Orchestration

**Purpose**: Create atomic, well-organized commits with automatic style detection and enforced best practices.

**Core Principle**: "One commit = automatic failure" when multiple files exist. This skill enforces intelligent commit splitting based on the atomic commit formula: **minimum commits = ceil(file_count / 3)**.

---

## Execution Workflow

### Phase 0: Parallel Context Gathering (MANDATORY FIRST STEP)

**CRITICAL**: Execute these Bash commands in parallel BEFORE any analysis:

```bash
# Run these 5 commands simultaneously using separate Bash tool calls:
git status
git diff --staged
git log --oneline -30
git rev-parse --abbrev-ref HEAD
git rev-list --count HEAD ^origin/main 2>/dev/null || echo "0"
```

**What This Establishes**:
- Staged files and their change types (new/modified/deleted)
- Full diff content for analysis
- Recent 30 commits for style detection
- Current branch name
- Number of local-only commits (not yet pushed)

**DO NOT PROCEED** until all 5 commands complete.

---

### Phase 1: Style Detection (BLOCKING OUTPUT REQUIRED)

Analyze the 30 recent commits to determine the repository's commit style.

**Detection Criteria**:

| Style | Pattern | Example |
|-------|---------|---------|
| SEMANTIC | Starts with type prefix | `feat: add user auth`, `fix: resolve null pointer` |
| PLAIN | Natural language, no prefix | `Add user authentication`, `Fix login bug` |
| SENTENCE | Complete grammatical sentences | `Adds comprehensive user authentication system.` |
| SHORT | 1-3 words, minimal | `auth fix`, `update deps` |

**Language Detection**: Count Korean vs English commits (Korean uses different character ranges).

**MANDATORY OUTPUT FORMAT** (must appear before Phase 3):
```
🎨 COMMIT STYLE DETECTED
Language: [KOREAN | ENGLISH]
Style: [SEMANTIC | PLAIN | SENTENCE | SHORT]

Reference Examples from Recent Commits:
- [actual commit message 1]
- [actual commit message 2]
- [actual commit message 3]

All subsequent commits will follow this detected style.
```

**Style Application Rules**:
- SEMANTIC: Use conventional commits (feat:, fix:, chore:, docs:, refactor:, test:, style:, perf:, ci:)
- PLAIN: Start with imperative verb (Add, Fix, Update, Remove, Refactor)
- SENTENCE: Write complete grammatical sentence with period
- SHORT: Keep to 1-3 words, no punctuation

---

### Phase 2: Atomic Commit Formula (HARD RULE)

**Formula**: `minimum_commits = ceil(file_count / 3)`

**Examples**:
- 3 files → minimum 1 commit (ceil(3/3) = 1)
- 5 files → minimum 2 commits (ceil(5/3) = 2)
- 10 files → minimum 4 commits (ceil(10/3) = 4)
- 15 files → minimum 5 commits (ceil(15/3) = 5)

**AUTOMATIC FAILURE CONDITIONS** (abort immediately):
- Creating 1 commit from 3+ files without explicit override
- Creating 2 commits from 10+ files
- Creating N commits from 3N+ files

**Override Conditions** (when 1 commit is acceptable):
- All files in same directory AND same component type
- All changes form single atomic unit (cannot be split without breaking functionality)
- Must provide explicit one-sentence justification

---

### Phase 3: File Grouping & Atomic Planning (BLOCKING OUTPUT REQUIRED)

**Split Priority Order** (apply sequentially):

1. **Different Directories** → Always separate commits
   - Example: `src/auth/` vs `src/api/` → different commits

2. **Different Component Types** → Separate commits
   - Example: Models vs Controllers vs Services → different commits

3. **Independent Revertibility** → Separate commits
   - Example: Feature A vs Feature B → different commits
   - Rule: "If reverting one change should not revert the other, they must be separate commits"

4. **New Files vs Modifications** → Consider separating
   - Example: New migration + modify existing code → potentially separate

5. **Separation of Concerns** → Separate commits
   - UI changes vs logic changes vs config changes vs tests → separate commits
   - Exception: Tests MUST accompany their implementation (see Test Pairing Rule)

**Test Pairing Rule** (CRITICAL):
- Test files MUST be committed WITH their implementation in the SAME commit
- Example: `auth_service.py` + `test_auth_service.py` → SAME commit
- Rationale: Tests validate the implementation; they are inseparable

**MANDATORY OUTPUT FORMAT** (must appear before execution):
```
📋 ATOMIC COMMIT PLAN

Total Files: X
Minimum Required Commits: Y (formula: ceil(X/3))
Planned Commits: Z

Commit 1: [N files]
Files: file1.py, file2.py, ...
Justification: [One-sentence explanation of why these files are grouped]
Message: [Proposed commit message in detected style]

Commit 2: [N files]
Files: file3.py, file4.py, ...
Justification: [One-sentence explanation]
Message: [Proposed commit message]

[... repeat for all commits ...]

✅ Validation:
- [X] Meets minimum commit count (Z >= Y)
- [X] Different directories separated
- [X] Tests paired with implementations
- [X] Independent changes separated
- [X] All groupings justified
```

**Invalid Justifications** (require re-planning):
- "All related to feature X" (too vague)
- "Part of the same PR" (not actionable)
- "Makes sense to group" (requires specificity)
- "Similar files" (directory/component type must be specific)

**Valid Justifications**:
- "Both files implement user authentication middleware in src/auth/"
- "Database migration and corresponding model changes are inseparable"
- "Frontend components and their test files for login page"

---

### Phase 4: User Confirmation

Present the atomic commit plan to the user and wait for approval:
- "Does this commit plan look correct?"
- Allow user to request changes to grouping or messages
- Proceed to Phase 5 only after explicit approval

---

### Phase 5: Execution

**For Standard Commits**:
```bash
# For each planned commit group:
git add <file1> <file2> <file3>
git commit -m "$(cat <<'EOF'
[Commit message following detected style]

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

**For Fixup Commits** (when changes complement existing commits):

First, identify fixup targets:
```bash
# Find merge base with main
MERGE_BASE=$(git merge-base HEAD origin/main)

# Show commits since merge base
git log --oneline $MERGE_BASE..HEAD
```

Then apply fixups:
```bash
# For each fixup group:
git add <files>
git commit --fixup=<target-commit-hash>

# After all fixups created, auto-squash:
GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash $MERGE_BASE
```

**Commit Message Footer**:
- ALWAYS add: `Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>`
- Use heredoc syntax for multi-line messages to preserve formatting

**Execution Validation**:
After each commit, verify success:
```bash
git log -1 --oneline  # Show just-created commit
```

---

### Phase 6: Post-Commit Verification

```bash
# Verify all changes are committed
git status

# Show commit log
git log --oneline -<number_of_commits>

# Verify no uncommitted changes remain
[ -z "$(git status --porcelain)" ] && echo "✅ All changes committed" || echo "⚠️  Uncommitted changes remain"
```

---

## Safety Rules (CRITICAL - NEVER VIOLATE)

### Rebase Safety

**NEVER** rebase main/master branches:
```bash
# Before any rebase, check current branch:
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  echo "❌ ABORT: Never rebase main/master branches"
  exit 1
fi
```

**ALWAYS** use `--force-with-lease` (never bare `--force`):
```bash
# CORRECT:
git push --force-with-lease

# WRONG (prevents overwriting colleagues' work):
git push --force
```

**ALWAYS** check for dirty working directory before rebase:
```bash
if [ -n "$(git status --porcelain)" ]; then
  echo "⚠️  WARNING: Uncommitted changes detected. Stash first:"
  git stash push -m "Auto-stash before rebase"
fi
```

### Commit Safety

**Pre-Commit Checklist**:
```
☐ File count check: N files → at least ceil(N/3) commits?
☐ Justification check: Multi-file commits have one-sentence explanations?
☐ Directory split check: Different directories in separate commits?
☐ Test pairing check: Tests bundled with implementations?
☐ Style check: Messages follow detected repository style?
```

**Hard Stop Conditions**:
- Making 1 commit from 3+ files (without valid override justification)
- Making 2 commits from 10+ files
- Different directories in same commit (without explicit justification)
- Tests separated from their implementations
- Unable to justify file grouping in one sentence

---

## Anti-Patterns (Automatic Failures)

### Commit Mode Violations

❌ **Single Giant Commit**
```bash
# WRONG: All 10 files in one commit
git add .
git commit -m "Update feature"
```

✅ **Correct Atomic Commits**
```bash
# RIGHT: Split into 4+ commits by directory/concern
git add src/auth/*.py
git commit -m "feat: implement OAuth2 authentication flow"

git add src/api/routes.py src/api/middleware.py
git commit -m "feat: add authenticated API routes"

git add tests/test_auth.py tests/test_api.py
git commit -m "test: add authentication and API test coverage"
```

❌ **Separating Tests from Implementation**
```bash
# WRONG:
git commit -m "feat: add auth service" src/auth.py
git commit -m "test: add auth tests" test_auth.py
```

✅ **Correct Test Pairing**
```bash
# RIGHT:
git add src/auth.py test_auth.py
git commit -m "feat: add auth service with test coverage"
```

❌ **Vague Grouping Justifications**
```
Justification: "All related to feature X"  # Too vague
Justification: "Part of same PR"           # Not actionable
Justification: "Makes sense to group"      # Requires specificity
```

✅ **Specific Justifications**
```
Justification: "Both implement database connection pooling in src/db/"
Justification: "Migration and model are inseparable schema changes"
Justification: "Login UI components and their Cypress integration tests"
```

---

## Advanced Features

### Fixup Workflow

When changes complement existing commits:

1. **Identify target commits**:
```bash
git log --oneline -10
```

2. **Create fixup commits**:
```bash
git add <files>
git commit --fixup=<target-hash>
```

3. **Auto-squash**:
```bash
MERGE_BASE=$(git merge-base HEAD origin/main)
GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash $MERGE_BASE
```

### Dependency-Ordered Commits

When commits have dependencies:
- Foundations before dependents
- Database migrations before code using new schema
- API contracts before implementations
- Type definitions before consumers

Example order:
1. Database migration (new `users` table)
2. User model (depends on table)
3. Authentication service (depends on model)
4. API routes (depends on service)
5. Tests (depends on all above)

---

## Usage Examples

### Example 1: Simple Feature (5 files)

**Context**: Added user registration feature with 5 files.

**Phase 0 Output**:
```bash
# Staged files:
src/models/user.py
src/services/auth_service.py
src/api/routes/auth.py
tests/test_auth_service.py
tests/test_auth_routes.py
```

**Phase 1 Output**:
```
🎨 COMMIT STYLE DETECTED
Language: ENGLISH
Style: SEMANTIC

Reference Examples:
- feat: add OAuth2 authentication
- fix: resolve CORS issue in API
- chore: update dependencies
```

**Phase 3 Output**:
```
📋 ATOMIC COMMIT PLAN

Total Files: 5
Minimum Required Commits: 2 (ceil(5/3))
Planned Commits: 2

Commit 1: 3 files
Files: src/models/user.py, src/services/auth_service.py, tests/test_auth_service.py
Justification: User model and auth service are inseparable core authentication logic with tests
Message: feat: implement user registration with authentication service

Commit 2: 2 files
Files: src/api/routes/auth.py, tests/test_auth_routes.py
Justification: Authentication API routes depend on service and include integration tests
Message: feat: add authentication API endpoints

✅ Validation:
- [X] Meets minimum commit count (2 >= 2)
- [X] Different concerns separated (model/service vs API)
- [X] Tests paired with implementations
- [X] Dependency order respected (service before routes)
```

### Example 2: Complex Refactor (12 files)

**Context**: Refactored authentication across multiple directories.

**Phase 3 Output**:
```
📋 ATOMIC COMMIT PLAN

Total Files: 12
Minimum Required Commits: 4 (ceil(12/3))
Planned Commits: 5

Commit 1: 2 files
Files: src/auth/models.py, migrations/001_add_auth_tables.sql
Justification: Database migration and corresponding model changes are inseparable
Message: refactor: update authentication database schema

Commit 2: 3 files
Files: src/auth/services/oauth.py, src/auth/services/jwt.py, tests/test_auth_services.py
Justification: OAuth and JWT services are core authentication logic in src/auth/services/ with tests
Message: refactor: modernize OAuth2 and JWT authentication services

Commit 3: 3 files
Files: src/api/middleware/auth.py, src/api/middleware/cors.py, tests/test_middleware.py
Justification: Authentication and CORS middleware are API-layer concerns in src/api/ with tests
Message: refactor: update API authentication middleware

Commit 4: 2 files
Files: src/config/auth_config.py, tests/test_config.py
Justification: Authentication configuration and its test in src/config/
Message: refactor: centralize authentication configuration

Commit 5: 2 files
Files: docs/authentication.md, README.md
Justification: Documentation updates for authentication refactor
Message: docs: update authentication documentation

✅ Validation:
- [X] Meets minimum commit count (5 >= 4)
- [X] Different directories separated (auth/ vs api/ vs config/ vs docs/)
- [X] Tests paired with implementations
- [X] Independent changes separated (migration vs services vs middleware vs config vs docs)
- [X] All groupings justified
```

---

## Troubleshooting

### Issue: "Too Few Commits Planned"

**Error**: Planning 2 commits for 10 files (minimum is 4).

**Solution**: Review file grouping. Look for:
- Files in different directories that should be separated
- Different component types (models vs services vs API)
- Independent features that can be split
- UI vs logic vs config separation opportunities

### Issue: "Cannot Justify File Grouping"

**Error**: Justification is too vague ("all related to feature X").

**Solution**: Be specific about WHY files are inseparable:
- Same directory AND same component type
- Technical dependency (migration + model, API contract + implementation)
- Single atomic unit (splitting would break functionality)
- Test pairing requirement

### Issue: "Tests Separated from Implementation"

**Error**: Test files in different commit from their implementation.

**Solution**: Always pair tests with implementation:
```bash
# WRONG:
git add src/service.py && git commit -m "feat: add service"
git add test_service.py && git commit -m "test: add tests"

# RIGHT:
git add src/service.py test_service.py
git commit -m "feat: add service with test coverage"
```

---

## Summary Checklist

Before executing commits, verify:

```
✅ Phase 0: Parallel context gathered (git status, diff, log, branch, local commits)
✅ Phase 1: Style detected and output displayed (language + style + examples)
✅ Phase 2: Atomic formula applied (minimum commits calculated)
✅ Phase 3: Atomic plan created and output displayed with justifications
✅ Phase 4: User confirmed the plan
✅ Phase 5: Ready to execute with Bash tool
✅ Safety: Not on main/master, working directory clean
✅ Anti-patterns: No single giant commit, tests paired, justifications specific
```

**Remember**: The goal is **atomic, revertible, well-organized commits** that tell a clear story of what changed and why. When in doubt, split into more commits rather than fewer.
