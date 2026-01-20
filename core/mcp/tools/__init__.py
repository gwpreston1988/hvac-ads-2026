# =============================================================================
# HVAC-ADS-2026 MCP Tools
# Phase D0: Connector Stubs
# =============================================================================
"""
MCP tool stubs for Phase D0.

All tools return NOT_IMPLEMENTED status.
No live API calls are made.

Tools:
- gsc_query: Google Search Console query
- indexing_publish: Google Indexing API publish
- twilio_events: Twilio events query
"""

from core.mcp.tools.gsc_query import gsc_query
from core.mcp.tools.indexing_publish import indexing_publish
from core.mcp.tools.twilio_events import twilio_events

__all__ = ["gsc_query", "indexing_publish", "twilio_events"]
