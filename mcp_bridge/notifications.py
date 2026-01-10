"""
Desktop Notifications Manager for Stravinsky.

Provides cross-platform desktop notifications (macOS, Linux, Windows)
for long-running operations like codebase indexing.

Supports:
- Non-blocking async notifications
- Platform-specific backends
- Notification queuing
"""

import logging
import platform
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Cross-platform desktop notification manager.
    
    Provides non-blocking notifications with automatic platform detection.
    """
    
    def __init__(self, app_name: str = "Stravinsky"):
        self.app_name = app_name
        self.system = platform.system()
    
    def _get_notification_command(
        self, 
        title: str, 
        message: str, 
        sound: bool = True
    ) -> list | None:
        """Get platform-specific notification command."""
        if self.system == "Darwin":  # macOS
            script = f'display notification "{message}" with title "{title}"'
            if sound:
                script += ' sound name "Glass"'
            return ["osascript", "-e", script]
        
        elif self.system == "Linux":
            cmd = ["notify-send", "--app-name", self.app_name, title, message]
            if sound:
                cmd.extend(["--urgency=normal"])
            return cmd
        
        elif self.system == "Windows":
            ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>{title}</text>
            <text>{message}</text>
        </binding>
    </visual>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{self.app_name}").Show($toast)
"""
            return ["powershell", "-Command", ps_script]
        
        return None
    
    def _send_notification_sync(
        self,
        title: str,
        message: str,
        sound: bool = True
    ) -> bool:
        """Send notification synchronously (blocking)."""
        cmd = self._get_notification_command(title, message, sound)
        
        if not cmd:
            logger.warning(
                f"[Notifications] Desktop notifications not supported on {self.system}"
            )
            return False
        
        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            logger.debug(f"[Notifications] Sent: {title}")
            return True
        except FileNotFoundError:
            logger.warning(f"[Notifications] Command not found: {cmd[0]}")
            return False
        except Exception as e:
            logger.error(f"[Notifications] Failed to send notification: {e}")
            return False
    
    async def notify_reindex_start(self, project_path: str) -> bool:
        """Notify that codebase reindexing has started."""
        path = Path(project_path).name or Path(project_path).parent.name
        title = "Codebase Indexing Started"
        message = f"Indexing {path}..."
        return self._send_notification_sync(title, message, sound=True)
    
    async def notify_reindex_complete(self, stats: dict) -> bool:
        """Notify that codebase reindexing is complete."""
        indexed = stats.get("indexed", 0)
        pruned = stats.get("pruned", 0)
        time_taken = stats.get("time_taken", 0)
        
        title = "Codebase Indexing Complete"
        message = f"Indexed {indexed} chunks, pruned {pruned} stale entries in {time_taken}s"
        
        return self._send_notification_sync(title, message, sound=True)
    
    async def notify_reindex_error(self, error_message: str) -> bool:
        """Notify that codebase reindexing failed."""
        title = "Codebase Indexing Failed"
        # Truncate long error messages
        message = error_message[:100] + "..." if len(error_message) > 100 else error_message
        
        return self._send_notification_sync(title, message, sound=True)


# Global singleton instance
_notification_manager: NotificationManager | None = None


def get_notification_manager() -> NotificationManager:
    """Get or create the global notification manager instance."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def reset_notification_manager() -> None:
    """Reset the global notification manager (for testing)."""
    global _notification_manager
    _notification_manager = None
