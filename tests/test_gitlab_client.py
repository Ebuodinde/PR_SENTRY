"""Tests for gitlab_client.py"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from gitlab_client import GitLabClient, get_gitlab_env


class TestGitLabClient:
    """Test suite for GitLabClient class."""

    def test_init_with_token(self):
        """Should initialize with provided token."""
        client = GitLabClient(token="glpat-test-token")
        assert client.token == "glpat-test-token"
        assert client.gitlab_url == "https://gitlab.com"

    def test_init_with_custom_url(self):
        """Should use custom GitLab URL."""
        client = GitLabClient(
            token="test-token",
            gitlab_url="https://gitlab.example.com/"
        )
        assert client.gitlab_url == "https://gitlab.example.com"
        assert client.api_url == "https://gitlab.example.com/api/v4"

    @patch.dict("os.environ", {"GITLAB_TOKEN": "env-token"})
    def test_init_from_env(self):
        """Should read token from environment."""
        client = GitLabClient()
        assert client.token == "env-token"

    @patch.dict("os.environ", {}, clear=True)
    def test_init_no_token_raises(self):
        """Should raise error without token."""
        with pytest.raises(ValueError, match="GitLab token is required"):
            GitLabClient()

    def test_get_headers(self):
        """Should return correct headers."""
        client = GitLabClient(token="test-token")
        headers = client._get_headers()
        assert headers["PRIVATE-TOKEN"] == "test-token"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_fetch_mr_data(self):
        """Should fetch MR data correctly."""
        client = GitLabClient(token="test-token")
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 1,
            "iid": 42,
            "title": "Test MR",
            "description": "Test description"
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.get.return_value = mock_response
        
        result = await client.fetch_mr_data(mock_http, "123", 42)
        
        assert result["title"] == "Test MR"
        mock_http.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_mr_diff(self):
        """Should fetch and format MR diff."""
        client = GitLabClient(token="test-token")
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "changes": [
                {
                    "old_path": "file.py",
                    "new_path": "file.py",
                    "diff": "@@ -1,3 +1,4 @@\n+new line\n"
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.get.return_value = mock_response
        
        result = await client.fetch_mr_diff(mock_http, "123", 42)
        
        assert "diff --git" in result
        assert "file.py" in result
        assert "+new line" in result

    @pytest.mark.asyncio
    async def test_fetch_mr_commits(self):
        """Should fetch commit messages."""
        client = GitLabClient(token="test-token")
        
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"message": "First commit"},
            {"message": "Second commit"}
        ]
        mock_response.raise_for_status = MagicMock()
        
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.get.return_value = mock_response
        
        result = await client.fetch_mr_commits(mock_http, "123", 42)
        
        assert len(result) == 2
        assert result[0] == "First commit"

    @pytest.mark.asyncio
    async def test_post_mr_comment(self):
        """Should post comment on MR."""
        client = GitLabClient(token="test-token")
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 999,
            "body": "Test comment"
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post.return_value = mock_response
        
        result = await client.post_mr_comment(mock_http, "123", 42, "Test comment")
        
        assert result["id"] == 999
        mock_http.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_existing_comment_found(self):
        """Should find existing PR-Sentry comment."""
        client = GitLabClient(token="test-token")
        
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": 1, "body": "Random comment"},
            {"id": 2, "body": "<!-- PR-Sentry -->\nReview content"},
            {"id": 3, "body": "Another comment"}
        ]
        mock_response.raise_for_status = MagicMock()
        
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.get.return_value = mock_response
        
        result = await client.find_existing_comment(mock_http, "123", 42)
        
        assert result == 2

    @pytest.mark.asyncio
    async def test_find_existing_comment_not_found(self):
        """Should return None if no PR-Sentry comment."""
        client = GitLabClient(token="test-token")
        
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": 1, "body": "Random comment"},
        ]
        mock_response.raise_for_status = MagicMock()
        
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.get.return_value = mock_response
        
        result = await client.find_existing_comment(mock_http, "123", 42)
        
        assert result is None


class TestGetGitLabEnv:
    """Test suite for get_gitlab_env function."""

    @patch.dict("os.environ", {
        "CI_PROJECT_ID": "12345",
        "CI_MERGE_REQUEST_IID": "42",
        "CI_SERVER_URL": "https://gitlab.example.com",
        "CI_PROJECT_PATH": "group/project"
    })
    def test_get_gitlab_env_full(self):
        """Should get all GitLab CI variables."""
        env = get_gitlab_env()
        assert env["project_id"] == "12345"
        assert env["mr_iid"] == "42"
        assert env["gitlab_url"] == "https://gitlab.example.com"
        assert env["project_path"] == "group/project"

    @patch.dict("os.environ", {}, clear=True)
    def test_get_gitlab_env_empty(self):
        """Should return empty strings for missing vars."""
        env = get_gitlab_env()
        assert env["project_id"] == ""
        assert env["mr_iid"] == ""
        assert env["gitlab_url"] == "https://gitlab.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
