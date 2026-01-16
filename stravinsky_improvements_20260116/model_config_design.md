# Model Configuration System Design

## Overview

User-configurable model routing with primary/fallback authentication methods, similar to Sisyphus cost-aware routing.

## User Requirements

From user feedback:
- "use sonnet and flash"
- "Right now we are using apis, but may move over to antigravity Oauth again"
- "It would also be helpful to have a config to specify primary, fallback for models"
- "e.g. gemini flash 3 preview: primary OAuth fallback api"
- "You select the models that are best for task similar to sisyphus"

## Solution: YAML Configuration + Loader Module

### 1. Configuration File

**Location**: `.stravinsky/model_config.yaml`

**Structure**:
```yaml
defaults:
  primary_auth: oauth
  fallback_auth: api
  timeout: 120

models:
  gemini-3-flash:
    primary_auth: oauth
    fallback_auth: api
    max_tokens: 8192
    temperature: 0.7

agent_models:
  explore: gemini-3-flash
  implementation-lead: claude-sonnet-4.5
```

### 2. Loader Module

**File**: `mcp_bridge/tools/model_config_loader.py`

```python
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Literal, Optional

@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    primary_auth: Literal["oauth", "api"]
    fallback_auth: Literal["oauth", "api"]
    max_tokens: int = 8192
    temperature: float = 0.7
    timeout: int = 120

class ModelConfigManager:
    """Manages model configuration loading and caching."""

    def __init__(self, config_path: str | None = None):
        if config_path is None:
            config_path = Path.cwd() / ".stravinsky" / "model_config.yaml"
        self.config_path = Path(config_path)
        self._config_cache: dict | None = None

    def load_config(self) -> dict:
        """Load configuration from YAML file."""
        if self._config_cache is not None:
            return self._config_cache

        if not self.config_path.exists():
            # Return default configuration
            return self._get_default_config()

        with open(self.config_path) as f:
            self._config_cache = yaml.safe_load(f)

        return self._config_cache

    def get_model_config(self, model_name: str) -> ModelConfig:
        """Get configuration for a specific model."""
        config = self.load_config()

        # Check if model has specific config
        model_config = config.get("models", {}).get(model_name, {})

        # Merge with defaults
        defaults = config.get("defaults", {})
        merged = {**defaults, **model_config}

        return ModelConfig(
            primary_auth=merged.get("primary_auth", "oauth"),
            fallback_auth=merged.get("fallback_auth", "api"),
            max_tokens=merged.get("max_tokens", 8192),
            temperature=merged.get("temperature", 0.7),
            timeout=merged.get("timeout", 120),
        )

    def get_agent_model(self, agent_type: str) -> str:
        """Get the preferred model for an agent type."""
        config = self.load_config()
        agent_models = config.get("agent_models", {})

        # Return configured model or default
        return agent_models.get(agent_type, "gemini-3-flash")

    def _get_default_config(self) -> dict:
        """Return default configuration if no file exists."""
        return {
            "defaults": {
                "primary_auth": "oauth",
                "fallback_auth": "api",
                "timeout": 120,
            },
            "models": {},
            "agent_models": {
                "explore": "gemini-3-flash",
                "dewey": "gemini-3-flash",
                "frontend": "gemini-3-pro",
                "delphi": "gpt-5.2-codex",
                "research-lead": "gemini-3-flash",
                "implementation-lead": "claude-sonnet-4.5",
            },
        }

# Global instance
_config_manager = None

def get_config_manager() -> ModelConfigManager:
    """Get or create the global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ModelConfigManager()
    return _config_manager
```

### 3. Integration with invoke_* Tools

**Modify**: `mcp_bridge/tools/model_invoke.py`

