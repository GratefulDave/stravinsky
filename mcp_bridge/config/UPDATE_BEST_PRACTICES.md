# Safe Auto-Update Patterns for Developer Tools

## Executive Summary

This document consolidates proven auto-update patterns from industry-leading developer tools (Homebrew, npm, pip/uv, VS Code, chezmoi, and Git) to provide best practices for safely updating managed artifacts (hooks, skills, extensions, configurations).

**Key Insight**: The most reliable auto-update systems don't prevent changes—they enable safe conflict resolution, provide rollback capabilities, and preserve user customizations like dotfiles managers do.

---

## Core Principles

### 1. **Separation of Concerns: Code vs Configuration**
- Keep update logic separate from user configuration
- Store configuration in independent files that survive updates
- Example: VS Code stores user settings separately from extension binaries; npm/yarn use lock files separate from package definitions
- **Implication for Stravinsky**: User-customized hooks/skills should be stored separately from core Stravinsky code

### 2. **Version Pinning with Semantic Versioning**
- Use semantic versioning (Major.Minor.Patch) to signal breaking changes
- Allow users to pin versions while auto-updating within version constraints
- Example: npm `^1.2.3` allows 1.x.x updates but blocks 2.0.0
- **Implication**: Stravinsky should support version constraints for hooks/skills

### 3. **Lock Files for Reproducibility**
- Maintain lock files (package-lock.json, yarn.lock, uv.lock) that record exact versions
- Use immutable installs to ensure reproducibility across environments
- Yarn's `--immutable` flag prevents lock file changes during install
- **Implication**: Stravinsky should maintain a lock file for hook/skill versions

### 4. **Three-Way Merge for Conflict Resolution**
- Use three-way merge (Base, Local, Incoming) instead of simple overwrite
- Chezmoi's merge command allows users to resolve conflicts interactively
- Git's conflict markers and merge strategies provide proven patterns
- **Implication**: When updating user customizations, use 3-way merge with fallback to user decision

### 5. **Atomic Operations with Rollback**
- Updates should be atomic: all-or-nothing
- Provide quick rollback via version snapshots or Git history
- Kubernetes Argo Rollouts demonstrates automated rollback on health check failure
- **Implication**: Stravinsky updates should be reversible with a single command

### 6. **Validation Before and After**
- Verify compatibility before applying updates (pip check, npm audit)
- Run smoke tests and health checks after updates
- Argo Rollouts uses metrics monitoring to automatically detect failures
- **Implication**: Stravinsky should validate hook/skill syntax before applying

### 7. **Transparent Control and Visibility**
- Provide clear user control over auto-update behavior
- Show what changed and why (release notes, breaking changes)
- Allow users to opt-out of auto-updates for specific items
- **Implication**: Stravinsky users should control update frequency and strategy

---

## Implementation Patterns

### Pattern 1: Version Pinning & Compatibility Checking

#### Semantic Versioning Strategy
```
# Homebrew Dependencies
depends_on "ruby" => ">=2.7,<3.0"

# npm/Yarn Constraints
"lodash": "^4.17.0"   # allows 4.17.0, 4.17.1, 4.18.0 but not 5.0.0
"express": "~4.17.0"  # allows 4.17.x but not 4.18.0

# Python/uv Constraints
requires_python = ">=3.11,<3.14"
package = { version = "^1.2.0" }

# VS Code Extension Compatibility
"engines": {
  "vscode": "^1.70.0"  # works with VS Code 1.70+
}
```

#### Validation Before Update
- **npm**: `npm ls` checks for conflicts; `npm audit` checks for vulnerabilities
- **pip**: `pip check` verifies dependency compatibility; `--dry-run` simulates install
- **Homebrew**: Dependency graph via `brew deps --graph`
- **VS Code**: Marketplace validates `engines.vscode` compatibility before allowing installation

#### Best Practice Implementation
```bash
# Before applying update
$ check_compatibility() {
    # Verify version constraints are satisfied
    # Check dependency resolution
    # Validate hook syntax
    # Test against known use cases
}

# Dry-run/test mode before committing
$ apply_update --dry-run --validate
```

