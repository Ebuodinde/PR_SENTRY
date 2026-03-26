#!/usr/bin/env python3
"""
PR-Sentry MCP Server

Model Context Protocol server for PR-Sentry, allowing AI assistants
like Claude Code to perform code reviews directly.

Usage:
    python mcp_server.py

Or add to your MCP configuration:
    {
        "mcpServers": {
            "pr-sentry": {
                "command": "python",
                "args": ["/path/to/pr-sentry/mcp_server.py"]
            }
        }
    }
"""

import json
import sys
from typing import Any

from slop_detector import SlopDetector
from diff_parser import DiffParser


class PRSentryMCP:
    """MCP server implementation for PR-Sentry."""
    
    def __init__(self):
        self.slop_detector = SlopDetector()
        self.diff_parser = DiffParser()
    
    def handle_request(self, request: dict) -> dict:
        """Handle incoming MCP request."""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        if method == "initialize":
            return self._initialize(request_id)
        elif method == "tools/list":
            return self._list_tools(request_id)
        elif method == "tools/call":
            return self._call_tool(request_id, params)
        else:
            return self._error(request_id, -32601, f"Method not found: {method}")
    
    def _initialize(self, request_id: Any) -> dict:
        """Handle initialize request."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "pr-sentry",
                    "version": "2.1.0"
                }
            }
        }
    
    def _list_tools(self, request_id: Any) -> dict:
        """List available tools."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "review_diff",
                        "description": "Review a code diff for security issues, bugs, and AI-generated content. Returns only critical issues - no style nitpicks.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "diff": {
                                    "type": "string",
                                    "description": "The git diff to review"
                                },
                                "title": {
                                    "type": "string",
                                    "description": "PR or commit title (optional)"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "PR or commit description (optional)"
                                }
                            },
                            "required": ["diff"]
                        }
                    },
                    {
                        "name": "check_slop",
                        "description": "Check if content appears to be AI-generated slop. Returns a score from 0-100.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "Title to analyze"
                                },
                                "body": {
                                    "type": "string",
                                    "description": "Body/description to analyze"
                                }
                            },
                            "required": ["title", "body"]
                        }
                    },
                    {
                        "name": "scan_security",
                        "description": "Scan code diff for security vulnerabilities like hardcoded secrets, SQL injection, XSS, etc.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "diff": {
                                    "type": "string",
                                    "description": "The git diff to scan"
                                }
                            },
                            "required": ["diff"]
                        }
                    }
                ]
            }
        }
    
    def _call_tool(self, request_id: Any, params: dict) -> dict:
        """Call a tool."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        try:
            if tool_name == "review_diff":
                result = self._review_diff(arguments)
            elif tool_name == "check_slop":
                result = self._check_slop(arguments)
            elif tool_name == "scan_security":
                result = self._scan_security(arguments)
            else:
                return self._error(request_id, -32602, f"Unknown tool: {tool_name}")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result
                        }
                    ]
                }
            }
        except Exception as e:
            return self._error(request_id, -32603, str(e))
    
    def _review_diff(self, args: dict) -> str:
        """Review a code diff."""
        diff = args.get("diff", "")
        title = args.get("title", "Code Review")
        description = args.get("description", "")
        
        # Parse diff
        parsed_files = self.diff_parser.parse_diff(diff)
        
        # Check for slop
        slop_result = self.slop_detector.evaluate_pr(title, description, [])
        
        # Collect security hints
        all_hints = []
        for f in parsed_files:
            all_hints.extend(f.get("security_hints", []))
        
        # Build response
        lines = ["## 🛡️ PR-Sentry Review\n"]
        
        # Slop check
        if slop_result["is_slop"]:
            lines.append(f"⚠️ **AI Slop Detected** (score: {slop_result['slop_score']}/100)\n")
            lines.append("This content appears to be AI-generated. Human review recommended.\n")
        
        # Security findings
        if all_hints:
            lines.append("### 🔒 Security Findings\n")
            for hint in all_hints:
                lines.append(f"- 🔴 {hint}")
            lines.append("")
        
        # File summary
        if parsed_files:
            total_add = sum(f.get("additions", 0) for f in parsed_files)
            total_del = sum(f.get("deletions", 0) for f in parsed_files)
            lines.append(f"### 📊 Summary\n")
            lines.append(f"**{len(parsed_files)} files** changed (+{total_add}/-{total_del})\n")
        
        if not all_hints and not slop_result["is_slop"]:
            lines.append("✅ No critical issues found in security scan.\n")
            lines.append("*Note: For full LLM-powered review, use the GitHub Action with an API key.*")
        
        return "\n".join(lines)
    
    def _check_slop(self, args: dict) -> str:
        """Check content for AI slop."""
        title = args.get("title", "")
        body = args.get("body", "")
        
        result = self.slop_detector.evaluate_pr(title, body, [])
        
        lines = ["## 🤖 Slop Detection Result\n"]
        lines.append(f"**Score:** {result['slop_score']}/100\n")
        
        if result["is_slop"]:
            lines.append("⚠️ **High AI content detected**\n")
            lines.append("This content shows signs of AI generation:\n")
            for metric, value in result.get("metrics", {}).items():
                if value > 0:
                    lines.append(f"- {metric}: {value}")
        else:
            lines.append("✅ Content appears to be human-written or lightly AI-assisted.")
        
        return "\n".join(lines)
    
    def _scan_security(self, args: dict) -> str:
        """Scan diff for security issues."""
        diff = args.get("diff", "")
        
        parsed_files = self.diff_parser.parse_diff(diff)
        
        all_hints = []
        file_hints = {}
        
        for f in parsed_files:
            hints = f.get("security_hints", [])
            if hints:
                file_hints[f["filename"]] = hints
                all_hints.extend(hints)
        
        lines = ["## 🔒 Security Scan Results\n"]
        
        if all_hints:
            lines.append(f"**{len(all_hints)} potential issues found**\n")
            
            for filename, hints in file_hints.items():
                lines.append(f"### `{filename}`\n")
                for hint in hints:
                    lines.append(f"- 🔴 {hint}")
                lines.append("")
        else:
            lines.append("✅ No security issues detected.\n")
            lines.append("*Scanned for: hardcoded secrets, SQL injection, XSS, command injection, path traversal, and 50+ other patterns.*")
        
        return "\n".join(lines)
    
    def _error(self, request_id: Any, code: int, message: str) -> dict:
        """Return JSON-RPC error."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    def run(self):
        """Run the MCP server (stdio transport)."""
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                response = self.handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError:
                error = self._error(None, -32700, "Parse error")
                print(json.dumps(error), flush=True)


def main():
    """Entry point."""
    server = PRSentryMCP()
    server.run()


if __name__ == "__main__":
    main()
