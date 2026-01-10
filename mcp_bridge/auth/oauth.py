"""
Antigravity OAuth 2.0 Implementation with PKCE

Implements Google OAuth for Antigravity (Gemini) authentication.
Based on the original TypeScript implementation from Stravinsky.
"""

import base64
import hashlib
import json
import os
import secrets
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

# OAuth 2.0 Client Credentials (from constants.ts)
ANTIGRAVITY_CLIENT_ID = "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
ANTIGRAVITY_CLIENT_SECRET = "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"

# OAuth Callback
ANTIGRAVITY_CALLBACK_PORT = 51121

# OAuth Scopes
ANTIGRAVITY_SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
]

# API Endpoints
# NOTE: Prefer production; sandbox endpoints may require special access.
ANTIGRAVITY_ENDPOINT_PROD = "https://cloudcode-pa.googleapis.com"
ANTIGRAVITY_ENDPOINT_DAILY = "https://daily-cloudcode-pa.sandbox.googleapis.com"
ANTIGRAVITY_ENDPOINT_AUTOPUSH = "https://autopush-cloudcode-pa.sandbox.googleapis.com"

# Default to production only.
# Set STRAVINSKY_ANTIGRAVITY_ENABLE_SANDBOX_ENDPOINTS=1 to also try sandbox endpoints.
ANTIGRAVITY_ENDPOINTS = [
    ANTIGRAVITY_ENDPOINT_PROD,
]

if os.getenv("STRAVINSKY_ANTIGRAVITY_ENABLE_SANDBOX_ENDPOINTS") in {"1", "true", "True"}:
    ANTIGRAVITY_ENDPOINTS.extend(
        [
            ANTIGRAVITY_ENDPOINT_DAILY,
            ANTIGRAVITY_ENDPOINT_AUTOPUSH,
        ]
    )


# Default Project ID
ANTIGRAVITY_DEFAULT_PROJECT_ID = "rising-fact-p41fc"

# API Version
ANTIGRAVITY_API_VERSION = "v1internal"

# Request Headers
# Per API spec: User-Agent should be "antigravity/{version} {platform}/{arch}"
ANTIGRAVITY_HEADERS = {
    "User-Agent": "antigravity/1.11.5 windows/amd64",
    "X-Goog-Api-Client": "google-cloud-sdk vscode_cloudshelleditor/0.1",
    "Client-Metadata": json.dumps(
        {
            "ideType": "IDE_UNSPECIFIED",
            "platform": "PLATFORM_UNSPECIFIED",
            "pluginType": "GEMINI",
        },
        separators=(",", ":"),
    ),
}

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

# Token refresh buffer (60 seconds before expiry)
TOKEN_REFRESH_BUFFER_MS = 60_000


@dataclass
class PKCEPair:
    """PKCE verifier and challenge pair."""

    verifier: str
    challenge: str
    method: str = "S256"


