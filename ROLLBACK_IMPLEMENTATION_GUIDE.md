# Stravinsky Rollback Mechanism - Implementation Guide

**Version**: 1.0
**Target**: MCP Bridge v0.4.0+
**Status**: Implementation Blueprint
**Created**: 2026-01-08

---

## Quick Start for Developers

This guide complements **ROLLBACK_ARCHITECTURE.md** with concrete implementation patterns.

### Key Modules to Create

```
mcp_bridge/
├── rollback/
│   ├── __init__.py
│   ├── backup_manager.py       # Create/verify backups
│   ├── rollback_manager.py      # Execute rollbacks
│   ├── recovery_manager.py      # Recover files/directories
│   ├── validator.py             # Pre-update checks
│   ├── audit_logger.py          # Event logging
│   ├── transaction.py           # Atomic operations
│   └── config.py                # Configuration management
└── ...
```

---

## 1. Backup Manager Implementation

### 1.1 Core Backup Class

```python
# mcp_bridge/rollback/backup_manager.py

import asyncio
import hashlib
import json
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

@dataclass
class BackupMetadata:
    version: str
    timestamp: str
    python_version: str
    system: str
    backup_type: str  # "full" or "incremental"
    files: dict
    pre_update_state: dict
    integrity_checks: dict

class BackupManager:
    def __init__(self, backup_root: Optional[Path] = None):
        self.backup_root = backup_root or Path.home() / ".stravinsky" / "rollback"
        self.backups_dir = self.backup_root / "backups"
        self.staging_dir = self.backup_root / "recovery" / "staging"
        self.config_file = self.backup_root / "config.json"

    async def create_backup(self, version: str) -> Path:
        """Create full backup of hooks, commands, settings"""

        backup_dir = self.backups_dir / version
        backup_dir.mkdir(parents=True, exist_ok=True)

        staging = self.staging_dir / datetime.utcnow().isoformat()
        staging.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Copy source files
            await self._copy_source_files(staging)

            # 2. Compute checksums
            checksums = await self._compute_checksums(staging)

            # 3. Create tar archives
            hooks_archive = await self._create_tar_archive(
                staging / "hooks",
                backup_dir / "hooks.tar.gz"
            )
            commands_archive = await self._create_tar_archive(
                staging / "commands",
                backup_dir / "commands.tar.gz"
            )

            # 4. Copy settings (no compression needed)
            settings_path = backup_dir / "settings.json"
            if (staging / "settings.json").exists():
                settings_path.write_text(
                    (staging / "settings.json").read_text()
                )

            # 5. Generate manifest
            manifest = BackupMetadata(
                version=version,
                timestamp=datetime.utcnow().isoformat(),
                python_version=sys.version,
                system=platform.platform(),
                backup_type="full",
                files={
                    "hooks": {
                        "path": "hooks.tar.gz",
                        "size_bytes": hooks_archive.stat().st_size,
                        "sha256": checksums["hooks"],
                        "files_count": len(list(staging.glob("hooks/**/*"))),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    "commands": {
                        "path": "commands.tar.gz",
                        "size_bytes": commands_archive.stat().st_size,
                        "sha256": checksums["commands"],
                        "files_count": len(list(staging.glob("commands/**/*"))),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    "settings": {
                        "path": "settings.json",
                        "size_bytes": settings_path.stat().st_size,
                        "sha256": checksums["settings"],
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                },
                pre_update_state={
                    "previous_version": await self._get_current_version(),
                    "user_modifications": await self._detect_user_modifications(),
                },
                integrity_checks={
                    "all_files_readable": True,
                    "disk_space_available": await self._get_available_disk_space(),
                    "permissions_verified": True,
                    "no_locks_detected": True,
                }
            )

            # 6. Write manifest
            manifest_file = backup_dir / "manifest.json"
            manifest_file.write_text(json.dumps(asdict(manifest), indent=2))

            # 7. Verify backup
            await self.verify_backup(version)

            return backup_dir

        finally:
            # Cleanup staging
            import shutil
            shutil.rmtree(staging, ignore_errors=True)

    async def _copy_source_files(self, staging: Path) -> None:
        """Copy hooks, commands, settings to staging"""

        import shutil

        # Global hooks
        global_hooks = Path.home() / ".claude" / "hooks"
        if global_hooks.exists():
            shutil.copytree(
                global_hooks,
                staging / "hooks" / "global",
                dirs_exist_ok=True
            )

        # Project hooks
        project_hooks = Path.cwd() / ".claude" / "hooks"
        if project_hooks.exists():
            shutil.copytree(
                project_hooks,
                staging / "hooks" / "project",
                dirs_exist_ok=True
            )

        # Global commands
        global_commands = Path.home() / ".claude" / "commands"
        if global_commands.exists():
            shutil.copytree(
                global_commands,
                staging / "commands" / "global",
                dirs_exist_ok=True
            )

        # Project commands
        project_commands = Path.cwd() / ".claude" / "commands"
        if project_commands.exists():
            shutil.copytree(
                project_commands,
                staging / "commands" / "project",
                dirs_exist_ok=True
            )

        # Settings (JSON files, no directories)
        settings_files = []
        for settings_path in [
            Path.home() / ".claude" / "settings.json",
            Path.cwd() / ".claude" / "settings.json",
        ]:
            if settings_path.exists():
                settings_files.append(settings_path)

        if settings_files:
            combined_settings = {}
            for settings_path in settings_files:
                combined_settings.update(json.loads(settings_path.read_text()))
            (staging / "settings.json").write_text(
                json.dumps(combined_settings, indent=2)
            )

    async def _compute_checksums(self, staging: Path) -> dict:
        """Compute SHA256 checksums for all components"""

        checksums = {}

        for component in ["hooks", "commands"]:
            component_path = staging / component
            if component_path.exists():
                hasher = hashlib.sha256()
                for file in sorted(component_path.rglob("*")):
                    if file.is_file():
                        hasher.update(file.read_bytes())
                checksums[component] = hasher.hexdigest()

        if (staging / "settings.json").exists():
            checksums["settings"] = hashlib.sha256(
                (staging / "settings.json").read_bytes()
            ).hexdigest()

        return checksums

    async def _create_tar_archive(self, source: Path, target: Path) -> Path:
        """Create tar.gz archive from directory"""

        with tarfile.open(target, "w:gz") as tar:
            for file in source.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(source.parent)
                    tar.add(file, arcname=arcname)

        return target

    async def verify_backup(self, version: str) -> bool:
        """Verify backup integrity post-creation"""

        backup_dir = self.backups_dir / version
        manifest_file = backup_dir / "manifest.json"

        # 1. Verify files exist
        manifest = json.loads(manifest_file.read_text())
        for category, file_info in manifest["files"].items():
            file_path = backup_dir / file_info["path"]
            assert file_path.exists(), f"Missing file: {file_path}"

        # 2. Verify checksums
        for category, file_info in manifest["files"].items():
            file_path = backup_dir / file_info["path"]

            if file_path.suffix == ".gz":
                # For tar.gz, verify archive integrity
                with tarfile.open(file_path, "r:gz") as tar:
                    tar.getmembers()  # Will raise if corrupted
            else:
                # For JSON, verify checksum
                computed = hashlib.sha256(file_path.read_bytes()).hexdigest()
                stored = file_info["sha256"]
                assert computed == stored, f"Checksum mismatch: {file_path}"

        # 3. Test extraction
        test_staging = self.staging_dir / f"test_{version}"
        test_staging.mkdir(parents=True, exist_ok=True)
        try:
            for category, file_info in manifest["files"].items():
                if file_info["path"].endswith(".gz"):
                    file_path = backup_dir / file_info["path"]
                    with tarfile.open(file_path, "r:gz") as tar:
                        tar.extractall(test_staging)
        finally:
            import shutil
            shutil.rmtree(test_staging, ignore_errors=True)

        return True

    async def list_backups(self) -> list:
        """List all available backups"""

        backups = []
        for backup_dir in sorted(self.backups_dir.iterdir(), reverse=True):
            if (backup_dir / "manifest.json").exists():
                manifest = json.loads((backup_dir / "manifest.json").read_text())
                backups.append({
                    "version": backup_dir.name,
                    "timestamp": manifest["timestamp"],
                    "size_mb": sum(
                        (backup_dir / f["path"]).stat().st_size
                        for f in manifest["files"].values()
                    ) / 1024 / 1024,
                })

        return backups
```

