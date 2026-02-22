"""Tests for MCP tools via direct function calls (no transport layer)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest

from pia_server.db import queries
from pia_server.models.spark import SparkReading


# We call the underlying tool functions directly after patching the DB
@asynccontextmanager
async def _fake_db(db_conn):
    yield db_conn


@pytest.mark.asyncio
async def test_mcp_get_system_current_empty(db_conn):
    with patch("pia_server.mcp_server.server.get_db_connection", lambda: _fake_db(db_conn)):
        from pia_server.mcp_server.server import get_system_current
        result = await get_system_current()
    assert result == {}


@pytest.mark.asyncio
async def test_mcp_get_system_current_returns_data(db_conn, sample_system_reading):
    await queries.insert_and_prune_system(db_conn, sample_system_reading)
    with patch("pia_server.mcp_server.server.get_db_connection", lambda: _fake_db(db_conn)):
        from pia_server.mcp_server.server import get_system_current
        result = await get_system_current()
    assert result["air_inlet_temp"] == sample_system_reading.air_inlet_temp
    assert result["btu_transfer"] > 0


@pytest.mark.asyncio
async def test_mcp_get_system_history(db_conn, sample_system_reading):
    for _ in range(5):
        await queries.insert_and_prune_system(db_conn, sample_system_reading)
    with patch("pia_server.mcp_server.server.get_db_connection", lambda: _fake_db(db_conn)):
        from pia_server.mcp_server.server import get_system_history
        result = await get_system_history(limit=3)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_mcp_get_spark_current(db_conn, sample_spark_reading):
    await queries.insert_and_prune_spark(db_conn, sample_spark_reading)
    with patch("pia_server.mcp_server.server.get_db_connection", lambda: _fake_db(db_conn)):
        from pia_server.mcp_server.server import get_spark_current
        result = await get_spark_current(server_id=1)
    assert result["server_id"] == 1
    assert result["spark_gpu_temp_celsius"] == sample_spark_reading.spark_gpu_temp_celsius


@pytest.mark.asyncio
async def test_mcp_get_all_spark_current(db_conn):
    for sid in range(1, 6):
        r = SparkReading(
            server_id=sid,
            spark_gpu_temp_celsius=65.0,
            spark_memory_temp_celsius=70.0,
            spark_throttle_thermal=False,
            spark_throttle_power=False,
            power_near_ttp=False,
            spark_sm_clock_mhz=1600.0,
        )
        await queries.insert_and_prune_spark(db_conn, r)

    with patch("pia_server.mcp_server.server.get_db_connection", lambda: _fake_db(db_conn)):
        from pia_server.mcp_server.server import get_all_spark_current
        result = await get_all_spark_current()
    assert len(result) == 5


@pytest.mark.asyncio
async def test_mcp_btu_summary(db_conn, sample_system_reading):
    for _ in range(5):
        await queries.insert_and_prune_system(db_conn, sample_system_reading)

    with patch("pia_server.mcp_server.server.get_db_connection", lambda: _fake_db(db_conn)):
        from pia_server.mcp_server.server import get_btu_summary
        result = await get_btu_summary()
    assert result["current_btu_transfer"] is not None
    assert result["rolling_avg_btu_transfer_20"] is not None
    assert result["sample_count"] == 5


@pytest.mark.asyncio
async def test_mcp_thermal_alert_no_alerts(db_conn):
    for sid in range(1, 6):
        r = SparkReading(
            server_id=sid,
            spark_gpu_temp_celsius=65.0,
            spark_memory_temp_celsius=70.0,
            spark_throttle_thermal=False,
            spark_throttle_power=False,
            power_near_ttp=False,
            spark_sm_clock_mhz=1600.0,
        )
        await queries.insert_and_prune_spark(db_conn, r)

    with patch("pia_server.mcp_server.server.get_db_connection", lambda: _fake_db(db_conn)):
        from pia_server.mcp_server.server import get_thermal_alert_status
        result = await get_thermal_alert_status()
    assert result == []


@pytest.mark.asyncio
async def test_mcp_thermal_alert_with_alert(db_conn):
    # Server 2 is throttling
    r = SparkReading(
        server_id=2,
        spark_gpu_temp_celsius=85.0,
        spark_memory_temp_celsius=80.0,
        spark_throttle_thermal=True,
        spark_throttle_power=False,
        power_near_ttp=True,
        spark_sm_clock_mhz=1200.0,
    )
    await queries.insert_and_prune_spark(db_conn, r)

    with patch("pia_server.mcp_server.server.get_db_connection", lambda: _fake_db(db_conn)):
        from pia_server.mcp_server.server import get_thermal_alert_status
        result = await get_thermal_alert_status()
    assert len(result) == 1
    assert result[0]["server_id"] == 2
    assert result[0]["spark_throttle_thermal"] is True
