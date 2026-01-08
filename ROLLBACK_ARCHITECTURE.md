# Stravinsky Rollback Architecture & Safety Guarantees

**Version**: 1.0
**Status**: Strategic Design
**Scope**: All package updates affecting hooks, commands, and settings
**Last Updated**: 2026-01-08

---

## Executive Summary

This document specifies a comprehensive, production-grade rollback mechanism with multi-layered safety guarantees. The system supports atomic version rollbacks, granular file-level recovery, transactional update semantics, and automatic error detection with self-healing capabilities.

**Key Guarantees**:
- ✅ **No data loss**: All user modifications preserved during updates/rollbacks
- ✅ **Atomic consistency**: Updates either fully complete or fully revert
- ✅ **Automatic recovery**: Detects failures and initiates rollback automatically
- ✅ **Audit completeness**: Every operation logged with timestamp, user, status, errors
- ✅ **Point-in-time recovery**: Can restore any previous version from backup history

---

## 1. Architecture Overview

### 1.1 Backup System

**Location Structure**:
```
~/.stravinsky/rollback/
├── backups/
│   ├── v0.3.8/
│   │   ├── hooks.tar.gz           # ~/.claude/hooks/ + .claude/hooks/
│   │   ├── commands.tar.gz        # ~/.claude/commands/ + .claude/commands/
│   │   ├── settings.json          # ~/.claude/settings.json + .claude/settings.json
│   │   └── manifest.json          # Metadata + checksums
│   ├── v0.3.9/
│   │   └── ...
│   └── latest.json                # Pointer to current version
├── audit/
│   ├── operations.log             # All update/rollback operations
│   └── audit.db                   # SQLite for querying operations
├── recovery/
│   ├── deltas/                    # Incremental change diffs (optional)
│   └── staging/                   # Temp space for in-progress operations
└── config.json                    # Rollback settings
```

**Storage Requirements**:
- **Per-version size**: ~5-50MB (typical hooks/commands + metadata)
- **Retention**: Last 10 versions (adjustable via config)
- **Total space estimate**: 50-500MB with rotation
- **Cleanup**: Auto-delete oldest version when exceeding max versions

### 1.2 Backup Metadata (manifest.json)

```json
{
  "version": "0.3.9",
  "timestamp": "2026-01-08T15:34:22Z",
  "python_version": "3.13",
  "system": "macOS-14.2-aarch64",
  "backup_type": "full",
  "files": {
    "hooks": {
      "path": "hooks.tar.gz",
      "size_bytes": 12345,
      "sha256": "abc123...",
      "files_count": 5,
      "timestamp": "2026-01-08T15:34:00Z"
    },
    "commands": {
      "path": "commands.tar.gz",
      "size_bytes": 23456,
      "sha256": "def456...",
      "files_count": 16,
      "timestamp": "2026-01-08T15:34:00Z"
    },
    "settings": {
      "path": "settings.json",
      "size_bytes": 1234,
      "sha256": "ghi789...",
      "timestamp": "2026-01-08T15:34:00Z"
    }
  },
  "pre_update_state": {
    "previous_version": "0.3.8",
    "user_modifications": [
      {
        "path": "~/.claude/commands/custom.md",
        "status": "user_added",
        "backed_up": true
      }
    ]
  },
  "integrity_checks": {
    "all_files_readable": true,
    "disk_space_available": 5000000000,
    "permissions_verified": true,
    "no_locks_detected": true
  }
}
```

---

## 2. Pre-Update Safety Checks

### 2.1 Pre-Update Validation Checklist

Before ANY update to hooks, commands, or settings:

```python
class PreUpdateValidator:
    async def run_all_checks(self) -> PreUpdateValidationResult:
        checks = [
            await self.check_disk_space(),           # Need 2x backup size
            await self.check_file_permissions(),     # Can read/write all targets
            await self.check_file_locks(),           # No files in use
            await self.check_backup_capacity(),      # Disk quota for backup
            await self.check_previous_backup(),      # Previous backups intact
            await self.check_hooks_syntax(),         # No malformed hooks
            await self.check_commands_validity(),    # All commands parse
            await self.check_settings_schema(),      # Settings comply with schema
        ]
        return combine_results(checks)
```

### 2.2 Individual Checks

#### 2.2.1 Disk Space Check
```
Requirement: Available disk space >= 2 × (hooks + commands + settings size)
Reason: Need space for backup + new version + safety margin
Action on failure: BLOCK update with user-friendly error
Recovery: Suggest cleaning old backups or freeing disk space
```

