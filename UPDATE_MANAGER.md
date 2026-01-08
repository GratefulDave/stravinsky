# Stravinsky Update Manager

The Update Manager provides safe, intelligent updates of hooks and skills during Stravinsky upgrades, with conflict detection and rollback capabilities.

## Features

### ✅ Safe Merging
- **3-way merge algorithm** (base, user, new) for intelligent conflict resolution
- **User customization preservation** - existing modifications never get overwritten without notice
- **Hook integrity** - never deletes user hooks, only adds/updates
- **Statusline preservation** - `.claude/settings.json` statusline always maintained

### ✅ Conflict Detection
- Detects when both user and upstream modified a file
- Generates conflict markers (<<<<<<, =======, >>>>>>>) for manual resolution
- Reports all conflicts with detailed information
- Supports line-based merging when changes don't overlap

### ✅ Backup & Rollback
- Automatic timestamped backups before every update
- List available backups with size and creation time
- One-command rollback to any previous state
- Backup directory: `~/.claude/.backups/`

### ✅ Version Tracking
- Manifest files track file versions and hashes
- Located in: `~/.claude/.manifests/`
- Enables intelligent diff detection

### ✅ Testing & Safety
- **Dry-run mode** (`--dry-run`) for testing without changes
- **Verbose logging** (`--verbose`) for detailed execution trace
- **Integrity verification** (`--verify`) to detect issues
- Comprehensive logging to `~/.claude/.logs/update_manager.log`

## Usage

### CLI Commands

#### Verify Installation
```bash
python mcp_bridge/update_manager.py --verify
```

Output:
```
Integrity: ✓ Valid
```

#### List Available Backups
```bash
python mcp_bridge/update_manager.py --list-backups
```

Output:
```
Found 3 backups:
  hooks_20250108_183000 (2.1 MB)
  hooks_20250107_120000 (2.1 MB)
  settings_20250106_090000 (0.01 MB)
```

#### Rollback to Previous State
```bash
python mcp_bridge/update_manager.py --rollback 20250108_183000
```

#### Test Update (Dry-run)
```bash
python mcp_bridge/update_manager.py --dry-run --verbose
```

### Python API

#### Basic Usage

```python
from mcp_bridge.update_manager import UpdateManager

# Create manager
manager = UpdateManager(dry_run=False, verbose=True)

# Update hooks with new versions
new_hooks = {
    "truncator.py": "#!/usr/bin/env python3\n...",
    "context.py": "#!/usr/bin/env python3\n...",
}

success, conflicts = manager.update_hooks(new_hooks, "0.4.0")

if conflicts:
    print(f"⚠️ {len(conflicts)} conflicts detected")
    for conflict in conflicts:
        print(f"  - {conflict.file_path}: {conflict.conflict_type}")
```

#### Update Settings.json

```python
new_settings = {
    "hooks": {...},
    "statusLine": "..."
}

success, conflicts = manager.update_settings_json(new_settings)
```

#### Verify Integrity

```python
is_valid, issues = manager.verify_integrity()

if not is_valid:
    for issue in issues:
        print(f"Issue: {issue}")
```

#### List Backups

```python
backups = manager.list_backups()

for backup in backups:
    print(f"{backup['name']} - {backup['size_mb']:.1f} MB")
```

#### Rollback

```python
success = manager.rollback("20250108_183000")
if success:
    print("✓ Rollback successful")
```

## How 3-Way Merge Works

The merge algorithm considers three versions:

1. **Base**: Last known state (from manifest)
2. **User**: Current state (what user may have modified)
3. **New**: Upstream version (from Stravinsky package)

### Merge Logic

| Base | User | New | Result |
|------|------|-----|--------|
| A | A | A | Use A (no changes) |
| A | B | A | Use B (user modified) |
| A | A | B | Use B (upstream updated) |
| A | B | B | Use B (both made same change) |
| A | B | C | **CONFLICT** (different changes) |
| ∅ | A | A | Keep A (user created) |
| ∅ | A | B | **CONFLICT** (both created differently) |
| A | ∅ | B | **CONFLICT** (user deleted, upstream updated) |

### Conflict Resolution

When conflicts are detected:

1. **File is marked** with conflict markers:
   ```python
   <<<<<<< USER VERSION
   user_content_here
   =======
   new_content_here
   >>>>>>> NEW VERSION
   ```

2. **Conflict is reported** with details:
   - File path
   - Conflict type (different_modifications, deleted_vs_new, etc.)
   - Version previews

3. **User can manually resolve** by:
   - Editing the file to remove conflict markers
   - Keeping desired content
   - Removing the other version