---

### Pattern 2: Configuration Preservation

#### File-Level Separation
**VS Code Model** (most effective):
- Extension code lives in: `/ext/extensions/my-ext/`
- User settings live in: `~/.config/Code/User/settings.json`
- User keybindings live in: `~/.config/Code/User/keybindings.json`
- → Settings survive extension updates automatically

**chezmoi Model** (encode state in filenames):
```
# Source state attributes in filenames preserve properties
private_config.yaml    # removes group/world permissions
readonly_bashrc        # prevents write access
executable_install.sh  # marks as executable
encrypted_secrets      # stored encrypted
template_.tmpl        # templated with variables
```

**Git Model** (for dotfiles):
```
# .gitattributes for merge drivers
config.json merge=union  # keeps both sides on merge
secrets.env merge=ours   # keep local version
```

#### Best Practice Implementation for Stravinsky
```yaml
# Stravinsky core hooks (auto-updated)
~/.stravinsky/hooks/core/pre_commit.md    # auto-updated

# User customizations (preserved)
~/.stravinsky/hooks/custom/user_hook.md   # never auto-updated
~/.stravinsky/config/stravinsky.toml      # config preserved

# Lock file
~/.stravinsky/.hook-lock.json             # pins exact versions
```

---

### Pattern 3: Three-Way Merge Strategies

#### How Three-Way Merge Works
```
BASE (common ancestor)
↓
├─→ SOURCE (new version from repository)
│
└─→ DESTINATION (current user version)
     ↓
  MERGED RESULT (intelligently combined)
```

#### chezmoi Example
```bash
$ chezmoi merge ~/.bashrc

# Opens merge tool with:
# - Destination: your current ~/.bashrc
# - Source: chezmoi's version
# - Target: desired merged state
# User manually resolves conflicts

$ chezmoi merge-all  # applies to all files needing merge
```

#### Git Example
```bash
# Show conflicts in 3-way diff format (includes base version)
$ git checkout --conflict=diff3 <file>

# Analyze changes from each perspective
$ git diff --ours          # our changes vs. merged result
$ git diff --theirs        # their changes vs. merged result
$ git diff --base          # base vs. merged result

# Advanced: extract and re-merge with custom logic
$ git show :1:<file> > common.txt  # base
$ git show :2:<file> > ours.txt    # our version
$ git show :3:<file> > theirs.txt  # their version
$ git merge-file -p ours.txt common.txt theirs.txt
```

#### Merge Driver Configuration
```bash
# Git attributes for custom merge behavior
$ cat > .gitattributes
*.json merge=union                     # keeps both sides
config.ini merge=ours                  # prefer local
package-lock.json merge=custom-driver  # run script

# Register custom merge driver
$ git config merge.custom-driver.driver './merge-script.sh %O %A %B'
#   %O = base file
#   %A = current (ours) file
#   %B = other (theirs) file

# Fallback: if merge fails, abort and ask user
$ git merge --abort
$ # user manually resolves using chezmoi merge or editor
```

---

### Pattern 4: Rollback Mechanisms

#### Version-Based Rollback
```bash
# Homebrew
$ brew switch python 3.11.0  # roll back to previous version
$ brew install python@3.11   # install specific version

# npm/Yarn
$ npm install lodash@4.17.0  # install specific version
$ npm ci --legacy-peer-deps  # reproduce lock file exactly

# pip
$ pip install Django==3.2.0  # install exact version
$ pip install -r requirements.txt  # restore from backup

# uv
$ uv pip install package==1.2.3
$ uv pip install -r backup-requirements.txt

# VS Code
$ Right-click extension → "Install Another Version"
```

#### Snapshot-Based Rollback (Dotfiles)
```bash
# Before applying major update, create snapshot
$ chezmoi apply --dry-run > pre_update.log

# If issues occur, restore from Git
$ git diff                    # see what changed
$ git checkout -- <file>      # restore specific file
$ git reset --hard HEAD~1     # undo entire update commit

# yadm (similar pattern)
$ yadm diff                   # see pending changes
$ yadm undo                   # revert changes
```

