from fastapi import APIRouter, HTTPException, Path

from pia_server.db.database import get_db_connection
from pia_server.db import queries
from pia_server.models.spark import SparkRecord

router = APIRouter(prefix="/spark", tags=["spark"])


@router.get("/current", response_model=list[SparkRecord])
async def get_all_spark_current():
    """Return the most recent reading for all 5 Spark servers."""
    async with get_db_connection() as conn:
        return await queries.get_all_spark_current(conn)


@router.get("/{server_id}/current", response_model=SparkRecord)
async def get_spark_current(
    server_id: int = Path(..., ge=1, le=5, description="Spark server ID (1-5)"),
):
    """Return the most recent reading for a single Spark server."""
    async with get_db_connection() as conn:
        record = await queries.get_spark_current(conn, server_id)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"No data available for Spark server {server_id}"
        )
    return record


@router.get("/{server_id}/history", response_model=list[SparkRecord])
async def get_spark_history(
    server_id: int = Path(..., ge=1, le=5, description="Spark server ID (1-5)"),
):
    """Return up to 20 prior readings for one Spark server."""
    async with get_db_connection() as conn:
        return await queries.get_spark_history(conn, server_id, limit=20)


@router.get("/{server_id}/history/{n}", response_model=list[SparkRecord])
async def get_spark_history_n(
    server_id: int = Path(..., ge=1, le=5, description="Spark server ID (1-5)"),
    n: int = Path(..., ge=1, le=20, description="Number of historical readings to return"),
):
    """Return the last N readings for one Spark server (1–20)."""
    async with get_db_connection() as conn:
        return await queries.get_spark_history(conn, server_id, limit=n)