```python
from .model_config_loader import get_config_manager

async def invoke_gemini(
    prompt: str,
    model: str = "gemini-3-flash",
    temperature: float = 0.7,
    max_tokens: int = 8192,
    thinking_budget: int = 0,
    agent_context: dict | None = None,
) -> str:
    """Invoke Gemini with fallback authentication."""

    # Load model configuration
    config_manager = get_config_manager()
    model_config = config_manager.get_model_config(model)

    # Try primary auth first
    if model_config.primary_auth == "oauth":
        try:
            return await _invoke_gemini_oauth(prompt, model, ...)
        except Exception as e:
            logger.warning(f"OAuth failed: {e}, trying API key fallback")
            if model_config.fallback_auth == "api":
                return await _invoke_gemini_api(prompt, model, ...)
            raise
    else:  # primary_auth == "api"
        try:
            return await _invoke_gemini_api(prompt, model, ...)
        except Exception as e:
            logger.warning(f"API key failed: {e}, trying OAuth fallback")
            if model_config.fallback_auth == "oauth":
                return await _invoke_gemini_oauth(prompt, model, ...)
            raise
```

### 4. Integration with agent_spawn

**Modify**: `mcp_bridge/tools/agent_manager.py`

```python
from .model_config_loader import get_config_manager

async def agent_spawn(
    prompt: str,
    agent_type: str = "explore",
    model: str | None = None,  # Optional - uses config if not specified
    ...
) -> str:
    """Spawn agent with model from configuration."""

    # If no model specified, use config
    if model is None:
        config_manager = get_config_manager()
        model = config_manager.get_agent_model(agent_type)

    # Rest of spawn logic...
```

## Implementation Steps

1. ✅ Create `.stravinsky/model_config.yaml` template
2. ⏳ Create `mcp_bridge/tools/model_config_loader.py` module
3. ⏳ Modify `invoke_gemini` to use primary/fallback auth
4. ⏳ Modify `invoke_openai` to use primary/fallback auth
5. ⏳ Modify `agent_spawn` to use agent_models from config
6. ⏳ Add CLI command: `stravinsky config edit` to open config in $EDITOR
7. ⏳ Add validation: Check config on load, warn about unknown models
8. ⏳ Add tests for config loading and fallback logic

## Benefits

1. **User Control**: Users can configure auth methods without code changes
2. **Graceful Fallback**: OAuth failures don't break workflows
3. **Cost Awareness**: Config defines cost tiers for agent routing
4. **Flexible**: Can add new models/agents without code changes
5. **Similar to Sisyphus**: Same cost-aware model selection pattern

## Migration Path

For existing users:
1. If `.stravinsky/model_config.yaml` doesn't exist, use hardcoded defaults
2. On first run, generate template config with current defaults
3. User can customize config as needed
4. No breaking changes - default behavior unchanged

## Future Enhancements

1. **Cost Tracking**: Log costs per agent/model for budget monitoring
2. **Model Aliasing**: Define custom aliases (e.g., "fast" → "gemini-3-flash")
3. **Per-Project Configs**: Override global config with project-specific `.stravinsky/model_config.yaml`
4. **Dynamic Routing**: Route based on prompt complexity (simple → haiku, complex → sonnet)
5. **Quota Management**: Stop using OAuth if quota exceeded, switch to API key

## Testing Strategy

```python
async def test_model_config_fallback():
    """Test OAuth → API key fallback."""
    config = ModelConfig(primary_auth="oauth", fallback_auth="api")

    # Simulate OAuth failure
    with mock.patch("invoke_gemini_oauth", side_effect=Exception("OAuth failed")):
        result = await invoke_gemini("test prompt")
        # Should succeed via API key
        assert result is not None

async def test_agent_model_selection():
    """Test agent uses model from config."""
    config_manager = get_config_manager()
    model = config_manager.get_agent_model("implementation-lead")
    assert model == "claude-sonnet-4.5"
```

## Configuration Example for User

```yaml
# .stravinsky/model_config.yaml
defaults:
  primary_auth: oauth  # Try OAuth first
  fallback_auth: api   # Fall back to API keys if OAuth fails

models:
  gemini-3-flash:
    primary_auth: oauth
    fallback_auth: api
    max_tokens: 8192

  claude-sonnet-4.5:
    primary_auth: api    # Use API key first for Claude
    fallback_auth: oauth # Fall back to OAuth

agent_models:
  explore: gemini-3-flash        # Fast, cheap for code search
  implementation-lead: claude-sonnet-4.5  # Powerful for code generation
  delphi: gpt-5.2-codex         # Strategic advisor
```

## Status

- ✅ Design complete
- ✅ YAML template created
- ⏳ Implementation pending (needs testing and integration)
- ⏳ Recommend implementing in v0.4.56 after current release