## Manifest Files

Located in `~/.claude/.manifests/`:

- **`base_manifest.json`**: Reference snapshot of installed hooks
- **`user_manifest.json`**: User-specific modifications (if tracked)
- **`new_manifest.json`**: Latest upstream version info

Example manifest:
```json
{
  "version": "0.4.0",
  "timestamp": "2025-01-08T18:30:00",
  "files": {
    "truncator.py": "a1b2c3d4e5f6g7h8",
    "context.py": "i9j8k7l6m5n4o3p2"
  }
}
```

## Backup Structure

Located in `~/.claude/.backups/`:

```
.backups/
├── hooks_20250108_183000/
│   ├── truncator.py
│   ├── context.py
│   └── ...
├── hooks_20250107_120000/
│   └── ...
└── settings_20250106_090000/
    └── settings.json
```

Backups are timestamped with format: `{type}_{YYYYMMDD_HHMMSS}`

## Logging

All operations logged to `~/.claude/.logs/update_manager.log`:

```
2025-01-08 18:30:45,123 - stravinsky.update_manager - INFO - Starting hooks update to version 0.4.0
2025-01-08 18:30:45,234 - stravinsky.update_manager - DEBUG - Wrote 1234 bytes to ~/.claude/hooks/truncator.py
2025-01-08 18:30:45,345 - stravinsky.update_manager - WARNING - Conflict detected in context.py: different_modifications
2025-01-08 18:30:45,456 - stravinsky.update_manager - INFO - Hooks update completed (10 files updated)
```

Enable verbose logging in code:
```python
manager = UpdateManager(verbose=True)
```

## Integration with Server Startup

The update manager should be called during Stravinsky server startup:

```python
# In server.py or similar
from mcp_bridge.update_manager import UpdateManager
from mcp_bridge.cli.install_hooks import HOOKS

# Check for updates
manager = UpdateManager()

# Update hooks if new version available
success, conflicts = manager.update_hooks(HOOKS, __version__)

if conflicts:
    logger.warning(f"Update conflicts detected: {len(conflicts)} files")
    for conflict in conflicts:
        logger.warning(f"  - {conflict.file_path}: {conflict.conflict_type}")
```

## Safety Guarantees

✅ **Never deletes files** - Adds/updates only, backups created first
✅ **Never overwrites user modifications** - Uses 3-way merge
✅ **Never loses statusline** - Explicitly preserved from settings.json
✅ **Never skips backups** - Backup created before any update
✅ **Never ignores conflicts** - All conflicts reported to user
✅ **Always auditable** - Full logging to `~/.claude/.logs/`

## Troubleshooting

### Conflicts Found During Update

**Symptom**: Update reports conflicts in hook files

**Solution**:
1. List conflicts from log: `tail -f ~/.claude/.logs/update_manager.log`
2. Edit conflicted file to remove `<<<<<<<`, `=======`, `>>>>>>>` markers
3. Keep the version you want (USER or NEW)
4. Verify with `--verify` command

### Backup Restore Failed

**Symptom**: Rollback command fails

**Solution**:
1. Check backups exist: `python mcp_bridge/update_manager.py --list-backups`
2. Verify timestamp format: `YYYYMMDD_HHMMSS`
3. Check backup directory permissions: `ls -la ~/.claude/.backups/`
4. Try manual restore from backup directory

### Manifest Missing

**Symptom**: "Base manifest missing" error from `--verify`

**Solution**:
```bash
# Run update again to recreate manifest
python mcp_bridge/update_manager.py --verbose

# Or manually verify by examining hooks
ls -la ~/.claude/hooks/
```

## Implementation Details

### Thread Safety

The UpdateManager is thread-safe for read operations. For update operations:
- Ensure only one update runs at a time
- Use file locking if needed for concurrent scenarios
- Recommended: Call during single-threaded startup phase

### Performance

- Backup creation: ~50-100ms per hook file
- Merge operation: ~10-20ms per file
- Manifest save: ~5-10ms
- Typical full update: <1 second

### Storage Requirements

- Each backup: ~2-5 MB (hooks only, or 10-50 KB for settings)
- Manifests: ~1 KB each
- Logs: ~100 KB per month
- Total for 100 backups: ~200-500 MB

## Future Enhancements

Potential improvements:
- [ ] Automatic cleanup of old backups (keep N most recent)
- [ ] Differential backups to reduce storage
- [ ] Conflict resolution templates/strategies
- [ ] Migration helpers for major version updates
- [ ] Rollback to specific version (not just timestamp)
- [ ] Integration with `uv publish` for version checking
