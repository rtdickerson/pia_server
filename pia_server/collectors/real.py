"""
Real hardware collector — stubs for NVML / platform sensor integration.

Install the 'real' extra for NVML support:
    uv sync --extra real

Replace each NotImplementedError body with actual sensor/NVML calls.
"""
from __future__ import annotations

from pia_server.models.spark import SparkReading
from pia_server.models.system import SystemReading


class RealCollector:
    """Collector backed by real hardware sensors and NVIDIA NVML."""

    async def startup(self) -> None:
        """Initialise NVML and any hardware sensor libraries."""
        # TODO: pynvml.nvmlInit()
        raise NotImplementedError("RealCollector.startup() is not yet implemented")

    async def shutdown(self) -> None:
        """Cleanly shut down NVML and release handles."""
        # TODO: pynvml.nvmlShutdown()
        raise NotImplementedError("RealCollector.shutdown() is not yet implemented")

    async def collect_system(self) -> SystemReading:
        """
        Read system thermal sensors.

        Suggested implementation:
          - air_inlet_temp  : IPMI sensor or platform-specific fan inlet sensor
          - air_exhaust_temp: IPMI sensor or platform-specific exhaust sensor
          - case_temp       : motherboard case-ambient sensor
          - exhaust_airflow : CFM from fan-controller (e.g. Dell iDRAC, HP iLO)
        """
        raise NotImplementedError("RealCollector.collect_system() is not yet implemented")

    async def collect_spark(self, server_id: int) -> SparkReading:
        """
        Read NVIDIA Spark GPU metrics via NVML.

        Suggested implementation:
          - Obtain handle: pynvml.nvmlDeviceGetHandleByIndex(server_id - 1)
          - spark_gpu_temp_celsius   : nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
          - spark_memory_temp_celsius: nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_MEMORY)
          - spark_throttle_thermal   : check NVML throttle reasons bitmask
          - spark_throttle_power     : check NVML throttle reasons bitmask
          - power_near_ttp           : compare power draw vs TTP limit
          - spark_sm_clock_mhz       : nvmlDeviceGetClockInfo(handle, NVML_CLOCK_SM)
        """
        raise NotImplementedError(
            f"RealCollector.collect_spark(server_id={server_id}) is not yet implemented"
        )
