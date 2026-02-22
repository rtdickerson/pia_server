from __future__ import annotations

from pydantic import BaseModel, Field


class SparkReading(BaseModel):
    """Raw reading from one NVIDIA Spark GPU server."""

    server_id: int = Field(..., ge=1, le=5)
    spark_gpu_temp_celsius: float
    spark_memory_temp_celsius: float
    spark_throttle_thermal: bool
    spark_throttle_power: bool
    power_near_ttp: bool
    spark_sm_clock_mhz: float


class SparkRecord(SparkReading):
    """A persisted Spark reading with DB primary key and timestamp."""

    id: int
    collected_at: str
