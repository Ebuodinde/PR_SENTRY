import os
import sys
import asyncio

import httpx
from dotenv import load_dotenv

load_dotenv()

from reviewer import Reviewer
from github_commenter import GitHubCommenter


# GitHub API headers
def get_github_headers(token: str, accept: str = "application/vnd.github+json") -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28"
    }


async def fetch_pr_data(client: httpx.AsyncClient, repo: str, pr_number: str, token: str) -> dict:
    """
    Fetch the PR title, description, and commit messages from the GitHub API.
    """
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    response = await client.get(url, headers=get_github_headers(token))
    response.raise_for_status()
    return response.json()


async def fetch_pr_diff(client: httpx.AsyncClient, repo: str, pr_number: str, token: str) -> str:
    """
    Fetch the raw diff for a PR from the GitHub API.
    """
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    response = await client.get(
        url,
        headers=get_github_headers(token, "application/vnd.github.v3.diff")
    )
    response.raise_for_status()
    return response.text


async def fetch_commit_messages(client: httpx.AsyncClient, repo: str, pr_number: str, token: str) -> list:
    """
    Fetch commit messages for a PR as a list.
    """
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/commits"
    response = await client.get(url, headers=get_github_headers(token))
    response.raise_for_status()
    commits = response.json()
    return [c["commit"]["message"] for c in commits]


async def async_main():
    """Async entry point for PR-Sentry."""
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
    anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-4-5-haiku-20251015")

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
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Fetch PR data, diff, and commits concurrently
            pr_data_task = fetch_pr_data(client, repo, pr_number, github_token)
            diff_task = fetch_pr_diff(client, repo, pr_number, github_token)
            commits_task = fetch_commit_messages(client, repo, pr_number, github_token)
            
            pr_data, raw_diff, commit_messages = await asyncio.gather(
                pr_data_task, diff_task, commits_task
            )
        
        title = pr_data.get("title", "")
        body = pr_data.get("body", "") or ""
        
        # Run the review (still sync for now, LLM calls are blocking)
        result = reviewer.review_pr(
            title=title,
            body=body,
            commit_messages=commit_messages,
            raw_diff=raw_diff
        )
    except httpx.HTTPStatusError as e:
        print(f"❌ GitHub API error: {e.response.status_code}")
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"❌ Network error: {e}")
        sys.exit(1)
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


def main():
    """Sync wrapper for async main."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
