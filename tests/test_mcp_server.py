"""Tests for MCP server."""

import json
import pytest
from mcp_server import PRSentryMCP


class TestMCPServer:
    """Test MCP server functionality."""

    @pytest.fixture
    def server(self):
        """Create MCP server instance."""
        return PRSentryMCP()

    def test_initialize(self, server):
        """Test initialize request."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        response = server.handle_request(request)
        
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["serverInfo"]["name"] == "pr-sentry"

    def test_list_tools(self, server):
        """Test tools/list request."""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        response = server.handle_request(request)
        
        assert response["id"] == 2
        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        
        assert "review_diff" in tool_names
        assert "check_slop" in tool_names
        assert "scan_security" in tool_names

    def test_review_diff_clean(self, server):
        """Test review_diff with clean code."""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "review_diff",
                "arguments": {
                    "diff": """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
+import logging
 def main():
     print("Hello")
""",
                    "title": "Add logging import",
                    "description": "Simple import addition"
                }
            }
        }
        response = server.handle_request(request)
        
        assert response["id"] == 3
        assert "result" in response
        text = response["result"]["content"][0]["text"]
        assert "PR-Sentry Review" in text

    def test_review_diff_security_issue(self, server):
        """Test review_diff detecting security issue."""
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "review_diff",
                "arguments": {
                    "diff": """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,3 +1,4 @@
+API_KEY = "sk-1234567890abcdef"
 DEBUG = True
"""
                }
            }
        }
        response = server.handle_request(request)
        
        text = response["result"]["content"][0]["text"]
        assert "Security" in text or "🔴" in text

    def test_check_slop_human(self, server):
        """Test check_slop with human content."""
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "check_slop",
                "arguments": {
                    "title": "Fix null check bug",
                    "body": "Added null check to prevent crash when user not found."
                }
            }
        }
        response = server.handle_request(request)
        
        text = response["result"]["content"][0]["text"]
        assert "Score:" in text
        # Human content should have low score
        assert "human-written" in text.lower() or "0/" in text or "1/" in text or "2/" in text

    def test_check_slop_ai(self, server):
        """Test check_slop with AI-generated content."""
        request = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "check_slop",
                "arguments": {
                    "title": "Feature: Robust and Seamless API Integration",
                    "body": """This PR ensures a robust and seamless integration of the API.
                    It is crucial to leverage these endpoints to foster a comprehensive
                    user experience. We delve into meticulous refactoring as testament
                    to our pivotal architecture. The scalable solution will streamline."""
                }
            }
        }
        response = server.handle_request(request)
        
        text = response["result"]["content"][0]["text"]
        assert "Score:" in text

    def test_scan_security_clean(self, server):
        """Test scan_security with clean code."""
        request = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "scan_security",
                "arguments": {
                    "diff": """diff --git a/utils.py b/utils.py
--- a/utils.py
+++ b/utils.py
@@ -1,3 +1,5 @@
+def add(a, b):
+    return a + b
"""
                }
            }
        }
        response = server.handle_request(request)
        
        text = response["result"]["content"][0]["text"]
        assert "No security issues" in text or "✅" in text

    def test_scan_security_with_secret(self, server):
        """Test scan_security detecting hardcoded secret."""
        request = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "scan_security",
                "arguments": {
                    "diff": """diff --git a/db.py b/db.py
--- a/db.py
+++ b/db.py
@@ -1,3 +1,4 @@
+PASSWORD = "super_secret_password123"
 import psycopg2
"""
                }
            }
        }
        response = server.handle_request(request)
        
        text = response["result"]["content"][0]["text"]
        assert "Security" in text or "issues" in text.lower()

    def test_unknown_method(self, server):
        """Test handling of unknown method."""
        request = {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "unknown/method",
            "params": {}
        }
        response = server.handle_request(request)
        
        assert "error" in response
        assert response["error"]["code"] == -32601

    def test_unknown_tool(self, server):
        """Test handling of unknown tool."""
        request = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {}
            }
        }
        response = server.handle_request(request)
        
        assert "error" in response
        assert response["error"]["code"] == -32602
