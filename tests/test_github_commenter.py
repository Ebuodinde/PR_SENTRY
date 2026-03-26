"""Tests for github_commenter.py"""

import pytest
from unittest.mock import patch, MagicMock
from github_commenter import load_locale


class TestGitHubCommenterFormatting:
    """Test comment formatting without actual GitHub API calls."""

    @pytest.fixture
    def mock_commenter(self):
        """Create a mock commenter that skips __init__ validation."""
        from github_commenter import GitHubCommenter, load_locale
        
        class MockCommenter(GitHubCommenter):
            def __init__(self, lang="en"):
                # Skip parent __init__ to avoid env var requirements
                self.lang = lang
                self.locale = load_locale(lang)
        
        return MockCommenter()

    @pytest.fixture
    def mock_commenter_tr(self):
        """Create a mock commenter with Turkish locale."""
        from github_commenter import GitHubCommenter, load_locale
        
        class MockCommenter(GitHubCommenter):
            def __init__(self, lang="tr"):
                self.lang = lang
                self.locale = load_locale(lang)
        
        return MockCommenter()

    def test_format_comment_clean_pr(self, mock_commenter):
        """Clean PR should format with review section."""
        result = {
            "is_slop": False,
            "slop_score": 10,
            "security_hints": [],
            "review": "✅ No critical issues found.",
            "provider": "anthropic",
            "skipped_llm": False
        }
        
        comment = mock_commenter._format_comment(result)
        
        assert "## 🛡️ PR-Sentry Review Report" in comment
        assert "### 🔍 Code Review" in comment
        assert "✅ No critical issues found." in comment
        assert "Slop score: 10/100" in comment

    def test_format_comment_slop_pr(self, mock_commenter):
        """Slop PR should format with warning and skip review."""
        result = {
            "is_slop": True,
            "slop_score": 75,
            "security_hints": [],
            "review": "",
            "provider": "none",
            "skipped_llm": True
        }
        
        comment = mock_commenter._format_comment(result)
        
        assert "### ⚠️ High AI Content Detected" in comment
        assert "75/100" in comment
        assert "human reviewer" in comment.lower()
        # Should not have code review section for slop
        assert "### 🔍 Code Review" not in comment

    def test_format_comment_with_security_hints(self, mock_commenter):
        """Security hints should appear in formatted comment."""
        result = {
            "is_slop": False,
            "slop_score": 5,
            "security_hints": ["Hardcoded API key", "Private key"],
            "review": "🔴 CRITICAL: API key exposed",
            "provider": "anthropic",
            "skipped_llm": False
        }
        
        comment = mock_commenter._format_comment(result)
        
        assert "### 🔐 Static Security Scan" in comment
        assert "- Hardcoded API key" in comment
        assert "- Private key" in comment

    def test_format_comment_provider_label_anthropic(self, mock_commenter):
        """Anthropic provider should show correct label."""
        result = {
            "is_slop": False,
            "slop_score": 0,
            "security_hints": [],
            "review": "✅ OK",
            "provider": "anthropic",
            "skipped_llm": False
        }
        
        comment = mock_commenter._format_comment(result)
        assert "Claude (Anthropic)" in comment

    def test_format_comment_provider_label_development(self, mock_commenter):
        """Development provider should show correct label."""
        result = {
            "is_slop": False,
            "slop_score": 0,
            "security_hints": [],
            "review": "✅ OK",
            "provider": "development",
            "skipped_llm": False
        }
        
        comment = mock_commenter._format_comment(result)
        assert "Development mode" in comment

    def test_format_comment_footer(self, mock_commenter):
        """Comment should have PR-Sentry footer."""
        result = {
            "is_slop": False,
            "slop_score": 20,
            "security_hints": [],
            "review": "✅ OK",
            "provider": "anthropic",
            "skipped_llm": False
        }
        
        comment = mock_commenter._format_comment(result)
        assert "PR-Sentry" in comment
        assert "Zero-Nitpick" in comment

    def test_format_comment_turkish(self, mock_commenter_tr):
        """Turkish locale should use Turkish strings."""
        result = {
            "is_slop": True,
            "slop_score": 80,
            "security_hints": [],
            "review": "",
            "provider": "anthropic",
            "skipped_llm": True
        }
        
        comment = mock_commenter_tr._format_comment(result)
        assert "İnceleme Raporu" in comment
        assert "Yapay Zeka İçeriği" in comment
        assert "Slop skoru" in comment


