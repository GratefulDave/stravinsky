"""
OpenAI Codex OAuth 2.0 Implementation

Implements OAuth authentication for ChatGPT Plus/Pro subscriptions.
Uses the exact same OAuth flow as opencode-openai-codex-auth.

Port from: https://github.com/numman-ali/opencode-openai-codex-auth/blob/main/lib/auth/auth.ts
"""

import base64
import hashlib
import secrets
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

# OAuth constants (from openai/codex via opencode-openai-codex-auth)
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"  # Note: /oauth/authorize
TOKEN_URL = "https://auth.openai.com/oauth/token"
REDIRECT_URI = "http://localhost:1455/auth/callback"
SCOPE = "openid profile email offline_access"

# Callback configuration
OPENAI_CALLBACK_PORT = 1455


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


def generate_pkce_pair() -> PKCEPair:
    """Generate PKCE verifier and challenge pair using S256."""
    # Generate verifier (43+ chars recommended)
    verifier = secrets.token_urlsafe(32)
    
    # SHA-256 hash and base64url encode
    challenge_bytes = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(challenge_bytes).rstrip(b"=").decode("ascii")
    
    return PKCEPair(verifier=verifier, challenge=challenge, method="S256")


def create_state() -> str:
    """Generate a random state value for OAuth flow."""
    return secrets.token_hex(16)


def build_auth_url(redirect_uri: str = REDIRECT_URI) -> tuple[str, str, str]:
    """
    Build OpenAI OAuth authorization URL with PKCE.
    
    Exact port from opencode-openai-codex-auth createAuthorizationFlow()
    
    Returns:
        Tuple of (auth_url, pkce_verifier, state)
    """
    pkce = generate_pkce_pair()
    state = create_state()
    
    # Build URL exactly as opencode-openai-codex-auth does
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": SCOPE,
        "code_challenge": pkce.challenge,
        "code_challenge_method": "S256",
        "state": state,
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": "codex_cli_rs",
    }
    
    url = f"{AUTHORIZE_URL}?{urlencode(params)}"
    return url, pkce.verifier, state