#### 2.2.2 File Permissions Check
```
Verify read access to:
- ~/.claude/hooks/ (recursive)
- .claude/hooks/ (recursive)
- ~/.claude/commands/ (recursive)
- .claude/commands/ (recursive)
- ~/.claude/settings.json
- .claude/settings.json

Verify write access to:
- ~/.stravinsky/rollback/backups/
- ~/.stravinsky/rollback/recovery/staging/
- ~/.stravinsky/rollback/audit/

Action on failure: BLOCK update, suggest chmod or re-run as proper user
```

#### 2.2.3 File Lock Detection
```
Using: fcntl.flock() on Unix / msvcrt.locking() on Windows
Check all affected files for active locks
Timeout: 5 seconds for lock check
Action on failure: WARN user, offer retry or force (with caution)
```

#### 2.2.4 Backup Capacity Check
```
Verify:
- At least 10-version retention possible (configurable)
- Total backup size won't exceed 500MB (configurable)
- No corrupted backups from previous operations
Action on failure: Auto-delete oldest backups until capacity available
```

#### 2.2.5 Previous Backup Integrity Check
```
For all existing backups:
- Verify manifest.json exists and is valid JSON
- Verify all referenced files exist
- Spot-check checksums on 10% random sample
- Verify backup tar archives not corrupted

Action on failure: Quarantine corrupted backup, log alert, continue with update
```

#### 2.2.6 Hooks Syntax Validation
```
For all hooks in ~/.claude/hooks/ and .claude/hooks/:
- Validate Markdown syntax
- Check for required hook sections
- Verify no infinite recursion patterns
- Test hook invocation without execution

Action on failure: BLOCK update if new hooks are malformed
```

#### 2.2.7 Commands Validity Check
```
For all commands in ~/.claude/commands/ and .claude/commands/:
- Parse Markdown headers
- Validate command ID uniqueness
- Check for required sections (description, usage)
- Verify no command name conflicts

Action on failure: WARN user about conflicts, allow override
```

#### 2.2.8 Settings Schema Validation
```
For ~/.claude/settings.json and .claude/settings.json:
- Validate against JSON schema
- Check all required fields present
- Verify no deprecated fields
- Type-check all values

Action on failure: BLOCK update if settings invalid
```

---

## 3. Backup Creation & Verification

### 3.1 Backup Creation Flow

```
1. Pre-flight checks (see section 2)
   ↓
2. Create staging directory: ~/.stravinsky/rollback/recovery/staging/{timestamp}/
   ↓
3. Copy source files to staging
   ├─ cp -r ~/.claude/hooks/ → staging/hooks/
   ├─ cp -r .claude/hooks/ → staging/project_hooks/
   ├─ cp -r ~/.claude/commands/ → staging/commands/
   ├─ cp -r .claude/commands/ → staging/project_commands/
   ├─ cp ~/.claude/settings.json → staging/settings.json
   └─ cp .claude/settings.json → staging/project_settings.json
   ↓
4. Compute checksums (SHA256) for all files
   ↓
5. Create tar.gz archives
   ├─ tar czf hooks.tar.gz -C staging hooks/ project_hooks/
   ├─ tar czf commands.tar.gz -C staging commands/ project_commands/
   └─ cp staging/settings.json settings.json (no compression, small file)
   ↓
6. Generate manifest.json with checksums and metadata
   ↓
7. Verify all files successfully created
   ↓
8. Move staging/{version}/ → backups/{version}/
   ↓
9. Update latest.json pointer
   ↓
10. Log operation to audit trail
```

### 3.2 Backup Integrity Verification

**Verification at creation time**:
```python
async def verify_backup_created(version: str) -> bool:
    """Post-backup verification"""
    backup_dir = Path.home() / ".stravinsky" / "rollback" / "backups" / version

    checks = [
        backup_dir.exists(),
        (backup_dir / "manifest.json").exists(),
        (backup_dir / "hooks.tar.gz").exists(),
        (backup_dir / "commands.tar.gz").exists(),
        (backup_dir / "settings.json").exists(),
        verify_manifest_schema(backup_dir / "manifest.json"),
        verify_tar_integrity(backup_dir / "hooks.tar.gz"),
        verify_tar_integrity(backup_dir / "commands.tar.gz"),
        verify_sha256_checksums(backup_dir),
    ]

    return all(checks)
```