@dataclass
class TokenResult:
    """OAuth token exchange result."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str


@dataclass
class UserInfo:
    """User info from Google."""

    email: str
    name: str | None = None
    picture: str | None = None


@dataclass
class OAuthResult:
    """Complete OAuth flow result."""

    tokens: TokenResult
    user_info: UserInfo
    verifier: str


def generate_pkce_pair() -> PKCEPair:
    """
    Generate PKCE verifier and challenge pair.

    Uses SHA-256 for the challenge (S256 method).
    """
    # Generate 32-byte random verifier
    verifier_bytes = secrets.token_bytes(32)
    verifier = base64.urlsafe_b64encode(verifier_bytes).rstrip(b"=").decode("ascii")

    # Generate challenge from verifier using SHA-256
    challenge_bytes = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(challenge_bytes).rstrip(b"=").decode("ascii")

    return PKCEPair(verifier=verifier, challenge=challenge, method="S256")


def encode_state(verifier: str, project_id: str | None = None) -> str:
    """Encode OAuth state as URL-safe base64 JSON."""
    state = {"verifier": verifier}
    if project_id:
        state["projectId"] = project_id
    return base64.urlsafe_b64encode(json.dumps(state).encode()).decode()


def decode_state(encoded: str) -> dict[str, Any]:
    """Decode OAuth state from base64 JSON."""
    # Handle both base64url and standard base64
    encoded = encoded.replace("-", "+").replace("_", "/")
    # Add padding
    padding = 4 - len(encoded) % 4
    if padding != 4:
        encoded += "=" * padding

    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return {}


def build_auth_url(
    port: int,
    project_id: str | None = None,
    client_id: str = ANTIGRAVITY_CLIENT_ID,
) -> tuple[str, str]:
    """
    Build Google OAuth authorization URL with PKCE.

    Returns:
        Tuple of (auth_url, pkce_verifier)
    """
    pkce = generate_pkce_pair()

    redirect_uri = f"http://localhost:{port}/oauth-callback"
    state = encode_state(pkce.verifier, project_id)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(ANTIGRAVITY_SCOPES),
        "state": state,
        "code_challenge": pkce.challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
    }

    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return url, pkce.verifier


def exchange_code(
    code: str,
    verifier: str,
    port: int,
    client_id: str = ANTIGRAVITY_CLIENT_ID,
    client_secret: str = ANTIGRAVITY_CLIENT_SECRET,
) -> TokenResult:
    """
    Exchange authorization code for tokens.

    Args:
        code: Authorization code from OAuth callback
        verifier: PKCE verifier from initial auth request
        port: Callback server port

    Returns:
        Token exchange result with access and refresh tokens.
    """
    redirect_uri = f"http://localhost:{port}/oauth-callback"

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }

    with httpx.Client() as client:
        response = client.post(
            GOOGLE_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")

        result = response.json()

        return TokenResult(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token", ""),
            expires_in=result.get("expires_in", 3600),
            token_type=result.get("token_type", "Bearer"),
        )


def refresh_access_token(
    refresh_token: str,
    client_id: str = ANTIGRAVITY_CLIENT_ID,
    client_secret: str = ANTIGRAVITY_CLIENT_SECRET,
) -> TokenResult:
    """
    Refresh an access token using a refresh token.

    Args:
        refresh_token: Valid refresh token

    Returns:
        New token result.
    """
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    with httpx.Client() as client:
        response = client.post(
            GOOGLE_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")

        result = response.json()

        return TokenResult(
            access_token=result["access_token"],
            refresh_token=refresh_token,  # Keep original refresh token
            expires_in=result.get("expires_in", 3600),
            token_type=result.get("token_type", "Bearer"),
        )


def fetch_user_info(access_token: str) -> UserInfo:
    """
    Fetch user info from Google's userinfo API.

    Args:
        access_token: Valid access token

    Returns:
        User info with email, name, and picture.
    """
    with httpx.Client() as client:
        response = client.get(
            f"{GOOGLE_USERINFO_URL}?alt=json",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if response.status_code != 200:
            raise Exception(f"Failed to fetch user info: {response.status_code}")

        data = response.json()

        return UserInfo(
            email=data.get("email", ""),
            name=data.get("name"),
            picture=data.get("picture"),
        )


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    callback_result: dict[str, Any] = {}
    server_ready = threading.Event()

    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass

    def do_GET(self):
        """Handle OAuth callback GET request."""
        parsed = urlparse(self.path)

        if parsed.path == "/oauth-callback":
            params = parse_qs(parsed.query)

            OAuthCallbackHandler.callback_result = {
                "code": params.get("code", [""])[0],
                "state": params.get("state", [""])[0],
                "error": params.get("error", [None])[0],
            }

            if (
                OAuthCallbackHandler.callback_result["code"]
                and not OAuthCallbackHandler.callback_result["error"]
            ):
                body = b"<html><body><h1>Login successful!</h1><p>You can close this window.</p></body></html>"
            else:
                body = b"<html><body><h1>Login failed</h1><p>Please check the CLI output.</p></body></html>"

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

            # Signal completion
            OAuthCallbackHandler.server_ready.set()
        else:
            self.send_response(404)
            self.end_headers()


def perform_oauth_flow(
    project_id: str | None = None,
    timeout: int = 300,
) -> OAuthResult:
    """
    Perform full OAuth flow with browser-based authentication.

    1. Start local callback server
    2. Open browser for Google auth
    3. Wait for callback
    4. Exchange code for tokens
    5. Fetch user info

    Args:
        project_id: Optional project ID for state
        timeout: Timeout in seconds (default 5 minutes)

    Returns:
        Complete OAuth result with tokens and user info.
    """
    # Reset callback state
    OAuthCallbackHandler.callback_result = {}
    OAuthCallbackHandler.server_ready.clear()

    # Start callback server
    server = HTTPServer(("localhost", 0), OAuthCallbackHandler)
    port = server.server_address[1]

    server_thread = threading.Thread(target=lambda: server.handle_request())
    server_thread.daemon = True
    server_thread.start()

    try:
        # Build auth URL and open browser
        auth_url, verifier = build_auth_url(port, project_id)

        print("\nOpening browser for Google authentication...")
        print(f"If browser doesn't open, visit:\n{auth_url}\n")

        webbrowser.open(auth_url)

        # Wait for callback
        if not OAuthCallbackHandler.server_ready.wait(timeout):
            raise Exception("OAuth callback timeout")

        result = OAuthCallbackHandler.callback_result

        if result.get("error"):
            raise Exception(f"OAuth error: {result['error']}")

        if not result.get("code"):
            raise Exception("No authorization code received")

        # Verify state
        state = decode_state(result["state"])
        if state.get("verifier") != verifier:
            raise Exception("PKCE verifier mismatch - possible security issue")

        # Exchange code for tokens
        tokens = exchange_code(result["code"], verifier, port)

        # Fetch user info
        user_info = fetch_user_info(tokens.access_token)

        print(f"✓ Authenticated as: {user_info.email}")

        return OAuthResult(tokens=tokens, user_info=user_info, verifier=verifier)

    finally:
        server.server_close()


if __name__ == "__main__":
    # Test the OAuth flow
    try:
        result = perform_oauth_flow()
        print(f"\nAccess Token: {result.tokens.access_token[:20]}...")
        print(f"Refresh Token: {result.tokens.refresh_token[:20]}...")
        print(f"Expires In: {result.tokens.expires_in}s")
        print(f"User: {result.user_info.email}")
    except Exception as e:
        print(f"OAuth failed: {e}")
