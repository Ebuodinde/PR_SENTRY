"""Tests for llm_router.py"""

import os
import pytest
from unittest.mock import patch
from llm_router import LLMRouter, calculate_pr_complexity, ModelConfig


class TestLLMRouter:
    """Test suite for LLMRouter class."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"})
    def test_init_with_anthropic_key(self):
        """Router should initialize with valid Anthropic key."""
        router = LLMRouter()
        assert router.has_anthropic is True

    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_anthropic_key(self):
        """Router should raise ValueError without Anthropic key."""
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
            LLMRouter()

    @patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "DEEPSEEK_API_KEY": "ds-test-key"
    })
    def test_init_with_multiple_providers(self):
        """Router should detect multiple providers."""
        router = LLMRouter()
        assert router.has_anthropic is True
        assert router.has_deepseek is True

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"})
    def test_select_model_ai_slop(self):
        """AI slop should skip LLM entirely."""
        router = LLMRouter()
        pr_analysis = {
            "is_slop": True,
            "slop_score": 85
        }
        model = router.select_model(pr_analysis)
        assert model is None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"})
    def test_select_model_security_patterns(self):
        """Security patterns should trigger premium model."""
        router = LLMRouter()
        pr_analysis = {
            "is_slop": False,
            "has_security_patterns": True,
            "file_count": 3,
            "complexity_score": 5,
            "diff_content": "const x = 1;"
        }
        model = router.select_model(pr_analysis)
        assert model is not None
        assert model.model == "claude-sonnet-4.5"
        assert model.provider == "anthropic"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"})
    def test_select_model_security_keywords(self):
        """Security keywords should trigger premium model."""
        router = LLMRouter()
        pr_analysis = {
            "is_slop": False,
            "has_security_patterns": False,
            "file_count": 2,
            "complexity_score": 2,
            "diff_content": "const password = localStorage.getItem('auth_token');"
        }
        model = router.select_model(pr_analysis)
        assert model is not None
        assert model.model == "claude-sonnet-4.5"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"})
    def test_select_model_simple_pr_anthropic_only(self):
        """Simple PR with only Anthropic should use Haiku."""
        router = LLMRouter()
        pr_analysis = {
            "is_slop": False,
            "has_security_patterns": False,
            "file_count": 2,
            "complexity_score": 1,
            "diff_content": "function hello() { return 'world'; }"
        }
        model = router.select_model(pr_analysis)
        assert model is not None
        assert model.model == "claude-haiku-4.5"
        assert model.cost_per_million == 1.00

    @patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "DEEPSEEK_API_KEY": "ds-test-key"
    })
    def test_select_model_simple_pr_with_deepseek(self):
        """Simple PR with DeepSeek available should use DeepSeek."""
        router = LLMRouter()
        pr_analysis = {
            "is_slop": False,
            "has_security_patterns": False,
            "file_count": 2,
            "complexity_score": 1,
            "diff_content": "function hello() { return 'world'; }"
        }
        model = router.select_model(pr_analysis)
        assert model is not None
        assert model.model == "deepseek-v3"
        assert model.cost_per_million == 0.25

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"})
    def test_select_model_complex_pr(self):
        """Complex PR should use premium model."""
        router = LLMRouter()
        pr_analysis = {
            "is_slop": False,
            "has_security_patterns": False,
            "file_count": 15,
            "complexity_score": 8,
            "diff_content": "lots of code changes"
        }
        model = router.select_model(pr_analysis)
        assert model is not None
        assert model.model == "claude-sonnet-4.5"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"})
    def test_should_skip_llm_ai_slop(self):
        """Should skip LLM for AI slop."""
        router = LLMRouter()
        pr_analysis = {"is_slop": True, "slop_score": 90}
        should_skip, reason = router.should_skip_llm(pr_analysis)
        assert should_skip is True
        assert "AI-generated" in reason

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"})
    def test_should_skip_llm_empty_pr(self):
        """Should skip LLM for empty PR."""
        router = LLMRouter()
        pr_analysis = {"is_slop": False, "file_count": 0}
        should_skip, reason = router.should_skip_llm(pr_analysis)
        assert should_skip is True
        assert "No files changed" in reason

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"})
    def test_should_not_skip_llm_normal_pr(self):
        """Should not skip LLM for normal PR."""
        router = LLMRouter()
        pr_analysis = {"is_slop": False, "file_count": 5}
        should_skip, reason = router.should_skip_llm(pr_analysis)
        assert should_skip is False
        assert reason == ""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"})
    def test_estimate_cost(self):
        """Should estimate cost correctly."""
        router = LLMRouter()
        model = ModelConfig(
            provider="anthropic",
            model="claude-sonnet-4.5",
            cost_per_million=3.00,
            speed="medium",
            description="Test"
        )
        cost = router.estimate_cost(model, 100_000)  # 100K tokens
        assert round(cost, 2) == 0.30  # $0.30 for 100K tokens at $3/M

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"})
    def test_get_cost_savings_message_no_deepseek(self):
        """Should suggest adding DeepSeek when not available."""
        router = LLMRouter()
        message = router.get_cost_savings_message()
        assert "DEEPSEEK_API_KEY" in message
        assert "60%" in message

    @patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
        "DEEPSEEK_API_KEY": "ds-test-key"
    })
    def test_get_cost_savings_message_with_deepseek(self):
        """Should confirm DeepSeek is enabled."""
        router = LLMRouter()
        message = router.get_cost_savings_message()
        assert "DeepSeek enabled" in message
        assert "60%" in message

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key"})
    def test_get_provider_priority(self):
        """Should return provider priority list."""
        router = LLMRouter()
        providers = router.get_provider_priority()
        assert "anthropic" in providers
        assert isinstance(providers, list)


class TestCalculatePRComplexity:
    """Test suite for calculate_pr_complexity function."""

    def test_empty_pr(self):
        """Empty PR should have complexity 0."""
        complexity = calculate_pr_complexity([])
        assert complexity == 0

    def test_simple_pr(self):
        """Simple 1-file PR should have low complexity (0 if very small)."""
        parsed_files = [
            {"filename": "test.js", "changes": "const x = 1;", "security_hints": []}
        ]
        complexity = calculate_pr_complexity(parsed_files)
        # 1 file (0), very few lines (0), no security (0) = 0
        assert complexity == 0
        
        # Slightly larger file should get some complexity
        parsed_files = [
            {"filename": "test.js", "changes": "\n".join(["code"] * 60), "security_hints": []}
        ]
        complexity = calculate_pr_complexity(parsed_files)
        assert complexity >= 1  # >50 lines = +1

    def test_large_pr(self):
        """Large multi-file PR should have high complexity."""
        parsed_files = [
            {"filename": f"file{i}.js", "changes": "\n".join(["code"] * 100), "security_hints": []}
            for i in range(25)
        ]
        complexity = calculate_pr_complexity(parsed_files)
        assert complexity >= 8

    def test_security_pr(self):
        """PR with security hints should have higher complexity."""
        parsed_files = [
            {
                "filename": "auth.js",
                "changes": "const password = 'secret';",
                "security_hints": ["Hardcoded password"]
            }
        ]
        complexity = calculate_pr_complexity(parsed_files)
        assert complexity >= 2  # Base + security bonus

    def test_complexity_capped_at_10(self):
        """Complexity should be capped at 10."""
        parsed_files = [
            {"filename": f"file{i}.js", "changes": "\n".join(["code"] * 200), "security_hints": ["test"]}
            for i in range(50)
        ]
        complexity = calculate_pr_complexity(parsed_files)
        assert complexity == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
