# PIA Metrics Server

A Python metrics server that collects **system thermal readings** and **NVIDIA Spark GPU metrics**, persists them in SQLite, and exposes them over three interfaces simultaneously:

- **REST API** — FastAPI, port 8000
- **GraphQL** — Strawberry, mounted at `/graphql` on port 8000
- **MCP** — fastmcp HTTP/SSE, port 8001 (for AI assistant integration)

Data is collected every 5 seconds (configurable) and a rolling window of 21 readings per entity is retained. A mock collector with realistic bounded random-walk simulation runs out of the box — no hardware required to get started.

---

## Quick Start

```bash
git clone https://github.com/rtdickerson/pia_server.git
cd pia_server

python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .

python -m pia_server.main
```

Both servers start immediately:

```
Collection loop started (interval=5.0s, collector=mock)
Uvicorn running on http://0.0.0.0:8000   ← REST + GraphQL
Uvicorn running on http://0.0.0.0:8001   ← MCP
```

> See [setup.md](setup.md) for the full Raspberry Pi installation guide.

---

## Configuration

Copy `.env.example` to `.env` and edit as needed. All settings have defaults and can also be overridden via environment variables.

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `pia_metrics.db` | SQLite database file path |
| `REST_PORT` | `8000` | Port for the REST + GraphQL server |
| `MCP_PORT` | `8001` | Port for the MCP server |
| `COLLECTION_INTERVAL_SECONDS` | `5.0` | How often metrics are collected |
| `COLLECTOR_TYPE` | `mock` | `mock` (simulated) or `real` (NVML + sensors) |
| `TEMP_UNIT` | `F` | Display unit: `F` or `C` |
| `LOG_LEVEL` | `INFO` | Python logging level |

---

## Data Model

### System Thermals

Collected once per cycle from the chassis sensors.

| Field | Type | Description |
|---|---|---|
| `id` | int | Auto-increment primary key |
| `collected_at` | string | ISO-8601 UTC timestamp |
| `air_inlet_temp` | float | Air inlet temperature (°F) |
| `air_exhaust_temp` | float | Air exhaust temperature (°F) |
| `case_temp` | float | Case ambient temperature (°F) |
| `exhaust_airflow` | float | Exhaust airflow in CFM |
| `btu_transfer` | float | Heat transfer — computed automatically |

**BTU formula:** `1.08 × exhaust_airflow × (air_exhaust_temp − air_inlet_temp)`

### Spark GPU Metrics

Collected once per cycle per server (5 servers, IDs 1–5).

| Field | Type | Description |
|---|---|---|
| `id` | int | Auto-increment primary key |
| `collected_at` | string | ISO-8601 UTC timestamp |
| `server_id` | int | Spark server number (1–5) |
| `spark_gpu_temp_celsius` | float | GPU die temperature (°C) |
| `spark_memory_temp_celsius` | float | GPU memory temperature (°C) |
| `spark_throttle_thermal` | bool | `true` when GPU temp > 83 °C |
| `spark_throttle_power` | bool | `true` when power throttling is active |
| `power_near_ttp` | bool | `true` when approaching TTP power limit |
| `spark_sm_clock_mhz` | float | SM (shader) clock speed in MHz |

### Retention

The database keeps a maximum of **21 rows per entity** (1 current + 20 history). Older rows are pruned automatically after every insert.

---

## REST API (port 8000)

Interactive docs available at **`http://localhost:8000/docs`** when the server is running.

### System Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/system/current` | Latest system reading, or 404 if no data yet |
| `GET` | `/system/history` | Up to 20 prior readings (newest first) |
| `GET` | `/system/history/{n}` | Last N readings, where N is 1–20 |

### Spark Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/spark/current` | Current reading for all 5 servers |
| `GET` | `/spark/{server_id}/current` | Latest for one server (server_id 1–5) |
| `GET` | `/spark/{server_id}/history` | Up to 20 prior readings for one server |
| `GET` | `/spark/{server_id}/history/{n}` | Last N readings for one server |

### Meta

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Returns `{"status": "ok"}` |

### Examples

```bash
curl http://localhost:8000/health

curl http://localhost:8000/system/current

curl http://localhost:8000/system/history/5

curl http://localhost:8000/spark/current

curl http://localhost:8000/spark/3/current

curl http://localhost:8000/spark/2/history/10
```

---

## GraphQL API (port 8000, path `/graphql`)

The GraphQL explorer (GraphiQL) is available at **`http://localhost:8000/graphql`** in a browser.

Field names are automatically camelCased in GraphQL (e.g. `air_inlet_temp` → `airInletTemp`).

### Queries

| Query | Arguments | Returns |
|---|---|---|
| `systemCurrent` | — | `SystemMetric` or `null` |
| `systemHistory` | `limit: Int = 20` | `[SystemMetric]` |
| `systemSnapshot` | — | `SystemSnapshot` (current + history in one call) |
| `sparkCurrent` | `serverId: Int!` | `SparkMetric` or `null` |
| `sparkHistory` | `serverId: Int!`, `limit: Int = 20` | `[SparkMetric]` |
| `sparkAllCurrent` | — | `[SparkMetric]` |
| `sparkSnapshot` | `serverId: Int!` | `SparkServerSnapshot` (current + history) |

### Examples

