# Stravinsky Configuration & Manifest System

## Overview

The `mcp_bridge/config/` directory contains:

1. **hooks_manifest.json** - Version tracking for 32 official hooks
2. **skills_manifest.json** - Metadata for 16 slash commands/skills
3. **MANIFEST_SCHEMA.md** - Detailed schema documentation
4. **hooks.py** - Hook configuration utilities
5. **README.md** - This file

## Quick Start

### For Users
No action needed. Manifests are automatically managed by the Stravinsky package.

### For Maintainers
When releasing a new version:

```bash
# 1. Update version in pyproject.toml and mcp_bridge/__init__.py
# 2. Regenerate manifests (if hooks/skills changed)
python scripts/generate_manifests.py

# 3. Commit changes
git add mcp_bridge/config/*.json
git commit -m "chore: update manifests for v0.3.X"
```

## File Descriptions

### hooks_manifest.json
Tracks all 32 official hooks provided by Stravinsky:

- **Core execution hooks** (3): `parallel_execution`, `stravinsky_mode`, `todo_delegation`
- **Context hooks** (6): `context`, `todo_continuation`, `todo_enforcer`, `directory_context`, `rules_injector`, `pre_compact`
- **Tool enhancement hooks** (6): `tool_messaging`, `edit_recovery`, `truncator`, `empty_message_sanitizer`, `comment_checker`, `compaction`
- **Agent lifecycle hooks** (4): `notification_hook`, `subagent_stop`, `session_recovery`, `task_validator`
- **Advanced optimization** (5): `preemptive_compaction`, `parallel_enforcer`, `auto_slash_command`, `agent_reminder`, `budget_optimizer`
- **Execution context** (3): `keyword_detector`, `git_noninteractive`, `session_idle`, `session_notifier`, `tmux_manager`

**Key Metrics:**
- 9 required hooks (critical path)
- 23 optional hooks (enhanced behavior)
- 2 critical priority, 11 high, 12 medium, 7 low

### skills_manifest.json
Tracks all 16 slash commands (skills):

**Core Skills (4):**
- `/strav` - Task orchestration
- `/strav:loop` - Continuation loop management
- `/strav:cancel-loop` - Loop cancellation
- `/version` - Diagnostic info

**Implementation Skills (4):**
- `/commit` - Git commit orchestration
- `/review` - Code review
- `/verify` - Testing and deployment verification
- `/publish` - PyPI deployment

**Research Skills (7):**
- `/dewey` - Documentation research
- `/index` - Semantic search indexing
- `/str:index` - Detailed semantic indexing
- `/str:search` - Semantic code search
- `/str:start_filewatch` - File watching
- `/str:stop_filewatch` - Stop file watching
- `/str:stats` - Index statistics

**Architecture Skills (1):**
- `/delphi` - Strategic advisor

**Key Metrics:**
- 6 blocking skills (immediate execution)
- 10 async skills (background execution)
- All skills marked updatable=true (user customizable)

## Integration with update_manager.py

The manifests enable smart update workflows:

### Version Checking
```python
# Load manifest from installed package
manifest = load_manifest_from_package()

# Compare with remote version
if manifest.manifest_version < remote_version:
    # Updates available
    show_update_notification()
```

### Integrity Verification
```python
# Before updating a hook, verify it hasn't been modified
current_hash = compute_sha256(hook_file)
expected_hash = manifest[hook_name].checksum

if current_hash != expected_hash:
    # User has customized this hook
    if manifest[hook_name].updatable:
        warn_about_modifications()
```

### Selective Updates
```python
# Only update files marked updatable=true
# Respect user customizations in .claude/hooks/
for hook_name, hook_info in manifest.hooks.items():
    if hook_info.updatable and hook_info.priority in ["critical", "high"]:
        update_hook(hook_name)
```

### Dependency Resolution
```python
# Ensure all dependencies are installed
for dependency in hook_info.dependencies:
    if not is_installed(dependency):
        error(f"Missing dependency: {dependency}")
```

## Manifest Fields Reference

### Hook Entry
```json
{
  "hook_name": {
    "version": "0.2.63",
    "source": "mcp_bridge/hooks/hook_name.py",
    "description": "What this hook does",
    "hook_type": "PreToolUse|PostToolUse|UserPromptSubmit|...",
    "checksum": "sha256_first_12_chars",
    "lines_of_code": 150,
    "updatable": true,
    "priority": "critical|high|medium|low",
    "required": true,
    "dependencies": ["manager.py"]
  }
}
```