#### Git-Based Rollback
```bash
# Simple rollback (local changes only)
$ git reset --hard HEAD~1     # undo last commit

# Rollback with history preservation (if already pushed)
$ git revert -m 1 HEAD        # creates new commit undoing merge
# Safe for shared branches

# Emergency: restore from backup
$ cp backup/config ~/.config/
```

---

### Pattern 5: Health Checks & Validation

#### Pre-Update Validation
```python
# Pseudo-code validation before update

def validate_before_update(old_version, new_version):
    # 1. Check version compatibility
    if not is_version_compatible(old_version, new_version):
        return False, "Breaking change detected"

    # 2. Verify dependencies
    if not check_dependencies(new_version):
        return False, "Missing dependencies"

    # 3. Syntax check
    if not validate_syntax(new_version):
        return False, "Syntax error in new version"

    # 4. Test against known cases
    if not run_smoke_tests(new_version):
        return False, "Smoke tests failed"

    return True, "Ready to update"
```

#### Post-Update Validation
```bash
# Run smoke tests
$ stravinsky-cli test-hooks --hook pre_commit

# Health checks
$ stravinsky-cli health
  ✓ All hooks loaded
  ✓ All skills available
  ✓ Configuration valid
  ✗ WARNING: 1 hook has breaking changes

# Verify functionality
$ stravinsky-cli verify-installation
  ✓ Core functionality: PASS
  ✓ Custom hooks: PASS
  ✓ Skills: PASS
```

#### Automated Rollback on Failure
**Argo Rollouts Pattern** (applicable to Stravinsky):
```bash
# Monitor metrics after update
for metric in error_rate latency memory_usage; do
    value=$(monitor_metric $metric)
    if is_unhealthy($value); then
        # Automatic rollback triggered
        echo "Health check failed: $metric = $value"
        perform_rollback()
        alert_user "Update rolled back due to health check failure"
        exit 1
    fi
done
```

---

## Tool-Specific Patterns

### Homebrew (System Package Manager)

#### Configuration Preservation
```bash
# Environment variables for controlling behavior
export HOMEBREW_NO_INSTALL_CLEANUP=1  # preserve multiple versions

# Pre/post hook support
brew install --verbose  # detailed output for debugging
```

#### Update Strategy
```bash
# Safe update flow
$ brew update              # fetch latest formulas
$ brew outdated           # show available updates
$ brew upgrade            # update everything (respects version constraints)
$ brew cleanup --prune=14 # cleanup after 14 days
```

#### Key Learnings
- ✅ Graceful dependency resolution with type qualifiers (:build, :test, :optional)
- ✅ Environment variable configuration system
- ✅ Human-reviewed security model
- ❌ Limited built-in rollback (must use version switching)

---

### npm & Yarn (JavaScript Package Manager)

#### Configuration Preservation
- **package.json**: Defines version constraints (developer specified)
- **package-lock.json** / **yarn.lock**: Records exact installed versions (machine generated)
- Never modify lock files manually; regenerate via `npm install` / `yarn install`

#### Update Strategy
```bash
# Safe npm update flow
$ npm list                    # show current versions
$ npm outdated               # show available updates
$ npm update                 # update within constraints
$ npm ls                     # verify no conflicts
$ npm audit                  # check for vulnerabilities

# Dry-run before committing lock file changes
$ npm update --dry-run
$ git diff package-lock.json # review before committing
```

#### Semantic Versioning Strategies
```json
{
  "dependencies": {
    "exact": "1.2.3",                    // only 1.2.3
    "caret": "^1.2.3",                   // 1.x.x (safe for minor/patch)
    "tilde": "~1.2.3",                   // 1.2.x (safe for patch only)
    "ranges": ">=1.2.0,<2.0.0"          // explicit range
  }
}
```