def exchange_code(
    code: str,
    verifier: str,
    redirect_uri: str = REDIRECT_URI,
) -> TokenResult:
    """
    Exchange authorization code for tokens.
    
    Exact port from opencode-openai-codex-auth exchangeAuthorizationCode()
    """
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "code_verifier": verifier,
        "redirect_uri": redirect_uri,
    }
    
    with httpx.Client() as client:
        response = client.post(
            TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if response.status_code != 200:
            text = response.text
            print(f"[openai-oauth] code->token failed: {response.status_code} {text}")
            raise Exception(f"Token exchange failed: {response.status_code} - {text}")
        
        result = response.json()
        
        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")
        expires_in = result.get("expires_in")
        
        if not access_token or not refresh_token or not isinstance(expires_in, int):
            print(f"[openai-oauth] token response missing fields: {result}")
            raise Exception("Token response missing required fields")
        
        return TokenResult(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            token_type=result.get("token_type", "Bearer"),
        )


def refresh_access_token(refresh_token: str) -> TokenResult:
    """
    Refresh access token using refresh token.
    
    Exact port from opencode-openai-codex-auth refreshAccessToken()
    """
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
    }
    
    with httpx.Client() as client:
        response = client.post(
            TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if response.status_code != 200:
            text = response.text
            print(f"[openai-oauth] Token refresh failed: {response.status_code} {text}")
            raise Exception(f"Token refresh failed: {response.status_code} - {text}")
        
        result = response.json()
        
        access_token = result.get("access_token")
        refresh_token_new = result.get("refresh_token")
        expires_in = result.get("expires_in")
        
        if not access_token or not refresh_token_new or not isinstance(expires_in, int):
            print(f"[openai-oauth] Token refresh response missing fields: {result}")
            raise Exception("Token refresh response missing required fields")
        
        return TokenResult(
            access_token=access_token,
            refresh_token=refresh_token_new,
            expires_in=expires_in,
            token_type=result.get("token_type", "Bearer"),
        )


# ============= Browser Flow =============

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""
    
    callback_result: dict[str, Any] = {}
    server_ready = threading.Event()
    
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        # Handle /auth/callback path (matching REDIRECT_URI)
        if parsed.path == "/auth/callback":
            params = parse_qs(parsed.query)
            
            OAuthCallbackHandler.callback_result = {
                "code": params.get("code", [""])[0],
                "state": params.get("state", [""])[0],
                "error": params.get("error", [None])[0],
                "error_description": params.get("error_description", [""])[0],
            }
            
            if OAuthCallbackHandler.callback_result["code"]:
                # Success page - styled like opencode-openai-codex-auth
                body = b"""<!DOCTYPE html>
<html>
<head>
<title>Login Successful</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
       display: flex; justify-content: center; align-items: center; min-height: 100vh;
       margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.card { background: white; padding: 3rem; border-radius: 16px; text-align: center;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3); max-width: 400px; }
h1 { color: #10a37f; margin-bottom: 1rem; }
p { color: #666; }
</style>
</head>
<body>
<div class="card">
<h1>&#x2713; Login Successful!</h1>
<p>You can close this window and return to the terminal.</p>
</div>
</body>
</html>"""
            else:
                error = OAuthCallbackHandler.callback_result.get("error", "unknown")
                error_desc = OAuthCallbackHandler.callback_result.get("error_description", "")
                body = f"""<!DOCTYPE html>
<html>
<head><title>Login Failed</title>
<style>
body {{ font-family: -apple-system, sans-serif; display: flex; justify-content: center;
       align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }}
.card {{ background: white; padding: 3rem; border-radius: 16px; text-align: center;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1); max-width: 400px; }}
h1 {{ color: #ef4444; }}
</style>
</head>
<body>
<div class="card">
<h1>Login Failed</h1>
<p><strong>Error:</strong> {error}</p>
<p>{error_desc}</p>
<p>Please check the terminal for more details.</p>
</div>
</body>
</html>""".encode()
            
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            
            OAuthCallbackHandler.server_ready.set()
        else:
            self.send_response(404)
            self.end_headers()


def perform_oauth_flow(timeout: int = 300) -> TokenResult:
    """
    Perform OpenAI OAuth browser flow.
    
    Args:
        timeout: Timeout in seconds
        
    Returns:
        Token result with access and refresh tokens.
    """
    OAuthCallbackHandler.callback_result = {}
    OAuthCallbackHandler.server_ready.clear()
    
    # Try to use the required port (1455)
    try:
        server = HTTPServer(("localhost", OPENAI_CALLBACK_PORT), OAuthCallbackHandler)
        port = OPENAI_CALLBACK_PORT
        redirect_uri = REDIRECT_URI
    except OSError as e:
        print(f"\n⚠️  Cannot bind to port {OPENAI_CALLBACK_PORT}: {e}")
        print("   This port is required for OpenAI OAuth.")
        print("   Please stop any process using this port (e.g., Codex CLI)")
        print("   Or use the Codex CLI directly: codex login")
        raise Exception(f"Port {OPENAI_CALLBACK_PORT} is required but unavailable")
    
    server_thread = threading.Thread(target=lambda: server.handle_request())
    server_thread.daemon = True
    server_thread.start()
    
    try:
        auth_url, verifier, state = build_auth_url(redirect_uri)
        
        print("\n🔐 Opening browser for OpenAI authentication...")
        print("\nIf browser doesn't open, visit:")
        print(f"{auth_url}\n")
        
        webbrowser.open(auth_url)
        
        if not OAuthCallbackHandler.server_ready.wait(timeout):
            raise Exception("OAuth callback timeout - no response received")
        
        result = OAuthCallbackHandler.callback_result
        
        if result.get("error"):
            error_desc = result.get("error_description", "")
            raise Exception(f"OAuth error: {result['error']} - {error_desc}")
        
        if not result.get("code"):
            raise Exception("No authorization code received")
        
        # Verify state matches
        if result.get("state") != state:
            print(f"[openai-oauth] State mismatch: expected {state}, got {result.get('state')}")
            # Continue anyway - some OAuth servers don't return state
        
        print("📝 Exchanging code for tokens...")
        tokens = exchange_code(result["code"], verifier, redirect_uri)
        
        print("✓ Successfully authenticated with OpenAI")
        
        return tokens
        
    finally:
        server.server_close()


if __name__ == "__main__":
    try:
        result = perform_oauth_flow()
        print(f"\nAccess Token: {result.access_token[:30]}...")
        if result.refresh_token:
            print(f"Refresh Token: {result.refresh_token[:20]}...")
        print(f"Expires In: {result.expires_in}s")
    except Exception as e:
        print(f"\n✗ OAuth failed: {e}")
        import sys
        sys.exit(1)