class TestLocaleLoading:
    """Test locale file loading."""

    def test_load_locale_english(self):
        """English locale should load correctly."""
        locale = load_locale("en")
        assert "report_title" in locale
        assert "PR-Sentry" in locale["report_title"]

    def test_load_locale_turkish(self):
        """Turkish locale should load correctly."""
        locale = load_locale("tr")
        assert "report_title" in locale
        assert "İnceleme" in locale["report_title"]

    def test_load_locale_fallback(self):
        """Unknown language should fallback to English."""
        locale = load_locale("xyz")
        assert "report_title" in locale
        assert "PR-Sentry" in locale["report_title"]


class TestGitHubCommenterInit:
    """Test GitHubCommenter initialization."""

    @patch.dict("os.environ", {
        "GITHUB_TOKEN": "ghp_test_token",
        "GITHUB_REPOSITORY": "owner/repo",
        "PR_NUMBER": "42"
    })
    def test_init_with_env_vars(self):
        """Should initialize successfully with all env vars."""
        from github_commenter import GitHubCommenter
        
        commenter = GitHubCommenter()
        assert commenter.github_token == "ghp_test_token"
        assert commenter.repo == "owner/repo"
        assert commenter.pr_number == "42"

    @patch.dict("os.environ", {
        "GITHUB_TOKEN": "",
        "GITHUB_REPOSITORY": "owner/repo",
        "PR_NUMBER": "42"
    }, clear=True)
    def test_init_missing_token(self):
        """Should raise ValueError when GITHUB_TOKEN is missing."""
        from github_commenter import GitHubCommenter
        
        with pytest.raises(ValueError, match="GITHUB_TOKEN"):
            GitHubCommenter()

    @patch.dict("os.environ", {
        "GITHUB_TOKEN": "ghp_test",
        "PR_NUMBER": "42"
    }, clear=True)
    def test_init_missing_repo(self):
        """Should raise ValueError when GITHUB_REPOSITORY is missing."""
        from github_commenter import GitHubCommenter
        
        with pytest.raises(ValueError, match="GITHUB_REPOSITORY"):
            GitHubCommenter()


class TestGitHubCommenterPost:
    """Test posting functionality (mocked)."""

    @patch("httpx.Client")
    @patch.dict("os.environ", {
        "GITHUB_TOKEN": "ghp_test",
        "GITHUB_REPOSITORY": "owner/repo",
        "PR_NUMBER": "1"
    })
    def test_post_review_success(self, mock_client_class):
        """Successful post should return True."""
        from github_commenter import GitHubCommenter
        
        mock_response = MagicMock()
        mock_response.status_code = 201
        
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client
        
        commenter = GitHubCommenter()
        result = commenter.post_review({
            "is_slop": False,
            "slop_score": 0,
            "security_hints": [],
            "review": "OK",
            "provider": "anthropic",
            "skipped_llm": False
        })
        
        assert result is True

    @patch("httpx.Client")
    @patch.dict("os.environ", {
        "GITHUB_TOKEN": "ghp_test",
        "GITHUB_REPOSITORY": "owner/repo",
        "PR_NUMBER": "1"
    })
    def test_post_review_http_error(self, mock_client_class):
        """HTTP error should return False."""
        from github_commenter import GitHubCommenter
        import httpx
        
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.RequestError("Connection failed")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client
        
        commenter = GitHubCommenter()
        result = commenter.post_review({
            "is_slop": False,
            "slop_score": 0,
            "security_hints": [],
            "review": "OK",
            "provider": "anthropic",
            "skipped_llm": False
        })
        
        assert result is False
