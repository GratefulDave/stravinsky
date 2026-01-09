# Git Master Skill

Atomic commits with conventional format and smart history search.

## Invocation

```
/git-master <command>
```

## Commands

### commit - Smart Atomic Commit

```
/git-master commit
```

Workflow:
1. Run `git status` and `git diff --staged`
2. Analyze changes to determine commit type
3. Generate conventional commit message
4. Create atomic commit

**Commit Types** (Conventional Commits):
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `test`: Adding/updating tests
- `chore`: Build, config, dependencies

**Message Format**:
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### search - History Search

```
/git-master search <pattern>
```

Find commits matching a pattern:
- By message: `/git-master search "fix auth"`
- By file: `/git-master search --file src/auth.py`
- By author: `/git-master search --author david`
- By date: `/git-master search --since "1 week ago"`

### split - Split Large Changes

```
/git-master split
```

When staged changes are too large:
1. Analyze logical groupings
2. Suggest split points
3. Create multiple atomic commits

### amend - Smart Amend

```
/git-master amend
```

Safely amend the last commit:
1. Verify commit hasn't been pushed
2. Verify you're the author
3. Add staged changes to last commit
4. Update message if requested

## Rules

1. **Atomic Commits**: One logical change per commit
2. **Conventional Format**: Always use conventional commits
3. **No Secrets**: Block commits containing secrets
4. **Pre-push Check**: Verify before push to main/master

## Examples

```bash
# Smart commit with auto-generated message
/git-master commit

# Search for auth-related commits
/git-master search "auth"

# Find commits that modified a specific file
/git-master search --file mcp_bridge/auth/oauth.py

# Split large staged changes
/git-master split
```

## Safety Checks

Before committing, Git Master checks for:
- Exposed secrets (API keys, tokens, passwords)
- Debug/test code that shouldn't be committed
- Large binary files
- Merge conflict markers

---

$ARGUMENTS: command (required) - The git-master command to execute
