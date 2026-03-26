"""Tests for reviewer.py"""

import pytest
from unittest.mock import patch, MagicMock
from reviewer import Reviewer, SYSTEM_PROMPT


class TestReviewerInit:
    """Test Reviewer initialization."""

    def test_init_anthropic_provider(self):
        """Anthropic provider with valid key should initialize."""
        reviewer = Reviewer(
            provider="anthropic",
            anthropic_api_key="sk-ant-test-key",
            anthropic_model="claude-4-5-haiku-20251015"
        )
        assert reviewer.provider == "anthropic"
        assert reviewer.anthropic_api_key == "sk-ant-test-key"

    def test_init_development_provider(self):
        """Development provider with valid key should initialize."""
        reviewer = Reviewer(
            provider="development",
            dev_llm_api_key="sk-openai-test-key"
        )
        assert reviewer.provider == "development"

    def test_init_invalid_provider(self):
        """Invalid provider should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid REVIEWER_PROVIDER"):
            Reviewer(provider="invalid_provider")

    def test_init_anthropic_missing_key(self):
        """Anthropic provider without key should raise ValueError."""
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required"):
            Reviewer(provider="anthropic", anthropic_api_key="")

    def test_init_development_missing_key(self):
        """Development provider without key should raise ValueError."""
        with pytest.raises(ValueError, match="DEV_LLM_API_KEY is required"):
            Reviewer(provider="development", dev_llm_api_key="")

    def test_init_default_model(self):
        """Default model should be set when not provided."""
        reviewer = Reviewer(
            provider="anthropic",
            anthropic_api_key="sk-ant-test-key"
        )
        assert reviewer.anthropic_model == "claude-4-5-haiku-20251015"

    def test_init_custom_model(self):
        """Custom model should be used when provided."""
        reviewer = Reviewer(
            provider="anthropic",
            anthropic_api_key="sk-ant-test-key",
            anthropic_model="claude-4-sonnet-20251015"
        )
        assert reviewer.anthropic_model == "claude-4-sonnet-20251015"


class TestReviewerReviewPR:
    """Test PR review functionality."""

    @pytest.fixture
    def reviewer(self):
        """Create a Reviewer instance for testing."""
        return Reviewer(
            provider="development",
            dev_llm_api_key="sk-test-key"
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

    @patch("reviewer._call_development_model")
    def test_review_pr_clean_pr(self, mock_llm, reviewer):
        """Clean PR should call LLM and return review."""
        mock_llm.return_value = "✅ No critical issues found."
        
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
        assert mock_llm.called

    @patch("reviewer._call_development_model")
    def test_review_pr_security_hints_collected(self, mock_llm, reviewer):
        """Security hints from diff should be collected."""
        mock_llm.return_value = "🔴 CRITICAL: Hardcoded API key"
        
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
        # Note: summary is only added for non-slop PRs
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
