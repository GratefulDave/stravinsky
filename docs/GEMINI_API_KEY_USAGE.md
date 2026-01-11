# Gemini API Key Authentication

Stravinsky now supports **two authentication methods** for accessing Gemini models:

1. **API Key** (Simple, recommended for development)
2. **OAuth** (Advanced, for production with scopes)

## Quick Start: API Key Authentication

### Step 1: Get Your API Key

Visit [Google AI Studio](https://aistudio.google.com/app/apikey) and create a free API key.

### Step 2: Add to Environment

**IMPORTANT:** The environment variable must be named **`GEMINI_API_KEY`** (NOT `GEMINI_API_TOKEN`).

Add your API key to `~/.stravinsky/.env` (user-global config):

```bash
# ~/.stravinsky/.env
# CRITICAL: Variable name is GEMINI_API_KEY (it's a KEY, not a TOKEN)
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Or use GOOGLE_API_KEY (same effect)
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**File locations checked (in priority order):**
1. `~/.stravinsky/.env` (RECOMMENDED - global for all projects)
2. `~/.env` (fallback - global for user)
3. Project-local `.env` (if using dotenv in your project)

### Step 3: Use Stravinsky

That's it! Stravinsky will automatically detect and use your API key:

```python
# In your code or via MCP
from mcp_bridge.tools.model_invoke import invoke_gemini
from mcp_bridge.auth.token_store import TokenStore

token_store = TokenStore()

response = await invoke_gemini(
    token_store=token_store,
    prompt="Explain async/await in Python",
    model="gemini-3-flash",
)

print(response)
```

## Authentication Priority

When both authentication methods are configured, **API key takes precedence**:

1. **API Key** - If `GEMINI_API_KEY` or `GOOGLE_API_KEY` is set → uses API key
2. **OAuth Fallback** - If no API key → uses OAuth tokens from `stravinsky-auth login gemini`

## Comparison: API Key vs OAuth

| Feature | API Key | OAuth |
|---------|---------|-------|
| **Setup** | 2 minutes (get key, add to .env) | 5-10 minutes (browser flow, token storage) |
| **Best For** | Development, testing, prototypes | Production, user-based access |
| **Requires** | Free API key from Google AI Studio | Google Account + OAuth consent |
| **Token Refresh** | Not needed (key doesn't expire) | Automatic background refresh |
| **Scopes** | Limited (public API only) | Full OAuth scopes available |
| **Multi-User** | Single key for all requests | Per-user authentication |

## When to Use Each Method

### Use API Key When:
- ✅ Quick development and testing
- ✅ Personal projects
- ✅ Don't need user-specific access control
- ✅ Want the simplest setup
- ✅ Using Gemini Developer API (free tier)

### Use OAuth When:
- ✅ Production applications
- ✅ Need OAuth scopes (cloud-platform, userinfo, etc.)
- ✅ User-based authentication required
- ✅ Using Vertex AI integration
- ✅ Need automatic token refresh with expiration handling

## Switching Between Methods

### From OAuth to API Key

Simply add `GEMINI_API_KEY` to your `.env` file. Stravinsky will automatically prefer the API key.

```bash
# Add this line to .env
GEMINI_API_KEY=your_key_here

# Stravinsky will now use API key instead of OAuth
# (OAuth tokens remain stored but won't be used)
```

### From API Key to OAuth

Remove `GEMINI_API_KEY` from your environment and authenticate via OAuth:

```bash
# Remove from .env or unset
unset GEMINI_API_KEY
unset GOOGLE_API_KEY

# Authenticate with OAuth
stravinsky-auth login gemini

# Stravinsky will now use OAuth
```

## Testing Your Setup

Use the provided test script to verify both authentication methods:

```bash
# Install google-genai dependency (if not already installed)
uv pip install google-genai

# Run authentication tests
python tests/test_api_key_auth.py
```

Expected output:

```
==============================================================
  GEMINI AUTHENTICATION TEST SUITE
==============================================================
✅ Found API key: AIzaSyXXXXXXXXXXXXXX...XXXX

🧪 Testing Gemini API key authentication...

✅ Response: API key authentication works!

✅ SUCCESS: API key authentication is working!

🧪 Testing OAuth fallback (no API key)...

✅ Correctly fell back to OAuth (not authenticated)
   Run 'stravinsky-auth login gemini' to set up OAuth

==============================================================
  TEST RESULTS
==============================================================
  API Key Auth:    ✅ PASS
  OAuth Fallback:  ✅ PASS
==============================================================
```

## Model Compatibility

Both authentication methods support the same models:

- `gemini-3-flash` → Uses `gemini-3-flash-preview` (API key, Tier 3) or Antigravity (OAuth)
- `gemini-3-pro-low` → Uses `gemini-3-flash-preview` (API key, Tier 3) or Antigravity (OAuth)
- `gemini-3-pro-high` → Uses `gemini-3-pro-preview` (API key, Tier 3) or Antigravity (OAuth)

## Troubleshooting

### Error: "google-genai library not installed"

```bash
# Install the google-genai library
uv pip install google-genai

# Or add to pyproject.toml dependencies
google-genai>=0.2.0
```

### Error: "GEMINI_API_TOKEN is not a valid variable"

**CRITICAL:** The variable name is `GEMINI_API_KEY` (KEY, not TOKEN).

❌ WRONG variable names:
- `GEMINI_API_TOKEN` - doesn't exist
- `GOOGLE_API_TOKEN` - doesn't exist
- `GEMINI_TOKEN` - doesn't exist

✅ CORRECT variable names:
- `GEMINI_API_KEY` - recommended
- `GOOGLE_API_KEY` - alias for GEMINI_API_KEY

**Don't confuse with other tokens:**

| Variable | Purpose | Notes |
|----------|---------|-------|
| `GEMINI_API_KEY` | Gemini auth | It's a KEY (doesn't have "token" in name) |
| `PYPI_API_TOKEN` | PyPI publishing | This IS a token |
| `OPENAI_API_KEY` | OpenAI auth | Also a KEY |

### Error: "API key request failed"

**Possible causes:**

1. **Wrong variable name** - Must be `GEMINI_API_KEY`, not `GEMINI_API_TOKEN`
2. **Wrong file location** - Should be in `~/.stravinsky/.env`, not project `.env`
3. **Invalid API key** - Double-check your key from Google AI Studio
4. **API key not loaded** - Restart Claude Code after adding to `.env`
5. **Quota exceeded** - Check your usage at Google AI Studio
6. **Model not available** - Some models require special access

**Solution:**

```bash
# Step 1: Check file exists
cat ~/.stravinsky/.env
# Should show: GEMINI_API_KEY=AIza...

# Step 2: Verify variable name is correct (not GEMINI_API_TOKEN!)
grep "GEMINI_API_KEY" ~/.stravinsky/.env

# Step 3: Fix if wrong variable name
sed -i '' 's/GEMINI_API_TOKEN/GEMINI_API_KEY/g' ~/.stravinsky/.env

# Step 4: Verify it's loaded
python3 -c "import os; from pathlib import Path; from dotenv import load_dotenv; load_dotenv(Path.home() / '.stravinsky' / '.env'); print('GEMINI_API_KEY:', os.getenv('GEMINI_API_KEY')[:20] + '...' if os.getenv('GEMINI_API_KEY') else 'NOT FOUND')"

# Step 5: Restart Claude Code completely
```

### Still Using OAuth When API Key is Set?

**Check precedence:**

```python
import os

# This should print your API key if set
print(os.getenv("GEMINI_API_KEY"))
print(os.getenv("GOOGLE_API_KEY"))

# If both print None, your .env isn't loaded
from dotenv import load_dotenv
load_dotenv()

# Now try again
print(os.getenv("GEMINI_API_KEY"))
```

## Security Best Practices

### Do NOT commit API keys to git

```bash
# Add .env to .gitignore
echo ".env" >> .gitignore

# Verify .env is ignored
git check-ignore .env
# Should output: .env
```

### Use different keys for different environments

```bash
# .env.development
GEMINI_API_KEY=dev_key_here

# .env.production
GEMINI_API_KEY=prod_key_here
```

### Rotate keys regularly

1. Create new API key at Google AI Studio
2. Update `.env` with new key
3. Test that it works
4. Delete old key from Google AI Studio

## Additional Resources

- [Google AI Studio](https://aistudio.google.com/)
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [google-genai Python SDK](https://googleapis.github.io/python-genai/)
