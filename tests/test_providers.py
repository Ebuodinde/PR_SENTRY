"""Tests for provider module."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from providers import (
    BaseProvider,
    ProviderConfig,
    ReviewResponse,
    AnthropicProvider,
    OpenAIProvider,
    DeepSeekProvider,
    get_provider,
    list_providers,
)


class TestProviderConfig:
    """Test ProviderConfig dataclass."""

    def test_config_defaults(self):
        config = ProviderConfig(api_key="test-key")
        assert config.api_key == "test-key"
        assert config.model is None
        assert config.max_tokens == 4096
        assert config.temperature == 0.3
        assert config.base_url is None
        assert config.timeout == 60

    def test_config_custom_values(self):
        config = ProviderConfig(
            api_key="custom-key",
            model="gpt-4o",
            max_tokens=2048,
            temperature=0.7,
            base_url="https://custom.api.com",
            timeout=120,
        )
        assert config.api_key == "custom-key"
        assert config.model == "gpt-4o"
        assert config.max_tokens == 2048
        assert config.temperature == 0.7
        assert config.base_url == "https://custom.api.com"
        assert config.timeout == 120


class TestReviewResponse:
    """Test ReviewResponse dataclass."""

    def test_response_basic(self):
        response = ReviewResponse(
            content="Test review",
            model="gpt-4o",
            provider="openai",
        )
        assert response.content == "Test review"
        assert response.model == "gpt-4o"
        assert response.provider == "openai"
        assert response.input_tokens == 0
        assert response.output_tokens == 0

    def test_response_with_tokens(self):
        response = ReviewResponse(
            content="Review content",
            model="claude-sonnet-4-20250514",
            provider="anthropic",
            input_tokens=100,
            output_tokens=50,
        )
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.total_tokens == 150


class TestAnthropicProvider:
    """Test Anthropic provider."""

    def test_provider_name(self):
        config = ProviderConfig(api_key="test")
        provider = AnthropicProvider(config)
        assert provider.name == "anthropic"

    def test_is_available_with_key(self):
        config = ProviderConfig(api_key="sk-ant-test")
        provider = AnthropicProvider(config)
        assert provider.is_available() is True

    def test_is_available_without_key(self):
        config = ProviderConfig(api_key="")
        provider = AnthropicProvider(config)
        assert provider.is_available() is False

    def test_default_model(self):
        config = ProviderConfig(api_key="test")
        provider = AnthropicProvider(config)
        assert provider.default_model == "claude-sonnet-4-20250514"

    def test_available_models(self):
        config = ProviderConfig(api_key="test")
        provider = AnthropicProvider(config)
        models = provider.available_models
        assert "claude-sonnet-4-20250514" in models
        assert "claude-haiku-3-5-20241022" in models
        assert len(models) >= 2

    @patch("anthropic.Anthropic")
    def test_review_code(self, mock_anthropic_cls):
        # Mock response
        mock_response = Mock()
        mock_response.content = [Mock(text="Review result")]
        mock_response.usage = Mock(input_tokens=50, output_tokens=25)
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        config = ProviderConfig(api_key="test-key")
        provider = AnthropicProvider(config)
        
        result = provider.review_code("Review this code", "You are a code reviewer")
        
        assert result.content == "Review result"
        assert result.provider == "anthropic"
        assert result.input_tokens == 50
        assert result.output_tokens == 25


class TestOpenAIProvider:
    """Test OpenAI provider."""

    def test_provider_name(self):
        config = ProviderConfig(api_key="test")
        provider = OpenAIProvider(config)
        assert provider.name == "openai"

    def test_is_available_with_key(self):
        config = ProviderConfig(api_key="sk-test")
        provider = OpenAIProvider(config)
        assert provider.is_available() is True

    def test_default_model(self):
        config = ProviderConfig(api_key="test")
        provider = OpenAIProvider(config)
        assert provider.default_model == "gpt-4o"

    def test_available_models(self):
        config = ProviderConfig(api_key="test")
        provider = OpenAIProvider(config)
        models = provider.available_models
        assert "gpt-4o" in models
        assert "gpt-4o-mini" in models
        assert "gpt-4o-mini" in models

    @patch("openai.OpenAI")
    def test_review_code(self, mock_openai_cls):
        mock_choice = Mock()
        mock_choice.message.content = "OpenAI review"
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = Mock(prompt_tokens=40, completion_tokens=20)
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)
        
        result = provider.review_code("Review code", "System prompt")
        
        assert result.content == "OpenAI review"
        assert result.provider == "openai"
        assert result.input_tokens == 40
        assert result.output_tokens == 20


class TestDeepSeekProvider:
    """Test DeepSeek provider."""

    def test_provider_name(self):
        config = ProviderConfig(api_key="test")
        provider = DeepSeekProvider(config)
        assert provider.name == "deepseek"

    def test_base_url(self):
        assert DeepSeekProvider.BASE_URL == "https://api.deepseek.com/v1"

    def test_default_model(self):
        config = ProviderConfig(api_key="test")
        provider = DeepSeekProvider(config)
        assert provider.default_model == "deepseek-chat"

    def test_available_models(self):
        config = ProviderConfig(api_key="test")
        provider = DeepSeekProvider(config)
        models = provider.available_models
        assert "deepseek-chat" in models
        assert "deepseek-coder" in models


class TestProviderFactory:
    """Test provider factory functions."""

    def test_get_provider_anthropic_explicit(self):
        provider = get_provider("anthropic", api_key="test-key")
        assert isinstance(provider, AnthropicProvider)
        assert provider.name == "anthropic"

    def test_get_provider_openai_explicit(self):
        provider = get_provider("openai", api_key="test-key")
        assert isinstance(provider, OpenAIProvider)
        assert provider.name == "openai"

    def test_get_provider_deepseek_explicit(self):
        provider = get_provider("deepseek", api_key="test-key")
        assert isinstance(provider, DeepSeekProvider)
        assert provider.name == "deepseek"

    def test_get_provider_case_insensitive(self):
        provider = get_provider("ANTHROPIC", api_key="test-key")
        assert isinstance(provider, AnthropicProvider)

    def test_get_provider_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("unknown-provider", api_key="test")

    def test_get_provider_no_key_raises(self):
        with pytest.raises(ValueError, match="API key required"):
            get_provider("anthropic", api_key=None)

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}, clear=True)
    def test_get_provider_autodetect_anthropic(self):
        provider = get_provider()
        assert isinstance(provider, AnthropicProvider)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}, clear=True)
    def test_get_provider_autodetect_openai(self):
        provider = get_provider()
        assert isinstance(provider, OpenAIProvider)

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "env-key"}, clear=True)
    def test_get_provider_autodetect_deepseek(self):
        provider = get_provider()
        assert isinstance(provider, DeepSeekProvider)

    @patch.dict(os.environ, {}, clear=True)
    def test_get_provider_no_env_raises(self):
        with pytest.raises(ValueError, match="No LLM provider configured"):
            get_provider()

    def test_get_provider_with_model_override(self):
        provider = get_provider("openai", api_key="test", model="gpt-4o")
        assert provider.config.model == "gpt-4o"

    def test_list_providers(self):
        result = list_providers()
        assert "anthropic" in result
        assert "openai" in result
        assert "deepseek" in result
        assert isinstance(result["anthropic"], list)
        assert len(result["anthropic"]) > 0


class TestProviderIntegration:
    """Integration tests for provider system."""

    def test_all_providers_have_required_methods(self):
        providers = [AnthropicProvider, OpenAIProvider, DeepSeekProvider]
        config = ProviderConfig(api_key="test")
        
        for provider_cls in providers:
            provider = provider_cls(config)
            assert hasattr(provider, "review_code")
            assert hasattr(provider, "is_available")
            assert hasattr(provider, "default_model")
            assert hasattr(provider, "available_models")
            assert hasattr(provider, "name")

    def test_all_providers_inherit_base(self):
        providers = [AnthropicProvider, OpenAIProvider, DeepSeekProvider]
        
        for provider_cls in providers:
            assert issubclass(provider_cls, BaseProvider)

    def test_response_total_tokens_calculation(self):
        response = ReviewResponse(
            content="test",
            model="test-model",
            provider="test",
            input_tokens=1000,
            output_tokens=500,
        )
        assert response.total_tokens == 1500

    def test_provider_config_immutability(self):
        config = ProviderConfig(api_key="original")
        provider = get_provider("anthropic", api_key="original")
        assert provider.config.api_key == "original"