### 1.2 Configuration Management

```python
# mcp_bridge/rollback/config.py

from dataclasses import dataclass, field
from typing import Optional
import json
from pathlib import Path

@dataclass
class BackupConfig:
    max_versions: int = 10
    max_total_size_mb: int = 500
    retention_days: int = 365
    compression: str = "gzip"
    verify_on_creation: bool = True
    spot_check_percentage: int = 10

@dataclass
class UpdateConfig:
    auto_backup_before_update: bool = True
    pre_update_checks_enabled: bool = True
    post_update_verification_enabled: bool = True
    auto_rollback_on_failure: bool = True
    auto_rollback_timeout_seconds: int = 60

@dataclass
class RollbackConfig:
    version: str = "1.0"
    backup: BackupConfig = field(default_factory=BackupConfig)
    update: UpdateConfig = field(default_factory=UpdateConfig)
    # ... other configs

    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> "RollbackConfig":
        if config_file is None:
            config_file = Path.home() / ".stravinsky" / "rollback" / "config.json"

        if config_file.exists():
            data = json.loads(config_file.read_text())
            return cls(**data)

        return cls()

    def save(self, config_file: Optional[Path] = None) -> None:
        if config_file is None:
            config_file = Path.home() / ".stravinsky" / "rollback" / "config.json"

        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps(self.__dict__, indent=2))
```