#### Handling Breaking Changes
```javascript
// Pattern: Wrapper module for version compatibility
// lib/lodash-wrapper.js
export const LODASH_VERSION = require('lodash/package.json').version;

export function mapAsync(collection, fn) {
  if (LODASH_VERSION.startsWith('4.')) {
    return Promise.all(collection.map(fn));
  } else if (LODASH_VERSION.startsWith('5.')) {
    return collection.mapAsync(fn);  // v5 API
  }
}

// Usage elsewhere never changes, version handling centralized
```

#### Immutable Installation (Yarn Best Practice)
```bash
$ yarn install --frozen-lockfile   # v1: fail if lock file would change
$ yarn install --immutable         # v2: modern flag name
# CI/CD should always use immutable install
```

#### Key Learnings
- ✅ Lock files provide reproducibility across environments
- ✅ Semver constraints allow automatic safe updates
- ✅ npm audit integrates security scanning
- ✅ Wrapper modules handle breaking changes elegantly
- ❌ Breaking changes require manual intervention (no automatic detection)

---

### pip & uv (Python Package Manager)

#### Configuration Preservation
```bash
# Backup current environment
$ pip freeze > requirements.txt
$ uv pip freeze > requirements.txt

# Restore from backup
$ pip install -r requirements.txt
$ uv pip install -r requirements.txt
```

#### Update Strategy
```bash
# Safe pip/uv update flow
$ pip check                    # verify current dependencies valid
$ pip list --outdated         # show available updates
$ pip install --upgrade pkg   # upgrade specific package
$ pip install --dry-run pkg   # simulate without installing

# For uv (faster resolver)
$ uv pip compile requirements.in  # generate lock file
$ uv pip sync requirements.txt    # install exactly from lock
```

#### PEP 440 Versioning
```
# Python uses PEP 440 (similar to SemVer but with distinctions)
1.2.3         # release
1.2.3a1       # alpha
1.2.3b1       # beta
1.2.3rc1      # release candidate
1.2.3.post1   # post-release
```

#### Configuration System (uv)
```toml
# pyproject.toml or uv.toml
[project]
requires-python = ">=3.11,<3.14"  # version constraint

[tool.uv]
index-url = "https://pypi.org/simple"
extra-index-urls = ["..."]

# Precedence: project > user > system
# Command-line overrides all
```

#### Compatibility Checking
```bash
# pip check finds version conflicts
$ pip check
ERROR: pip-package-1.0 requires other-package>=2.0, but you have other-package 1.5

# Use pip install --upgrade-strategy only-if-needed to avoid breaking deps
$ pip install --upgrade-strategy only-if-needed new-package
```

#### Key Learnings
- ✅ pip check validates dependency tree before/after updates
- ✅ uv resolver is deterministic (better for reproducibility)
- ✅ freeze/lock pattern for environment snapshots
- ✅ Hierarchical configuration system (project > user > system)
- ❌ Breaking changes not detected automatically

---

### VS Code Extensions

#### Configuration Preservation (Excellent Pattern!)
- **User Settings** (`~/.config/Code/User/settings.json`): Separate from extension code
- **Workspace Settings** (`.vscode/settings.json`): Separate from extension code
- **Settings Sync**: Synchronizes settings + extensions + state across machines
- Result: Settings survive extension updates automatically

#### Update Strategy
```bash
# VS Code handles auto-updates transparently
# User control via settings:
{
  "extensions.autoUpdate": true,    // default: auto-update
  "extensions.autoCheckUpdates": true,
  "extensions.ignoreRecommendations": false
}

# Per-extension control
# Right-click extension → "Install Another Version"
```

#### Compatibility Checking
```json
// package.json for extension
{
  "engines": {
    "vscode": "^1.70.0"  // requires VS Code 1.70 or higher
  }
}
```

Marketplace validates:
- Extension declares compatible VS Code version
- Uses published APIs only
- No deprecated API usage

#### Activation & Lazy Loading (Safety)
```json
{
  "activationEvents": [
    "onLanguage:javascript",
    "onCommand:extension.helloWorld",
    "onView:myView"
  ]
}
```

