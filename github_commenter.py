import os
import json
from typing import Dict, Any
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Supported languages
SUPPORTED_LANGUAGES = {"en", "tr"}
DEFAULT_LANGUAGE = "en"


def load_locale(lang: str) -> Dict[str, str]:
    """Load locale strings from JSON file."""
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    
    locale_path = Path(__file__).parent / "locales" / f"{lang}.json"
    
    try:
        with open(locale_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Fallback to English
        fallback_path = Path(__file__).parent / "locales" / "en.json"
        with open(fallback_path, "r", encoding="utf-8") as f:
            return json.load(f)


class GitHubCommenter:
    """
    Posts the review result as a GitHub PR comment.

    Requires pull-requests: write permission.
    Supports multiple languages via SENTRY_LANG environment variable.
    """

    def __init__(self, lang: str = None):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo = os.getenv("GITHUB_REPOSITORY")  # "owner/repo" format
        self.pr_number = os.getenv("PR_NUMBER")
        
        # Language selection: param > env > default
        self.lang = lang or os.getenv("SENTRY_LANG", DEFAULT_LANGUAGE).lower()
        self.locale = load_locale(self.lang)

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
        import httpx

        comment_body = self._format_comment(review_result)

        url = f"https://api.github.com/repos/{self.repo}/issues/{self.pr_number}/comments"

        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json={"body": comment_body}, headers=headers)
                
                if response.status_code == 201:
                    print(f"✅ Comment posted successfully: PR #{self.pr_number}")
                    return True
                else:
                    print(f"❌ Unexpected status code: {response.status_code}")
                    return False
        except httpx.HTTPStatusError as e:
            print(f"❌ GitHub API error: {e.response.status_code}")
            return False
        except httpx.RequestError as e:
            print(f"❌ GitHub network error: {e}")
            return False

    def _format_comment(self, result: Dict[str, Any]) -> str:
        """Format the review result as a readable GitHub comment using locale."""
        t = self.locale  # Translation dict
        
        lines = [f"## {t['report_title']}\n"]

        # Slop warning
        if result["is_slop"]:
            lines.append(
                f"### {t['slop_warning_title']}\n"
                f"**{t['slop_score_label']}:** {result['slop_score']}/100\n\n"
                f"{t['slop_warning_message']}\n"
            )
            lines.append("---")
            lines.append(f"*{t['footer_signature']}*")
            return "\n".join(lines)

        # Security warnings
        if result["security_hints"]:
            hints = "\n".join(f"- {h}" for h in result["security_hints"])
            lines.append(f"### {t['security_scan_title']}\n{hints}\n")

        # PR Summary (if available)
        if result.get("summary"):
            summary_title = t.get("summary_title", "📝 Summary")
            lines.append(f"### {summary_title}\n{result['summary']}\n")

        # LLM review
        lines.append(f"### {t['code_review_title']}\n{result['review']}\n")

        # Footer
        t = self.locale
        provider_label = t["provider_anthropic"] if result["provider"] == "anthropic" else t["provider_development"]
        lines.append("---")
        lines.append(
            f"*{t['footer_signature']} — "
            f"{t['model_label']}: {provider_label} — "
            f"{t['slop_score_label']}: {result['slop_score']}/100*"
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
