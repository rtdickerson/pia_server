"""Shared pytest fixtures."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import patch

import aiosqlite
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from pia_server.db.schema import init_db
from pia_server.models.system import SystemReading
from pia_server.models.spark import SparkReading


# ---------------------------------------------------------------------------
# In-memory SQLite database
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_conn() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Yield a fresh in-memory aiosqlite connection with schema applied."""
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await init_db(conn)
        yield conn


# ---------------------------------------------------------------------------
# FastAPI test client backed by in-memory DB
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def rest_client(db_conn: aiosqlite.Connection) -> AsyncGenerator[AsyncClient, None]:
    """
    FastAPI test client with the collection loop disabled and
    DB operations redirected to the in-memory connection.
    """
    from pia_server.api.app import create_app
    from pia_server import db

    # Patch get_db_connection to return our in-memory conn
    @asynccontextmanager
    async def _fake_db():
        yield db_conn

    with patch("pia_server.api.routes.system.get_db_connection", _fake_db), \
         patch("pia_server.api.routes.spark.get_db_connection", _fake_db), \
         patch("pia_server.graphql.schema.get_db_connection", _fake_db), \
         patch("pia_server.api.app.get_db_connection", _fake_db), \
         patch("pia_server.api.app.collection_loop", return_value=None):

        app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client


# ---------------------------------------------------------------------------
# Sample readings
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_system_reading() -> SystemReading:
    return SystemReading(
        air_inlet_temp=70.0,
        air_exhaust_temp=95.0,
        case_temp=80.0,
        exhaust_airflow=215.0,
    )


@pytest.fixture
def sample_spark_reading() -> SparkReading:
    return SparkReading(
        server_id=1,
        spark_gpu_temp_celsius=65.0,
        spark_memory_temp_celsius=70.0,
        spark_throttle_thermal=False,
        spark_throttle_power=False,
        power_near_ttp=False,
        spark_sm_clock_mhz=1600.0,
    )
