"""
Configuration loader for PR-Sentry.

Loads user configuration from .github/sentry-config.yml or sentry-config.yml
and merges with default settings.
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path


# Default configuration
DEFAULT_CONFIG = {
    "language": "en",
    "ignore_paths": [],
    "ignore_patterns": [],
    "custom_rules": [],
    "slop_threshold": 60,
    "max_diff_size": 12000,
}


def find_config_file() -> Optional[Path]:
    """
    Find the configuration file in the repository.
    
    Looks for (in order):
    1. .github/sentry-config.yml
    2. .github/sentry-config.yaml
    3. sentry-config.yml
    4. sentry-config.yaml
    """
    search_paths = [
        ".github/sentry-config.yml",
        ".github/sentry-config.yaml",
        "sentry-config.yml",
        "sentry-config.yaml",
    ]
    
    # Try to find repo root via git
    repo_root = os.getenv("GITHUB_WORKSPACE", ".")
    
    for path in search_paths:
        full_path = Path(repo_root) / path
        if full_path.exists():
            return full_path
    
    return None


def load_config() -> Dict[str, Any]:
    """
    Load and merge configuration with defaults.
    
    Returns merged config dict with all settings.
    """
    config = DEFAULT_CONFIG.copy()
    
    config_path = find_config_file()
    if config_path is None:
        return config
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
    except (yaml.YAMLError, IOError) as e:
        print(f"⚠️ Warning: Could not load config from {config_path}: {e}")
        return config
    
    # Merge user config into defaults
    for key, value in user_config.items():
        if key in config:
            if isinstance(config[key], list) and isinstance(value, list):
                # Extend lists instead of replacing
                config[key] = config[key] + value
            else:
                config[key] = value
        else:
            # Allow custom keys
            config[key] = value
    
    return config


def build_custom_prompt_additions(config: Dict[str, Any]) -> str:
    """
    Build additional prompt text from custom rules.
    
    Args:
        config: Loaded configuration dictionary
        
    Returns:
        Additional prompt text to append to system prompt
    """
    custom_rules = config.get("custom_rules", [])
    if not custom_rules:
        return ""
    
    rules_text = "\n".join(f"- {rule}" for rule in custom_rules)
    
    return f"""

ADDITIONAL USER-DEFINED RULES:
The repository maintainer has specified additional rules to check:
{rules_text}

Apply these rules with the same priority as the built-in security checks."""


def should_ignore_file(filepath: str, config: Dict[str, Any]) -> bool:
    """
    Check if a file should be ignored based on configuration.
    
    Args:
        filepath: Path to the file
        config: Loaded configuration dictionary
        
    Returns:
        True if file should be ignored
    """
    import fnmatch
    
    ignore_paths = config.get("ignore_paths", [])
    ignore_patterns = config.get("ignore_patterns", [])
    
    # Check exact path matches
    for path in ignore_paths:
        if filepath.startswith(path):
            return True
    
    # Check pattern matches
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(filepath, pattern):
            return True
    
    return False


# --- Test Area ---
if __name__ == "__main__":
    print("=== Config Loader Test ===\n")
    
    # Test default config
    config = load_config()
    print(f"Loaded config: {config}")
    
    # Test custom prompt building
    test_config = {
        "custom_rules": [
            "Check for SQL injection in any ORM call",
            "Flag memory leaks in C++ destructors",
            "Verify all API endpoints require authentication"
        ]
    }
    
    prompt_addition = build_custom_prompt_additions(test_config)
    print(f"\nCustom prompt addition:\n{prompt_addition}")
    
    # Test file ignore
    test_config_ignore = {
        "ignore_paths": ["vendor/", "node_modules/"],
        "ignore_patterns": ["*.min.js", "*.generated.*"]
    }
    
    print("\nFile ignore tests:")
    print(f"  vendor/package.js: {should_ignore_file('vendor/package.js', test_config_ignore)}")
    print(f"  src/main.js: {should_ignore_file('src/main.js', test_config_ignore)}")
    print(f"  bundle.min.js: {should_ignore_file('bundle.min.js', test_config_ignore)}")