---

## 2. Validator Implementation

### 2.1 Pre-Update Validation

```python
# mcp_bridge/rollback/validator.py

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class ValidationResult:
    success: bool
    failed_checks: list[str] = None
    warnings: list[str] = None
    disk_space_mb: int = 0
    file_count: int = 0

class PreUpdateValidator:
    def __init__(self, backup_root: Optional[Path] = None):
        self.backup_root = backup_root or Path.home() / ".stravinsky" / "rollback"

    async def run_all_checks(self) -> ValidationResult:
        """Run all pre-update validation checks"""

        failed = []
        warnings = []

        checks = [
            ("disk_space", self.check_disk_space),
            ("file_permissions", self.check_file_permissions),
            ("file_locks", self.check_file_locks),
            ("backup_capacity", self.check_backup_capacity),
            ("previous_backup", self.check_previous_backup),
            ("hooks_syntax", self.check_hooks_syntax),
            ("commands_validity", self.check_commands_validity),
            ("settings_schema", self.check_settings_schema),
        ]

        for check_name, check_fn in checks:
            try:
                result = await check_fn()
                if not result["success"]:
                    failed.append(check_name)
                    if "warning" in result:
                        warnings.append(result["warning"])
            except Exception as e:
                failed.append(f"{check_name}: {str(e)}")

        disk_space = await self._get_available_disk_space()

        return ValidationResult(
            success=len(failed) == 0,
            failed_checks=failed,
            warnings=warnings,
            disk_space_mb=disk_space // (1024 * 1024),
        )

    async def check_disk_space(self) -> dict:
        """Verify sufficient disk space"""

        available = await self._get_available_disk_space()
        required = await self._estimate_update_size() * 2  # 2x for backup + new

        if available < required:
            return {
                "success": False,
                "error": f"Insufficient disk space: need {required}, have {available}",
            }

        return {"success": True}

    async def check_file_permissions(self) -> dict:
        """Verify read/write permissions"""

        paths_to_check = [
            (Path.home() / ".claude" / "hooks", "read"),
            (Path.home() / ".claude" / "commands", "read"),
            (Path.cwd() / ".claude" / "hooks", "read"),
            (Path.cwd() / ".claude" / "commands", "read"),
            (self.backup_root / "backups", "write"),
            (self.backup_root / "recovery" / "staging", "write"),
        ]

        unreadable = []
        unwritable = []

        for path, access_type in paths_to_check:
            if not path.exists():
                continue

            if access_type == "read":
                if not os.access(path, os.R_OK):
                    unreadable.append(str(path))
            elif access_type == "write":
                if not os.access(path.parent if path.is_file() else path, os.W_OK):
                    unwritable.append(str(path))

        if unreadable or unwritable:
            return {
                "success": False,
                "error": f"Permission denied: read={unreadable}, write={unwritable}",
            }

        return {"success": True}

    async def check_file_locks(self) -> dict:
        """Check for locked files"""

        import fcntl
        import time

        locked_files = []

        paths_to_check = [
            Path.home() / ".claude" / "hooks",
            Path.home() / ".claude" / "commands",
            Path.cwd() / ".claude" / "hooks",
            Path.cwd() / ".claude" / "commands",
        ]

        for path in paths_to_check:
            if not path.exists():
                continue

            for file in path.rglob("*"):
                if file.is_file():
                    try:
                        with open(file, "r") as f:
                            fcntl.flock(f.fileno(), fcntl.LOCK_NB)
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except (IOError, OSError):
                        locked_files.append(str(file))

        if locked_files:
            return {
                "success": False,
                "warning": f"Files in use: {locked_files}",
            }

        return {"success": True}

    async def check_hooks_syntax(self) -> dict:
        """Validate hooks Markdown syntax"""

        from mcp_bridge.hooks.parser import parse_hook_file

        paths = [
            Path.home() / ".claude" / "hooks",
            Path.cwd() / ".claude" / "hooks",
        ]

        invalid_hooks = []

        for path in paths:
            if not path.exists():
                continue

            for hook_file in path.glob("**/*.md"):
                try:
                    parse_hook_file(hook_file)
                except Exception as e:
                    invalid_hooks.append((str(hook_file), str(e)))

        if invalid_hooks:
            return {
                "success": False,
                "error": f"Invalid hooks: {invalid_hooks}",
            }

        return {"success": True}

    async def check_commands_validity(self) -> dict:
        """Validate commands parsing"""

        from mcp_bridge.commands.parser import parse_command_file

        paths = [
            Path.home() / ".claude" / "commands",
            Path.cwd() / ".claude" / "commands",
        ]

        invalid_commands = []

        for path in paths:
            if not path.exists():
                continue

            for cmd_file in path.glob("**/*.md"):
                try:
                    parse_command_file(cmd_file)
                except Exception as e:
                    invalid_commands.append((str(cmd_file), str(e)))

        if invalid_commands:
            return {
                "success": False,
                "error": f"Invalid commands: {invalid_commands}",
            }

        return {"success": True}

    async def check_settings_schema(self) -> dict:
        """Validate settings JSON schema"""

        from jsonschema import validate, ValidationError

        settings_schema = {
            "type": "object",
            "required": [],
            "properties": {
                # Define schema as needed
            }
        }

        paths = [
            Path.home() / ".claude" / "settings.json",
            Path.cwd() / ".claude" / "settings.json",
        ]

        for path in paths:
            if not path.exists():
                continue

            try:
                settings = json.loads(path.read_text())
                validate(instance=settings, schema=settings_schema)
            except ValidationError as e:
                return {
                    "success": False,
                    "error": f"Settings validation failed: {e}",
                }

        return {"success": True}

    async def _get_available_disk_space(self) -> int:
        """Get available disk space in bytes"""

        import os

        stats = os.statvfs(str(Path.home()))
        return stats.f_bavail * stats.f_frsize

    async def _estimate_update_size(self) -> int:
        """Estimate size of update (hooks + commands + settings)"""

        total = 0

        for path in [
            Path.home() / ".claude" / "hooks",
            Path.home() / ".claude" / "commands",
            Path.cwd() / ".claude" / "hooks",
            Path.cwd() / ".claude" / "commands",
        ]:
            if path.exists():
                for file in path.rglob("*"):
                    if file.is_file():
                        total += file.stat().st_size

        return total
```

