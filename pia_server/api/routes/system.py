from fastapi import APIRouter, HTTPException, Path

from pia_server.db.database import get_db_connection
from pia_server.db import queries
from pia_server.models.system import SystemRecord

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/current", response_model=SystemRecord)
async def get_system_current():
    """Return the most recent system thermal reading."""
    async with get_db_connection() as conn:
        record = await queries.get_system_current(conn)
    if record is None:
        raise HTTPException(status_code=404, detail="No system data available yet")
    return record


@router.get("/history", response_model=list[SystemRecord])
async def get_system_history():
    """Return up to the 20 most recent prior system readings."""
    async with get_db_connection() as conn:
        return await queries.get_system_history(conn, limit=20)


@router.get("/history/{n}", response_model=list[SystemRecord])
async def get_system_history_n(
    n: int = Path(..., ge=1, le=20, description="Number of historical readings to return"),
):
    """Return the last N system readings (1–20)."""
    async with get_db_connection() as conn:
        return await queries.get_system_history(conn, limit=n)
