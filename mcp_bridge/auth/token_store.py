"""
Secure token storage using system keyring.

Stores OAuth tokens securely using the OS keyring:
- macOS: Keychain
- Linux: Secret Service (GNOME Keyring, KWallet)
- Windows: Windows Credential Locker
"""

import json
import time
from pathlib import Path
from typing import TypedDict

from cryptography.fernet import Fernet


class TokenData(TypedDict, total=False):
    """OAuth token data structure."""

    access_token: str
    refresh_token: str
    expires_at: float  # Unix timestamp
    token_type: str
    scope: str


class TokenStore:
    """
    Secure storage for OAuth tokens using system keyring with encrypted file fallback.

    Each provider (gemini, openai) stores its tokens separately.
    Tokens are serialized as JSON for storage.
    Falls back to encrypted file storage if keyring fails.
    """

    SERVICE_NAME = "stravinsky"
    FALLBACK_DIR = Path.home() / ".stravinsky" / "tokens"

    def __init__(self, service_name: str | None = None):
        """Initialize the token store.

        Args:
            service_name: Override the default service name for testing.
        """
        self.service_name = service_name or self.SERVICE_NAME
        self._init_fallback_storage()

    def _init_fallback_storage(self) -> None:
        """Initialize encrypted file storage fallback directory."""
        self.FALLBACK_DIR.mkdir(parents=True, exist_ok=True)

    def _get_fallback_path(self, provider: str) -> Path:
        """Get the path for encrypted fallback storage."""
        return self.FALLBACK_DIR / f"{provider}.enc"

    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key for fallback storage."""
        key_file = self.FALLBACK_DIR / ".key"
        if key_file.exists():
            return key_file.read_bytes()
        # Create new key and save it
        key = Fernet.generate_key()
        key_file.write_bytes(key)
        key_file.chmod(0o600)  # Read/write for owner only
        return key

    def _save_encrypted(self, provider: str, data: str) -> None:
        """Save data to encrypted file."""
        try:
            key = self._get_or_create_key()
            cipher = Fernet(key)
            encrypted = cipher.encrypt(data.encode())
            path = self._get_fallback_path(provider)
            path.write_bytes(encrypted)
            path.chmod(0o600)
        except Exception as e:
            raise RuntimeError(f"Failed to save encrypted token: {e}")

    def _load_encrypted(self, provider: str) -> str | None:
        """Load data from encrypted file."""
        try:
            path = self._get_fallback_path(provider)
            if not path.exists():
                return None
            key = self._get_or_create_key()
            cipher = Fernet(key)
            encrypted = path.read_bytes()
            decrypted = cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception:
            return None

    def _delete_encrypted(self, provider: str) -> bool:
        """Delete encrypted token file."""
        try:
            path = self._get_fallback_path(provider)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception:
            return False

    def _key(self, provider: str) -> str:
        """Generate the keyring key for a provider."""
        return f"{self.service_name}-{provider}"

    def get_token(self, provider: str) -> TokenData | None:
        """
        Retrieve stored token for a provider.

        Args:
            provider: The provider name (e.g., 'gemini', 'openai')

        Returns:
            TokenData if found and valid, None otherwise.
        """
        # Try keyring first (import inside try to catch backend initialization errors)
        try:
            import keyring
            data = keyring.get_password(self.service_name, self._key(provider))
            if data:
                return json.loads(data)
        except Exception:
            pass  # Fall back to encrypted file (catches KeyringError, import errors, etc.)

        # Fall back to encrypted file storage
        try:
            data = self._load_encrypted(provider)
            if data:
                return json.loads(data)
        except json.JSONDecodeError:
            pass

        return None

    def set_token(
        self,
        provider: str,
        token: TokenData | None = None,
        *,
        access_token: str | None = None,
        refresh_token: str | None = None,
        expires_at: float | None = None,
    ) -> None:
        """
        Store a token for a provider.

        Can be called with a TokenData dict or individual parameters.
        Falls back to encrypted file storage if keyring fails.

        Args:
            provider: The provider name (e.g., 'gemini', 'openai')
            token: The token data dict to store (optional)
            access_token: Access token string (optional)
            refresh_token: Refresh token string (optional)
            expires_at: Expiry timestamp (optional)
        """
        if token is not None:
            data = json.dumps(token)
        else:
            token_data: TokenData = {}
            if access_token:
                token_data["access_token"] = access_token
            if refresh_token:
                token_data["refresh_token"] = refresh_token
            if expires_at:
                token_data["expires_at"] = expires_at
            data = json.dumps(token_data)

        # Try keyring first, but always also write to encrypted storage
        # Import inside try to catch backend initialization errors (e.g., "No recommended backend")
        keyring_failed = False
        try:
            import keyring
            keyring.set_password(self.service_name, self._key(provider), data)
        except Exception:
            # Keyring failed - fall back to encrypted file
            keyring_failed = True

        # Always write to encrypted file storage as fallback
        try:
            self._save_encrypted(provider, data)
        except Exception as e:
            # Only fail if both backends failed
            if keyring_failed:
                raise RuntimeError(
                    f"Failed to save token to both keyring and encrypted storage: {e}"
                )


    def delete_token(self, provider: str) -> bool:
        """
        Delete stored token for a provider.

        Args:
            provider: The provider name (e.g., 'gemini', 'openai')

        Returns:
            True if deleted, False if not found.
        """
        # Try keyring first (import inside try to catch backend initialization errors)
        deleted_from_keyring = False
        try:
            import keyring
            keyring.delete_password(self.service_name, self._key(provider))
            deleted_from_keyring = True
        except Exception:
            # Keyring failed (no backend, delete error, etc.) - continue to encrypted file
            pass

        # Also delete from encrypted file storage
        deleted_from_file = self._delete_encrypted(provider)

        return deleted_from_keyring or deleted_from_file

    def has_valid_token(self, provider: str) -> bool:
        """
        Check if a valid (non-expired) token exists for a provider.

        Args:
            provider: The provider name

        Returns:
            True if a valid token exists.
        """
        token = self.get_token(provider)
        if not token:
            return False

        # Check if token has expired
        expires_at = token.get("expires_at", 0)
        if expires_at > 0 and time.time() > expires_at:
            return False

        return "access_token" in token

    def get_access_token(self, provider: str) -> str | None:
        """
        Get the access token for a provider, if valid.

        Args:
            provider: The provider name

        Returns:
            Access token string if valid, None otherwise.
        """
        token = self.get_token(provider)
        if not token:
            return None

        # Check expiration
        expires_at = token.get("expires_at", 0)
        if expires_at > 0 and time.time() > expires_at:
            return None

        return token.get("access_token")

    def needs_refresh(self, provider: str, buffer_seconds: int = 300) -> bool:
        """
        Check if a token needs refreshing.

        Args:
            provider: The provider name
            buffer_seconds: Refresh this many seconds before actual expiry

        Returns:
            True if token needs refresh or doesn't exist.
        """
        token = self.get_token(provider)
        if not token:
            return True

        expires_at = token.get("expires_at", 0)
        if expires_at <= 0:
            return False  # No expiry set, assume valid

        return time.time() > (expires_at - buffer_seconds)

    def update_access_token(
        self, provider: str, access_token: str, expires_in: int | None = None
    ) -> None:
        """
        Update just the access token (after refresh).

        Args:
            provider: The provider name
            access_token: New access token
            expires_in: Seconds until expiration (optional)
        """
        token = self.get_token(provider) or {}
        token["access_token"] = access_token
        if expires_in:
            token["expires_at"] = time.time() + expires_in
        self.set_token(provider, token)
