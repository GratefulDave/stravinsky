# Stravinsky Manifest Schema Documentation

## Overview

The manifest files (`hooks_manifest.json` and `skills_manifest.json`) track version information, integrity, and metadata for all Stravinsky-provided hooks and skills. These manifests enable:

- **Integrity Verification**: Detect unauthorized or accidental modifications
- **Update Management**: Determine which files need updating during package upgrades
- **User Customization**: Distinguish between official Stravinsky files and user modifications
- **Dependency Tracking**: Understand hook dependencies and required relationships

## File Locations

```
mcp_bridge/config/
├── hooks_manifest.json      # Official hook metadata
├── skills_manifest.json     # Slash command metadata
└── MANIFEST_SCHEMA.md       # This documentation
```

## Manifest Structure

### Common Fields

Both manifests share these top-level fields:

| Field | Type | Purpose |
|-------|------|---------|
| `schema_version` | string | Manifest format version (e.g., "1.0.0") |
| `manifest_version` | string | Stravinsky package version this manifest was generated for |
| `description` | string | Brief description of manifest purpose |
| `generated_date` | ISO 8601 | Timestamp when manifest was created/updated |
| `schema` | object | Field definitions and their meanings |
| `[items]` | object | Collection of hooks or skills with metadata |
| `usage` | object | Integration notes for `update_manager.py` |

### hooks_manifest.json Schema

Each hook entry has these fields:

```json
{
  "hook_name": {
    "version": "0.2.63",
    "source": "mcp_bridge/hooks/hook_name.py",
    "description": "Brief description of hook purpose",
    "hook_type": "PreToolUse|PostToolUse|UserPromptSubmit|Notification|SubagentStop|PreCompact|package|manager|session_idle|session_manager",
    "checksum": "sha256_first_12_chars",
    "lines_of_code": 150,
    "updatable": true,
    "priority": "critical|high|medium|low",
    "required": true,
    "dependencies": ["manager.py", "other_hook.py"]
  }
}
```

### skills_manifest.json Schema

Each skill entry has these fields:

```json
{
  "skill_name": {
    "file_path": "strav.md or str/search.md",
    "description": "Description from skill frontmatter",
    "category": "core|research|implementation|architecture",
    "checksum": "sha256_first_12_chars",
    "lines_of_code": 200,
    "updatable": true,
    "priority": "critical|high|medium|low",
    "agent_type": "explore|dewey|frontend|delphi|stravinsky|implementation_lead|code_reviewer",
    "blocking": true,
    "requires_auth": true,
    "version_first_added": "0.1.0",
    "notes": "Additional context or special considerations"
  }
}
```

## Field Definitions

### `version`
Semantic version of the hook/skill implementation. Format: `X.Y.Z` (e.g., `0.2.63`).

### `source` / `file_path`
Absolute path (hooks) or relative path from `.claude/commands/` (skills).

### `description`
One-line functional description of what the hook/skill does.

### `hook_type` (hooks only)
Claude Code hook type that this hook implements:
- **PreToolUse**: Runs before tool execution (can block with exit code 2)
- **PostToolUse**: Runs after tool completes
- **UserPromptSubmit**: Runs when user submits prompt
- **Notification**: Runs on notification events
- **SubagentStop**: Runs when agent completes
- **PreCompact**: Runs before context compaction
- **package**: Module/package initialization
- **manager**: Hook management infrastructure
- **session_idle**: Session idle detection

### `category` (skills only)
Skill category for organization:
- **core**: Essential orchestration features
- **research**: Documentation and code search
- **implementation**: Development workflows (test, review, deploy)
- **architecture**: Strategic advice and complex debugging

### `checksum`
SHA-256 hash (first 12 characters) for integrity verification.

**How to verify/generate:**
```bash
# Generate checksum
sha256sum mcp_bridge/hooks/hook_name.py | awk '{print substr($1,1,12)}'

# Verify file hasn't been modified
sha256sum -c <<< "checksum_value mcp_bridge/hooks/hook_name.py"
```

### `updatable`
- **true**: Official Stravinsky file - can be auto-updated by `update_manager.py`
- **false**: User customization or user-provided hook - skip during updates

**CRITICAL**: User hooks from `.claude/hooks/` should ALWAYS have `updatable: false` in the internal manifest comparison.

### `priority`
Update urgency level:
- **critical**: Security fixes, core functionality - update immediately
- **high**: New features, important improvements - include in next release
- **medium**: Enhancements, can batch with other updates
- **low**: Optional improvements, can defer

### `required`
- **true**: Hook is essential for core functionality and cannot be disabled
- **false**: Optional hook that provides enhanced behavior but isn't critical

### `blocking` (skills only)
- **true**: Skill blocks execution until completion
- **false**: Skill runs asynchronously in background

