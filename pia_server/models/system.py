from __future__ import annotations

from pydantic import BaseModel, model_validator


class SystemReading(BaseModel):
    """Raw reading from the system thermal collector."""

    air_inlet_temp: float
    air_exhaust_temp: float
    case_temp: float
    exhaust_airflow: float  # CFM
    btu_transfer: float = 0.0  # pre-computed; populated by validator

    @model_validator(mode="after")
    def compute_btu(self) -> "SystemReading":
        self.btu_transfer = 1.08 * self.exhaust_airflow * (
            self.air_exhaust_temp - self.air_inlet_temp
        )
        return self


class SystemRecord(SystemReading):
    """A persisted system reading with DB primary key and timestamp."""

    id: int
    collected_at: str
