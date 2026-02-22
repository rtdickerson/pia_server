"""Tests for the mock (and protocol conformance of the real) collector."""
import pytest

from pia_server.collectors.base import MetricsCollector
from pia_server.collectors.mock import MockCollector
from pia_server.models.system import SystemReading
from pia_server.models.spark import SparkReading


@pytest.mark.asyncio
async def test_mock_collector_protocol():
    collector = MockCollector()
    assert isinstance(collector, MetricsCollector)


@pytest.mark.asyncio
async def test_mock_collect_system_returns_valid_reading():
    collector = MockCollector()
    await collector.startup()
    reading = await collector.collect_system()
    assert isinstance(reading, SystemReading)
    assert 65.0 <= reading.air_inlet_temp <= 75.0
    assert 85.0 <= reading.air_exhaust_temp <= 105.0
    assert 72.0 <= reading.case_temp <= 88.0
    assert 180.0 <= reading.exhaust_airflow <= 250.0
    # BTU must be positive (exhaust > inlet)
    assert reading.btu_transfer > 0


@pytest.mark.asyncio
async def test_mock_collect_system_btu_formula():
    collector = MockCollector()
    reading = await collector.collect_system()
    expected = 1.08 * reading.exhaust_airflow * (
        reading.air_exhaust_temp - reading.air_inlet_temp
    )
    assert reading.btu_transfer == pytest.approx(expected, rel=1e-6)


@pytest.mark.asyncio
async def test_mock_collect_spark_returns_valid_reading():
    collector = MockCollector()
    for sid in range(1, 6):
        reading = await collector.collect_spark(sid)
        assert isinstance(reading, SparkReading)
        assert reading.server_id == sid
        assert 55.0 <= reading.spark_gpu_temp_celsius <= 90.0
        assert 60.0 <= reading.spark_memory_temp_celsius <= 90.0
        assert 1200.0 <= reading.spark_sm_clock_mhz <= 1980.0


@pytest.mark.asyncio
async def test_mock_collect_spark_invalid_server_id():
    collector = MockCollector()
    with pytest.raises(ValueError):
        await collector.collect_spark(0)


@pytest.mark.asyncio
async def test_mock_throttle_flags_at_high_temp():
    """Force GPU temp above threshold and verify throttle flags."""
    collector = MockCollector()
    state = collector._sparks[1]
    state.gpu_temp = 84.0  # above 83 °C threshold
    reading = state.step()
    assert reading.spark_throttle_thermal is True
    assert reading.power_near_ttp is True


@pytest.mark.asyncio
async def test_mock_startup_shutdown():
    collector = MockCollector()
    await collector.startup()   # should not raise
    await collector.shutdown()  # should not raise


@pytest.mark.asyncio
async def test_mock_produces_varied_readings():
    """Verify the random walk produces different values across cycles."""
    collector = MockCollector()
    readings = [await collector.collect_system() for _ in range(10)]
    temps = [r.air_inlet_temp for r in readings]
    # Not all the same
    assert len(set(temps)) > 1
