"""Tests for the REST API endpoints."""
from __future__ import annotations

import pytest

from pia_server.db import queries


@pytest.mark.asyncio
async def test_health(rest_client):
    response = await rest_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_system_current_404_when_empty(rest_client):
    response = await rest_client.get("/system/current")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_system_current_returns_data(rest_client, db_conn, sample_system_reading):
    await queries.insert_and_prune_system(db_conn, sample_system_reading)
    response = await rest_client.get("/system/current")
    assert response.status_code == 200
    data = response.json()
    assert data["air_inlet_temp"] == sample_system_reading.air_inlet_temp
    assert "btu_transfer" in data
    assert data["btu_transfer"] > 0


@pytest.mark.asyncio
async def test_system_history_empty(rest_client):
    response = await rest_client.get("/system/history")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_system_history_returns_records(rest_client, db_conn, sample_system_reading):
    for _ in range(5):
        await queries.insert_and_prune_system(db_conn, sample_system_reading)
    response = await rest_client.get("/system/history")
    assert response.status_code == 200
    assert len(response.json()) == 5


@pytest.mark.asyncio
async def test_system_history_n(rest_client, db_conn, sample_system_reading):
    for _ in range(10):
        await queries.insert_and_prune_system(db_conn, sample_system_reading)
    response = await rest_client.get("/system/history/3")
    assert response.status_code == 200
    assert len(response.json()) == 3


@pytest.mark.asyncio
async def test_system_history_n_invalid(rest_client):
    response = await rest_client.get("/system/history/0")
    assert response.status_code == 422

    response = await rest_client.get("/system/history/21")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_spark_current_all_empty(rest_client):
    response = await rest_client.get("/spark/current")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_spark_current_all_returns_data(rest_client, db_conn, sample_spark_reading):
    for sid in range(1, 6):
        from pia_server.models.spark import SparkReading
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

    response = await rest_client.get("/spark/current")
    assert response.status_code == 200
    assert len(response.json()) == 5


@pytest.mark.asyncio
async def test_spark_server_current_404(rest_client):
    response = await rest_client.get("/spark/1/current")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_spark_server_current_returns_data(rest_client, db_conn, sample_spark_reading):
    await queries.insert_and_prune_spark(db_conn, sample_spark_reading)
    response = await rest_client.get("/spark/1/current")
    assert response.status_code == 200
    data = response.json()
    assert data["server_id"] == 1
    assert data["spark_gpu_temp_celsius"] == sample_spark_reading.spark_gpu_temp_celsius


@pytest.mark.asyncio
async def test_spark_server_id_out_of_range(rest_client):
    response = await rest_client.get("/spark/0/current")
    assert response.status_code == 422

    response = await rest_client.get("/spark/6/current")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_spark_history(rest_client, db_conn, sample_spark_reading):
    for _ in range(5):
        await queries.insert_and_prune_spark(db_conn, sample_spark_reading)
    response = await rest_client.get("/spark/1/history")
    assert response.status_code == 200
    assert len(response.json()) == 5


@pytest.mark.asyncio
async def test_spark_history_n(rest_client, db_conn, sample_spark_reading):
    for _ in range(10):
        await queries.insert_and_prune_spark(db_conn, sample_spark_reading)
    response = await rest_client.get("/spark/1/history/4")
    assert response.status_code == 200
    assert len(response.json()) == 4
