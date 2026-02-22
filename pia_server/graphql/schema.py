"""Strawberry schema with all Query resolvers, mounted as a FastAPI router."""
from __future__ import annotations

from typing import Optional

import strawberry
from strawberry.fastapi import GraphQLRouter

from pia_server.db.database import get_db_connection
from pia_server.db import queries
from pia_server.graphql.types import (
    SparkMetric,
    SparkServerSnapshot,
    SystemMetric,
    SystemSnapshot,
)
from pia_server.models.spark import SparkRecord
from pia_server.models.system import SystemRecord


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def _system_record_to_type(r: SystemRecord) -> SystemMetric:
    return SystemMetric(
        id=r.id,
        collected_at=r.collected_at,
        air_inlet_temp=r.air_inlet_temp,
        air_exhaust_temp=r.air_exhaust_temp,
        case_temp=r.case_temp,
        exhaust_airflow=r.exhaust_airflow,
        btu_transfer=r.btu_transfer,
    )


def _spark_record_to_type(r: SparkRecord) -> SparkMetric:
    return SparkMetric(
        id=r.id,
        collected_at=r.collected_at,
        server_id=r.server_id,
        spark_gpu_temp_celsius=r.spark_gpu_temp_celsius,
        spark_memory_temp_celsius=r.spark_memory_temp_celsius,
        spark_throttle_thermal=r.spark_throttle_thermal,
        spark_throttle_power=r.spark_throttle_power,
        power_near_ttp=r.power_near_ttp,
        spark_sm_clock_mhz=r.spark_sm_clock_mhz,
    )


# ---------------------------------------------------------------------------
# Query resolvers
# ---------------------------------------------------------------------------

@strawberry.type
class Query:
    @strawberry.field
    async def system_current(self) -> Optional[SystemMetric]:
        async with get_db_connection() as conn:
            record = await queries.get_system_current(conn)
        return _system_record_to_type(record) if record else None

    @strawberry.field
    async def system_history(self, limit: int = 20) -> list[SystemMetric]:
        async with get_db_connection() as conn:
            records = await queries.get_system_history(conn, limit=limit)
        return [_system_record_to_type(r) for r in records]

    @strawberry.field
    async def system_snapshot(self) -> SystemSnapshot:
        async with get_db_connection() as conn:
            current = await queries.get_system_current(conn)
            history = await queries.get_system_history(conn, limit=20)
        return SystemSnapshot(
            current=_system_record_to_type(current) if current else None,
            history=[_system_record_to_type(r) for r in history],
        )

    @strawberry.field
    async def spark_current(self, server_id: int) -> Optional[SparkMetric]:
        async with get_db_connection() as conn:
            record = await queries.get_spark_current(conn, server_id)
        return _spark_record_to_type(record) if record else None

    @strawberry.field
    async def spark_history(self, server_id: int, limit: int = 20) -> list[SparkMetric]:
        async with get_db_connection() as conn:
            records = await queries.get_spark_history(conn, server_id, limit=limit)
        return [_spark_record_to_type(r) for r in records]

    @strawberry.field
    async def spark_all_current(self) -> list[SparkMetric]:
        async with get_db_connection() as conn:
            records = await queries.get_all_spark_current(conn)
        return [_spark_record_to_type(r) for r in records]

    @strawberry.field
    async def spark_snapshot(self, server_id: int) -> SparkServerSnapshot:
        async with get_db_connection() as conn:
            current = await queries.get_spark_current(conn, server_id)
            history = await queries.get_spark_history(conn, server_id, limit=20)
        return SparkServerSnapshot(
            server_id=server_id,
            current=_spark_record_to_type(current) if current else None,
            history=[_spark_record_to_type(r) for r in history],
        )


schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)
