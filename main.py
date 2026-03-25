import os
import sys
import json
import urllib.request
import urllib.error

from dotenv import load_dotenv

load_dotenv()

from reviewer import Reviewer
from github_commenter import GitHubCommenter


def fetch_pr_data(repo: str, pr_number: str, token: str) -> dict:
    """
    Fetch the PR title, description, and commit messages from the GitHub API.
    """
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API HTTP error fetching PR data: {e.code} — {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error fetching PR data: {e.reason}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON fetching PR data: {e}") from e


def fetch_pr_diff(repo: str, pr_number: str, token: str) -> str:
    """
    Fetch the raw diff for a PR from the GitHub API.
    """
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3.diff",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API HTTP error fetching diff: {e.code} — {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error fetching diff: {e.reason}") from e


def fetch_commit_messages(repo: str, pr_number: str, token: str) -> list:
    """
    Fetch commit messages for a PR as a list.
    """
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/commits"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            commits = json.loads(response.read().decode("utf-8"))
            return [c["commit"]["message"] for c in commits]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API HTTP error fetching commits: {e.code} — {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error fetching commits: {e.reason}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON fetching commits: {e}") from e


def main():
    # Read environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")

    if not all([github_token, repo, pr_number]):
        print("❌ GITHUB_TOKEN, GITHUB_REPOSITORY, and PR_NUMBER are required.")
        sys.exit(1)

    provider = os.getenv("REVIEWER_PROVIDER", "anthropic").strip()
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    dev_llm_api_key = os.getenv("DEV_LLM_API_KEY")
    anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    try:
        reviewer = Reviewer(
            provider=provider,
            anthropic_api_key=anthropic_api_key,
            dev_llm_api_key=dev_llm_api_key,
            anthropic_model=anthropic_model,
        )
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print(f"🔍 PR-Sentry started: {repo} PR #{pr_number}")

    try:
        pr_data = fetch_pr_data(repo, pr_number, github_token)
        raw_diff = fetch_pr_diff(repo, pr_number, github_token)
        commit_messages = fetch_commit_messages(repo, pr_number, github_token)
        title = pr_data.get("title", "")
        body = pr_data.get("body", "") or ""
        # Run the review
        result = reviewer.review_pr(
            title=title,
            body=body,
            commit_messages=commit_messages,
            raw_diff=raw_diff
        )
    except RuntimeError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print(f"📄 PR title: {title}")
    print(f"📝 Commit count: {len(commit_messages)}")

    print(f"\n🧠 Slop score: {result['slop_score']}/100")
    if result["is_slop"]:
        print("⚠️  High AI content — LLM review skipped")
    else:
        provider_label = "Claude (Anthropic)" if result["provider"] == "anthropic" else "Development mode"
        print(f"✅ Provider: {provider_label}")

    if result["security_hints"]:
        print(f"🔐 Security warnings: {', '.join(result['security_hints'])}")

    # Post a PR comment
    commenter = GitHubCommenter()
    success = commenter.post_review(result)

    if not success:
        print("❌ Comment could not be posted.")
        sys.exit(1)

    print("\n✅ PR-Sentry completed.")


if __name__ == "__main__":
    main()