**Recovery-time verification**:
```python
async def verify_backup_readable(version: str) -> bool:
    """Can this backup be restored?"""
    # Same checks plus:
    # - Attempt test extraction to temp dir
    # - Verify file count matches manifest
    # - Spot-check random files in extraction
```

---

## 4. Update Transaction Model

### 4.1 Atomic Update (All-or-Nothing)

**Approach**: Copy-on-write pattern with rollback stack

```
Phase 1: PREPARE
├─ Create backup of current state (if not already done)
├─ Run all pre-update checks (Section 2)
└─ Download new package files to staging area

Phase 2: VALIDATE
├─ Unpack new version to staging: ~/.stravinsky/rollback/recovery/staging/{new_version}/
├─ Run syntax/schema validation on new files
├─ Check no breaking changes to schemas
└─ Verify dependencies resolvable

Phase 3: SWAP (Atomic)
├─ Create recovery point with symlink to current
├─ Atomically replace with new files
│  └─ For each file: rename(old, old.bak) && rename(new, target)
│     (atomic at filesystem level on Unix)
├─ Verify new files in place
└─ Update version pointer in ~/.stravinsky/rollback/latest.json

Phase 4: VERIFY (Post-Update)
├─ Run all checks again (Section 2)
├─ Test hook invocation (dry-run)
├─ Test command parsing
├─ Verify settings readable
└─ If ANY failure → AUTOROLLBACK (Phase 5)

Phase 5: AUTOROLLBACK (if Phase 4 fails)
├─ Rename(new.bak → target) to restore previous version
├─ Verify restoration successful
├─ Log AUTOROLLBACK event with error details
└─ Alert user with recovery information
```

### 4.2 Atomic File Replacement Pattern

```python
def atomic_replace(target_path: Path, new_content: bytes) -> None:
    """Atomic file replacement using copy-on-write"""
    backup_path = target_path.with_suffix(target_path.suffix + '.bak')
    temp_path = target_path.parent / f".tmp.{uuid4().hex}"

    try:
        # Write to temp file first
        temp_path.write_bytes(new_content)

        # Atomic rename on Unix-like systems
        if target_path.exists():
            target_path.rename(backup_path)  # Atomic on same filesystem

        temp_path.rename(target_path)        # Atomic swap

        # Success - remove backup
        if backup_path.exists():
            backup_path.unlink()

    except Exception as e:
        # Recovery: restore from backup
        if backup_path.exists():
            backup_path.rename(target_path)
        if temp_path.exists():
            temp_path.unlink()
        raise
```

### 4.3 Directory-Level Atomicity

For multi-file updates (hooks, commands), use transaction log:

```python
class UpdateTransaction:
    def __init__(self, version: str):
        self.version = version
        self.tx_log = Path.home() / ".stravinsky" / "rollback" / f"tx.{version}.json"
        self.operations = []

    async def add_operation(self, op_type: str, target: Path, old_hash: str, new_hash: str):
        """Log each file operation"""
        self.operations.append({
            "type": op_type,  # "create" | "modify" | "delete"
            "path": str(target),
            "old_hash": old_hash,
            "new_hash": new_hash,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "pending"
        })
        self.tx_log.write_text(json.dumps(self.operations, indent=2))

    async def mark_operation_complete(self, path: Path):
        """Mark operation as durable"""
        for op in self.operations:
            if op["path"] == str(path):
                op["status"] = "complete"
        self.tx_log.write_text(json.dumps(self.operations, indent=2))

    async def rollback_incomplete(self):
        """Recover from partial failure"""
        for op in self.operations:
            if op["status"] != "complete":
                # Restore from backup hash
                self._restore_from_backup(Path(op["path"]), op["old_hash"])
        self.tx_log.unlink()
```

---

## 5. Rollback Procedures

### 5.1 Manual Rollback

**User-initiated rollback**:

```bash
# List available versions
stravinsky rollback list

# Show details of a version
stravinsky rollback show v0.3.8

# Rollback to specific version
stravinsky rollback to v0.3.8

# Rollback to previous version
stravinsky rollback undo
```

**Implementation**:

