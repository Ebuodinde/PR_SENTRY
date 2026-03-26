"""Performance optimization utilities for PR-Sentry.

Handles:
- Smart file filtering (skip test files, generated code, vendor)
- Caching (avoid re-analyzing same commits)
- Parallel processing (batch file analysis)
- Rate limiting (GitHub API quota management)
"""

import hashlib
import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path


class PerformanceOptimizer:
    """Handles performance optimizations for large PRs."""
    
    # Files/paths to skip for performance (auto-ignored patterns)
    SKIP_PATTERNS = [
        # Dependencies
        "node_modules/", "vendor/", ".venv/", "venv/", "__pycache__/",
        # Lock files
        "package-lock.json", "yarn.lock", "poetry.lock", "cargo.lock", "gemfile.lock",
        # Build outputs
        "dist/", "build/", "target/", "out/", ".next/", ".nuxt/",
        # Generated code
        "_generated/", "generated/", ".gen/", "proto/",
        # IDE
        ".idea/", ".vscode/", ".vs/",
        # Large binary
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar.gz",
    ]
    
    # File priorities (higher = review first)
    PRIORITY_PATTERNS = {
        # Core security files (priority 10)
        "auth": 10, "security": 10, "crypto": 10, "password": 10,
        # API/Network (priority 8)
        "api": 8, "router": 8, "handler": 8, "controller": 8,
        # Core logic (priority 6)
        "service": 6, "model": 6, "repository": 6, "manager": 6,
        # Utils (priority 4)
        "util": 4, "helper": 4, "common": 4,
        # Tests (priority 2) - Note: "test" keyword has lower priority than "auth"
        ".test.": 2, ".spec.": 2, "_test.": 2, "test/": 2, "tests/": 2, "spec/": 2,
        # Docs/Config (priority 1)
        "readme": 1, "config": 1, "doc": 1, ".md": 1, ".yml": 1, ".yaml": 1,
    }
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize performance optimizer.
        
        Args:
            cache_dir: Directory for caching (default: ~/.pr-sentry-cache)
        """
        if cache_dir is None:
            cache_dir = os.path.expanduser("~/.pr-sentry-cache")
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def should_skip_file(self, filepath: str) -> bool:
        """
        Check if file should be skipped for performance.
        
        Args:
            filepath: File path to check
        
        Returns:
            True if file should be skipped
        """
        filepath_lower = filepath.lower()
        
        for pattern in self.SKIP_PATTERNS:
            if pattern in filepath_lower:
                return True
        
        return False
    
    def get_file_priority(self, filepath: str) -> int:
        """
        Get priority score for file (higher = more important).
        
        Args:
            filepath: File path
        
        Returns:
            Priority score (0-10)
        """
        filepath_lower = filepath.lower()
        
        # Special handling: test files have fixed priority 2 (even if they contain "auth")
        if any(pattern in filepath_lower for pattern in [".test.", ".spec.", "_test.", "test/", "tests/", "spec/"]):
            return 2
        
        # Check for priority keywords
        max_priority = 5  # Default
        
        for keyword, priority in self.PRIORITY_PATTERNS.items():
            if keyword in filepath_lower:
                # Take the highest matching priority
                max_priority = max(max_priority, priority)
        
        return max_priority
    
    def prioritize_files(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort files by priority (highest first).
        
        Args:
            files: List of file dicts with 'filename' key
        
        Returns:
            Sorted list of files
        """
        # Add priority to each file
        for file in files:
            file["_priority"] = self.get_file_priority(file.get("filename", ""))
        
        # Sort by priority (descending)
        return sorted(files, key=lambda f: f.get("_priority", 0), reverse=True)
    
    def filter_large_pr(
        self,
        files: List[Dict[str, Any]],
        max_files: int = 50,
        max_lines: int = 5000
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Filter large PRs to focus on most important files.
        
        Args:
            files: List of parsed files
            max_files: Maximum files to analyze
            max_lines: Maximum total lines to analyze
        
        Returns:
            (filtered_files, stats_dict)
        """
        # Skip performance-irrelevant files
        relevant_files = [f for f in files if not self.should_skip_file(f.get("filename", ""))]
        
        # Prioritize remaining files
        prioritized = self.prioritize_files(relevant_files)
        
        # Filter by file count and line count
        filtered = []
        total_lines = 0
        
        for file in prioritized:
            if len(filtered) >= max_files:
                break
            
            file_lines = len(file.get("changes", "").split("\n"))
            if total_lines + file_lines > max_lines:
                break
            
            filtered.append(file)
            total_lines += file_lines
        
        stats = {
            "total_files": len(files),
            "skipped_files": len(files) - len(relevant_files),
            "analyzed_files": len(filtered),
            "analyzed_lines": total_lines,
            "skipped_low_priority": len(relevant_files) - len(filtered)
        }
        
        return filtered, stats
    
    def get_pr_cache_key(self, repo: str, pr_number: int, commit_sha: str) -> str:
        """
        Generate cache key for PR analysis.
        
        Args:
            repo: Repository (owner/name)
            pr_number: PR number
            commit_sha: HEAD commit SHA
        
        Returns:
            Cache key (hash)
        """
        data = f"{repo}:{pr_number}:{commit_sha}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached review result.
        
        Args:
            cache_key: Cache key
        
        Returns:
            Cached result or None
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    
    def cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """
        Cache review result.
        
        Args:
            cache_key: Cache key
            result: Result to cache
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
        except Exception:
            pass  # Fail silently on cache errors
    
    def clear_cache(self, max_age_days: int = 7) -> int:
        """
        Clear old cache files.
        
        Args:
            max_age_days: Maximum age in days
        
        Returns:
            Number of files deleted
        """
        import time
        
        deleted = 0
        cutoff = time.time() - (max_age_days * 86400)
        
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.stat().st_mtime < cutoff:
                cache_file.unlink()
                deleted += 1
        
        return deleted


def estimate_pr_size(files: List[Dict[str, Any]]) -> str:
    """
    Estimate PR size category.
    
    Args:
        files: List of parsed files
    
    Returns:
        Size category: tiny, small, medium, large, xlarge
    """
    file_count = len(files)
    total_lines = sum(len(f.get("changes", "").split("\n")) for f in files)
    
    if file_count <= 3 and total_lines <= 100:
        return "tiny"
    elif file_count <= 10 and total_lines <= 500:
        return "small"
    elif file_count <= 30 and total_lines <= 2000:
        return "medium"
    elif file_count <= 100 and total_lines <= 5000:
        return "large"
    else:
        return "xlarge"


if __name__ == "__main__":
    # Example usage
    optimizer = PerformanceOptimizer()
    
    # Test file filtering
    test_files = [
        {"filename": "src/auth.py", "changes": "code"},
        {"filename": "node_modules/pkg/index.js", "changes": "code"},
        {"filename": "test/auth.test.py", "changes": "code"},
        {"filename": "package-lock.json", "changes": "json"},
    ]
    
    for f in test_files:
        skip = optimizer.should_skip_file(f["filename"])
        priority = optimizer.get_file_priority(f["filename"])
        print(f"{f['filename']}: skip={skip}, priority={priority}")
    
    # Test prioritization
    prioritized = optimizer.prioritize_files(test_files)
    print("\nPrioritized:")
    for f in prioritized:
        print(f"  {f['filename']} (priority={f.get('_priority')})")
