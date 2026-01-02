"""
Secure token storage using system keyring.

Stores OAuth tokens securely using the OS keyring:
- macOS: Keychain
- Linux: Secret Service (GNOME Keyring, KWallet)
- Windows: Windows Credential Locker
"""

import json
import time
from typing import TypedDict

import keyring


class TokenData(TypedDict, total=False):
    """OAuth token data structure."""

    access_token: str
    refresh_token: str
    expires_at: float  # Unix timestamp
    token_type: str
    scope: str


class TokenStore:
    """
    Secure storage for OAuth tokens using system keyring.

    Each provider (gemini, openai) stores its tokens separately.
    Tokens are serialized as JSON for storage.
    """

    SERVICE_NAME = "stravinsky"

    def __init__(self, service_name: str | None = None):
        """Initialize the token store.

        Args:
            service_name: Override the default service name for testing.
        """
        self.service_name = service_name or self.SERVICE_NAME

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
        try:
            data = keyring.get_password(self.service_name, self._key(provider))
            if not data:
                return None
            return json.loads(data)
        except (json.JSONDecodeError, keyring.errors.KeyringError):
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
        keyring.set_password(self.service_name, self._key(provider), data)

    def delete_token(self, provider: str) -> bool:
        """
        Delete stored token for a provider.

        Args:
            provider: The provider name (e.g., 'gemini', 'openai')

        Returns:
            True if deleted, False if not found.
        """
        try:
            keyring.delete_password(self.service_name, self._key(provider))
            return True
        except keyring.errors.PasswordDeleteError:
            return False

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