```python
async def manual_rollback(target_version: str) -> RollbackResult:
    """User-initiated rollback"""

    # 1. Verify backup exists and is readable
    backup_dir = get_backup_dir(target_version)
    if not backup_dir.exists():
        raise BackupNotFoundError(f"No backup for {target_version}")

    await verify_backup_readable(target_version)

    # 2. Create backup of CURRENT state (before rollback!)
    current_version = read_current_version()
    await create_backup(current_version)

    # 3. Run pre-rollback checks
    await PreUpdateValidator().run_all_checks()

    # 4. Extract and validate backup
    staging_dir = Path.home() / ".stravinsky" / "rollback" / "recovery" / "staging"
    await extract_backup(target_version, staging_dir)
    await validate_backup_contents(staging_dir)

    # 5. Perform atomic swap
    await atomic_swap_directories(staging_dir, target_paths)

    # 6. Post-rollback verification
    await verify_rollback_success(target_version)

    # 7. Log operation
    await log_rollback(
        from_version=current_version,
        to_version=target_version,
        status="success",
        timestamp=datetime.utcnow()
    )

    return RollbackResult(
        success=True,
        from_version=current_version,
        to_version=target_version,
        backup_created=f"{current_version}.pre-rollback"
    )
```

### 5.2 Automatic Rollback

**Triggered by**:
- Post-update verification failures
- Hook/command parsing errors
- Settings schema validation failures
- User-requested emergency rollback

**Flow**:

```python
async def auto_rollback(failed_version: str, error: Exception) -> None:
    """Automatic rollback on update failure"""

    previous_version = get_previous_version(failed_version)

    log_event(
        event_type="UPDATE_FAILED",
        version=failed_version,
        error=str(error),
        action="INITIATING_AUTO_ROLLBACK"
    )

    try:
        result = await manual_rollback(previous_version)

        log_event(
            event_type="AUTO_ROLLBACK_SUCCESS",
            from_version=failed_version,
            to_version=previous_version
        )

        # Alert user
        await notify_user(
            title="Update Failed - Automatic Rollback Completed",
            message=f"Rolled back to {previous_version} due to: {error}",
            level="warning"
        )

    except Exception as rollback_error:
        # CRITICAL: Rollback itself failed
        log_event(
            event_type="AUTO_ROLLBACK_FAILED",
            from_version=failed_version,
            error=str(rollback_error),
            level="critical"
        )

        await notify_user(
            title="CRITICAL: Rollback Failed",
            message=f"Automatic rollback failed: {rollback_error}\nManual recovery required.",
            level="critical"
        )

        # Provide recovery instructions
        await save_recovery_guide(previous_version, rollback_error)
```

---

## 6. Error Detection & Automatic Rollback Triggers

### 6.1 Error Detection Matrix

| Error Type | Detection | Auto-Rollback | Manual OK | Recovery |
|------------|-----------|---------------|-----------|----------|
| **Parse Error** (hooks/commands) | Syntax validation | ✅ Yes | ✅ Yes | Previous version |
| **Validation Error** (schema) | Schema check | ✅ Yes | ✅ Yes | Previous version |
| **Permission Error** | File access test | ❌ No | ✅ Manual | Chmod or user fix |
| **Disk Full** | Space check | ✅ Yes (undo backup) | ✅ Yes | Free space + retry |
| **Corrupted Backup** | Checksum failure | ❌ No | ✅ Manual | Restore older backup |
| **Lock Timeout** | fcntl/msvcrt check | ❌ No | ✅ Wait + retry | User intervention |
| **Dependency Failure** | Import test | ✅ Yes | ✅ Yes | Previous version |
| **Partial Write** | Transaction log | ✅ Yes | ✅ Yes | Use tx log to recover |
| **Version Mismatch** | Version file check | ✅ Yes | ✅ Yes | Sync version files |
| **Unknown Error** | Exception catch-all | ✅ Yes | ✅ Yes | Previous version |

### 6.2 Automatic Rollback Implementation

```python
async def run_post_update_verification(version: str) -> VerificationResult:
    """Comprehensive post-update checks with auto-rollback on failure"""

    checks = {
        "hooks_syntax": check_hooks_syntax,
        "commands_valid": check_commands_valid,
        "settings_schema": check_settings_schema,
        "dependencies": check_dependencies_resolvable,
        "file_permissions": check_file_permissions,
        "version_consistency": check_version_consistency,
    }

    failed_checks = []

    for check_name, check_fn in checks.items():
        try:
            result = await check_fn()
            if not result.success:
                failed_checks.append((check_name, result.error))
        except Exception as e:
            failed_checks.append((check_name, str(e)))

    if failed_checks:
        # Get version before this failed update
        previous_version = get_previous_version(version)

        # Initiate auto-rollback
        try:
            await auto_rollback(version, error=failed_checks[0][1])
            return VerificationResult(
                success=False,
                auto_rolled_back=True,
                rolled_back_to=previous_version,
                failures=failed_checks
            )
        except Exception as rollback_error:
            return VerificationResult(
                success=False,
                auto_rolled_back=False,
                rollback_error=str(rollback_error),
                failures=failed_checks,
                recovery_required=True
            )

    return VerificationResult(success=True)
```