```bash
# Current system reading
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ systemCurrent { airInletTemp airExhaustTemp btuTransfer } }"}'

# All 5 Spark servers in one call
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ sparkAllCurrent { serverId sparkGpuTempCelsius sparkThrottleThermal powerNearTtp } }"}'

# Full snapshot — current + 20-reading history — for server 4
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ sparkSnapshot(serverId: 4) { serverId current { sparkGpuTempCelsius sparkSmClockMhz } history { collectedAt sparkGpuTempCelsius } } }"}'

# System snapshot (current + history in one round trip)
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ systemSnapshot { current { btuTransfer } history { collectedAt btuTransfer } } }"}'
```

---

## MCP (Model Context Protocol) — port 8001

The MCP server uses HTTP/SSE transport and is designed for integration with
AI assistants (Claude, etc.). Connect via the SSE endpoint:

```
http://localhost:8001/sse
```

### Tools

| Tool | Arguments | Description |
|---|---|---|
| `get_system_current` | — | Latest system thermal reading |
| `get_system_history` | `limit=20` | Historical system readings |
| `get_spark_current` | `server_id` | Latest reading for one Spark server |
| `get_spark_history` | `server_id`, `limit=20` | Historical readings for one server |
| `get_all_spark_current` | — | Current reading for all 5 servers |
| `get_btu_summary` | — | Current BTU + 20-reading rolling average |
| `get_thermal_alert_status` | — | Servers where any throttle/TTP flag is active |

`get_thermal_alert_status` returns an empty list when all servers are nominal, making it ideal for polling-style health checks from an AI assistant.

### Resources

| URI | Description |
|---|---|
| `pia://system/current` | Current system reading (JSON) |
| `pia://system/history` | Last 20 system readings (JSON) |
| `pia://spark/{server_id}/current` | Current reading for one server |
| `pia://spark/{server_id}/history` | Last 20 readings for one server |
| `pia://spark/all/current` | Current readings for all 5 servers |
| `pia://config` | Server configuration (ports, interval, collector type) |

### Connecting Claude Desktop

Add this to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "pia-metrics": {
      "url": "http://localhost:8001/sse"
    }
  }
}
```

---

## Mock Collector

The default `mock` collector simulates realistic hardware behaviour — no
physical devices needed.

Each sensor value performs a **Gaussian random walk** every collection cycle,
clamped to an operating range:

| Sensor | Range | Walk σ per cycle |
|---|---|---|
| Air inlet temp | 65–75 °F | ±0.3 |
| Air exhaust temp | 85–105 °F | ±0.5 |
| Case temp | 72–88 °F | ±0.4 |
| Exhaust airflow | 180–250 CFM | ±2.0 |
| GPU temp | 55–85 °C | ±0.8 |
| Memory temp | 60–90 °C | ±0.7 |
| SM clock | 1200–1980 MHz | ±10.0 |

**Thermal throttle flags** are derived automatically:
- `spark_throttle_thermal = True` when GPU temp > 83 °C
- `power_near_ttp = True` when GPU temp > 80 °C

**Ramp episodes** — each server has a 1% chance per cycle of entering a ramp
episode lasting 6–20 cycles, pushing GPU temperature toward ~90 °C before
recovering. This exercises throttle detection without requiring real hardware.

---

## Real Collector

Set `COLLECTOR_TYPE=real` in `.env` to enable the hardware-backed collector.
The stubs are in `pia_server/collectors/real.py` and raise `NotImplementedError`
until implemented.

**System thermals** — implement `collect_system()` using IPMI or platform-specific
sensor APIs (e.g. `ipmitool`, `python-ipmi`, Dell iDRAC, HP iLO).

**Spark GPU metrics** — implement `collect_spark()` using `nvidia-ml-py`
(`pynvml`). Install with:

```bash
pip install -e ".[real]"
```

`libnvidia-ml.so` must be present on the host (provided by the NVIDIA driver).
See [setup.md](setup.md) for options when running on a Raspberry Pi.

---

## Project Structure

```
pia_server/
├── pyproject.toml
├── .env.example
├── setup.md                  ← Raspberry Pi installation guide
├── pia_server/
│   ├── main.py               # Entry point — starts both servers
│   ├── config.py             # pydantic-settings (reads .env)
│   ├── db/
│   │   ├── database.py       # aiosqlite connection context manager
│   │   ├── schema.py         # DDL + init_db()
│   │   └── queries.py        # All SQL (insert, select, prune)
│   ├── models/
│   │   ├── system.py         # SystemReading (BTU validator), SystemRecord
│   │   └── spark.py          # SparkReading, SparkRecord
│   ├── collectors/
│   │   ├── base.py           # MetricsCollector Protocol
│   │   ├── mock.py           # Bounded random-walk simulator
│   │   └── real.py           # NotImplementedError stubs
│   ├── api/
│   │   ├── app.py            # FastAPI factory + lifespan
│   │   └── routes/
│   │       ├── system.py     # REST system endpoints
│   │       └── spark.py      # REST Spark endpoints
│   ├── graphql/
│   │   ├── types.py          # Strawberry type definitions
│   │   └── schema.py         # Query resolvers + GraphQLRouter
│   └── mcp_server/
│       └── server.py         # FastMCP tools + resources
└── tests/                    # 46 tests (pytest-asyncio)
```

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v --tb=short
```

All 46 tests use an in-memory SQLite database and do not require the server
to be running.

---

## Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | REST API framework |
| `uvicorn[standard]` | ASGI server (includes uvloop, websockets) |
| `strawberry-graphql[fastapi]` | GraphQL schema + FastAPI router |
| `fastmcp` | MCP server (HTTP/SSE transport) |
| `aiosqlite` | Async SQLite driver |
| `pydantic` | Data validation and serialisation |
| `pydantic-settings` | `.env` / environment variable config |
| `nvidia-ml-py` *(optional)* | NVML bindings for real GPU collector |