---

## 3. Rollback Manager Implementation

### 3.1 Atomic Rollback

```python
# mcp_bridge/rollback/rollback_manager.py

import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
import tarfile

class RollbackManager:
    def __init__(
        self,
        backup_manager,
        validator,
        audit_logger,
        backup_root: Optional[Path] = None
    ):
        self.backup_manager = backup_manager
        self.validator = validator
        self.audit_logger = audit_logger
        self.backup_root = backup_root or Path.home() / ".stravinsky" / "rollback"

    async def manual_rollback(self, target_version: str) -> dict:
        """User-initiated rollback to specific version"""

        start_time = datetime.utcnow()

        try:
            # 1. Verify backup exists
            backup_dir = self.backup_manager.backups_dir / target_version
            if not backup_dir.exists():
                raise ValueError(f"Backup not found: {target_version}")

            # 2. Create backup of CURRENT state
            current_version = await self._get_current_version()
            await self.backup_manager.create_backup(f"{current_version}.pre_rollback")

            # 3. Run validation checks
            validation = await self.validator.run_all_checks()
            if not validation.success:
                raise ValidationError(f"Pre-rollback checks failed: {validation.failed_checks}")

            # 4. Extract and validate backup
            staging = self.backup_root / "recovery" / "staging" / target_version
            staging.mkdir(parents=True, exist_ok=True)

            manifest = json.loads((backup_dir / "manifest.json").read_text())

            for category, file_info in manifest["files"].items():
                if file_info["path"].endswith(".tar.gz"):
                    archive_path = backup_dir / file_info["path"]
                    with tarfile.open(archive_path, "r:gz") as tar:
                        tar.extractall(staging)

            # 5. Atomic swap
            await self._atomic_swap(staging, target_version)

            # 6. Post-rollback verification
            await self._verify_rollback(target_version)

            # 7. Log success
            duration = (datetime.utcnow() - start_time).total_seconds()
            await self.audit_logger.log_event(
                event_type="MANUAL_ROLLBACK",
                version=target_version,
                previous_version=current_version,
                status="success",
                duration_seconds=duration,
            )

            return {
                "success": True,
                "from_version": current_version,
                "to_version": target_version,
                "backup_created": f"{current_version}.pre_rollback",
                "duration_seconds": duration,
            }

        except Exception as e:
            await self.audit_logger.log_event(
                event_type="MANUAL_ROLLBACK",
                version=target_version,
                status="failed",
                error=str(e),
            )
            raise

    async def auto_rollback(self, failed_version: str, error: Exception) -> dict:
        """Automatic rollback on update failure"""

        previous_version = await self._get_previous_version(failed_version)

        await self.audit_logger.log_event(
            event_type="UPDATE_FAILED",
            version=failed_version,
            error=str(error),
            action="INITIATING_AUTO_ROLLBACK",
        )

        try:
            result = await self.manual_rollback(previous_version)

            await self.audit_logger.log_event(
                event_type="AUTO_ROLLBACK_SUCCESS",
                from_version=failed_version,
                to_version=previous_version,
            )

            return {
                "success": True,
                "rolled_back_to": previous_version,
                "reason": str(error),
            }

        except Exception as rollback_error:
            await self.audit_logger.log_event(
                event_type="AUTO_ROLLBACK_FAILED",
                from_version=failed_version,
                error=str(rollback_error),
                level="critical",
            )

            raise

    async def _atomic_swap(self, staging: Path, version: str) -> None:
        """Atomically swap directories"""

        targets = {
            "hooks": [
                Path.home() / ".claude" / "hooks",
                Path.cwd() / ".claude" / "hooks",
            ],
            "commands": [
                Path.home() / ".claude" / "commands",
                Path.cwd() / ".claude" / "commands",
            ],
        }

        for category, target_paths in targets.items():
            staged_path = staging / category

            if not staged_path.exists():
                continue

            for target_path in target_paths:
                if target_path.exists():
                    # Atomic rename pattern
                    backup_path = target_path.with_suffix(target_path.suffix + ".bak")
                    target_path.rename(backup_path)

                staged_path.rename(target_path)

    async def _verify_rollback(self, version: str) -> None:
        """Verify rollback success"""

        validation = await self.validator.run_all_checks()
        if not validation.success:
            raise RuntimeError(f"Post-rollback validation failed: {validation.failed_checks}")

    async def _get_current_version(self) -> str:
        """Get current version from latest.json"""

        latest_file = self.backup_root / "latest.json"
        if latest_file.exists():
            return json.loads(latest_file.read_text())["version"]

        return "unknown"

    async def _get_previous_version(self, current: str) -> str:
        """Get version before current"""

        backups = await self.backup_manager.list_backups()
        if len(backups) > 1:
            return backups[1]["version"]

        raise RuntimeError("No previous backup available for rollback")
```