---

## 7. Recovery Procedures

### 7.1 Three-Level Recovery Model

#### Level 1: Single-File Recovery
```python
async def recover_single_file(filepath: Path, backup_version: str = None) -> None:
    """Recover one file from backup"""

    if backup_version is None:
        # Use latest backup
        backup_version = get_latest_version()

    backup_dir = get_backup_dir(backup_version)
    manifest = load_manifest(backup_dir)

    # Find file in backup
    for category in ["hooks", "commands", "settings"]:
        if category in manifest["files"]:
            archive_path = backup_dir / manifest["files"][category]["path"]

            # Extract specific file from tar
            with tarfile.open(archive_path) as tar:
                for member in tar.getmembers():
                    if filepath.name in member.name:
                        tar.extract(member, path=filepath.parent)
                        return

    raise FileNotFoundError(f"{filepath} not found in backup {backup_version}")
```

#### Level 2: Directory Recovery
```python
async def recover_directory(dirpath: Path, backup_version: str = None) -> None:
    """Recover entire directory (hooks/, commands/, settings/) from backup"""

    if backup_version is None:
        backup_version = get_latest_version()

    backup_dir = get_backup_dir(backup_version)

    # Determine which archive contains this directory
    if "hooks" in str(dirpath):
        archive_name = "hooks.tar.gz"
    elif "commands" in str(dirpath):
        archive_name = "commands.tar.gz"
    else:
        raise ValueError(f"Unknown directory type: {dirpath}")

    archive_path = backup_dir / archive_name

    # Extract to staging, verify, then swap
    staging = Path.home() / ".stravinsky" / "rollback" / "recovery" / "staging"
    with tarfile.open(archive_path) as tar:
        tar.extractall(staging)

    # Verify extracted files
    await verify_directory_contents(staging / archive_name.replace(".tar.gz", ""))

    # Atomic swap
    dirpath.rename(dirpath.with_suffix(".bak"))
    (staging / archive_name.replace(".tar.gz", "")).rename(dirpath)
```

#### Level 3: Full Version Recovery
```python
async def recover_full_version(target_version: str) -> None:
    """Full rollback to previous version (see Section 5.2)"""
    await manual_rollback(target_version)
```

### 7.2 Recovery Decision Tree

```
User reports issue
│
├─ Single file corrupted?
│  └─ → Level 1: recover_single_file()
│
├─ Entire directory affected?
│  └─ → Level 2: recover_directory()
│
├─ Version fundamentally broken?
│  └─ → Level 3: recover_full_version()
│
└─ Backup itself corrupted?
   └─ → Emergency recovery (see Section 7.3)
```

### 7.3 Emergency Recovery (Corrupted Backup)

```python
async def emergency_recovery(current_version: str) -> None:
    """Recovery when backups are corrupted"""

    # Find oldest intact backup
    intact_backup = None
    for version in sorted_versions_asc():
        try:
            await verify_backup_readable(version)
            intact_backup = version
            break
        except CorruptedBackupError:
            log_event("CORRUPTED_BACKUP", version=version)
            continue

    if intact_backup is None:
        # No good backups - guide user through manual recovery
        await save_emergency_recovery_guide(current_version)
        raise RecoveryImpossibleError(
            "No intact backups found. See RECOVERY_GUIDE.md for manual steps."
        )

    # Rollback to oldest intact version
    log_event(
        "EMERGENCY_RECOVERY_INITIATED",
        from_version=current_version,
        to_version=intact_backup,
        reason="All recent backups corrupted"
    )

    await manual_rollback(intact_backup)
```

---

## 8. Audit Trail & Logging

### 8.1 Audit Log Schema