- Extensions only load when needed
- Prevents startup impact
- Reduces resource consumption

#### Key Learnings
- ✅ **BEST PATTERN**: Separate code from configuration completely
- ✅ Settings Sync provides robust state management
- ✅ Lazy loading prevents resource issues
- ✅ Extension Host isolation (separate process) prevents crashes
- ✅ Marketplace pre-validates compatibility
- ❌ Extension host restart required after updates (not automatic)

---

### chezmoi (Dotfiles Manager)

#### Configuration Preservation (Excellent Pattern!)
**Source State Attributes** encode file properties in filenames:
```
sources/
├── private_bashrc              # removes group/world permissions
├── readonly_config             # read-only file
├── executable_install.sh       # executable file
├── empty_.gitkeep              # empty file marker
├── encrypted_secrets.yml       # encrypted storage
└── template_.tmpl              # templated with variables
```

#### Handling External Modifications
```bash
$ chezmoi apply     # check for external changes
# If target differs from managed version:
# "file has changed since last apply: keep local changes or use new version?"

# Two options:
# 1. Use chezmoi merge to resolve conflicts interactively
$ chezmoi merge ~/.bashrc

# 2. Use hooks to run scripts before/after apply
# .chezmoi.toml.tmpl
pre-apply = ["script-to-backup.sh"]
post-apply = ["script-to-verify.sh"]
```

#### Three-Way Merge in Action
```bash
$ chezmoi merge ~/.bashrc

# Opens vimdiff (or configured tool) with:
# Left window   (top): destination (current ~/.bashrc)
# Middle window (bot left): source (chezmoi's version)
# Right window  (bot right): target (desired state)
#
# User manually resolves:
# ]c = next conflict
# dp = diff put (take from destination)
# do = diff obtain (take from other)
# Save and exit to accept merge result
```

#### Hooks System
```toml
# .chezmoi.toml
[hooks]
apply.pre = ["echo 'backing up config'"]
apply.post = ["echo 'running tests'"]

# Hooks receive environment variables:
# CHEZMOI=1
# CHEZMOI_COMMAND="apply"
# CHEZMOI_COMMAND_DIR="/path/to/project"
# CHEZMOI_ARGS="[arg1, arg2]"
```

#### Key Learnings
- ✅ **BEST PATTERN**: Filename attributes encode state (self-documenting)
- ✅ 3-way merge respects user modifications
- ✅ Hooks allow custom logic before/after updates
- ✅ Encryption support for sensitive files
- ✅ Templating allows dynamic configuration
- ✅ Detects external modifications and prompts user

---

### Git Merge & Conflict Resolution

#### Three-Way Merge Mechanics
```bash
# Git stores three versions during merge
$ git show :1:file  # ancestor (base)
$ git show :2:file  # HEAD (ours)
$ git show :3:file  # MERGE_HEAD (theirs)
```

#### Conflict Visualization
```
# Default style (basic)
<<<<<<< HEAD
our version
=======
their version
>>>>>>> branch

# diff3 style (includes base, much more useful!)
# git config --global merge.conflictstyle diff3

<<<<<<< HEAD
our version
||||||| merged common ancestors
base version
=======
their version
>>>>>>> branch
```

#### Advanced Merge Options
```bash
# Whitespace-aware merging
$ git merge -Xignore-all-space     # ignore all whitespace
$ git merge -Xignore-space-change  # treat whitespace as equivalent

# Preference strategies
$ git merge -Xours branch     # conflict: keep our version
$ git merge -Xtheirs branch   # conflict: keep their version

# Custom merge drivers via .gitattributes
config.json merge=union          # keep both sides
package-lock.json merge=resolve  # run resolve-lock-conflicts.sh
secrets.env merge=ours          # always keep local
```

