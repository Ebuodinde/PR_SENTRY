"""Tests for config_loader.py"""

import pytest
import os
from config_loader import (
    load_config,
    build_custom_prompt_additions,
    should_ignore_file,
    DEFAULT_CONFIG
)


class TestDefaultConfig:
    """Test default configuration values."""

    def test_default_config_exists(self):
        """Default config should have all required keys."""
        assert "language" in DEFAULT_CONFIG
        assert "ignore_paths" in DEFAULT_CONFIG
        assert "custom_rules" in DEFAULT_CONFIG
        assert "slop_threshold" in DEFAULT_CONFIG

    def test_default_language_english(self):
        """Default language should be English."""
        assert DEFAULT_CONFIG["language"] == "en"

    def test_default_slop_threshold(self):
        """Default slop threshold should be 60."""
        assert DEFAULT_CONFIG["slop_threshold"] == 60


class TestLoadConfig:
    """Test configuration loading."""

    def test_load_config_returns_dict(self):
        """load_config should return a dictionary."""
        config = load_config()
        assert isinstance(config, dict)

    def test_load_config_has_defaults(self):
        """Loaded config should have default values."""
        config = load_config()
        assert "language" in config
        assert "slop_threshold" in config


class TestBuildCustomPrompt:
    """Test custom prompt building."""

    def test_empty_rules(self):
        """No custom rules should return empty string."""
        config = {"custom_rules": []}
        result = build_custom_prompt_additions(config)
        assert result == ""

    def test_with_rules(self):
        """Custom rules should be formatted properly."""
        config = {
            "custom_rules": [
                "Check for SQL injection",
                "Flag memory leaks"
            ]
        }
        result = build_custom_prompt_additions(config)
        assert "ADDITIONAL USER-DEFINED RULES" in result
        assert "- Check for SQL injection" in result
        assert "- Flag memory leaks" in result

    def test_no_rules_key(self):
        """Missing custom_rules key should return empty string."""
        config = {}
        result = build_custom_prompt_additions(config)
        assert result == ""

    def test_single_rule(self):
        """Single rule should work correctly."""
        config = {"custom_rules": ["Always check null pointers"]}
        result = build_custom_prompt_additions(config)
        assert "Always check null pointers" in result


class TestShouldIgnoreFile:
    """Test file ignore logic."""

    def test_ignore_by_path(self):
        """Files in ignored paths should be ignored."""
        config = {"ignore_paths": ["vendor/", "node_modules/"]}
        assert should_ignore_file("vendor/package.js", config) is True
        assert should_ignore_file("node_modules/react/index.js", config) is True
        assert should_ignore_file("src/main.js", config) is False

    def test_ignore_by_pattern(self):
        """Files matching patterns should be ignored."""
        config = {"ignore_patterns": ["*.min.js", "*.generated.*"]}
        assert should_ignore_file("bundle.min.js", config) is True
        assert should_ignore_file("api.generated.ts", config) is True
        assert should_ignore_file("main.js", config) is False

    def test_empty_config(self):
        """Empty config should not ignore any files."""
        config = {"ignore_paths": [], "ignore_patterns": []}
        assert should_ignore_file("any/file.js", config) is False

    def test_combined_ignore(self):
        """Both paths and patterns should work together."""
        config = {
            "ignore_paths": ["vendor/"],
            "ignore_patterns": ["*.test.js"]
        }
        assert should_ignore_file("vendor/lib.js", config) is True
        assert should_ignore_file("main.test.js", config) is True
        assert should_ignore_file("src/main.js", config) is False

    def test_nested_path_ignore(self):
        """Nested paths should be properly ignored."""
        config = {"ignore_paths": ["dist/"]}
        assert should_ignore_file("dist/bundle.js", config) is True
        assert should_ignore_file("dist/chunks/vendor.js", config) is True
        assert should_ignore_file("src/dist.js", config) is False

    def test_glob_pattern_star(self):
        """Glob star patterns should work."""
        config = {"ignore_patterns": ["*.log", "*.tmp"]}
        assert should_ignore_file("error.log", config) is True
        assert should_ignore_file("cache.tmp", config) is True
        assert should_ignore_file("main.py", config) is False

    def test_missing_keys(self):
        """Config without ignore keys should not crash."""
        config = {}
        assert should_ignore_file("any/file.js", config) is False