```json
{
  "event_id": "evt_abc123def456",
  "timestamp": "2026-01-08T15:34:22.123456Z",
  "event_type": "UPDATE_START|UPDATE_SUCCESS|UPDATE_FAILED|AUTO_ROLLBACK|MANUAL_ROLLBACK|VERIFICATION_FAILURE|RECOVERY_ATTEMPT",
  "version": "0.3.9",
  "previous_version": "0.3.8",
  "user": "user@example.com",
  "hostname": "MacBook.local",
  "python_version": "3.13",
  "operation_duration_seconds": 12.345,
  "status": "success|failed|rolled_back|recovered",
  "details": {
    "pre_checks": {
      "disk_space_mb": 5000,
      "file_count": 21,
      "backup_size_mb": 45
    },
    "operations": [
      {
        "type": "backup_create",
        "status": "success",
        "duration_ms": 234
      },
      {
        "type": "update_apply",
        "status": "success",
        "duration_ms": 567
      },
      {
        "type": "verification",
        "status": "success",
        "duration_ms": 345
      }
    ]
  },
  "error": null,
  "error_trace": null,
  "recovery_action": null,
  "backup_created": "v0.3.8.pre_update",
  "notes": "User-initiated update via CLI"
}
```

### 8.2 Audit Log Storage

**Primary storage**: `~/.stravinsky/rollback/audit/operations.log` (JSONL format)
- Each line is a complete JSON event
- Immutable append-only
- Rotated at 50MB or 90 days

**Secondary storage**: `~/.stravinsky/rollback/audit/audit.db` (SQLite)
- Indexed for querying
- Schema:
  ```sql
  CREATE TABLE audit_events (
    event_id TEXT PRIMARY KEY,
    timestamp DATETIME,
    event_type TEXT,
    version TEXT,
    status TEXT,
    operation_duration_seconds REAL,
    error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp),
    INDEX idx_event_type (event_type),
    INDEX idx_version (version),
    INDEX idx_status (status)
  );
  ```

### 8.3 Audit Trail Queries

```python
async def query_audit_trail(filters: AuditFilter) -> List[AuditEvent]:
    """Query audit log"""

    query = "SELECT * FROM audit_events WHERE 1=1"
    params = []

    if filters.event_type:
        query += " AND event_type = ?"
        params.append(filters.event_type)

    if filters.version:
        query += " AND version = ?"
        params.append(filters.version)

    if filters.start_date:
        query += " AND timestamp >= ?"
        params.append(filters.start_date.isoformat())

    if filters.end_date:
        query += " AND timestamp <= ?"
        params.append(filters.end_date.isoformat())

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(filters.limit or 1000)

    db = get_audit_db()
    return [AuditEvent.from_row(row) for row in db.execute(query, params)]
```

### 8.4 Audit Trail Retention

```
- **Hot storage** (last 90 days): ~/.stravinsky/rollback/audit/operations.log
- **Archive** (90+ days): ~/.stravinsky/rollback/audit/archive/operations.log.YYYY-MM-DD
- **Compression**: gzip after 90 days
- **Retention period**: 2 years (configurable)
- **Tamper detection**: SHA256 of each event + previous event hash (chain)
```

---

## 9. Configuration

### 9.1 Rollback Configuration File

**Location**: `~/.stravinsky/rollback/config.json`

```json
{
  "version": "1.0",
  "backup": {
    "max_versions": 10,
    "max_total_size_mb": 500,
    "retention_days": 365,
    "compression": "gzip",
    "verify_on_creation": true,
    "spot_check_percentage": 10
  },
  "update": {
    "auto_backup_before_update": true,
    "pre_update_checks_enabled": true,
    "post_update_verification_enabled": true,
    "auto_rollback_on_failure": true,
    "auto_rollback_timeout_seconds": 60
  },
  "recovery": {
    "enable_auto_recovery": true,
    "max_recovery_attempts": 3,
    "recovery_retry_delay_seconds": 5
  },
  "audit": {
    "enable_audit_logging": true,
    "log_retention_days": 730,
    "log_rotation_size_mb": 50,
    "tamper_detection_enabled": true
  },
  "safety": {
    "require_manual_confirmation_for_rollback": false,
    "fail_safe_on_backup_error": true,
    "disk_space_threshold_mb": 100,
    "lock_timeout_seconds": 5
  }
}
```

### 9.2 User Configuration Overrides

Users can customize via environment variables or config file:

```bash
# Environment variables
export STRAVINSKY_BACKUP_MAX_VERSIONS=15
export STRAVINSKY_AUTO_ROLLBACK=false
export STRAVINSKY_AUDIT_RETENTION_DAYS=1095

# Or edit ~/.stravinsky/rollback/config.json directly
```

