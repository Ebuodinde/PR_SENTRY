"""Anthropic (Claude) provider implementation."""

from .base import BaseProvider, ProviderConfig, ReviewResponse


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider."""
    
    name = "anthropic"
    
    MODELS = {
        "claude-sonnet-4-6": "Claude Sonnet 4.6",
        "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
        "claude-opus-4-6": "Claude Opus 4.6",
    }
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.config.api_key)
        return self._client
    
    def is_available(self) -> bool:
        return bool(self.config.api_key)
    
    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-6"
    
    @property
    def available_models(self) -> list[str]:
        return list(self.MODELS.keys())
    
    def review_code(self, prompt: str, system_prompt: str = "") -> ReviewResponse:
        model = self.config.model or self.default_model
        
        kwargs = {
            "model": model,
            "max_tokens": self.config.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        
        response = self.client.messages.create(**kwargs)
        
        content = response.content[0].text if response.content else ""
        
        return ReviewResponse(
            content=content,
            model=model,
            provider=self.name,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
