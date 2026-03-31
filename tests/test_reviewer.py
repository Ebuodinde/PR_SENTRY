"""Tests for reviewer.py"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from reviewer import Reviewer, SYSTEM_PROMPT


class TestReviewerInit:
    """Test Reviewer initialization."""

    @patch("reviewer.get_provider")
    def test_init_anthropic_provider(self, mock_get_provider):
        """Anthropic provider with valid key should initialize."""
        mock_provider = Mock()
        mock_provider.name = "anthropic"
        mock_get_provider.return_value = mock_provider
        
        reviewer = Reviewer(
            provider="anthropic",
            api_key="sk-ant-test-key",
            model="claude-sonnet-4-20250514"
        )
        assert reviewer.provider_name == "anthropic"

    @patch("reviewer.get_provider")
    def test_init_openai_provider(self, mock_get_provider):
        """OpenAI provider with valid key should initialize."""
        mock_provider = Mock()
        mock_provider.name = "openai"
        mock_get_provider.return_value = mock_provider
        
        reviewer = Reviewer(
            provider="openai",
            api_key="sk-openai-test-key"
        )
        assert reviewer.provider_name == "openai"

    def test_init_invalid_provider(self):
        """Invalid provider should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid provider"):
            Reviewer(provider="invalid_provider", api_key="test")

    def test_init_missing_key(self):
        """Missing API key should raise ValueError."""
        with pytest.raises(ValueError, match="API key required"):
            Reviewer(provider="anthropic", api_key="")

    @patch("reviewer.get_provider")
    def test_init_with_model(self, mock_get_provider):
        """Custom model should be passed to provider."""
        mock_provider = Mock()
        mock_provider.name = "openai"
        mock_get_provider.return_value = mock_provider
        
        reviewer = Reviewer(
            provider="openai",
            api_key="sk-test",
            model="gpt-4o"
        )
        
        mock_get_provider.assert_called_once_with(
            provider_name="openai",
            api_key="sk-test",
            model="gpt-4o",
        )


class TestReviewerReviewPR:
    """Test PR review functionality."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider."""
        provider = Mock()
        provider.name = "openai"
        provider.review_code.return_value = Mock(
            content="✅ No critical issues found.",
            model="gpt-4o"
        )
        return provider

    @pytest.fixture
    def reviewer(self, mock_provider):
        """Create a Reviewer instance for testing."""
        with patch("reviewer.get_provider", return_value=mock_provider):
            return Reviewer(
                provider="openai",
                api_key="sk-test-key"
            )

    def test_review_pr_slop_detected(self, reviewer):
        """High slop PR should skip LLM and return warning."""
        result = reviewer.review_pr(
            title="Feature: Robust and Seamless API Integration",
            body="""
            This PR ensures a robust and seamless integration of the new API.
            It is crucial to leverage these new endpoints to foster a comprehensive
            user experience. We delve into the intricate details of the meticulous
            refactoring process, which acts as a testament to our pivotal architecture.
            The scalable solution will streamline all future development efforts.
            """,
            commit_messages=["feat: ensure robust utilization of new endpoints"],
            raw_diff=""
        )
        
        assert result["is_slop"] is True
        assert result["skipped_llm"] is True
        assert result["slop_score"] >= 60
        assert "AI-generated content" in result["review"]

    def test_review_pr_clean_pr(self, reviewer, mock_provider):
        """Clean PR should call LLM and return review."""
        result = reviewer.review_pr(
            title="Fix null pointer in auth",
            body="Added null check before token assignment.",
            commit_messages=["fix: add null check"],
            raw_diff="""diff --git a/auth.py b/auth.py
--- a/auth.py
+++ b/auth.py
@@ -1,3 +1,4 @@
+if token is not None:
     process(token)
"""
        )
        
        assert result["is_slop"] is False
        assert result["skipped_llm"] is False
        assert mock_provider.review_code.called

    def test_review_pr_security_hints_collected(self, reviewer, mock_provider):
        """Security hints from diff should be collected."""
        mock_provider.review_code.return_value = Mock(
            content="🔴 CRITICAL: Hardcoded API key",
            model="gpt-4o"
        )
        
        result = reviewer.review_pr(
            title="Add config",
            body="Added configuration file with necessary constants",
            commit_messages=["feat: add config"],
            raw_diff="""diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,3 +1,4 @@
+API_KEY = "sk-1234567890abcdef"
"""
        )
        
        assert "Hardcoded API key" in result["security_hints"]

    def test_review_pr_result_structure_slop(self, reviewer):
        """Result should have expected structure (slop case to avoid LLM call)."""
        # Use slop content to skip LLM call
        result = reviewer.review_pr(
            title="Feature: Robust and Seamless Integration",
            body="""This PR ensures a robust and seamless integration of the API.
            It is crucial to leverage these endpoints to foster comprehensive
            user experience. We delve into meticulous refactoring as testament
            to our pivotal architecture. The scalable solution will streamline.""",
            commit_messages=["feat: ensure robust utilization"],
            raw_diff=""
        )
        
        expected_keys = {"is_slop", "slop_score", "security_hints", "review", "provider", "skipped_llm"}
        assert expected_keys.issubset(set(result.keys()))


class TestSystemPrompt:
    """Test system prompt configuration."""

    def test_system_prompt_exists(self):
        """System prompt should be defined."""
        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 100

    def test_system_prompt_contains_rules(self):
        """System prompt should contain strict rules."""
        assert "NEVER" in SYSTEM_PROMPT
        assert "ONLY" in SYSTEM_PROMPT

    def test_system_prompt_mentions_security(self):
        """System prompt should mention security focus."""
        assert "security" in SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_format(self):
        """System prompt should specify report format."""
        assert "🔴 CRITICAL" in SYSTEM_PROMPT or "CRITICAL" in SYSTEM_PROMPT
