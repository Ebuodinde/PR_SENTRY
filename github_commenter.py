import os
from typing import Dict, Any

from dotenv import load_dotenv

load_dotenv()


class GitHubCommenter:
    """
    Posts the review result as a GitHub PR comment.

    Requires pull-requests: write permission.
    """

    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo = os.getenv("GITHUB_REPOSITORY")  # "owner/repo" format
        self.pr_number = os.getenv("PR_NUMBER")

        if not all([self.github_token, self.repo, self.pr_number]):
            raise ValueError(
                "GITHUB_TOKEN, GITHUB_REPOSITORY, and PR_NUMBER environment variables are required."
            )

    def post_review(self, review_result: Dict[str, Any]) -> bool:
        """
        Post the review result as a PR comment.

        Args:
            review_result: Dictionary returned by reviewer.py

        Returns:
            True if successful, False otherwise
        """
        import urllib.request
        import urllib.error
        import json

        comment_body = self._format_comment(review_result)

        url = f"https://api.github.com/repos/{self.repo}/issues/{self.pr_number}/comments"

        payload = json.dumps({"body": comment_body}).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status == 201:
                    print(f"✅ Comment posted successfully: PR #{self.pr_number}")
                    return True
                else:
                    print(f"❌ Unexpected status code: {response.status}")
                    return False
        except urllib.error.HTTPError as e:
            print(f"❌ GitHub API error: {e.code} — {e.reason}")
            return False
        except urllib.error.URLError as e:
            print(f"❌ GitHub network error: {e.reason}")
            return False

    def _format_comment(self, result: Dict[str, Any]) -> str:
        """Format the review result as a readable GitHub comment."""

        lines = ["## 🛡️ PR-Sentry Review Report\n"]

        # Slop warning
        if result["is_slop"]:
            lines.append(
                f"### ⚠️ High AI Content Detected\n"
                f"**Slop score:** {result['slop_score']}/100\n\n"
                f"This PR shows signs of automatically generated content. "
                f"Please assign a human reviewer.\n"
            )
            lines.append("---")
            lines.append("*PR-Sentry — Zero-Nitpick AI Code Review*")
            return "\n".join(lines)

        # Security warnings
        if result["security_hints"]:
            hints = "\n".join(f"- {h}" for h in result["security_hints"])
            lines.append(f"### 🔐 Static Security Scan\n{hints}\n")

        # LLM review
        lines.append(f"### 🔍 Code Review\n{result['review']}\n")

        # Footer
        provider_label = "Claude (Anthropic)" if result["provider"] == "anthropic" else "Development mode"
        lines.append("---")
        lines.append(
            f"*PR-Sentry — Zero-Nitpick AI Code Review — "
            f"Model: {provider_label} — "
            f"Slop score: {result['slop_score']}/100*"
        )

        return "\n".join(lines)


# --- Test Area ---
if __name__ == "__main__":
    # To test with a real GitHub connection
    # add the following to .env:
    # GITHUB_TOKEN=ghp_...
    # GITHUB_REPOSITORY=username/repo_name
    # PR_NUMBER=1

    # For now, test only the formatted output
    commenter = None

    test_result_clean = {
        "is_slop": False,
        "slop_score": 10,
        "security_hints": ["Hardcoded API key"],
        "review": "🔴 CRITICAL: API key hardcoded in source — auth.py:12 — Exposes credentials in version control.",
        "provider": "development",
        "skipped_llm": False
    }

    test_result_slop = {
        "is_slop": True,
        "slop_score": 75,
        "security_hints": [],
        "review": "",
        "provider": "none",
        "skipped_llm": True
    }

    # Format tests — without sending anything to GitHub
    from github_commenter import GitHubCommenter as _GC

    class _MockCommenter(_GC):
        def __init__(self):
            # Skip __init__; only testing formatting
            pass

    mock = _MockCommenter()

    print("=== Clean PR Comment ===\n")
    print(mock._format_comment(test_result_clean))

    print("\n=== Slop PR Comment ===\n")
    print(mock._format_comment(test_result_slop))