### Skill Entry
```json
{
  "skill_name": {
    "file_path": "strav.md or str/search.md",
    "description": "What this skill does",
    "category": "core|research|implementation|architecture",
    "checksum": "sha256_first_12_chars",
    "lines_of_code": 200,
    "updatable": true,
    "priority": "critical|high|medium|low",
    "agent_type": "explore|dewey|frontend|...",
    "blocking": true,
    "requires_auth": true,
    "version_first_added": "0.1.0"
  }
}
```

See **MANIFEST_SCHEMA.md** for complete field documentation.

## Checksum Verification

### Generate Checksums
```bash
# For a single file
sha256sum mcp_bridge/hooks/parallel_execution.py | awk '{print substr($1,1,12)}'

# For all hooks
for f in mcp_bridge/hooks/*.py; do
  echo "$(basename $f): $(sha256sum $f | awk '{print substr($1,1,12)}')"
done
```

### Verify File Integrity
```bash
# Check if a file has been modified
current=$(sha256sum mcp_bridge/hooks/parallel_execution.py | awk '{print substr($1,1,12)}')
expected=$(jq -r '.hooks.parallel_execution.checksum' mcp_bridge/config/hooks_manifest.json)

if [ "$current" != "$expected" ]; then
  echo "File has been modified locally"
fi
```

## Update Strategy

### Priority Levels
- **critical**: Security, core functionality - update immediately
- **high**: New features, important improvements - include in next release
- **medium**: Enhancements - can batch together
- **low**: Optional improvements - can defer

### Update Workflow
1. Check `manifest_version` against installed version
2. If newer version available, proceed to verify step
3. For each hook/skill:
   - Compute current checksum
   - Compare with manifest checksum
   - If modified: warn user or skip (respect customizations)
   - If unmodified and priority is high/critical: update
4. After updates, recompute checksums
5. Update manifest with new version

## Best Practices

### For Stravinsky Maintainers
1. **Always update manifests on release** - Use `scripts/generate_manifests.py`
2. **Document hook changes** - Update descriptions if functionality changes
3. **Keep checksums current** - Run verification script before commits
4. **Track dependencies** - Add any new hook dependencies to manifest
5. **Test manifest generation** - Validate JSON before commit

### For Package Users
1. **Don't edit manifests manually** - Let automated tools manage them
2. **Preserve customizations** - Store custom hooks in `.claude/hooks/` instead
3. **Check authentication** - Skills requiring auth need OAuth setup
4. **Review update notes** - Read manifest notes for important context

### For Hook Developers
1. **Add to manifest immediately** - New hooks must be in manifest
2. **Include checksum** - Use `sha256sum | awk '{print substr($1,1,12)}'`
3. **Document dependencies** - List all other hooks/modules needed
4. **Test locally** - Verify hook works before adding to manifest
5. **Update version field** - Bump manifest version on release

## Troubleshooting

### Manifest JSON is invalid
```bash
# Validate JSON syntax
python -m json.tool mcp_bridge/config/hooks_manifest.json > /dev/null
```

### Checksums don't match
```bash
# Regenerate checksums
python scripts/generate_manifests.py --recalc-checksums
```

### Missing hooks in manifest
```bash
# List all hooks not in manifest
diff <(ls mcp_bridge/hooks/*.py | sed 's/.*\///' | sort) \
     <(jq -r '.hooks | keys[]' mcp_bridge/config/hooks_manifest.json | sort)
```

### Update fails for a hook
1. Check file permissions: `ls -l mcp_bridge/hooks/hook_name.py`
2. Verify checksum: Compare current vs manifest
3. Check dependencies: Ensure all are installed
4. Review logs: Look for error messages in update output

## Related Files

- `mcp_bridge/__init__.py` - Package version
- `mcp_bridge/hooks/manager.py` - Hook execution system
- `mcp_bridge/cli/install_hooks.py` - Hook installation
- `.claude/settings.json` - Hook configuration
- `pyproject.toml` - Package metadata

## Version History

### v1.0.0 (Current)
- Initial manifest schema
- 32 hooks tracked
- 16 skills tracked
- SHA-256 checksum verification
- Priority-based update strategy

## Questions?

See **MANIFEST_SCHEMA.md** for detailed documentation.
