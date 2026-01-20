#!/usr/bin/env python3
# =============================================================================
# HVAC-ADS-2026 MCP Server
# Phase D0: Containerization + MCP Connector Stubs
# =============================================================================
"""
MCP (Model Context Protocol) Server for HVAC-ADS-2026.

This server exposes tool endpoints that can be called by LLM assistants.
Phase D0 implements stub endpoints that return NOT_IMPLEMENTED.

Tools registered:
- gsc_query: Google Search Console query (stub)
- indexing_publish: Google Indexing API publish (stub)
- twilio_events: Twilio events query (stub)

Usage:
    python -m core.mcp.server
    # or
    bin/mcp
"""

import json
import os
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import parse_qs, urlparse

# Import tool stubs
from core.mcp.tools.gsc_query import gsc_query
from core.mcp.tools.indexing_publish import indexing_publish
from core.mcp.tools.twilio_events import twilio_events


# =============================================================================
# Configuration
# =============================================================================

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8080"))

# Tool registry: maps tool names to handler functions
TOOL_REGISTRY = {
    "gsc_query": gsc_query,
    "indexing_publish": indexing_publish,
    "twilio_events": twilio_events,
}

# Tool metadata for discovery
TOOL_METADATA = {
    "gsc_query": {
        "name": "gsc_query",
        "description": "Query Google Search Console for search analytics data",
        "parameters": {
            "site_url": "The verified site URL (e.g., https://buycomfortdirect.com)",
            "start_date": "Start date for query (YYYY-MM-DD)",
            "end_date": "End date for query (YYYY-MM-DD)",
            "dimensions": "List of dimensions: query, page, device, country",
            "row_limit": "Maximum rows to return (default: 1000)",
        },
        "returns": "Search analytics data or NOT_IMPLEMENTED status",
        "api_access": "READ",
        "status": "NOT_IMPLEMENTED",
    },
    "indexing_publish": {
        "name": "indexing_publish",
        "description": "Submit URL to Google Indexing API for crawling/indexing",
        "parameters": {
            "url": "The URL to submit for indexing",
            "action": "Action type: URL_UPDATED or URL_DELETED",
        },
        "returns": "Indexing request status or NOT_IMPLEMENTED status",
        "api_access": "WRITE",
        "status": "NOT_IMPLEMENTED",
    },
    "twilio_events": {
        "name": "twilio_events",
        "description": "Query Twilio call/SMS event logs",
        "parameters": {
            "event_type": "Type of events: calls, messages, or all",
            "start_date": "Start date for query (YYYY-MM-DD)",
            "end_date": "End date for query (YYYY-MM-DD)",
            "phone_number": "Filter by phone number (optional)",
            "limit": "Maximum events to return (default: 100)",
        },
        "returns": "Event logs or NOT_IMPLEMENTED status",
        "api_access": "READ",
        "status": "NOT_IMPLEMENTED",
    },
}


# =============================================================================
# HTTP Request Handler
# =============================================================================


class MCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP server."""

    def _send_json_response(self, data: dict, status_code: int = 200):
        """Send a JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode("utf-8"))

    def _send_error_response(self, message: str, status_code: int = 400):
        """Send an error response."""
        self._send_json_response(
            {
                "status": "ERROR",
                "error": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            status_code,
        )

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        # Health check endpoint
        if path == "/health":
            self._send_json_response(
                {
                    "status": "OK",
                    "service": "hvac-ads-mcp",
                    "version": "D0.1",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            return

        # Tool discovery endpoint
        if path == "/tools":
            self._send_json_response(
                {
                    "status": "OK",
                    "tools": TOOL_METADATA,
                    "count": len(TOOL_METADATA),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            return

        # Tool metadata endpoint
        if path.startswith("/tools/"):
            tool_name = path.split("/")[-1]
            if tool_name in TOOL_METADATA:
                self._send_json_response(
                    {
                        "status": "OK",
                        "tool": TOOL_METADATA[tool_name],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            else:
                self._send_error_response(f"Tool not found: {tool_name}", 404)
            return

        # Root endpoint
        if path == "/":
            self._send_json_response(
                {
                    "status": "OK",
                    "service": "HVAC-ADS-2026 MCP Server",
                    "version": "D0.1",
                    "phase": "D0 - Containerization + Stubs",
                    "endpoints": {
                        "GET /health": "Health check",
                        "GET /tools": "List available tools",
                        "GET /tools/<name>": "Get tool metadata",
                        "POST /invoke/<name>": "Invoke a tool",
                    },
                    "tools_registered": list(TOOL_REGISTRY.keys()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            return

        self._send_error_response(f"Unknown endpoint: {path}", 404)

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        # Tool invocation endpoint
        if path.startswith("/invoke/"):
            tool_name = path.split("/")[-1]

            if tool_name not in TOOL_REGISTRY:
                self._send_error_response(f"Tool not found: {tool_name}", 404)
                return

            # Parse request body
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 0:
                    body = self.rfile.read(content_length).decode("utf-8")
                    params = json.loads(body) if body else {}
                else:
                    params = {}
            except json.JSONDecodeError as e:
                self._send_error_response(f"Invalid JSON: {e}", 400)
                return

            # Invoke tool
            try:
                result = TOOL_REGISTRY[tool_name](params)
                self._send_json_response(result)
            except Exception as e:
                self._send_error_response(f"Tool execution failed: {e}", 500)
            return

        self._send_error_response(f"Unknown endpoint: {path}", 404)

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format: str, *args):
        """Custom log format."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {self.address_string()} - {format % args}")


# =============================================================================
# Server Startup
# =============================================================================


def run_server():
    """Start the MCP server."""
    server_address = (MCP_HOST, MCP_PORT)
    httpd = HTTPServer(server_address, MCPRequestHandler)

    print("=" * 70)
    print("HVAC-ADS-2026 MCP Server")
    print("Phase D0: Containerization + MCP Connector Stubs")
    print("=" * 70)
    print()
    print(f"Server running on http://{MCP_HOST}:{MCP_PORT}")
    print()
    print("Registered tools:")
    for name, meta in TOOL_METADATA.items():
        status = meta.get("status", "UNKNOWN")
        api_access = meta.get("api_access", "UNKNOWN")
        print(f"  - {name} [{api_access}] ({status})")
    print()
    print("Endpoints:")
    print("  GET  /           - Server info")
    print("  GET  /health     - Health check")
    print("  GET  /tools      - List all tools")
    print("  GET  /tools/<n>  - Get tool metadata")
    print("  POST /invoke/<n> - Invoke a tool")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        httpd.shutdown()


if __name__ == "__main__":
    run_server()
