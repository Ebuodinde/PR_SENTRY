#!/usr/bin/env python3
"""PR-Sentry CLI - Command line interface for PR reviews.

Usage:
    pr-sentry review --repo owner/repo --pr 123
    pr-sentry analyze-diff < diff.patch
    pr-sentry stats [--daily|--all-time]
"""

import argparse
import asyncio
import sys
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()


def get_reviewer():
    """Import and create Reviewer instance."""
    from reviewer import Reviewer
    return Reviewer(
        provider="anthropic",
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )


async def review_github_pr(repo: str, pr_number: int, token: str) -> dict:
    """Review a GitHub PR."""
    from main import fetch_pr_data, fetch_pr_diff, fetch_commit_messages
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        pr_data = await fetch_pr_data(client, repo, str(pr_number), token)
        diff = await fetch_pr_diff(client, repo, str(pr_number), token)
        commits = await fetch_commit_messages(client, repo, str(pr_number), token)
    
    reviewer = get_reviewer()
    result = reviewer.review_pr(
        title=pr_data.get("title", ""),
        body=pr_data.get("body", "") or "",
        commit_messages=commits,
        raw_diff=diff
    )
    
    return result


async def review_gitlab_mr(project_id: str, mr_iid: int, token: str, gitlab_url: str) -> dict:
    """Review a GitLab MR."""
    from gitlab_client import GitLabClient
    
    client = GitLabClient(token=token, gitlab_url=gitlab_url)
    
    async with httpx.AsyncClient(timeout=60.0) as http:
        mr_data = await client.fetch_mr_data(http, project_id, mr_iid)
        diff = await client.fetch_mr_diff(http, project_id, mr_iid)
        commits = await client.fetch_mr_commits(http, project_id, mr_iid)
    
    reviewer = get_reviewer()
    result = reviewer.review_pr(
        title=mr_data.get("title", ""),
        body=mr_data.get("description", "") or "",
        commit_messages=commits,
        raw_diff=diff
    )
    
    return result


def analyze_diff(diff_text: str) -> dict:
    """Analyze a diff from stdin or file."""
    reviewer = get_reviewer()
    result = reviewer.review_pr(
        title="CLI Analysis",
        body="Diff analysis via CLI",
        commit_messages=[],
        raw_diff=diff_text
    )
    return result


def show_stats(daily: bool = False, all_time: bool = False):
    """Show metrics statistics."""
    from metrics import MetricsTracker
    
    tracker = MetricsTracker()
    
    if all_time:
        stats = tracker.get_all_time_stats()
    else:
        stats = tracker.get_daily_stats()
    
    print(tracker.format_stats_report(stats))


def format_result(result: dict) -> str:
    """Format review result for CLI output."""
    lines = []
    lines.append("=" * 60)
    lines.append("PR-Sentry Review Result")
    lines.append("=" * 60)
    lines.append("")
    
    if result.get("is_slop"):
        lines.append(f"⚠️  AI SLOP DETECTED (score: {result.get('slop_score', 0)}/100)")
        lines.append("")
    
    if result.get("security_hints"):
        lines.append("🔒 Security Issues:")
        for hint in result["security_hints"]:
            lines.append(f"   • {hint}")
        lines.append("")
    
    if result.get("review"):
        lines.append("📝 Review:")
        lines.append(result["review"])
        lines.append("")
    
    if result.get("summary"):
        lines.append("📊 Summary:")
        lines.append(result["summary"])
        lines.append("")
    
    if result.get("routing_info"):
        info = result["routing_info"]
        lines.append(f"ℹ️  Model: {info.get('model', 'unknown')}")
        lines.append(f"   Cost: ~${info.get('cost_per_million', 0) * 0.001:.4f} (estimate)")
    
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="pr-sentry",
        description="Zero-Nitpick AI code review for PR/MR"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Review command
    review_parser = subparsers.add_parser("review", help="Review a PR/MR")
    review_parser.add_argument("--repo", "-r", help="Repository (owner/repo)")
    review_parser.add_argument("--pr", "-p", type=int, help="PR/MR number")
    review_parser.add_argument("--gitlab", action="store_true", help="Use GitLab instead of GitHub")
    review_parser.add_argument("--project-id", help="GitLab project ID")
    review_parser.add_argument("--gitlab-url", default="https://gitlab.com", help="GitLab URL")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze diff from stdin")
    analyze_parser.add_argument("--file", "-f", help="Diff file path (or use stdin)")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show usage statistics")
    stats_parser.add_argument("--daily", action="store_true", help="Show daily stats")
    stats_parser.add_argument("--all-time", action="store_true", help="Show all-time stats")
    
    # Version
    parser.add_argument("--version", "-v", action="version", version="pr-sentry 2.0.0")
    
    args = parser.parse_args()
    
    if args.command == "review":
        if args.gitlab:
            # GitLab MR review
            token = os.environ.get("GITLAB_TOKEN")
            if not token:
                print("Error: GITLAB_TOKEN environment variable required", file=sys.stderr)
                sys.exit(1)
            
            project_id = args.project_id or os.environ.get("CI_PROJECT_ID")
            mr_iid = args.pr or int(os.environ.get("CI_MERGE_REQUEST_IID", 0))
            
            if not project_id or not mr_iid:
                print("Error: --project-id and --pr required for GitLab", file=sys.stderr)
                sys.exit(1)
            
            result = asyncio.run(review_gitlab_mr(
                project_id, mr_iid, token, args.gitlab_url
            ))
        else:
            # GitHub PR review
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                print("Error: GITHUB_TOKEN environment variable required", file=sys.stderr)
                sys.exit(1)
            
            if not args.repo or not args.pr:
                print("Error: --repo and --pr required", file=sys.stderr)
                sys.exit(1)
            
            result = asyncio.run(review_github_pr(args.repo, args.pr, token))
        
        print(format_result(result))
    
    elif args.command == "analyze":
        if args.file:
            with open(args.file, "r") as f:
                diff_text = f.read()
        else:
            diff_text = sys.stdin.read()
        
        if not diff_text.strip():
            print("Error: No diff provided", file=sys.stderr)
            sys.exit(1)
        
        result = analyze_diff(diff_text)
        print(format_result(result))
    
    elif args.command == "stats":
        show_stats(daily=args.daily, all_time=args.all_time)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