#### Custom Merge Driver Script
```bash
#!/bin/bash
# merge-driver.sh
# Called by: git config merge.custom-driver.driver './merge-driver.sh %O %A %B'
# %O = ancestor, %A = current, %B = other

ANCESTOR=$1
CURRENT=$2
OTHER=$3

# Example: JSON merge that keeps both arrays
if [[ $ANCESTOR =~ .json$ ]]; then
    jq -s '.[0] * .[1]' "$ANCESTOR" "$OTHER" > "$CURRENT"
    exit 0
fi

# Fallback to default 3-way
git merge-file -p "$CURRENT" "$ANCESTOR" "$OTHER" > "$CURRENT"
exit $?
```

#### Key Learnings
- ✅ 3-way merge (not 2-way) respects base version
- ✅ diff3 style shows base, making conflicts clearer
- ✅ Merge strategy options for whitespace/preference
- ✅ Custom merge drivers for special file types
- ✅ git diff variants for analyzing conflicts

---

## Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Storing Configuration in Code
**Problem**: Configuration gets overwritten on updates
```
# BAD: config inside plugin code
class Plugin:
    def __init__(self):
        self.api_key = "default"        # overwritten on update!
        self.debug_mode = True          # overwritten on update!
```

**Solution**: Use configuration file separate from code
```
# GOOD: external config file
~/.plugin/config.json               # preserved across updates
/etc/plugin/plugin.conf             # system config
```

### ❌ Anti-Pattern 2: Auto-Update Without Validation
**Problem**: Broken updates deployed silently
```bash
# BAD: just install latest without checking
$ curl https://example.com/latest | bash
```

**Solution**: Validate before applying
```bash
# GOOD: verify, test, then apply
$ new_version=$(fetch_latest)
$ validate_syntax($new_version)  || exit 1
$ run_tests($new_version)        || exit 1
$ apply_update($new_version)
```

### ❌ Anti-Pattern 3: Overwriting User Customizations
**Problem**: User changes lost on update
```bash
# BAD: just copy new version over old
$ cp new_config.yaml ~/.config/myapp/config.yaml  # LOST USER EDITS!
```

**Solution**: Use 3-way merge
```bash
# GOOD: merge with user changes
$ merge_with_base(new_config, old_config, user_config)
```

### ❌ Anti-Pattern 4: No Rollback Strategy
**Problem**: Broken update leaves system broken
```bash
# BAD: no way to recover
$ update_system()
$ # If broken, user stuck!
```

**Solution**: Snapshot and rollback capability
```bash
# GOOD: easy recovery
$ create_snapshot()
$ apply_update()
$ if_failed() { restore_snapshot(); }
```

### ❌ Anti-Pattern 5: Trusting Semver Alone
**Problem**: Breaking changes despite semver claims
```
# Even with semver ^1.2.0, breaking changes can happen
# in practice, semantic versioning is not foolproof
```

**Solution**: Validate in addition to semver
```bash
$ check_semver_constraint()  # version is in range?
$ validate_compatibility()   # actually compatible?
$ run_smoke_tests()          # works in practice?
```

### ❌ Anti-Pattern 6: Silent Failures
**Problem**: Update partially succeeds, leaving broken state
```bash
# BAD: update fails partway through, state unknown
$ upgrade_component_1()  # succeeds
$ upgrade_component_2()  # FAILS
$ upgrade_component_3()  # skipped?
# System in broken state, unclear what went wrong
```

**Solution**: Atomic updates or explicit recovery
```bash
# GOOD: all-or-nothing
$ if_any_step_fails() {
    rollback_all()
    report_error()
    exit 1
}
```

---

## Real-World Best Practices

### Implementation Checklist for Auto-Update System

#### Before Update
- [ ] Fetch new version from source
- [ ] Validate syntax/structure (no parse errors)
- [ ] Check version constraints (within allowed range)
- [ ] Verify dependency tree (all deps resolvable)
- [ ] Run compatibility checks
- [ ] Create pre-update snapshot
- [ ] Inform user what will change

#### During Update
- [ ] Log all changes for debugging
- [ ] Use atomic operations (all-or-nothing)
- [ ] Apply 3-way merge for conflicting files
- [ ] Preserve user customizations
- [ ] Update lock file/manifest

