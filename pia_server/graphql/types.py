"""Strawberry GraphQL type definitions."""
import strawberry


@strawberry.type
class SystemMetric:
    id: int
    collected_at: str
    air_inlet_temp: float
    air_exhaust_temp: float
    case_temp: float
    exhaust_airflow: float
    btu_transfer: float


@strawberry.type
class SystemSnapshot:
    current: SystemMetric | None
    history: list[SystemMetric]


@strawberry.type
class SparkMetric:
    id: int
    collected_at: str
    server_id: int
    spark_gpu_temp_celsius: float
    spark_memory_temp_celsius: float
    spark_throttle_thermal: bool
    spark_throttle_power: bool
    power_near_ttp: bool
    spark_sm_clock_mhz: float


@strawberry.type
class SparkServerSnapshot:
    server_id: int
    current: SparkMetric | None
    history: list[SparkMetric]
