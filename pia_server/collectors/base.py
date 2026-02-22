from typing import Protocol, runtime_checkable

from pia_server.models.spark import SparkReading
from pia_server.models.system import SystemReading


@runtime_checkable
class MetricsCollector(Protocol):
    """Protocol every collector must satisfy."""

    async def collect_system(self) -> SystemReading: ...

    async def collect_spark(self, server_id: int) -> SparkReading: ...

    async def startup(self) -> None: ...

    async def shutdown(self) -> None: ...