#### After Update
- [ ] Run smoke tests / validation
- [ ] Check health metrics
- [ ] Verify all hooks/skills loaded
- [ ] Compare manifest changes
- [ ] Offer rollback if issues detected

#### Failure Recovery
- [ ] Detect failures automatically
- [ ] Trigger rollback if health checks fail
- [ ] Restore from snapshot
- [ ] Alert user with clear error message
- [ ] Preserve logs for debugging

### Configuration Management Strategy

```
Project Structure (Following VS Code Pattern):
├── ~/.stravinsky/
│   ├── hooks/
│   │   ├── core/                    # Auto-updated core hooks
│   │   │   ├── pre_commit.md
│   │   │   └── post_install.md
│   │   ├── custom/                  # User customizations (never auto-updated)
│   │   │   └── user_hook.md
│   │   └── .hook-lock.json         # Lock file for reproducibility
│   ├── skills/
│   │   ├── core/                   # Auto-updated core skills
│   │   ├── custom/                 # User custom skills
│   │   └── .skill-lock.json
│   ├── config/
│   │   ├── stravinsky.toml         # User configuration (preserved)
│   │   └── .gitignore              # Protect custom files
│   └── backups/
│       └── pre_update_*.tar.gz      # Snapshots for rollback

Version Control:
├── .gitignore
│   custom/*           # Never commit user customizations
│   *.local.md        # Local overrides
│   backups/*         # Snapshots
│   .stravinsky/cache/*
```

### User Communication Pattern

```
1. Auto-check phase (silent)
   - Check for updates hourly/daily
   - Background validation

2. Pre-update notification
   - "Update available: stravinsky-hooks v2.0.0"
   - "Changes: Added 3 hooks, Updated 2 hooks, Removed 1 hook"
   - "Breaking change: pre_commit hook signature changed"
   - Allow user to defer/skip

3. Update phase (logged)
   - "Backing up current configuration..."
   - "Downloading stravinsky-hooks v2.0.0..."
   - "Validating compatibility..."
   - "Applying 3-way merge for conflicting hooks..."
   - "Running smoke tests..."

4. Post-update feedback
   - "Update complete! ✓"
   - "Migration needed: See BREAKING_CHANGES.md"
   - "Rollback available: stravinsky rollback"

5. On failure
   - "Update failed: Syntax error in pre_commit.md"
   - "Rolling back to v1.9.0..."
   - "Restored successfully. View log: /tmp/stravinsky_update.log"
   - "Report bug: github.com/stravinsky/issues"
```

---

## Summary: Key Patterns for Stravinsky

1. **Separate code from configuration**: Store user hooks/skills apart from core
2. **Version pinning + lock files**: Enable reproducibility
3. **3-way merge**: Respect user customizations during updates
4. **Validation pipeline**: Check before, during, after updates
5. **Atomic operations**: Updates are all-or-nothing
6. **Easy rollback**: Snapshot + version history
7. **Transparent control**: Users control update frequency/strategy
8. **Clear communication**: Inform users of changes and breaking changes

---

## References

- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [npm Semantic Versioning](https://docs.npmjs.com/about-semantic-versioning/)
- [Yarn Lock File Documentation](https://yarnpkg.com/cli/install)
- [pip check - pip documentation](https://pip.pypa.io/en/stable/cli/pip_check/)
- [uv Configuration Files](https://docs.astral.sh/uv/concepts/configuration-files/)
- [VS Code Extension Host Architecture](https://code.visualstudio.com/api/advanced-topics/extension-host)
- [VS Code User and Workspace Settings](https://code.visualstudio.com/docs/getstarted/settings)
- [chezmoi Documentation](https://www.chezmoi.io/)
- [Git Advanced Merging](https://git-scm.com/book/en/v2/Git-Tools-Advanced-Merging)
- [Argo Rollouts - Progressive Delivery](https://argoproj.github.io/argo-rollouts/)
