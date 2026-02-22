"""
Bounded random-walk mock collector.

Each sensor value performs a Gaussian random walk on every call, clamped
to a realistic operating range.  Thermal-throttle / TTP flags are derived
from temperature thresholds.  A probabilistic "ramp episode" can push GPU
temperatures toward 90 °C for 6-20 cycles before recovering.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from pia_server.models.spark import SparkReading
from pia_server.models.system import SystemReading


def _walk(current: float, sigma: float, lo: float, hi: float) -> float:
    """Return `current` perturbed by N(0, sigma), clamped to [lo, hi]."""
    return max(lo, min(hi, current + random.gauss(0, sigma)))


@dataclass
class _SparkState:
    server_id: int
    gpu_temp: float = 65.0
    mem_temp: float = 70.0
    sm_clock: float = 1600.0
    # Ramp episode state
    ramp_cycles_remaining: int = 0
    ramp_target: float = 90.0

    def step(self) -> SparkReading:
        # Possibly start a ramp episode (1 % chance per cycle)
        if self.ramp_cycles_remaining == 0 and random.random() < 0.01:
            self.ramp_cycles_remaining = random.randint(6, 20)
            self.ramp_target = 88.0 + random.uniform(0, 2)

        if self.ramp_cycles_remaining > 0:
            # Push GPU temp toward ramp_target
            self.gpu_temp = _walk(self.gpu_temp, 1.5, 55.0, self.ramp_target)
            self.ramp_cycles_remaining -= 1
        else:
            self.gpu_temp = _walk(self.gpu_temp, 0.8, 55.0, 85.0)

        self.mem_temp = _walk(self.mem_temp, 0.7, 60.0, 90.0)
        self.sm_clock = _walk(self.sm_clock, 10.0, 1200.0, 1980.0)

        throttle_thermal = self.gpu_temp > 83.0
        power_near = self.gpu_temp > 80.0

        return SparkReading(
            server_id=self.server_id,
            spark_gpu_temp_celsius=round(self.gpu_temp, 2),
            spark_memory_temp_celsius=round(self.mem_temp, 2),
            spark_throttle_thermal=throttle_thermal,
            spark_throttle_power=False,  # power throttle not simulated
            power_near_ttp=power_near,
            spark_sm_clock_mhz=round(self.sm_clock, 1),
        )


@dataclass
class _SystemState:
    inlet: float = 70.0
    exhaust: float = 95.0
    case: float = 80.0
    airflow: float = 215.0

    def step(self) -> SystemReading:
        self.inlet = _walk(self.inlet, 0.3, 65.0, 75.0)
        self.exhaust = _walk(self.exhaust, 0.5, 85.0, 105.0)
        self.case = _walk(self.case, 0.4, 72.0, 88.0)
        self.airflow = _walk(self.airflow, 2.0, 180.0, 250.0)
        return SystemReading(
            air_inlet_temp=round(self.inlet, 2),
            air_exhaust_temp=round(self.exhaust, 2),
            case_temp=round(self.case, 2),
            exhaust_airflow=round(self.airflow, 2),
        )


class MockCollector:
    """Simulated collector — no real hardware required."""

    def __init__(self) -> None:
        self._system = _SystemState()
        self._sparks: dict[int, _SparkState] = {
            sid: _SparkState(server_id=sid) for sid in range(1, 6)
        }

    async def startup(self) -> None:
        pass  # nothing to initialise

    async def shutdown(self) -> None:
        pass  # nothing to teardown

    async def collect_system(self) -> SystemReading:
        return self._system.step()

    async def collect_spark(self, server_id: int) -> SparkReading:
        if server_id not in self._sparks:
            raise ValueError(f"Invalid server_id {server_id!r}; must be 1-5")
        return self._sparks[server_id].step()
