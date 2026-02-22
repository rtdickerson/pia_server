"""All SQL operations: insert, select current/history, prune."""
from __future__ import annotations

from typing import Any

import aiosqlite

from pia_server.models.spark import SparkReading, SparkRecord
from pia_server.models.system import SystemReading, SystemRecord

# ---------------------------------------------------------------------------
# System metrics
# ---------------------------------------------------------------------------

_INSERT_SYSTEM = """
INSERT INTO system_metrics
    (air_inlet_temp, air_exhaust_temp, case_temp, exhaust_airflow, btu_transfer)
VALUES
    (:air_inlet_temp, :air_exhaust_temp, :case_temp, :exhaust_airflow, :btu_transfer)
"""

_PRUNE_SYSTEM = """
DELETE FROM system_metrics
WHERE id NOT IN (
    SELECT id FROM system_metrics ORDER BY id DESC LIMIT 21
)
"""

_SELECT_SYSTEM_CURRENT = """
SELECT * FROM system_metrics ORDER BY id DESC LIMIT 1
"""

_SELECT_SYSTEM_HISTORY = """
SELECT * FROM system_metrics ORDER BY id DESC LIMIT :limit
"""


def _row_to_system_record(row: aiosqlite.Row) -> SystemRecord:
    return SystemRecord(
        id=row["id"],
        collected_at=row["collected_at"],
        air_inlet_temp=row["air_inlet_temp"],
        air_exhaust_temp=row["air_exhaust_temp"],
        case_temp=row["case_temp"],
        exhaust_airflow=row["exhaust_airflow"],
        btu_transfer=row["btu_transfer"],
    )


async def insert_and_prune_system(conn: aiosqlite.Connection, reading: SystemReading) -> None:
    params: dict[str, Any] = {
        "air_inlet_temp": reading.air_inlet_temp,
        "air_exhaust_temp": reading.air_exhaust_temp,
        "case_temp": reading.case_temp,
        "exhaust_airflow": reading.exhaust_airflow,
        "btu_transfer": reading.btu_transfer,
    }
    await conn.execute(_INSERT_SYSTEM, params)
    await conn.execute(_PRUNE_SYSTEM)
    await conn.commit()


async def get_system_current(conn: aiosqlite.Connection) -> SystemRecord | None:
    async with conn.execute(_SELECT_SYSTEM_CURRENT) as cur:
        row = await cur.fetchone()
    return _row_to_system_record(row) if row else None


async def get_system_history(conn: aiosqlite.Connection, limit: int = 20) -> list[SystemRecord]:
    limit = max(1, min(limit, 20))
    async with conn.execute(_SELECT_SYSTEM_HISTORY, {"limit": limit}) as cur:
        rows = await cur.fetchall()
    return [_row_to_system_record(r) for r in rows]


# ---------------------------------------------------------------------------
# Spark metrics
# ---------------------------------------------------------------------------

_INSERT_SPARK = """
INSERT INTO spark_metrics
    (server_id, spark_gpu_temp_celsius, spark_memory_temp_celsius,
     spark_throttle_thermal, spark_throttle_power, power_near_ttp, spark_sm_clock_mhz)
VALUES
    (:server_id, :spark_gpu_temp_celsius, :spark_memory_temp_celsius,
     :spark_throttle_thermal, :spark_throttle_power, :power_near_ttp, :spark_sm_clock_mhz)
"""

_PRUNE_SPARK = """
DELETE FROM spark_metrics
WHERE server_id = :server_id
  AND id NOT IN (
      SELECT id FROM spark_metrics WHERE server_id = :server_id ORDER BY id DESC LIMIT 21
  )
"""

_SELECT_SPARK_CURRENT = """
SELECT * FROM spark_metrics WHERE server_id = :server_id ORDER BY id DESC LIMIT 1
"""

_SELECT_SPARK_HISTORY = """
SELECT * FROM spark_metrics WHERE server_id = :server_id ORDER BY id DESC LIMIT :limit
"""

_SELECT_SPARK_ALL_CURRENT = """
SELECT s.*
FROM spark_metrics s
INNER JOIN (
    SELECT server_id, MAX(id) AS max_id
    FROM spark_metrics
    GROUP BY server_id
) latest ON s.server_id = latest.server_id AND s.id = latest.max_id
ORDER BY s.server_id
"""


def _row_to_spark_record(row: aiosqlite.Row) -> SparkRecord:
    return SparkRecord(
        id=row["id"],
        collected_at=row["collected_at"],
        server_id=row["server_id"],
        spark_gpu_temp_celsius=row["spark_gpu_temp_celsius"],
        spark_memory_temp_celsius=row["spark_memory_temp_celsius"],
        spark_throttle_thermal=bool(row["spark_throttle_thermal"]),
        spark_throttle_power=bool(row["spark_throttle_power"]),
        power_near_ttp=bool(row["power_near_ttp"]),
        spark_sm_clock_mhz=row["spark_sm_clock_mhz"],
    )


async def insert_and_prune_spark(conn: aiosqlite.Connection, reading: SparkReading) -> None:
    params: dict[str, Any] = {
        "server_id": reading.server_id,
        "spark_gpu_temp_celsius": reading.spark_gpu_temp_celsius,
        "spark_memory_temp_celsius": reading.spark_memory_temp_celsius,
        "spark_throttle_thermal": int(reading.spark_throttle_thermal),
        "spark_throttle_power": int(reading.spark_throttle_power),
        "power_near_ttp": int(reading.power_near_ttp),
        "spark_sm_clock_mhz": reading.spark_sm_clock_mhz,
    }
    await conn.execute(_INSERT_SPARK, params)
    await conn.execute(_PRUNE_SPARK, {"server_id": reading.server_id})
    await conn.commit()


async def get_spark_current(conn: aiosqlite.Connection, server_id: int) -> SparkRecord | None:
    async with conn.execute(_SELECT_SPARK_CURRENT, {"server_id": server_id}) as cur:
        row = await cur.fetchone()
    return _row_to_spark_record(row) if row else None


async def get_spark_history(
    conn: aiosqlite.Connection, server_id: int, limit: int = 20
) -> list[SparkRecord]:
    limit = max(1, min(limit, 20))
    async with conn.execute(
        _SELECT_SPARK_HISTORY, {"server_id": server_id, "limit": limit}
    ) as cur:
        rows = await cur.fetchall()
    return [_row_to_spark_record(r) for r in rows]


async def get_all_spark_current(conn: aiosqlite.Connection) -> list[SparkRecord]:
    async with conn.execute(_SELECT_SPARK_ALL_CURRENT) as cur:
        rows = await cur.fetchall()
    return [_row_to_spark_record(r) for r in rows]
