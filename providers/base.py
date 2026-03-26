"""Base provider interface for LLM integrations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProviderConfig:
    """Configuration for LLM provider."""
    
    api_key: str
    model: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.3
    base_url: Optional[str] = None
    timeout: int = 60


@dataclass
class ReviewResponse:
    """Standardized response from LLM review."""
    
    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""
    
    name: str = "base"
    
    def __init__(self, config: ProviderConfig):
        self.config = config
    
    @abstractmethod
    def review_code(self, prompt: str, system_prompt: str = "") -> ReviewResponse:
        """Send code review request to LLM."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available."""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Get default model for this provider."""
        pass
    
    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """List available models for this provider."""
        pass
