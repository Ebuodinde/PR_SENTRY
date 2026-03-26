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


def detect_provider_config():
    """Auto-detect provider from environment variables."""
    # Explicit provider selection
    provider = os.getenv("PR_SENTRY_PROVIDER", "").strip()
    api_key = os.getenv("PR_SENTRY_API_KEY", "").strip()
    model = os.getenv("PR_SENTRY_MODEL", "").strip()
    
    # Provider-specific keys (new format)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    
    # Auto-detect if no explicit provider
    if not provider:
        if anthropic_key:
            provider = "anthropic"
            api_key = anthropic_key
        elif openai_key:
            provider = "openai"
            api_key = openai_key
        elif deepseek_key:
            provider = "deepseek"
            api_key = deepseek_key
    
    # Use provider-specific key if api_key not set
    if not api_key:
        if provider == "anthropic":
            api_key = anthropic_key
        elif provider == "openai":
            api_key = openai_key
        elif provider == "deepseek":
            api_key = deepseek_key
    
    return provider, api_key, model


async def async_main():
    """Async entry point for PR-Sentry."""
    # Read environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")

    if not all([github_token, repo, pr_number]):
        print("❌ GITHUB_TOKEN, GITHUB_REPOSITORY, and PR_NUMBER are required.")
        sys.exit(1)

    # Auto-detect provider configuration
    provider, api_key, model = detect_provider_config()
    
    if not provider or not api_key:
        print("❌ No LLM provider configured. Set one of:")
        print("   - ANTHROPIC_API_KEY")
        print("   - OPENAI_API_KEY")
        print("   - DEEPSEEK_API_KEY")
        print("   Or use PR_SENTRY_PROVIDER + PR_SENTRY_API_KEY")
        sys.exit(1)

    try:
        reviewer = Reviewer(
            provider=provider,
            api_key=api_key,
            model=model or None,
        )
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print(f"🔍 PR-Sentry started: {repo} PR #{pr_number}")
    print(f"🤖 Provider: {provider}")

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
        print(f"✅ Provider: {result['provider']}")

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