### `agent_type` (skills only)
Primary agent spawned by this skill:
- **stravinsky**: Task orchestration
- **explore**: Codebase search
- **dewey**: Documentation research
- **delphi**: Strategic architecture advisor
- **frontend**: UI/UX design
- **implementation_lead**: Coordinates implementation
- **code_reviewer**: Quality analysis

### `requires_auth` (skills only)
- **true**: Skill requires OAuth setup (Gemini or OpenAI)
- **false**: Skill works without authentication

### `dependencies`
List of other files this hook/skill depends on:
- Hooks typically depend on `manager.py`
- Some hooks depend on other hooks they coordinate with
- Skills may list dependent tools or agents

## Integration with update_manager.py

The `update_manager.py` module should use these manifests to:

### 1. Version Checking
```python
# Load installed manifest
installed_manifest = load_manifest("hooks_manifest.json")

# Compare with remote version
if installed_manifest.version < remote_manifest.version:
    # Updates available
    pass
```

### 2. Integrity Verification
```python
# Before updating, verify file hasn't been locally modified
current_checksum = compute_sha256(file_path)
expected_checksum = manifest[hook_name].checksum

if current_checksum != expected_checksum and manifest[hook_name].updatable:
    # Local modifications detected - warn user or skip
    skip_update(hook_name)
```

### 3. Selective Updates
```python
# Only update files marked updatable=true
for hook_name, hook_info in manifest.items():
    if hook_info.updatable and should_update(hook_info.priority):
        update_hook(hook_name, new_version)
```

### 4. Dependency Resolution
```python
# Ensure dependencies are met before updating
for dependency in hook_info.dependencies:
    if not is_dependency_installed(dependency):
        error("Missing dependency: " + dependency)
```

## Usage Examples

### Checking Hook Status
```bash
# Find all critical hooks needing updates
jq '.hooks | to_entries[] | select(.value.priority == "critical")' \
  mcp_bridge/config/hooks_manifest.json

# Check if a hook is required
jq '.hooks.parallel_enforcer.required' \
  mcp_bridge/config/hooks_manifest.json
```

### Verifying File Integrity
```bash
# Verify all hooks match expected checksums
python -c "
import json
from pathlib import Path

with open('mcp_bridge/config/hooks_manifest.json') as f:
    manifest = json.load(f)

for hook_name, info in manifest['hooks'].items():
    file_path = info['source']
    if Path(file_path).exists():
        # Compute checksum and compare
        pass
"
```

### Listing Available Skills
```bash
# Extract all skills with their agents
jq '.skills | to_entries[] | {name: .key, agent: .value.agent_type, blocking: .value.blocking}' \
  mcp_bridge/config/skills_manifest.json
```

## Best Practices

### For Stravinsky Maintainers

1. **Update on Release**: Regenerate manifests when releasing a new version
2. **Verify Checksums**: Ensure all checksums are current and accurate
3. **Document Changes**: Add notes to skills when updating functionality
4. **Priority Assignment**: Use priority levels consistently across releases
5. **Dependency Tracking**: Keep dependency lists current and accurate

### For Package Users

1. **Don't Modify Manifests**: Let `update_manager.py` handle manifest updates
2. **Preserve Customizations**: Don't modify hooks marked as required=true without good reason
3. **Check Auth Requirements**: Ensure OAuth is configured for skills requiring authentication
4. **Monitor Critical Updates**: Subscribe to updates for hooks marked priority=critical

### For Developers

1. **Custom Hooks**: Create custom hooks in `.claude/hooks/` (not in package)
2. **Hook Testing**: Always test hooks with sample input before deploying
3. **Checksum Calculation**: Update checksums when modifying hook files
4. **Dependency Management**: Clearly document all hook dependencies

## Schema Evolution

### Version 1.0.0 (Current)
- Initial manifest format
- Hook and skill metadata tracking
- Integrity verification via checksums
- Priority-based update strategy

### Future Versions
- Will be tracked in `schema_version`
- Backward compatibility maintained where possible
- Migration guides provided for breaking changes

## Troubleshooting

### Checksum Mismatch
**Problem**: Hook has been modified locally
**Solution**:
- If intentional: Update manifest checksum or move to custom hooks
- If accidental: Restore original file from package

### Missing Dependencies
**Problem**: Hook dependency is not installed
**Solution**: Ensure all required hooks in `dependencies` list are installed

### Update Failures
**Problem**: `update_manager.py` fails to update a hook
**Solution**:
- Check file permissions
- Verify checksum hasn't changed unexpectedly
- Check for read-only files

## Related Files

- `mcp_bridge/cli/install_hooks.py` - Hook installation script
- `mcp_bridge/config/hooks.py` - Hook configuration utilities
- `mcp_bridge/hooks/manager.py` - Hook execution manager
- `.claude/settings.json` - Claude Code hook configuration