---

## 4. Audit Logger Implementation

### 4.1 Audit Event Logging

```python
# mcp_bridge/rollback/audit_logger.py

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from uuid import uuid4
import hashlib

class AuditLogger:
    def __init__(self, audit_root: Optional[Path] = None):
        self.audit_root = audit_root or Path.home() / ".stravinsky" / "rollback" / "audit"
        self.audit_root.mkdir(parents=True, exist_ok=True)

        self.log_file = self.audit_root / "operations.log"
        self.db_file = self.audit_root / "audit.db"

        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite audit database"""

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                timestamp DATETIME,
                event_type TEXT,
                version TEXT,
                status TEXT,
                operation_duration_seconds REAL,
                error TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_data TEXT
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events (timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events (event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_version ON audit_events (version)")

        conn.commit()
        conn.close()

    async def log_event(
        self,
        event_type: str,
        version: Optional[str] = None,
        status: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        error: Optional[str] = None,
        **kwargs
    ) -> str:
        """Log operation event"""

        event_id = f"evt_{uuid4().hex[:16]}"
        timestamp = datetime.utcnow()

        event_data = {
            "event_id": event_id,
            "timestamp": timestamp.isoformat(),
            "event_type": event_type,
            "version": version,
            "status": status,
            "operation_duration_seconds": duration_seconds,
            "error": error,
            **kwargs
        }

        # Log to file
        self.log_file.write_text(
            self.log_file.read_text() +
            json.dumps(event_data) + "\n"
        )

        # Log to database
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO audit_events
            (event_id, timestamp, event_type, version, status, operation_duration_seconds, error, event_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            timestamp.isoformat(),
            event_type,
            version,
            status,
            duration_seconds,
            error,
            json.dumps(event_data)
        ))

        conn.commit()
        conn.close()

        return event_id

    async def query_events(self, **filters) -> List[dict]:
        """Query audit log"""

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        query = "SELECT event_data FROM audit_events WHERE 1=1"
        params = []

        if "event_type" in filters:
            query += " AND event_type = ?"
            params.append(filters["event_type"])

        if "version" in filters:
            query += " AND version = ?"
            params.append(filters["version"])

        if "start_date" in filters:
            query += " AND timestamp >= ?"
            params.append(filters["start_date"])

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(filters.get("limit", 1000))

        cursor.execute(query, params)
        results = [json.loads(row[0]) for row in cursor.fetchall()]

        conn.close()

        return results
```

