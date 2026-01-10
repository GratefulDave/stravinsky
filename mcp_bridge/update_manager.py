#!/usr/bin/env python3
"""
Update Manager for Stravinsky Hooks and Skills

Safely merges hooks and skills during Stravinsky updates with:
- Version tracking via manifest files
- 3-way merge algorithm (base, user, new)
- User customization preservation
- Conflict detection and reporting
- Automatic backups before updates
- Rollback capability
- Dry-run mode for testing
- Comprehensive logging
"""

import json
import logging
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class MergeConflict:
    """Represents a merge conflict for a file."""
    file_path: str
    base_version: str | None
    user_version: str | None
    new_version: str | None
    conflict_type: str


@dataclass
class UpdateManifest:
    """Manifest tracking file versions and update status."""
    version: str
    timestamp: str
    files: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> 'UpdateManifest':
        return UpdateManifest(
            version=data.get('version', ''),
            timestamp=data.get('timestamp', ''),
            files=data.get('files', {})
        )


class UpdateManager:
    """Manages safe updates of hooks and skills with conflict detection and rollback."""

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        """Initialize update manager."""
        self.dry_run = dry_run
        self.verbose = verbose
        self.home = Path.home()
        self.global_claude_dir = self.home / ".claude"
        self.backup_dir = self.global_claude_dir / ".backups"
        self.manifest_dir = self.global_claude_dir / ".manifests"

        self.logger = self._setup_logging()

        if not self.dry_run:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            self.manifest_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> logging.Logger:
        """Setup logging with file and console output."""
        logger = logging.getLogger("stravinsky.update_manager")
        logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        logger.handlers.clear()

        log_dir = self.global_claude_dir / ".logs"
        if not self.dry_run:
            log_dir.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_dir / "update_manager.log")
            fh.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING if not self.verbose else logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        return logger

    def _hash_file(self, path: Path) -> str:
        """Generate hash of file content."""
        import hashlib
        try:
            content = path.read_bytes()
            return hashlib.sha256(content).hexdigest()[:16]
        except Exception:
            return "unknown"

    def _load_manifest(self, manifest_type: str) -> UpdateManifest | None:
        """Load manifest file (base, user, new)."""
        manifest_path = self.manifest_dir / f"{manifest_type}_manifest.json"

        if not manifest_path.exists():
            return None

        try:
            data = json.loads(manifest_path.read_text())
            return UpdateManifest.from_dict(data)
        except Exception as e:
            self.logger.error(f"Failed to load manifest: {e}")
            return None

    def _save_manifest(self, manifest: UpdateManifest, manifest_type: str) -> bool:
        """Save manifest file."""
        if self.dry_run:
            self.logger.debug(f"[DRY-RUN] Would save {manifest_type} manifest")
            return True

        manifest_path = self.manifest_dir / f"{manifest_type}_manifest.json"

        try:
            manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2))
            self.logger.info(f"Saved {manifest_type} manifest")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save manifest: {e}")
            return False

    def _create_backup(self, source_dir: Path, backup_name: str) -> Path | None:
        """Create timestamped backup of directory."""
        if self.dry_run:
            return None

        if not source_dir.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{backup_name}_{timestamp}"

        try:
            shutil.copytree(source_dir, backup_path)
            self.logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None

    def _read_file_safely(self, path: Path) -> str | None:
        """Read file with error handling."""
        try:
            if not path.exists():
                return None
            return path.read_text(encoding='utf-8')
        except Exception as e:
            self.logger.error(f"Failed to read {path}: {e}")
            return None

    def _write_file_safely(self, path: Path, content: str) -> bool:
        """Write file with error handling."""
        if self.dry_run:
            self.logger.debug(f"[DRY-RUN] Would write {len(content)} bytes to {path}")
            return True

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            path.chmod(0o755)
            self.logger.debug(f"Wrote {len(content)} bytes to {path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to write {path}: {e}")
            return False

    def _detect_conflicts(
        self,
        base: str | None,
        user: str | None,
        new: str | None,
        file_path: str
    ) -> MergeConflict | None:
        """Detect merge conflicts using 3-way merge logic."""
        if new == base:
            return None

        if user == base or user is None:
            return None

        if user == new:
            return None

        conflict_type = "different_modifications"
        if base is None and user is not None and new is not None:
            conflict_type = "added_both_ways"
        elif base is not None and user is None and new is not None:
            conflict_type = "deleted_vs_new"

        return MergeConflict(
            file_path=file_path,
            base_version=base[:50] if base else None,
            user_version=user[:50] if user else None,
            new_version=new[:50] if new else None,
            conflict_type=conflict_type
        )

    def _merge_3way(
        self,
        base: str | None,
        user: str | None,
        new: str | None,
        file_path: str
    ) -> tuple[str, bool]:
        """Perform 3-way merge on file content."""
        if base is None:
            if user is None:
                return new or "", False
            elif new is None or user == new:
                return user, False
            else:
                return self._format_conflict_markers(user, new), True

        if user is None:
            if new is None:
                return "", False
            else:
                return self._format_conflict_markers(None, new), True

        if new is None:
            return self._format_conflict_markers(user, None), True

        if base == new:
            return user, False

        if base == user:
            return new, False

        if user != new:
            merged, has_conflict = self._line_based_merge(base, user, new)
            return merged, has_conflict

        return user, False

    def _line_based_merge(self, base: str, user: str, new: str) -> tuple[str, bool]:
        """Perform line-based merge for text conflicts."""
        base_lines = base.splitlines(keepends=True)
        user_lines = user.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)

        merged = []
        has_conflict = False

        if len(base_lines) == len(user_lines) == len(new_lines):
            for i, (b, u, n) in enumerate(zip(base_lines, user_lines, new_lines)):
                if u == b == n:
                    merged.append(u)
                elif u == b and n != b:
                    merged.append(n)
                elif n == b and u != b or u == n:
                    merged.append(u)
                else:
                    merged.append(f"<<<<<<< {u}======= {n}>>>>>>> ")
                    has_conflict = True
        else:
            has_conflict = True
            merged.append("<<<<<<< USER VERSION\n")
            merged.extend(user_lines)
            merged.append("=======\n")
            merged.extend(new_lines)
            merged.append(">>>>>>> NEW VERSION\n")

        return "".join(merged), has_conflict

    def _format_conflict_markers(self, user: str | None, new: str | None) -> str:
        """Format conflict markers for display."""
        lines = ["<<<<<<< USER VERSION\n"]
        if user:
            lines.append(user)
            if not user.endswith('\n'):
                lines.append('\n')
        lines.append("=======\n")
        if new:
            lines.append(new)
            if not new.endswith('\n'):
                lines.append('\n')
        lines.append(">>>>>>> NEW VERSION\n")
        return "".join(lines)

    def _preserve_statusline(self, settings_file: Path) -> dict[str, Any] | None:
        """Read and preserve statusline from settings.json."""
        try:
            if not settings_file.exists():
                return None
            settings = json.loads(settings_file.read_text())
            statusline = settings.get("statusLine")
            if statusline:
                self.logger.debug(f"Preserved statusline: {statusline}")
            return statusline
        except Exception as e:
            self.logger.error(f"Failed to read statusline: {e}")
            return None

    def _merge_settings_json(
        self,
        base: dict[str, Any] | None,
        user: dict[str, Any] | None,
        new: dict[str, Any] | None
    ) -> tuple[dict[str, Any], list[MergeConflict]]:
        """Merge settings.json with special handling for hooks and statusline."""
        conflicts = []

        if base is None:
            base = {}
        if user is None:
            user = {}
        if new is None:
            new = {}

        merged = {}

        if "statusLine" in user:
            merged["statusLine"] = user["statusLine"]
            self.logger.debug("Preserved user statusLine")
        elif "statusLine" in new:
            merged["statusLine"] = new["statusLine"]

        user_hooks = user.get("hooks", {})
        new_hooks = new.get("hooks", {})
        base_hooks = base.get("hooks", {})

        merged_hooks = {}

        for hook_type in set(list(user_hooks.keys()) + list(new_hooks.keys()) + list(base_hooks.keys())):
            user_type_hooks = user_hooks.get(hook_type, [])
            new_type_hooks = new_hooks.get(hook_type, [])
            base_type_hooks = base_hooks.get(hook_type, [])

            merged_type_hooks = user_type_hooks.copy()

            for new_hook in new_type_hooks:
                if new_hook not in base_type_hooks and new_hook not in merged_type_hooks:
                    merged_type_hooks.append(new_hook)
                    self.logger.debug(f"Added new {hook_type} hook")

            if merged_type_hooks:
                merged_hooks[hook_type] = merged_type_hooks

        if merged_hooks:
            merged["hooks"] = merged_hooks

        for key in set(list(user.keys()) + list(new.keys()) + list(base.keys())):
            if key in ("hooks", "statusLine"):
                continue

            if key in user:
                merged[key] = user[key]
            elif key in new:
                merged[key] = new[key]

        return merged, conflicts

    def update_hooks(
        self,
        new_hooks: dict[str, str],
        stravinsky_version: str
    ) -> tuple[bool, list[MergeConflict]]:
        """Update hooks with 3-way merge and conflict detection."""
        self.logger.info(f"Starting hooks update to version {stravinsky_version}")

        hooks_dir = self.global_claude_dir / "hooks"
        conflicts = []

        backup_path = self._create_backup(hooks_dir, "hooks")

        base_manifest = self._load_manifest("base")

        updated_files = {}

        for filename, new_content in new_hooks.items():
            hook_path = hooks_dir / filename

            base_content = None
            user_content = self._read_file_safely(hook_path)

            if base_manifest:
                base_file_hash = base_manifest.files.get(filename)
                if base_file_hash and backup_path:
                    base_path = backup_path / filename
                    base_content = self._read_file_safely(base_path)

            conflict = self._detect_conflicts(base_content, user_content, new_content, filename)
            if conflict:
                conflicts.append(conflict)
                self.logger.warning(f"Conflict detected in {filename}: {conflict.conflict_type}")

            merged_content, has_conflict = self._merge_3way(
                base_content,
                user_content,
                new_content,
                filename
            )

            if self._write_file_safely(hook_path, merged_content):
                updated_files[filename] = self._hash_file(hook_path)
                if has_conflict:
                    self.logger.warning(f"Updated {filename} with conflict markers")
                else:
                    self.logger.info(f"Updated {filename}")
            else:
                self.logger.error(f"Failed to write {filename}")
                return False, conflicts

        new_manifest = UpdateManifest(
            version=stravinsky_version,
            timestamp=datetime.now().isoformat(),
            files=updated_files
        )

        if not self._save_manifest(new_manifest, "base"):
            return False, conflicts

        self.logger.info(f"Hooks update completed ({len(updated_files)} files updated)")
        return True, conflicts

    def update_settings_json(self, new_settings: dict[str, Any]) -> tuple[bool, list[MergeConflict]]:
        """Update settings.json with hook merging and statusline preservation."""
        self.logger.info("Starting settings.json update")

        settings_file = self.global_claude_dir / "settings.json"

        self._create_backup(settings_file.parent, "settings")

        user_settings = {}
        if settings_file.exists():
            try:
                user_settings = json.loads(settings_file.read_text())
            except Exception as e:
                self.logger.error(f"Failed to parse settings.json: {e}")

        base_settings = {}

        merged_settings, conflicts = self._merge_settings_json(
            base_settings or None,
            user_settings or None,
            new_settings or None
        )

        if self._write_file_safely(settings_file, json.dumps(merged_settings, indent=2)):
            self.logger.info("Updated settings.json")
            return True, conflicts
        else:
            self.logger.error("Failed to write settings.json")
            return False, conflicts

    def rollback(self, backup_timestamp: str) -> bool:
        """Rollback to a previous backup."""
        if self.dry_run:
            self.logger.info(f"[DRY-RUN] Would rollback to {backup_timestamp}")
            return True

        self.logger.info(f"Rolling back to backup {backup_timestamp}")

        backups = list(self.backup_dir.glob(f"*_{backup_timestamp}"))

        if not backups:
            self.logger.error(f"No backups found for timestamp {backup_timestamp}")
            return False

        success = True
        for backup_path in backups:
            try:
                if "hooks" in backup_path.name:
                    restore_dir = self.global_claude_dir / "hooks"
                elif "settings" in backup_path.name:
                    restore_dir = self.global_claude_dir
                else:
                    continue

                if restore_dir.exists():
                    shutil.rmtree(restore_dir)

                shutil.copytree(backup_path, restore_dir)
                self.logger.info(f"Restored from {backup_path}")
            except Exception as e:
                self.logger.error(f"Failed to restore from backup: {e}")
                success = False

        return success

    def verify_integrity(self) -> tuple[bool, list[str]]:
        """Verify integrity of installed hooks and settings."""
        issues = []
        hooks_dir = self.global_claude_dir / "hooks"
        settings_file = self.global_claude_dir / "settings.json"

        if not hooks_dir.exists():
            issues.append("Hooks directory doesn't exist")
            return False, issues

        if not settings_file.exists():
            issues.append("settings.json doesn't exist")
            return False, issues

        try:
            json.loads(settings_file.read_text())
        except Exception as e:
            issues.append(f"settings.json is invalid: {e}")
            return False, issues

        if not self._load_manifest("base"):
            issues.append("Base manifest missing")

        for hook_file in hooks_dir.glob("*.py"):
            if not (hook_file.stat().st_mode & 0o111):
                issues.append(f"{hook_file.name} is not executable")

        return len(issues) == 0, issues

    def list_backups(self) -> list[dict[str, Any]]:
        """List all available backups."""
        backups = []

        if not self.backup_dir.exists():
            return backups

        for backup_path in sorted(self.backup_dir.iterdir(), reverse=True):
            if backup_path.is_dir():
                stat = backup_path.stat()
                size_mb = sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file()) / (1024 * 1024)
                backups.append({
                    "name": backup_path.name,
                    "size_mb": size_mb,
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        return backups


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Stravinsky Update Manager")
    parser.add_argument("--dry-run", action="store_true", help="Don't make actual changes")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--verify", action="store_true", help="Verify integrity")
    parser.add_argument("--list-backups", action="store_true", help="List backups")
    parser.add_argument("--rollback", type=str, help="Rollback to backup")

    args = parser.parse_args()

    manager = UpdateManager(dry_run=args.dry_run, verbose=args.verbose)

    if args.verify:
        is_valid, issues = manager.verify_integrity()
        print(f"Integrity: {'✓ Valid' if is_valid else '✗ Invalid'}")
        for issue in issues:
            print(f"  - {issue}")
        return 0 if is_valid else 1

    if args.list_backups:
        backups = manager.list_backups()
        if not backups:
            print("No backups found")
        else:
            print(f"Found {len(backups)} backups:")
            for backup in backups:
                print(f"  {backup['name']} ({backup['size_mb']:.1f} MB)")
        return 0

    if args.rollback:
        success = manager.rollback(args.rollback)
        print(f"Rollback: {'✓ Success' if success else '✗ Failed'}")
        return 0 if success else 1

    print("Use --verify, --list-backups, or --rollback")
    return 0


if __name__ == "__main__":
    sys.exit(main())
