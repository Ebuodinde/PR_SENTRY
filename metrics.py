"""Metrics tracking and analytics for PR-Sentry.

Tracks:
- Token usage per PR
- Cost estimation per PR
- Model usage statistics
- Performance metrics
- Cache hit rates
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


class MetricsTracker:
    """Tracks PR review metrics for analytics and cost monitoring."""
    
    def __init__(self, metrics_dir: Optional[str] = None):
        """
        Initialize metrics tracker.
        
        Args:
            metrics_dir: Directory for storing metrics (default: ~/.pr-sentry-metrics)
        """
        if metrics_dir is None:
            metrics_dir = os.path.expanduser("~/.pr-sentry-metrics")
        
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session = {
            "session_id": f"session_{int(time.time())}",
            "start_time": time.time(),
            "prs_analyzed": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "models_used": {},
            "slop_detected": 0,
            "security_issues": 0,
        }
    
    def track_pr_review(
        self,
        repo: str,
        pr_number: int,
        result: Dict[str, Any],
        tokens_used: Optional[int] = None
    ) -> None:
        """
        Track a PR review event.
        
        Args:
            repo: Repository name (owner/name)
            pr_number: PR number
            result: Review result dict
            tokens_used: Tokens consumed (if available)
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Extract metrics from result
        is_slop = result.get("is_slop", False)
        skipped_llm = result.get("skipped_llm", False)
        routing_info = result.get("routing_info", {})
        performance = result.get("performance", {})
        
        model = routing_info.get("model", "unknown")
        cost_per_million = routing_info.get("cost_per_million", 0.0)
        
        # Estimate tokens if not provided (rough estimate: 4 chars = 1 token)
        if tokens_used is None and not skipped_llm:
            # Rough estimate based on review length
            review_text = result.get("review", "")
            tokens_used = len(review_text) // 4 + 500  # +500 for prompt overhead
        elif skipped_llm:
            tokens_used = 0
        
        # Calculate cost
        cost = 0.0
        if tokens_used > 0:
            cost = (tokens_used / 1_000_000) * cost_per_million
        
        # Update session stats
        self.current_session["prs_analyzed"] += 1
        self.current_session["total_tokens"] += tokens_used
        self.current_session["total_cost"] += cost
        
        if is_slop:
            self.current_session["slop_detected"] += 1
        
        security_count = len(result.get("security_hints", []))
        self.current_session["security_issues"] += security_count
        
        # Track model usage
        if model not in self.current_session["models_used"]:
            self.current_session["models_used"][model] = 0
        self.current_session["models_used"][model] += 1
        
        # Save individual PR metric
        pr_metric = {
            "timestamp": timestamp,
            "repo": repo,
            "pr_number": pr_number,
            "is_slop": is_slop,
            "skipped_llm": skipped_llm,
            "model": model,
            "tokens_used": tokens_used,
            "cost": cost,
            "security_issues": security_count,
            "pr_size": performance.get("pr_size", "unknown"),
            "complexity": routing_info.get("complexity", 0),
        }
        
        self._save_pr_metric(pr_metric)
    
    def _save_pr_metric(self, metric: Dict[str, Any]) -> None:
        """Save individual PR metric to file."""
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_file = self.metrics_dir / f"daily_{date}.jsonl"
        
        with open(daily_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(metric) + "\n")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get current session summary."""
        elapsed = time.time() - self.current_session["start_time"]
        
        return {
            **self.current_session,
            "elapsed_seconds": int(elapsed),
            "avg_cost_per_pr": (
                self.current_session["total_cost"] / self.current_session["prs_analyzed"]
                if self.current_session["prs_analyzed"] > 0
                else 0.0
            ),
        }
    
    def get_daily_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a specific day.
        
        Args:
            date: Date in YYYY-MM-DD format (default: today)
        
        Returns:
            Daily statistics
        """
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        daily_file = self.metrics_dir / f"daily_{date}.jsonl"
        
        if not daily_file.exists():
            return {
                "date": date,
                "prs_analyzed": 0,
                "total_cost": 0.0,
                "total_tokens": 0,
            }
        
        stats = {
            "date": date,
            "prs_analyzed": 0,
            "total_cost": 0.0,
            "total_tokens": 0,
            "slop_detected": 0,
            "security_issues": 0,
            "models_used": {},
            "pr_sizes": {},
        }
        
        with open(daily_file, "r", encoding="utf-8") as f:
            for line in f:
                metric = json.loads(line)
                stats["prs_analyzed"] += 1
                stats["total_cost"] += metric.get("cost", 0.0)
                stats["total_tokens"] += metric.get("tokens_used", 0)
                
                if metric.get("is_slop"):
                    stats["slop_detected"] += 1
                
                stats["security_issues"] += metric.get("security_issues", 0)
                
                model = metric.get("model", "unknown")
                stats["models_used"][model] = stats["models_used"].get(model, 0) + 1
                
                pr_size = metric.get("pr_size", "unknown")
                stats["pr_sizes"][pr_size] = stats["pr_sizes"].get(pr_size, 0) + 1
        
        return stats
    
    def get_all_time_stats(self) -> Dict[str, Any]:
        """Get all-time statistics across all daily files."""
        all_stats = {
            "prs_analyzed": 0,
            "total_cost": 0.0,
            "total_tokens": 0,
            "slop_detected": 0,
            "security_issues": 0,
            "models_used": {},
            "pr_sizes": {},
            "daily_breakdown": [],
        }
        
        for daily_file in sorted(self.metrics_dir.glob("daily_*.jsonl")):
            date = daily_file.stem.replace("daily_", "")
            daily_stats = self.get_daily_stats(date)
            
            all_stats["prs_analyzed"] += daily_stats["prs_analyzed"]
            all_stats["total_cost"] += daily_stats["total_cost"]
            all_stats["total_tokens"] += daily_stats["total_tokens"]
            all_stats["slop_detected"] += daily_stats["slop_detected"]
            all_stats["security_issues"] += daily_stats["security_issues"]
            
            # Merge model usage
            for model, count in daily_stats["models_used"].items():
                all_stats["models_used"][model] = all_stats["models_used"].get(model, 0) + count
            
            # Merge PR sizes
            for size, count in daily_stats["pr_sizes"].items():
                all_stats["pr_sizes"][size] = all_stats["pr_sizes"].get(size, 0) + count
            
            all_stats["daily_breakdown"].append({
                "date": date,
                "prs": daily_stats["prs_analyzed"],
                "cost": daily_stats["total_cost"],
            })
        
        return all_stats
    
    def format_stats_report(self, stats: Dict[str, Any]) -> str:
        """Format statistics as human-readable report."""
        lines = []
        lines.append("=" * 60)
        lines.append("PR-Sentry Metrics Report")
        lines.append("=" * 60)
        lines.append("")
        
        lines.append(f"PRs Analyzed: {stats['prs_analyzed']}")
        lines.append(f"Total Cost: ${stats['total_cost']:.4f}")
        lines.append(f"Total Tokens: {stats['total_tokens']:,}")
        lines.append(f"AI Slop Detected: {stats['slop_detected']}")
        lines.append(f"Security Issues Found: {stats['security_issues']}")
        lines.append("")
        
        if stats.get("avg_cost_per_pr"):
            lines.append(f"Avg Cost/PR: ${stats['avg_cost_per_pr']:.4f}")
            lines.append("")
        
        if stats.get("models_used"):
            lines.append("Models Used:")
            for model, count in sorted(stats["models_used"].items(), key=lambda x: x[1], reverse=True):
                pct = (count / stats["prs_analyzed"] * 100) if stats["prs_analyzed"] > 0 else 0
                lines.append(f"  {model}: {count} ({pct:.1f}%)")
            lines.append("")
        
        if stats.get("pr_sizes"):
            lines.append("PR Sizes:")
            for size, count in sorted(stats["pr_sizes"].items(), key=lambda x: x[1], reverse=True):
                pct = (count / stats["prs_analyzed"] * 100) if stats["prs_analyzed"] > 0 else 0
                lines.append(f"  {size}: {count} ({pct:.1f}%)")
            lines.append("")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# Global tracker instance
_global_tracker: Optional[MetricsTracker] = None


def get_tracker() -> MetricsTracker:
    """Get or create global metrics tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = MetricsTracker()
    return _global_tracker


if __name__ == "__main__":
    # Example usage
    tracker = MetricsTracker()
    
    # Simulate PR review
    result = {
        "is_slop": False,
        "skipped_llm": False,
        "security_hints": ["SQL injection risk"],
        "review": "Code looks good overall. Found 1 security issue.",
        "routing_info": {
            "model": "claude-sonnet-4.5",
            "cost_per_million": 3.0,
            "complexity": 5,
        },
        "performance": {
            "pr_size": "medium"
        }
    }
    
    tracker.track_pr_review("owner/repo", 123, result, tokens_used=5000)
    
    # Get session summary
    summary = tracker.get_session_summary()
    print(tracker.format_stats_report(summary))
    
    # Get daily stats
    daily = tracker.get_daily_stats()
    print("\nDaily Stats:")
    print(tracker.format_stats_report(daily))
