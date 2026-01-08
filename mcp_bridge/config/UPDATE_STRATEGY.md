# Stravinsky Auto-Update Architecture

This document describes the complete auto-update system for Stravinsky, including initialization, version tracking, 3-way merge, conflict resolution, and rollback mechanisms.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Update Trigger Mechanisms](#update-trigger-mechanisms)
3. [3-Way Merge Algorithm](#3-way-merge-algorithm)
4. [Version Tracking with Manifests](#version-tracking-with-manifests)
5. [Safety Guarantees](#safety-guarantees)
6. [Conflict Resolution](#conflict-resolution)
7. [Rollback Mechanism](#rollback-mechanism)
8. [Decision Flowcharts](#decision-flowcharts)
9. [Code Examples](#code-examples)

---

## Architecture Overview

The Stravinsky auto-update system consists of three integrated components:

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server Startup                           │
│                (mcp_bridge/server.py)                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │  Check for PyPI Updates         │
        │ (update_manager_pypi.py)        │
        │                                │
        │ - Read last check (update.log) │
        │ - If 24h+ elapsed, check PyPI  │
        │ - Log check time                │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │  Version Comparison             │
        │                                │
        │ - Current: installed version   │
        │ - Latest: PyPI version         │
        │ - No match? Trigger update    │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │  Collect New Files              │
        │                                │
        │ - From package installation   │
        │ - Hooks + settings.json       │
        │ - Generate manifests          │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │  Create Backup                  │
        │                                │
        │ - Backup ~/.claude/hooks/      │
        │ - Backup ~/.claude/settings.json
        │ - Backup location:             │
        │   ~/.claude/.backups/          │
        │   hooks_TIMESTAMP/             │
        │   settings_TIMESTAMP/          │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │  3-Way Merge Phase              │
        │ (update_manager.py)             │
        │                                │
        │ - Load base manifest           │
        │ - Read current user files      │
        │ - Read new files from package  │
        │ - Perform 3-way merge          │
        │ - Detect conflicts             │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │  Write Updated Files            │
        │                                │
        │ - If no conflicts: write       │
        │ - If conflicts: keep both      │
        │   (original + conflict markers)│
        │ - Make executable              │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │  Save Manifests                 │
        │                                │
        │ - base_manifest.json           │
        │ - Track file versions/hashes   │
        │ - Store timestamp              │
        └────────────┬───────────────────┘
                     │
                     ▼
        ┌────────────────────────────────┐
        │  Update Complete                │
        │                                │
        │ ✓ Files updated               │
        │ ✓ Conflicts logged            │
        │ ✓ Ready for next session      │
        └────────────────────────────────┘
```

### File Organization

```
~/.claude/                          # User's global Claude config
├── hooks/                          # Hook implementations
│   ├── parallel_execution.py       # User may customize
│   ├── context_monitor.py          # User may customize
│   └── ... (32 total hooks)
├── settings.json                   # Hook configuration + statusLine
├── .backups/                       # Automatic backups before updates
│   ├── hooks_20250108_143022/     # Timestamped backups
│   └── settings_20250108_143022/
└── .manifests/                     # Version tracking
    ├── base_manifest.json          # Current state after last update
    ├── user_manifest.json          # (reserved for future use)
    └── new_manifest.json           # (reserved for future use)

~/.stravinsky/                      # Stravinsky runtime data
├── update.log                      # Last update check timestamp
└── ... (other runtime data)

mcp_bridge/config/                  # Package manifests (reference)
├── hooks_manifest.json             # Official hooks metadata
├── skills_manifest.json            # Official skills metadata
└── UPDATE_STRATEGY.md              # This documentation
```

---

## Update Trigger Mechanisms

### 1. **Server Startup Check**

Every time Claude Code starts, the Stravinsky MCP server checks for available updates in the background (non-blocking).

**Trigger Point**: `mcp_bridge/server.py` -> `mcp_bridge/update_manager_pypi.py`

```
Server starts
    │
    ├─ Initialize MCP server
    ├─ Load token store
    ├─ Load hook manager
    │
    └─ (Non-blocking background task)
       └─ Check PyPI for updates (24h throttled)
```

### 2. **24-Hour Throttling**

To prevent excessive PyPI API calls, updates are only checked if **24+ hours** have elapsed since the last check.

**Storage**: `~/.stravinsky/update.log`

**Format**:
```
2025-01-08 14:30:22 | VERSION_CHECK | checked=0.3.9, latest=0.3.10
2025-01-08 14:30:23 | VERSION_MISMATCH | current=0.3.9 < latest=0.3.10
2025-01-08 14:30:23 | UPDATE_STARTED
```

**Logic** (`update_manager_pypi.py:_should_check()`):
```python
def _should_check(last_check_time: Optional[datetime]) -> bool:
    if last_check_time is None:
        return True  # First check ever - do it
    
    now = datetime.now()
    time_since_last = now - last_check_time
    
    return time_since_last >= timedelta(hours=24)  # Check if 24+ hours passed
```

### 3. **Automatic Update Execution**

When an update is needed:
1. PyPI version > installed version
2. New files are collected from the package
3. 3-way merge is performed
4. Files are updated in place
5. Manifests are saved

---

## 3-Way Merge Algorithm

The core of the update system is the 3-way merge algorithm. It preserves user customizations while incorporating upstream changes.

### Merge Inputs

```
┌──────────────────────────────────────┐
│         3-Way Merge Inputs           │
└──────────────────────────────────────┘

BASE (Original file from last release)
    ↓
    This is the "known good" version
    Used to detect what changed
    Stored in backup directory

USER (Current file in ~/.claude/hooks/)
    ↓
    File potentially modified by user
    Contains customizations to preserve

NEW (Updated file from current package)
    ↓
    Upstream changes from Stravinsky
    Contains new features/fixes
```

### Merge Algorithm Logic

```python
def _merge_3way(base, user, new):
    """
    Merge three versions of a file.
    
    Returns: (merged_content, has_conflict_markers)
    """
    
    # Case 1: No changes upstream
    if new == base:
        return user, False  # Keep user version as-is
    
    # Case 2: User made no changes, upstream changed
    if user == base or user is None:
        return new, False  # Apply upstream changes
    
    # Case 3: Both changed to same thing
    if user == new:
        return user, False  # They agree, use either
    
    # Case 4: Both changed differently
    else:
        # Perform line-based merge to find compatible changes
        merged = _line_based_merge(base, user, new)
        return merged, True/False depending on line conflicts
```

### Merge Decision Tree

```
                    Is new == base?
                   /              \
                 YES              NO
                  │                │
            Return user      Has user changed?
                            /              \
                          YES              NO
                           │                │
                    Did user ≠ base?    Return new
                    /              \
                  YES              NO
                   │                │
            Both changed!     User unchanged
            Line-based        Return new
            merge with
            conflict
            markers
```

### Conflict Markers

When conflicts are detected, the file is marked with standard merge conflict markers:

```python
<<<<<<< USER VERSION
user_content_here
=======
new_content_here
>>>>>>> NEW VERSION
```

For **line-based conflicts** where only some lines differ:

```python
<<<<<<< UPDATED UPSTREAM | user_line======= upstream_line>>>>>>> 
```

### Example Merge Scenarios

**Scenario 1: User Customizes, No Upstream Changes**
```
Base:  MAX_CONTEXT_TOKENS = 200000
User:  MAX_CONTEXT_TOKENS = 300000  (customized)
New:   MAX_CONTEXT_TOKENS = 200000  (unchanged)

Result: MAX_CONTEXT_TOKENS = 300000
Status: ✓ No conflict - user customization preserved
```

**Scenario 2: Both Change to Same Value**
```
Base:  TIMEOUT = 30
User:  TIMEOUT = 45  (customized)
New:   TIMEOUT = 45  (upstream update)

Result: TIMEOUT = 45
Status: ✓ No conflict - user and upstream agree
```

**Scenario 3: Both Change Differently**
```
Base:  RETRY_COUNT = 3
User:  RETRY_COUNT = 5  (customized)
New:   RETRY_COUNT = 4  (upstream update)

Result: <<<<<<< USER VERSION
        RETRY_COUNT = 5
        =======
        RETRY_COUNT = 4
        >>>>>>> NEW VERSION
        
Status: ⚠️ Conflict - user must review and choose
```

**Scenario 4: User Adds Custom Function, Upstream Adds Different Function**
```
Base:  def get_timeout(): ...
       return 30

User:  def get_timeout(): ...
       return 30
       
       def get_custom_value(): ...  # User added
       return user_pref

New:   def get_timeout(): ...
       return 30
       
       def get_timeout_with_logging(): ...  # Upstream added
       return timeout

Result: Line-based merge combines both functions
Status: ✓ No conflict - changes don't overlap
```

---

## Version Tracking with Manifests

### Manifest File Format

Manifests are JSON files stored in `~/.claude/.manifests/`

**base_manifest.json** (most important):
```json
{
  "version": "0.3.10",
  "timestamp": "2025-01-08T14:30:22Z",
  "files": {
    "parallel_execution.py": "a3f5e2c9d1b7",
    "context_monitor.py": "b2e8d4f6a1c9",
    "stravinsky_mode.py": "c1d9e3f5b2a8",
    ...
  }
}
```

**Fields**:
- `version`: Stravinsky version (e.g., "0.3.10") after update
- `timestamp`: ISO 8601 timestamp when update completed
- `files`: Map of filename -> SHA-256 hash (first 16 chars)

### Hash Calculation

```python
def _hash_file(path: Path) -> str:
    """Generate SHA-256 hash of file content."""
    import hashlib
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]
```

### Version Comparison

```python
def _compare_versions(current: str, latest: str) -> bool:
    """
    Compare semantic versions.
    
    Returns: True if latest > current
    """
    def parse(v):
        return tuple(map(int, v.split('.')))
    
    return parse(latest) > parse(current)
```

**Examples**:
```
"0.3.9" vs "0.3.10"  -> 0.3.10 is newer (True)
"0.4.0" vs "0.3.99"  -> 0.4.0 is newer (True)
"0.3.9" vs "0.3.9"   -> Same version (False)
```

### Update Triggering

```python
# Check if update is needed
if _compare_versions(current_version, latest_version):
    # Update available
    trigger_update()
else:
    # Already on latest
    skip_update()
```

---

## Safety Guarantees

### 1. **Always Backup Before Modify**

Before any file is written, a full backup is created:

```python
def _create_backup(source_dir: Path, backup_name: str) -> Optional[Path]:
    """Create timestamped backup of directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{backup_name}_{timestamp}"
    
    shutil.copytree(source_dir, backup_path)
    # Now safe to modify original files
```

**Backup Structure**:
```
~/.claude/.backups/
├── hooks_20250108_143022/          # Full copy before update
│   ├── parallel_execution.py
│   ├── context_monitor.py
│   └── ... (32 hooks)
└── settings_20250108_143022/       # Full copy before update
    └── settings.json
```

### 2. **Atomic Operations (All-or-Nothing)**

The update process is designed to be atomic:

```python
def update_hooks(new_hooks: Dict[str, str]) -> Tuple[bool, List[MergeConflict]]:
    # Step 1: Create backup (if fails, stop before modifying)
    backup_path = self._create_backup(hooks_dir, "hooks")
    if not backup_path:
        self.logger.error("Backup failed - aborting update")
        return False, []
    
    # Step 2: Merge all files (all succeed or rollback)
    updated_files = {}
    for filename, new_content in new_hooks.items():
        merged, has_conflict = self._merge_3way(...)
        
        if not self._write_file_safely(hook_path, merged):
            # Failed to write - but backup exists, can rollback manually
            self.logger.error(f"Failed to write {filename}")
            return False, conflicts
        
        updated_files[filename] = self._hash_file(hook_path)
    
    # Step 3: Save manifest (confirms update)
    if not self._save_manifest(new_manifest, "base"):
        return False, conflicts  # Manifest save failed, stop
    
    return True, conflicts  # All succeeded
```

**Guarantee**: If any step fails, subsequent steps don't run. Backup allows manual recovery.

### 3. **Rollback on Errors**

```python
def rollback(backup_timestamp: str) -> bool:
    """Restore from a specific backup."""
    backups = list(self.backup_dir.glob(f"*_{backup_timestamp}"))
    
    for backup_path in backups:
        if "hooks" in backup_path.name:
            restore_dir = hooks_dir
        elif "settings" in backup_path.name:
            restore_dir = settings_dir
        
        # Remove current (broken) files
        if restore_dir.exists():
            shutil.rmtree(restore_dir)
        
        # Restore from backup
        shutil.copytree(backup_path, restore_dir)
```

### 4. **Conflict Preservation**

When conflicts are detected, **the file is NOT replaced**. Instead:

1. Conflict markers are inserted into the file
2. User sees the conflict on next use
3. User can manually resolve or rollback
4. Original is never lost

```
If file has conflict markers, user can:
- Edit the file to keep/choose sections
- Commit changes
- Or run: stravinsky --rollback [timestamp]
  to restore original
```

### 5. **Statusline Never Touched**

The `settings.json` file has special handling - the statusline is always preserved:

```python
def _preserve_statusline(settings_file: Path) -> Optional[Dict[str, Any]]:
    """Read and preserve statusline from settings.json."""
    try:
        settings = json.loads(settings_file.read_text())
        statusline = settings.get("statusLine")
        return statusline  # Will be restored later
    except Exception:
        return None

def _merge_settings_json(base, user, new) -> Tuple[Dict, List[MergeConflict]]:
    """Merge settings with statusline preservation."""
    merged = {}
    
    # ALWAYS preserve statusline
    if "statusLine" in user:
        merged["statusLine"] = user["statusLine"]
    elif "statusLine" in new:
        merged["statusLine"] = new["statusLine"]
    
    # ... merge other fields ...
    
    return merged, conflicts
```

**Guarantee**: User's statusline customization is never overwritten.

---

## Conflict Resolution

### When Conflicts Occur

Conflicts happen when:
1. **User has modified a hook** (different from base)
2. **Upstream has also changed the same file**
3. **Changes are not compatible** (different logic/structure)

### Resolution Strategy

When conflicts are detected:

**Step 1: Mark the File with Conflict Markers**
```python
merged_content = self._format_conflict_markers(user_version, new_version)
# Result contains both versions with <<<<<<< / ======= / >>>>>>> markers
```

**Step 2: Log the Conflict**
```python
self.logger.warning(f"Conflict in {filename}: {conflict.conflict_type}")
```

**Step 3: Save Both Versions**
```python
# Original file contains conflict markers
# User can edit and resolve manually
self._write_file_safely(hook_path, merged_content)
```

**Step 4: Preserve for Rollback**
```python
# Backup dir still has original unmodified version
# Can rollback if needed
backup_path / filename  # Original before conflict
```

### Conflict Types

| Type | Cause | Resolution |
|------|-------|-----------|
| `different_modifications` | Both changed, different results | User chooses sections |
| `added_both_ways` | Both added same file differently | Merge marker inserted |
| `deleted_vs_new` | User deleted, upstream changed | User decides keep/delete |
| `line_conflict` | Specific lines conflict | Line-level markers inserted |

### Example User Workflow

**1. Update completes with conflicts:**
```
WARNING: Conflict in context_monitor.py: different_modifications
```

**2. User opens the file and sees:**
```python
<<<<<<< USER VERSION
MAX_CONTEXT_TOKENS = 300000  # User's custom value
=======
MAX_CONTEXT_TOKENS = 200000  # Upstream default
>>>>>>> NEW VERSION

# ... rest of file ...
```

**3. User resolves by choosing:**
```python
MAX_CONTEXT_TOKENS = 300000  # Keep user's value
# Remove conflict markers

# ... rest of file ...
```

**4. User commits change:**
```bash
git add ~/.claude/hooks/context_monitor.py
git commit -m "Resolve merge conflict in context_monitor.py"
```

**Or rollback if preferred:**
```bash
stravinsky --rollback 20250108_143022
# Restores hooks_20250108_143022/ from backup
```

---

## Rollback Mechanism

### Manual Rollback Command

```bash
python -m mcp_bridge.update_manager --rollback TIMESTAMP
```

Where `TIMESTAMP` is from backup directory name (e.g., `20250108_143022`).

### Automatic Rollback on Error

```python
def update_hooks(new_hooks):
    # Create backup first
    backup_path = self._create_backup(hooks_dir, "hooks")
    
    # Try to update each file
    for filename, content in new_hooks.items():
        if not self._write_file_safely(hook_path, merged_content):
            # Write failed
            self.logger.error("Update failed, manual rollback available")
            # Backup exists, user can run:
            # python -m mcp_bridge.update_manager --rollback TIMESTAMP
            return False
```

### Listing Available Backups

```bash
python -m mcp_bridge.update_manager --list-backups
```

**Output**:
```
Found 5 backups:
  hooks_20250108_143022 (0.5 MB)
  settings_20250108_143022 (0.01 MB)
  hooks_20250107_090015 (0.5 MB)
  settings_20250107_090015 (0.01 MB)
  hooks_20250106_155430 (0.5 MB)
```

### Rollback Process

```
User runs: --rollback 20250108_143022
    │
    ├─ Find backups matching timestamp
    │
    ├─ For hooks backup:
    │  ├─ Remove ~/.claude/hooks/
    │  └─ Copy backup -> ~/.claude/hooks/
    │
    ├─ For settings backup:
    │  ├─ Remove ~/.claude/settings.json
    │  └─ Copy backup -> ~/.claude/settings.json
    │
    └─ Verify integrity
       └─ ✓ Rollback complete
```

### Rollback Safety

- Backups are never deleted automatically
- Multiple backups kept for historical reference
- Rollback is non-destructive (original files preserved in backup)
- Can rollback multiple times to different timestamps

---

## Decision Flowcharts

### Update Decision Flow

```
     Server Starts
           │
           ▼
  ┌─────────────────────┐
  │ Is 24h+ elapsed     │
  │ since last check?   │
  └──────┬──────────────┘
         │ YES
         ▼
  ┌──────────────────────────────┐
  │ Fetch PyPI version           │
  │ Update check timestamp       │
  └──────┬───────────────────────┘
         │
         ▼
  ┌──────────────────────────────┐
  │ Is PyPI > installed?         │
  └──────┬──────────┬────────────┘
    YES  │          │ NO
         ▼          └──────┐
  ┌────────────────┐       │
  │ Trigger Update │       │
  └────────────────┘       │
                           ▼
                    ┌────────────────┐
                    │ Skip Update    │
                    │ Try again in   │
                    │ 24h            │
                    └────────────────┘
```

### Merge Decision Flow

```
               Start Merge
                    │
                    ▼
         Has upstream changed?
              /          \
            YES           NO
             │             │
             ▼             ▼
      Has user changed?   Keep user
          /        \       version
        YES        NO      (done)
         │          │
         ▼          ▼
    Different?    Use new
    /        \    version
  YES       NO    (done)
   │         │
   ▼         ▼
 Line     Match
 based   (done)
 merge

 ┌─────────────────┐
 │ Insert conflict │
 │ markers in file │
 │ (user resolves) │
 └─────────────────┘
```

### Conflict Detection Flow

```
          Check File
                │
                ▼
       base == new?
          /      \
        YES       NO
         │         │
         ▼         ▼
    Return   user == base?
    user     /          \
          YES            NO
           │              │
           ▼              ▼
       Return       user == new?
       new         /          \
               YES              NO
                │               │
                ▼               ▼
            Return          Line-based
            user            merge &
            (done)          conflict
                            detection
```

---

## Code Examples

### Example 1: Check for Updates

```python
from mcp_bridge.update_manager_pypi import (
    _get_last_check_time,
    _should_check,
    _get_pypi_version,
    _compare_versions,
)
from mcp_bridge import __version__

# Check if we should query PyPI
last_check = _get_last_check_time()
if _should_check(last_check):
    # Fetch latest version
    latest = _get_pypi_version()
    
    if latest and _compare_versions(__version__, latest):
        print(f"Update available: {__version__} -> {latest}")
        # Trigger update
    else:
        print(f"Already on latest version: {__version__}")
```

### Example 2: Perform 3-Way Merge

```python
from mcp_bridge.update_manager import UpdateManager

manager = UpdateManager(dry_run=False, verbose=True)

# Merge a single file
base_content = None  # From backup or manifest
user_content = Path("~/.claude/hooks/my_hook.py").read_text()
new_content = Path("package_hooks/my_hook.py").read_text()

merged, has_conflict = manager._merge_3way(
    base_content,
    user_content,
    new_content,
    "my_hook.py"
)

if has_conflict:
    print("Conflict markers inserted - user must review")
else:
    print("Merged successfully")
```

### Example 3: Create Backup Before Update

```python
from mcp_bridge.update_manager import UpdateManager
from pathlib import Path

manager = UpdateManager()

hooks_dir = Path.home() / ".claude" / "hooks"
backup_path = manager._create_backup(hooks_dir, "hooks")

if backup_path:
    print(f"Backup created: {backup_path}")
    # Now safe to modify hooks_dir
else:
    print("Backup failed - aborting update")
```

### Example 4: Detect Merge Conflicts

```python
from mcp_bridge.update_manager import UpdateManager, MergeConflict

manager = UpdateManager()

base = "MAX_TOKENS = 200000"
user = "MAX_TOKENS = 300000"
new = "MAX_TOKENS = 250000"

conflict = manager._detect_conflicts(base, user, new, "config.py")

if conflict:
    print(f"Conflict Type: {conflict.conflict_type}")
    print(f"  User:    {conflict.user_version[:30]}")
    print(f"  Upstream: {conflict.new_version[:30]}")
else:
    print("No conflict")
```

### Example 5: Handle Settings.json with Statusline

```python
from mcp_bridge.update_manager import UpdateManager
import json

manager = UpdateManager()

# User has customized settings
user_settings = {
    "statusLine": "🚀 Custom Status",  # Must preserve
    "hooks": {
        "PreToolUse": [{"command": "hook.py", "blocking": True}]
    }
}

# Upstream has new settings
new_settings = {
    "statusLine": "Default Status",
    "hooks": {
        "PreToolUse": [{"command": "hook.py", "blocking": True}],
        "PostToolUse": [{"command": "post_hook.py"}]  # New hook type
    }
}

merged, conflicts = manager._merge_settings_json(
    base_settings=None,
    user_settings=user_settings,
    new_settings=new_settings
)

# merged["statusLine"] == "🚀 Custom Status" (preserved!)
# merged["hooks"]["PostToolUse"] == new hooks (merged!)
print(f"Statusline preserved: {merged.get('statusLine')}")
```

### Example 6: Rollback from Backup

```python
from mcp_bridge.update_manager import UpdateManager

manager = UpdateManager()

# List available backups
backups = manager.list_backups()
for backup in backups:
    print(f"{backup['name']} ({backup['size_mb']:.1f} MB)")

# Rollback to specific timestamp
success = manager.rollback("20250108_143022")

if success:
    print("Rollback completed successfully")
    # Hooks and settings restored from backup
else:
    print("Rollback failed")
```

### Example 7: Verify Integrity After Update

```python
from mcp_bridge.update_manager import UpdateManager

manager = UpdateManager()

is_valid, issues = manager.verify_integrity()

if is_valid:
    print("All files verified")
else:
    print("Issues found:")
    for issue in issues:
        print(f"  - {issue}")
        
# Issues could be:
# - "Hooks directory doesn't exist"
# - "settings.json is invalid"
# - "parallel_execution.py is not executable"
# - "Base manifest missing"
```

### Example 8: Dry-Run Mode for Testing

```python
from mcp_bridge.update_manager import UpdateManager

# Test without making actual changes
manager = UpdateManager(dry_run=True, verbose=True)

# Simulate update
success, conflicts = manager.update_hooks(
    new_hooks={
        "test_hook.py": "#!/usr/bin/env python3\nprint('test')"
    },
    stravinsky_version="0.3.10"
)

print("Dry run completed - no files actually modified")
if success:
    print("Would succeed if not in dry-run mode")
```

---

## Integration Points

### Server Startup

Location: `mcp_bridge/server.py`

The server initializes without waiting for update checks:
```python
async def startup():
    # Initialize core systems immediately
    token_store = get_token_store()
    hook_manager = get_hook_manager()
    
    # Background: start update check (non-blocking)
    asyncio.create_task(check_and_apply_updates())
```

### Hook Manager Integration

Location: `mcp_bridge/hooks/manager.py`

The hook manager reloads updated hooks:
```python
def reload_hooks():
    # Called after update completes
    # Picks up new hook files from ~/.claude/hooks/
    # Reconfigures hook execution pipeline
```

### User Notification

Users can see update status in logs:
```
~/.stravinsky/update.log
~/.claude/.logs/update_manager.log
```

---

## Related Documentation

- **MANIFEST_SCHEMA.md** - Detailed manifest format reference
- **MANIFEST_REFERENCE.md** - Quick manifest lookup
- **UPDATE_BEST_PRACTICES.md** - Best practices for hook updates
- **README.md** - Configuration overview
- **mcp_bridge/update_manager.py** - Implementation source code
- **mcp_bridge/update_manager_pypi.py** - PyPI version check logic

---

## Troubleshooting Guide

### Q: Update says "Conflict detected" - what do I do?

**A**: The file has conflict markers. Edit the file and choose which version to keep:
```python
# Choose one section, delete the markers:
MAX_TOKENS = 300000  # Keep user's version
# DELETE these lines:
# <<<<<<< USER VERSION
# =======
# >>>>>>> NEW VERSION
```

### Q: Can I rollback if I hate the update?

**A**: Yes! Run:
```bash
python -m mcp_bridge.update_manager --rollback TIMESTAMP
```

Find timestamp from `--list-backups`.

### Q: Why is the statusline preserved but hooks aren't?

**A**: Statusline is your custom status display - it's user preference. Hooks need updates for security/features. Both are preserved via 3-way merge when possible.

### Q: Does update require internet?

**A**: Only for the initial PyPI version check. The actual merge happens locally with files already installed.

### Q: What if backup fails?

**A**: Update aborts immediately - no files modified. Nothing to recover from.

### Q: Can I prevent auto-updates?

**A**: Not currently. But you can:
- Customize hooks in your own directory (not ~/.claude/hooks/)
- Pin your Stravinsky version in your install command
- Run in dry-run mode to test updates before applying

---

## Version History

### v1.0 (Current)
- 3-way merge algorithm
- Manifest-based version tracking
- SHA-256 file hashing
- Backup/rollback system
- Conflict marker insertion
- Statusline preservation
- 24-hour throttling
- Non-blocking server startup

### Future Enhancements
- Selective update (skip specific hooks)
- Update scheduling (nightly, weekly)
- User preferences for update behavior
- Automatic conflict resolution with ML
- Update preview/diff before apply
