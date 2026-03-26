"""DeepSeek provider implementation."""

from .base import BaseProvider, ProviderConfig, ReviewResponse


class DeepSeekProvider(BaseProvider):
    """DeepSeek provider (OpenAI-compatible API)."""
    
    name = "deepseek"
    BASE_URL = "https://api.deepseek.com/v1"
    
    MODELS = {
        "deepseek-chat": "DeepSeek V3",
        "deepseek-coder": "DeepSeek Coder",
    }
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url or self.BASE_URL,
            )
        return self._client
    
    def is_available(self) -> bool:
        return bool(self.config.api_key)
    
    @property
    def default_model(self) -> str:
        return "deepseek-chat"
    
    @property
    def available_models(self) -> list[str]:
        return list(self.MODELS.keys())
    
    def review_code(self, prompt: str, system_prompt: str = "") -> ReviewResponse:
        model = self.config.model or self.default_model
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        
        content = response.choices[0].message.content or "" if response.choices else ""
        
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        
        return ReviewResponse(
            content=content,
            model=model,
            provider=self.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