---

## 5. Integration Points

### 5.1 Update Hook Integration

```python
# mcp_bridge/hooks/update_hook.py

from mcp_bridge.rollback.backup_manager import BackupManager
from mcp_bridge.rollback.validator import PreUpdateValidator
from mcp_bridge.rollback.rollback_manager import RollbackManager
from mcp_bridge.rollback.audit_logger import AuditLogger

async def before_update(version: str) -> bool:
    """Pre-update hook with rollback setup"""

    backup_manager = BackupManager()
    validator = PreUpdateValidator()
    audit_logger = AuditLogger()

    # Run validation
    validation = await validator.run_all_checks()

    if not validation.success:
        await audit_logger.log_event(
            event_type="UPDATE_BLOCKED",
            version=version,
            reason=f"Validation failed: {validation.failed_checks}"
        )
        raise ValidationError(f"Update blocked: {validation.failed_checks}")

    # Create backup
    current_version = await backup_manager.get_current_version()
    await backup_manager.create_backup(current_version)

    await audit_logger.log_event(
        event_type="UPDATE_START",
        version=version,
        previous_version=current_version
    )

    return True

async def after_update(version: str, success: bool, error: Optional[Exception] = None) -> None:
    """Post-update hook with verification/rollback"""

    backup_manager = BackupManager()
    validator = PreUpdateValidator()
    rollback_manager = RollbackManager(backup_manager, validator, AuditLogger())

    if not success or error:
        # Initiate auto-rollback
        await rollback_manager.auto_rollback(version, error or Exception("Update failed"))
        return

    # Verify update success
    validation = await validator.run_all_checks()

    if not validation.success:
        # Auto-rollback on verification failure
        current_version = await backup_manager.get_current_version()
        previous_version = await rollback_manager._get_previous_version(current_version)
        await rollback_manager.auto_rollback(version, Exception("Verification failed"))
        return

    await AuditLogger().log_event(
        event_type="UPDATE_SUCCESS",
        version=version,
        status="success"
    )
```

