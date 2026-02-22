"""Tests for the database layer (schema, queries)."""
import pytest
import pytest_asyncio

from pia_server.db import queries
from pia_server.models.system import SystemReading
from pia_server.models.spark import SparkReading


@pytest.mark.asyncio
async def test_system_insert_and_current(db_conn, sample_system_reading):
    await queries.insert_and_prune_system(db_conn, sample_system_reading)
    record = await queries.get_system_current(db_conn)
    assert record is not None
    assert record.air_inlet_temp == sample_system_reading.air_inlet_temp
    assert record.btu_transfer == pytest.approx(
        1.08 * sample_system_reading.exhaust_airflow * (
            sample_system_reading.air_exhaust_temp - sample_system_reading.air_inlet_temp
        ),
        rel=1e-4,
    )


@pytest.mark.asyncio
async def test_system_current_empty(db_conn):
    record = await queries.get_system_current(db_conn)
    assert record is None


@pytest.mark.asyncio
async def test_system_history_limit(db_conn):
    for i in range(25):
        reading = SystemReading(
            air_inlet_temp=70.0 + i * 0.01,
            air_exhaust_temp=95.0,
            case_temp=80.0,
            exhaust_airflow=215.0,
        )
        await queries.insert_and_prune_system(db_conn, reading)

    history = await queries.get_system_history(db_conn, limit=20)
    assert len(history) == 20

    # Prune should keep max 21 rows total
    async with db_conn.execute("SELECT COUNT(*) FROM system_metrics") as cur:
        (count,) = await cur.fetchone()
    assert count <= 21


@pytest.mark.asyncio
async def test_spark_insert_and_current(db_conn, sample_spark_reading):
    await queries.insert_and_prune_spark(db_conn, sample_spark_reading)
    record = await queries.get_spark_current(db_conn, server_id=1)
    assert record is not None
    assert record.server_id == 1
    assert record.spark_gpu_temp_celsius == sample_spark_reading.spark_gpu_temp_celsius


@pytest.mark.asyncio
async def test_spark_current_empty(db_conn):
    record = await queries.get_spark_current(db_conn, server_id=3)
    assert record is None


@pytest.mark.asyncio
async def test_spark_history_prune(db_conn):
    for i in range(25):
        reading = SparkReading(
            server_id=2,
            spark_gpu_temp_celsius=65.0 + i * 0.1,
            spark_memory_temp_celsius=70.0,
            spark_throttle_thermal=False,
            spark_throttle_power=False,
            power_near_ttp=False,
            spark_sm_clock_mhz=1600.0,
        )
        await queries.insert_and_prune_spark(db_conn, reading)

    history = await queries.get_spark_history(db_conn, server_id=2, limit=20)
    assert len(history) == 20

    async with db_conn.execute(
        "SELECT COUNT(*) FROM spark_metrics WHERE server_id = 2"
    ) as cur:
        (count,) = await cur.fetchone()
    assert count <= 21


@pytest.mark.asyncio
async def test_get_all_spark_current(db_conn):
    for sid in range(1, 6):
        reading = SparkReading(
            server_id=sid,
            spark_gpu_temp_celsius=60.0 + sid,
            spark_memory_temp_celsius=70.0,
            spark_throttle_thermal=False,
            spark_throttle_power=False,
            power_near_ttp=False,
            spark_sm_clock_mhz=1600.0,
        )
        await queries.insert_and_prune_spark(db_conn, reading)

    all_current = await queries.get_all_spark_current(db_conn)
    assert len(all_current) == 5
    server_ids = {r.server_id for r in all_current}
    assert server_ids == {1, 2, 3, 4, 5}
