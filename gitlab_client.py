"""GitLab API integration for PR-Sentry.

Provides GitLab merge request fetching and commenting capabilities.
"""

import os
from typing import Dict, Any, Optional, List
import httpx


class GitLabClient:
    """Client for GitLab API interactions."""
    
    def __init__(
        self,
        token: Optional[str] = None,
        gitlab_url: str = "https://gitlab.com"
    ):
        """
        Initialize GitLab client.
        
        Args:
            token: GitLab personal access token or CI job token
            gitlab_url: GitLab instance URL (default: gitlab.com)
        """
        self.token = token or os.environ.get("GITLAB_TOKEN") or os.environ.get("CI_JOB_TOKEN")
        self.gitlab_url = gitlab_url.rstrip("/")
        self.api_url = f"{self.gitlab_url}/api/v4"
        
        if not self.token:
            raise ValueError("GitLab token is required (GITLAB_TOKEN or CI_JOB_TOKEN)")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers with authentication."""
        return {
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json"
        }
    
    async def fetch_mr_data(
        self,
        client: httpx.AsyncClient,
        project_id: str,
        mr_iid: int
    ) -> Dict[str, Any]:
        """
        Fetch merge request data.
        
        Args:
            client: httpx async client
            project_id: GitLab project ID or URL-encoded path
            mr_iid: Merge request IID (internal ID)
        
        Returns:
            MR data dict with title, description, etc.
        """
        url = f"{self.api_url}/projects/{project_id}/merge_requests/{mr_iid}"
        response = await client.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()
    
    async def fetch_mr_diff(
        self,
        client: httpx.AsyncClient,
        project_id: str,
        mr_iid: int
    ) -> str:
        """
        Fetch merge request diff as unified diff format.
        
        Args:
            client: httpx async client
            project_id: GitLab project ID
            mr_iid: Merge request IID
        
        Returns:
            Unified diff string
        """
        # Get the list of changes
        url = f"{self.api_url}/projects/{project_id}/merge_requests/{mr_iid}/changes"
        response = await client.get(url, headers=self._get_headers())
        response.raise_for_status()
        data = response.json()
        
        # Convert GitLab changes to unified diff format
        diff_parts = []
        for change in data.get("changes", []):
            diff = change.get("diff", "")
            old_path = change.get("old_path", "")
            new_path = change.get("new_path", "")
            
            # Add diff header
            diff_parts.append(f"diff --git a/{old_path} b/{new_path}")
            diff_parts.append(f"--- a/{old_path}")
            diff_parts.append(f"+++ b/{new_path}")
            diff_parts.append(diff)
        
        return "\n".join(diff_parts)
    
    async def fetch_mr_commits(
        self,
        client: httpx.AsyncClient,
        project_id: str,
        mr_iid: int
    ) -> List[str]:
        """
        Fetch commit messages for a merge request.
        
        Args:
            client: httpx async client
            project_id: GitLab project ID
            mr_iid: Merge request IID
        
        Returns:
            List of commit messages
        """
        url = f"{self.api_url}/projects/{project_id}/merge_requests/{mr_iid}/commits"
        response = await client.get(url, headers=self._get_headers())
        response.raise_for_status()
        commits = response.json()
        
        return [commit.get("message", "") for commit in commits]
    
    async def post_mr_comment(
        self,
        client: httpx.AsyncClient,
        project_id: str,
        mr_iid: int,
        body: str
    ) -> Dict[str, Any]:
        """
        Post a comment on a merge request.
        
        Args:
            client: httpx async client
            project_id: GitLab project ID
            mr_iid: Merge request IID
            body: Comment body (markdown)
        
        Returns:
            Created note data
        """
        url = f"{self.api_url}/projects/{project_id}/merge_requests/{mr_iid}/notes"
        response = await client.post(
            url,
            headers=self._get_headers(),
            json={"body": body}
        )
        response.raise_for_status()
        return response.json()
    
    async def update_mr_comment(
        self,
        client: httpx.AsyncClient,
        project_id: str,
        mr_iid: int,
        note_id: int,
        body: str
    ) -> Dict[str, Any]:
        """
        Update an existing comment on a merge request.
        
        Args:
            client: httpx async client
            project_id: GitLab project ID
            mr_iid: Merge request IID
            note_id: Note ID to update
            body: New comment body
        
        Returns:
            Updated note data
        """
        url = f"{self.api_url}/projects/{project_id}/merge_requests/{mr_iid}/notes/{note_id}"
        response = await client.put(
            url,
            headers=self._get_headers(),
            json={"body": body}
        )
        response.raise_for_status()
        return response.json()
    
    async def find_existing_comment(
        self,
        client: httpx.AsyncClient,
        project_id: str,
        mr_iid: int,
        marker: str = "<!-- PR-Sentry -->"
    ) -> Optional[int]:
        """
        Find existing PR-Sentry comment on MR.
        
        Args:
            client: httpx async client
            project_id: GitLab project ID
            mr_iid: Merge request IID
            marker: Marker to identify PR-Sentry comments
        
        Returns:
            Note ID if found, None otherwise
        """
        url = f"{self.api_url}/projects/{project_id}/merge_requests/{mr_iid}/notes"
        response = await client.get(url, headers=self._get_headers())
        response.raise_for_status()
        notes = response.json()
        
        for note in notes:
            if marker in note.get("body", ""):
                return note.get("id")
        
        return None


def get_gitlab_env() -> Dict[str, str]:
    """
    Get GitLab CI environment variables.
    
    Returns:
        Dict with project_id, mr_iid, gitlab_url
    """
    return {
        "project_id": os.environ.get("CI_PROJECT_ID", ""),
        "mr_iid": os.environ.get("CI_MERGE_REQUEST_IID", ""),
        "gitlab_url": os.environ.get("CI_SERVER_URL", "https://gitlab.com"),
        "project_path": os.environ.get("CI_PROJECT_PATH", ""),
    }


if __name__ == "__main__":
    import asyncio
    
    async def test():
        # Example usage
        env = get_gitlab_env()
        print(f"GitLab CI Environment: {env}")
        
        if env["project_id"] and env["mr_iid"]:
            client = GitLabClient(gitlab_url=env["gitlab_url"])
            async with httpx.AsyncClient() as http:
                mr_data = await client.fetch_mr_data(http, env["project_id"], int(env["mr_iid"]))
                print(f"MR Title: {mr_data.get('title')}")
    
    asyncio.run(test())