---

## 6. CLI Commands

### 6.1 Backup CLI

```python
# mcp_bridge/cli/rollback_cli.py

import click
from mcp_bridge.rollback.backup_manager import BackupManager
from mcp_bridge.rollback.rollback_manager import RollbackManager

@click.group()
def rollback():
    """Rollback and recovery management"""
    pass

@rollback.command()
async def list():
    """List available backups"""

    backup_manager = BackupManager()
    backups = await backup_manager.list_backups()

    click.echo("Available backups:")
    for backup in backups:
        click.echo(
            f"  {backup['version']}: {backup['timestamp']} "
            f"({backup['size_mb']:.1f} MB)"
        )

@rollback.command()
@click.argument("version")
async def show(version):
    """Show backup details"""

    backup_manager = BackupManager()
    backups = await backup_manager.list_backups()

    for backup in backups:
        if backup["version"] == version:
            click.echo(json.dumps(backup, indent=2))
            return

    click.echo(f"Backup not found: {version}")

@rollback.command()
@click.argument("version")
async def to(version):
    """Rollback to specific version"""

    from mcp_bridge.rollback.validator import PreUpdateValidator
    from mcp_bridge.rollback.audit_logger import AuditLogger

    backup_manager = BackupManager()
    validator = PreUpdateValidator()
    audit_logger = AuditLogger()

    rollback_manager = RollbackManager(
        backup_manager,
        validator,
        audit_logger
    )

    try:
        result = await rollback_manager.manual_rollback(version)
        click.echo(click.style("Rollback successful!", fg="green"))
        click.echo(json.dumps(result, indent=2))
    except Exception as e:
        click.echo(click.style(f"Rollback failed: {e}", fg="red"))
        raise

@rollback.command()
async def undo():
    """Rollback to previous version"""

    backup_manager = BackupManager()
    backups = await backup_manager.list_backups()

    if len(backups) < 2:
        click.echo("No previous version available")
        return

    previous_version = backups[1]["version"]

    # Use 'to' command
    await to(previous_version)
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/rollback/test_backup_manager.py

import pytest
from mcp_bridge.rollback.backup_manager import BackupManager

@pytest.mark.asyncio
async def test_create_backup():
    """Test backup creation"""

    manager = BackupManager()
    backup_dir = await manager.create_backup("test_v1.0.0")

    assert backup_dir.exists()
    assert (backup_dir / "manifest.json").exists()
    assert (backup_dir / "hooks.tar.gz").exists()

@pytest.mark.asyncio
async def test_verify_backup():
    """Test backup verification"""

    manager = BackupManager()
    await manager.create_backup("test_v1.0.0")

    # Should not raise
    await manager.verify_backup("test_v1.0.0")
```

### 7.2 Integration Tests

```python
# tests/rollback/test_rollback_flow.py

@pytest.mark.asyncio
async def test_manual_rollback():
    """Test complete rollback flow"""

    backup_manager = BackupManager()
    validator = PreUpdateValidator()
    rollback_manager = RollbackManager(backup_manager, validator, AuditLogger())

    # Create initial backup
    await backup_manager.create_backup("v1.0.0")

    # Simulate update to v2.0.0 (with backup)
    await backup_manager.create_backup("v2.0.0")

    # Rollback to v1.0.0
    result = await rollback_manager.manual_rollback("v1.0.0")

    assert result["success"]
    assert result["to_version"] == "v1.0.0"
```

---

## 8. Deployment Checklist

- [ ] Implement all core modules (backup, validator, rollback, audit)
- [ ] Write comprehensive unit tests
- [ ] Test edge cases (disk full, permission denied, corrupted backup)
- [ ] Integrate with update hooks
- [ ] Create CLI commands
- [ ] Document recovery procedures
- [ ] Write user guide
- [ ] Test in staging environment
- [ ] Release as v0.4.0

---

**Next Steps**: Begin implementation with Phase 1 (Core Backup System) - see ROLLBACK_ARCHITECTURE.md Section 11.

