"""
fastmcp MCP server — tools and resources over HTTP/SSE transport.

Tools expose the same DB queries as the REST API, with additional
computed tools (BTU summary, thermal alert status).

Resources mirror the REST endpoints as pia:// URIs.
"""
from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP

from pia_server.config import settings
from pia_server.db.database import get_db_connection
from pia_server.db import queries

mcp = FastMCP(
    name="pia-metrics",
    instructions=(
        "PIA Metrics Server — provides system thermal readings and "
        "NVIDIA Spark GPU metrics. Use the tools to query current and "
        "historical data, or resources for structured access."
    ),
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _record_to_dict(record) -> dict[str, Any]:
    if record is None:
        return {}
    return record.model_dump()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_system_current() -> dict[str, Any]:
    """Return the most recent system thermal reading."""
    async with get_db_connection() as conn:
        record = await queries.get_system_current(conn)
    return _record_to_dict(record)


@mcp.tool()
async def get_system_history(limit: int = 20) -> list[dict[str, Any]]:
    """Return historical system thermal readings (max 20)."""
    async with get_db_connection() as conn:
        records = await queries.get_system_history(conn, limit=limit)
    return [r.model_dump() for r in records]


@mcp.tool()
async def get_spark_current(server_id: int) -> dict[str, Any]:
    """Return the most recent reading for a single Spark server (server_id 1-5)."""
    async with get_db_connection() as conn:
        record = await queries.get_spark_current(conn, server_id)
    return _record_to_dict(record)


@mcp.tool()
async def get_spark_history(server_id: int, limit: int = 20) -> list[dict[str, Any]]:
    """Return historical readings for one Spark server (server_id 1-5, max 20)."""
    async with get_db_connection() as conn:
        records = await queries.get_spark_history(conn, server_id, limit=limit)
    return [r.model_dump() for r in records]


@mcp.tool()
async def get_all_spark_current() -> list[dict[str, Any]]:
    """Return the current reading for all 5 Spark servers."""
    async with get_db_connection() as conn:
        records = await queries.get_all_spark_current(conn)
    return [r.model_dump() for r in records]


@mcp.tool()
async def get_btu_summary() -> dict[str, Any]:
    """
    Return the current BTU transfer value and the 20-reading rolling average.

    BTU formula: 1.08 × CFM × (exhaust_temp − inlet_temp)
    """
    async with get_db_connection() as conn:
        current = await queries.get_system_current(conn)
        history = await queries.get_system_history(conn, limit=20)

    current_btu = current.btu_transfer if current else None
    avg_btu: float | None = None
    if history:
        avg_btu = sum(r.btu_transfer for r in history) / len(history)

    return {
        "current_btu_transfer": current_btu,
        "rolling_avg_btu_transfer_20": round(avg_btu, 2) if avg_btu is not None else None,
        "sample_count": len(history),
    }


@mcp.tool()
async def get_thermal_alert_status() -> list[dict[str, Any]]:
    """
    Return Spark servers where any throttle flag or power-near-TTP is active.

    Returns an empty list when all servers are operating normally.
    """
    async with get_db_connection() as conn:
        records = await queries.get_all_spark_current(conn)

    alerts = []
    for r in records:
        if r.spark_throttle_thermal or r.spark_throttle_power or r.power_near_ttp:
            alerts.append({
                "server_id": r.server_id,
                "spark_throttle_thermal": r.spark_throttle_thermal,
                "spark_throttle_power": r.spark_throttle_power,
                "power_near_ttp": r.power_near_ttp,
                "spark_gpu_temp_celsius": r.spark_gpu_temp_celsius,
                "collected_at": r.collected_at,
            })
    return alerts


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("pia://system/current")
async def resource_system_current() -> str:
    """Current system thermal reading as JSON."""
    async with get_db_connection() as conn:
        record = await queries.get_system_current(conn)
    return json.dumps(_record_to_dict(record))


@mcp.resource("pia://system/history")
async def resource_system_history() -> str:
    """Last 20 system thermal readings as JSON."""
    async with get_db_connection() as conn:
        records = await queries.get_system_history(conn, limit=20)
    return json.dumps([r.model_dump() for r in records])


@mcp.resource("pia://spark/{server_id}/current")
async def resource_spark_current(server_id: int) -> str:
    """Current reading for a single Spark server as JSON."""
    async with get_db_connection() as conn:
        record = await queries.get_spark_current(conn, server_id)
    return json.dumps(_record_to_dict(record))


@mcp.resource("pia://spark/{server_id}/history")
async def resource_spark_history(server_id: int) -> str:
    """Last 20 readings for a single Spark server as JSON."""
    async with get_db_connection() as conn:
        records = await queries.get_spark_history(conn, server_id, limit=20)
    return json.dumps([r.model_dump() for r in records])


@mcp.resource("pia://spark/all/current")
async def resource_spark_all_current() -> str:
    """Current readings for all 5 Spark servers as JSON."""
    async with get_db_connection() as conn:
        records = await queries.get_all_spark_current(conn)
    return json.dumps([r.model_dump() for r in records])


@mcp.resource("pia://config")
async def resource_config() -> str:
    """Server configuration (non-sensitive settings) as JSON."""
    return json.dumps({
        "rest_port": settings.rest_port,
        "mcp_port": settings.mcp_port,
        "collection_interval_seconds": settings.collection_interval_seconds,
        "collector_type": settings.collector_type,
        "temp_unit": settings.temp_unit,
    })
