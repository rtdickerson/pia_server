import aiosqlite

DDL = """
CREATE TABLE IF NOT EXISTS system_metrics (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    collected_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    air_inlet_temp   REAL NOT NULL,
    air_exhaust_temp REAL NOT NULL,
    case_temp        REAL NOT NULL,
    exhaust_airflow  REAL NOT NULL,
    btu_transfer     REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS spark_metrics (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    collected_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    server_id                 INTEGER NOT NULL CHECK (server_id BETWEEN 1 AND 5),
    spark_gpu_temp_celsius    REAL NOT NULL,
    spark_memory_temp_celsius REAL NOT NULL,
    spark_throttle_thermal    INTEGER NOT NULL CHECK (spark_throttle_thermal IN (0,1)),
    spark_throttle_power      INTEGER NOT NULL CHECK (spark_throttle_power   IN (0,1)),
    power_near_ttp            INTEGER NOT NULL CHECK (power_near_ttp         IN (0,1)),
    spark_sm_clock_mhz        REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_system_id ON system_metrics (id DESC);
CREATE INDEX IF NOT EXISTS idx_spark_sid ON spark_metrics (server_id, id DESC);
"""


async def init_db(conn: aiosqlite.Connection) -> None:
    """Execute DDL statements to initialise the database schema."""
    await conn.executescript(DDL)
    await conn.commit()