---

## 10. Safety Guarantees

### 10.1 Data Loss Prevention

✅ **Guarantee**: User modifications to hooks/commands/settings are NEVER lost

**Mechanism**:
- Every file backed up BEFORE any update
- User modifications preserved in backup even if update changes schema
- Recovery possible from any point in time (within retention)

**Verification**:
```python
async def verify_no_data_loss(version_before: str, version_after: str) -> None:
    """Prove user data not lost"""

    # Load user-modified files from before backup
    before_backup = get_backup_dir(version_before)
    before_files = await extract_backup_metadata(before_backup)

    # Load current state after update
    current_files = await scan_current_state()

    # Verify all user files still accessible
    for user_file in before_files:
        # Either still in current state, or recoverable from backup
        assert (user_file in current_files or
                can_recover_from_backup(user_file, version_before))
```

### 10.2 Atomic Consistency

✅ **Guarantee**: Updates either fully complete or fully revert (no partial states)

**Mechanism**:
- Transaction log tracks all file operations
- Atomic filesystem operations (rename) for single files
- Directory-level consistency via staging → swap pattern
- Post-update verification ensures complete state

**Verification**:
```python
async def verify_atomic_consistency(version: str) -> None:
    """Verify no partial states after update"""

    # Check version consistency
    version_files = [
        Path.home() / ".stravinsky" / "rollback" / "latest.json",
        Path.home() / ".claude" / "version.txt",
        # ... etc
    ]

    versions = [read_version(f) for f in version_files]
    assert all(v == version for v in versions), "Version mismatch detected"

    # Check all expected files present
    manifest = load_manifest(get_backup_dir(version))
    for category, file_info in manifest["files"].items():
        file_path = Path(file_info["path"])
        assert file_path.exists(), f"Missing file: {file_path}"

        # Verify checksum
        computed = compute_sha256(file_path)
        assert computed == file_info["sha256"], f"Checksum mismatch: {file_path}"
```

### 10.3 Automatic Error Recovery

✅ **Guarantee**: Critical errors automatically trigger rollback without data loss

**Mechanism**:
- Post-update verification runs exhaustively
- Auto-rollback on any verification failure
- Previous version always available (just backed up)
- Error logged with recovery details

### 10.4 Audit Completeness

✅ **Guarantee**: Every operation logged with full traceability

**Mechanism**:
- All operations logged to immutable audit trail
- Chain-of-custody via event hashing
- Tamper detection via hash chain
- Full error context preserved

### 10.5 Point-in-Time Recovery

✅ **Guarantee**: Can restore any previous version within retention window

**Mechanism**:
- All versions backed up before update
- Configurable retention (default 2 years)
- Multiple recovery paths (file, directory, full version)
- Verified recovery (test extraction before final swap)

---

## 11. Implementation Roadmap

### Phase 1: Core Backup System (Foundation)
- [ ] Backup directory structure
- [ ] Pre-update validation checks (Sections 2-3)
- [ ] Manifest generation with checksums
- [ ] Backup creation and verification
- [ ] Audit logging infrastructure

### Phase 2: Atomic Updates (Safety)
- [ ] Transaction log implementation
- [ ] Atomic file replacement pattern
- [ ] Directory-level atomicity
- [ ] Post-update verification checks
- [ ] Auto-rollback on failure

### Phase 3: Recovery & Resilience
- [ ] Three-level recovery procedures
- [ ] Recovery decision tree
- [ ] Emergency recovery for corrupted backups
- [ ] Manual rollback CLI commands
- [ ] Recovery testing framework

### Phase 4: Configuration & Monitoring
- [ ] Configuration file system
- [ ] Audit log querying
- [ ] Retention policies
- [ ] Monitoring and alerting
- [ ] User notification system

### Phase 5: Testing & Hardening
- [ ] Chaos testing (simulate failures)
- [ ] Recovery procedure validation
- [ ] Edge case handling
- [ ] Performance optimization
- [ ] Documentation completion

---

## 12. Command Reference

### Backup Management

```bash
# List all backups
stravinsky backup list

# Show backup details
stravinsky backup show v0.3.8

# Create manual backup
stravinsky backup create

# Verify backup integrity
stravinsky backup verify v0.3.8

# Delete old backups
stravinsky backup cleanup --keep 5
```

### Rollback Operations

