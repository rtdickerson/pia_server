"""Tests for GraphQL queries via the Strawberry router."""
from __future__ import annotations

import pytest

from pia_server.db import queries
from pia_server.models.spark import SparkReading


GQL_SYSTEM_CURRENT = '{ systemCurrent { id airInletTemp airExhaustTemp caseTemp exhaustAirflow btuTransfer } }'
GQL_SYSTEM_HISTORY = '{ systemHistory(limit: 5) { id btuTransfer } }'
GQL_SYSTEM_SNAPSHOT = '{ systemSnapshot { current { id } history { id } } }'
GQL_SPARK_ALL = '{ sparkAllCurrent { serverId sparkGpuTempCelsius } }'
GQL_SPARK_CURRENT = '{ sparkCurrent(serverId: 1) { serverId sparkGpuTempCelsius } }'
GQL_SPARK_HISTORY = '{ sparkHistory(serverId: 1, limit: 3) { id } }'
GQL_SPARK_SNAPSHOT = '{ sparkSnapshot(serverId: 1) { serverId current { id } history { id } } }'


async def _gql(client, query: str):
    resp = await client.post("/graphql", json={"query": query})
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_system_current_null_when_empty(rest_client):
    data = await _gql(rest_client, GQL_SYSTEM_CURRENT)
    assert data["data"]["systemCurrent"] is None


@pytest.mark.asyncio
async def test_system_current_returns_data(rest_client, db_conn, sample_system_reading):
    await queries.insert_and_prune_system(db_conn, sample_system_reading)
    data = await _gql(rest_client, GQL_SYSTEM_CURRENT)
    result = data["data"]["systemCurrent"]
    assert result is not None
    assert result["airInletTemp"] == sample_system_reading.air_inlet_temp
    assert result["btuTransfer"] > 0


@pytest.mark.asyncio
async def test_system_history(rest_client, db_conn, sample_system_reading):
    for _ in range(5):
        await queries.insert_and_prune_system(db_conn, sample_system_reading)
    data = await _gql(rest_client, GQL_SYSTEM_HISTORY)
    assert len(data["data"]["systemHistory"]) == 5


@pytest.mark.asyncio
async def test_system_snapshot(rest_client, db_conn, sample_system_reading):
    for _ in range(3):
        await queries.insert_and_prune_system(db_conn, sample_system_reading)
    data = await _gql(rest_client, GQL_SYSTEM_SNAPSHOT)
    snap = data["data"]["systemSnapshot"]
    assert snap["current"] is not None
    assert len(snap["history"]) == 3


@pytest.mark.asyncio
async def test_spark_all_current_empty(rest_client):
    data = await _gql(rest_client, GQL_SPARK_ALL)
    assert data["data"]["sparkAllCurrent"] == []


@pytest.mark.asyncio
async def test_spark_all_current_returns_data(rest_client, db_conn):
    for sid in range(1, 6):
        r = SparkReading(
            server_id=sid,
            spark_gpu_temp_celsius=65.0 + sid,
            spark_memory_temp_celsius=70.0,
            spark_throttle_thermal=False,
            spark_throttle_power=False,
            power_near_ttp=False,
            spark_sm_clock_mhz=1600.0,
        )
        await queries.insert_and_prune_spark(db_conn, r)

    data = await _gql(rest_client, GQL_SPARK_ALL)
    result = data["data"]["sparkAllCurrent"]
    assert len(result) == 5
    server_ids = {r["serverId"] for r in result}
    assert server_ids == {1, 2, 3, 4, 5}


@pytest.mark.asyncio
async def test_spark_current_null_when_empty(rest_client):
    data = await _gql(rest_client, GQL_SPARK_CURRENT)
    assert data["data"]["sparkCurrent"] is None


@pytest.mark.asyncio
async def test_spark_history(rest_client, db_conn, sample_spark_reading):
    for _ in range(5):
        await queries.insert_and_prune_spark(db_conn, sample_spark_reading)
    data = await _gql(rest_client, GQL_SPARK_HISTORY)
    assert len(data["data"]["sparkHistory"]) == 3


@pytest.mark.asyncio
async def test_spark_snapshot(rest_client, db_conn, sample_spark_reading):
    for _ in range(3):
        await queries.insert_and_prune_spark(db_conn, sample_spark_reading)
    data = await _gql(rest_client, GQL_SPARK_SNAPSHOT)
    snap = data["data"]["sparkSnapshot"]
    assert snap["serverId"] == 1
    assert snap["current"] is not None
    assert len(snap["history"]) == 3
