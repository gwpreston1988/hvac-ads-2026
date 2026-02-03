#!/usr/bin/env python3
# =============================================================================
# HVAC-ADS-2026 MCP Tool: gsc_query
# Phase D1: Snapshot-Based Implementation
# =============================================================================
"""
Google Search Console Query Tool

This tool queries Google Search Console data from snapshots (READ-ONLY).
No live API calls are made - all data comes from snapshot files.

Parameters:
- snapshot_id: The snapshot ID to query (e.g., "2026-01-21T150850Z" or "latest")
- query_type: Type of query ("queries", "pages", "summary")
- filter_query: Optional filter for query text (partial match)
- limit: Maximum number of results to return (default: 100)

Returns:
- GSC data from the specified snapshot
- If snapshot missing or no GSC data, returns NOT_FOUND status
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def gsc_query(params: dict[str, Any]) -> dict[str, Any]:
    """
    Query Google Search Console data from snapshots.

    Args:
        params: Dictionary containing:
            - snapshot_id: Snapshot ID or "latest"
            - query_type: "queries", "pages", or "summary"
            - filter_query: Optional query filter (case-insensitive partial match)
            - limit: Max results (default: 100)

    Returns:
        Dictionary with GSC data or error status.
    """
    # Extract parameters
    snapshot_id = params.get("snapshot_id", "latest")
    query_type = params.get("query_type", "summary")
    filter_query = params.get("filter_query", "").lower()
    limit = params.get("limit", 100)

    # Find project root (assumes this script is in core/mcp/tools/)
    tool_dir = Path(__file__).parent
    project_root = tool_dir.parent.parent.parent
    snapshots_dir = project_root / "snapshots"

    # Resolve "latest" to actual snapshot ID
    if snapshot_id == "latest":
        try:
            snapshot_dirs = sorted([d for d in snapshots_dir.iterdir() if d.is_dir()], reverse=True)
            if not snapshot_dirs:
                return {
                    "status": "NOT_FOUND",
                    "error": "No snapshots found",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            snapshot_id = snapshot_dirs[0].name
        except Exception as e:
            return {
                "status": "ERROR",
                "error": f"Failed to resolve latest snapshot: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # Build path to GSC normalized data
    snapshot_dir = snapshots_dir / snapshot_id / "normalized" / "gsc"

    if not snapshot_dir.exists():
        return {
            "status": "NOT_FOUND",
            "error": f"GSC data not found in snapshot {snapshot_id}",
            "snapshot_id": snapshot_id,
            "note": "GSC data may not be configured or snapshot was created before GSC integration",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Load requested data
    try:
        if query_type == "summary":
            summary_path = snapshot_dir / "summary.json"
            if not summary_path.exists():
                return {
                    "status": "NOT_FOUND",
                    "error": "summary.json not found",
                    "snapshot_id": snapshot_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            with open(summary_path) as f:
                data = json.load(f)

            return {
                "status": "OK",
                "snapshot_id": snapshot_id,
                "query_type": "summary",
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        elif query_type == "queries":
            queries_path = snapshot_dir / "queries.json"
            if not queries_path.exists():
                return {
                    "status": "NOT_FOUND",
                    "error": "queries.json not found",
                    "snapshot_id": snapshot_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            with open(queries_path) as f:
                data = json.load(f)

            records = data.get("records", [])

            # Apply filter if specified
            if filter_query:
                records = [r for r in records if filter_query in r.get("query", "").lower()]

            # Apply limit
            records = records[:limit]

            return {
                "status": "OK",
                "snapshot_id": snapshot_id,
                "query_type": "queries",
                "count": len(records),
                "filtered": bool(filter_query),
                "filter": filter_query if filter_query else None,
                "limit": limit,
                "records": records,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        elif query_type == "pages":
            pages_path = snapshot_dir / "pages.json"
            if not pages_path.exists():
                return {
                    "status": "NOT_FOUND",
                    "error": "pages.json not found",
                    "snapshot_id": snapshot_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            with open(pages_path) as f:
                data = json.load(f)

            records = data.get("records", [])

            # Apply filter if specified (filter on page URL)
            if filter_query:
                records = [r for r in records if filter_query in r.get("page", "").lower()]

            # Apply limit
            records = records[:limit]

            return {
                "status": "OK",
                "snapshot_id": snapshot_id,
                "query_type": "pages",
                "count": len(records),
                "filtered": bool(filter_query),
                "filter": filter_query if filter_query else None,
                "limit": limit,
                "records": records,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        else:
            return {
                "status": "INVALID_PARAMETER",
                "error": f"Invalid query_type: {query_type}",
                "valid_types": ["queries", "pages", "summary"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "snapshot_id": snapshot_id,
            "query_type": query_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