```bash
# List available versions for rollback
stravinsky rollback list

# Show rollback details
stravinsky rollback show v0.3.8

# Rollback to specific version
stravinsky rollback to v0.3.8

# Rollback to previous version
stravinsky rollback undo

# Automatic rollback (internal - triggered on failure)
stravinsky rollback auto v0.3.8
```

### Recovery Operations

```bash
# Recover single file
stravinsky recovery file ~/.claude/hooks/custom.md v0.3.8

# Recover directory
stravinsky recovery directory ~/.claude/hooks v0.3.8

# Full version recovery
stravinsky recovery version v0.3.8

# Emergency recovery guide
stravinsky recovery emergency
```

### Audit Trail

```bash
# Show recent operations
stravinsky audit log --limit 20

# Query by event type
stravinsky audit log --type UPDATE_FAILED

# Query by date range
stravinsky audit log --from 2026-01-01 --to 2026-01-08

# Export audit trail
stravinsky audit export --format csv > audit.csv
```

---

## 13. Testing & Validation

### 13.1 Test Coverage

```python
# Core backup functionality
test_create_backup()
test_verify_backup_integrity()
test_backup_checksum_validation()
test_backup_retention_policy()
test_backup_space_cleanup()

# Atomic updates
test_atomic_file_replacement()
test_atomic_directory_swap()
test_transaction_log_consistency()
test_partial_failure_recovery()

# Rollback procedures
test_manual_rollback_success()
test_auto_rollback_on_parse_error()
test_auto_rollback_on_schema_error()
test_rollback_to_arbitrary_version()

# Recovery
test_single_file_recovery()
test_directory_recovery()
test_full_version_recovery()
test_emergency_recovery()

# Audit trail
test_audit_event_logging()
test_audit_tamper_detection()
test_audit_log_rotation()
test_audit_querying()

# Error scenarios
test_disk_full_during_backup()
test_permission_denied_on_file()
test_corrupted_backup_detection()
test_version_mismatch_detection()
test_lock_timeout_handling()
```

### 13.2 Chaos Testing

```python
# Simulate failures during update
@chaos_test
def test_update_interrupted_mid_swap():
    """Kill process during atomic swap"""
    # Verify recovery is possible

@chaos_test
def test_backup_corruption_detected():
    """Corrupt backup during creation"""
    # Verify detection and handling

@chaos_test
def test_disk_full_during_update():
    """Simulate ENOSPC during file write"""
    # Verify rollback and cleanup

@chaos_test
def test_audit_log_write_failure():
    """Simulate audit logging failure"""
    # Verify update continues safely
```

---

## 14. Conclusion

This architecture provides **production-grade safety guarantees** for Stravinsky MCP Bridge updates:

1. **Data Safety**: Backups ensure user modifications never lost
2. **Consistency**: Atomic updates prevent partial states
3. **Reliability**: Auto-rollback handles failures gracefully
4. **Auditability**: Complete operation history for debugging
5. **Recoverability**: Multiple recovery paths for any scenario

The system is designed to make updates **safer than no update** by ensuring:
- ✅ Every backup verified before update
- ✅ Updates atomic at filesystem level
- ✅ Failures detected and rolled back automatically
- ✅ Recovery possible from any point in time
- ✅ Complete audit trail for accountability

---

## Appendix A: Glossary

- **Backup**: Complete copy of hooks, commands, settings at a point in time
- **Rollback**: Revert to previous version (manual or automatic)
- **Recovery**: Restore deleted/corrupted files from backup
- **Manifest**: Metadata file listing all files in backup with checksums
- **Atomic**: Either fully succeeds or fully fails (no partial states)
- **Transaction Log**: Records all file operations during update
- **Checksum**: SHA256 hash of file contents for integrity verification
- **Audit Trail**: Immutable log of all operations
- **Point-in-Time Recovery**: Ability to restore to any previous version

## Appendix B: Quick Reference

| Scenario | Command | Recovery Level |
|----------|---------|-----------------|
| Single file corrupted | `stravinsky recovery file <path>` | Level 1 |
| Directory broken | `stravinsky recovery directory <dir>` | Level 2 |
| Update failed | Auto-rollback triggered | Level 3 |
| Version mismatch | `stravinsky rollback undo` | Level 3 |
| All backups corrupted | `stravinsky recovery emergency` | Emergency |

---

**Document Version**: 1.0
**Status**: Strategic Design Ready for Implementation
**Next Phase**: Detailed implementation in `.claude/agents/rollback-architect.md`
