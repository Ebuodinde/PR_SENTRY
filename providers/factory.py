"""Provider factory - creates the right provider based on config."""

import os
from typing import Optional

from .base import BaseProvider, ProviderConfig
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider
from .deepseek_provider import DeepSeekProvider


PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "deepseek": DeepSeekProvider,
}


def get_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> BaseProvider:
    """Get the appropriate LLM provider.
    
    Auto-detects provider from environment if not specified.
    
    Args:
        provider_name: Provider name (anthropic, openai, deepseek)
        api_key: API key (or uses environment variable)
        model: Model name override
        
    Returns:
        Configured provider instance
    """
    # Auto-detect from environment
    if not provider_name:
        if os.environ.get("ANTHROPIC_API_KEY") or api_key:
            provider_name = "anthropic"
        elif os.environ.get("OPENAI_API_KEY"):
            provider_name = "openai"
        elif os.environ.get("DEEPSEEK_API_KEY"):
            provider_name = "deepseek"
        else:
            raise ValueError(
                "No LLM provider configured. Set one of: "
                "ANTHROPIC_API_KEY, OPENAI_API_KEY, or DEEPSEEK_API_KEY"
            )
    
    provider_name = provider_name.lower()
    
    if provider_name not in PROVIDERS:
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Available: {', '.join(PROVIDERS.keys())}"
        )
    
    # Get API key from environment if not provided
    if not api_key:
        env_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
        }
        api_key = os.environ.get(env_map.get(provider_name, ""))
    
    if not api_key:
        raise ValueError(f"API key required for {provider_name}")
    
    config = ProviderConfig(api_key=api_key, model=model)
    return PROVIDERS[provider_name](config)


def list_providers() -> dict[str, list[str]]:
    """List available providers and their models."""
    result = {}
    for name, cls in PROVIDERS.items():
        # Create dummy instance to get models
        dummy_config = ProviderConfig(api_key="dummy")
        provider = cls(dummy_config)
        result[name] = provider.available_models
    return result
