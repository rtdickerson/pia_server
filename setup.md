# PIA Server — Raspberry Pi Setup Guide

## Supported Hardware

- Raspberry Pi 4 (2 GB RAM minimum, 4 GB recommended)
- Raspberry Pi 5
- Raspberry Pi OS **Bookworm** (64-bit) — ships with Python 3.11 ✓

> **32-bit OS is not supported.** Several dependencies (pydantic-core, uvloop) ship
> ARM64 wheels only. Use the 64-bit image.

---

## 1. Operating System

Flash **Raspberry Pi OS Bookworm (64-bit)** using Raspberry Pi Imager.
Verify after boot:

```bash
uname -m          # should print aarch64
python3 --version # should print 3.11.x or newer
```

If you are on Bullseye or need a newer Python, install from deadsnakes:

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

---

## 2. System Packages

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
    python3-pip \
    python3-venv \
    git \
    sqlite3 \
    build-essential \
    libssl-dev \
    libffi-dev \
    libsqlite3-dev
```

| Package | Why it's needed |
|---|---|
| `python3-venv` | Virtual environment support |
| `sqlite3` | CLI for inspecting the metrics DB |
| `build-essential` | C toolchain for any packages without ARM64 wheels |
| `libssl-dev` / `libffi-dev` | Required by `cryptography` (fastmcp dependency) |
| `libsqlite3-dev` | Required if Python is compiled from source |

---

## 3. Clone the Repository

```bash
git clone https://github.com/rtdickerson/pia_server.git
cd pia_server
```

---

## 4. Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

---

## 5. Install the Project

**Mock collector only (default):**

```bash
pip install -e .
```

**With dev/test tools:**

```bash
pip install -e ".[dev]"
```

**With real NVML support** (requires network or direct access to NVIDIA Spark servers — see §8):

```bash
pip install -e ".[real]"
```

> `nvidia-ml-py` provides Python bindings for NVML. The NVML library itself
> (`libnvidia-ml.so`) must be accessible — either locally or via a remote
> stub. See §8 for details.

---

## 6. Configuration

Copy the example env file and edit as needed:

```bash
cp .env.example .env
nano .env
```

Key settings for a Pi deployment:

```ini
# Use absolute path so the DB survives working-directory changes
DB_PATH=/home/pi/pia_metrics.db

REST_PORT=8000
MCP_PORT=8001

COLLECTION_INTERVAL_SECONDS=5.0

# Start with mock; switch to real once sensors are wired up
COLLECTOR_TYPE=mock

TEMP_UNIT=F
LOG_LEVEL=INFO
```

---

## 7. Run the Server

```bash
source .venv/bin/activate
python -m pia_server.main
```

Verify both servers are up:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/system/current
```

---

## 8. Real Collector Prerequisites

The `real` collector (`collectors/real.py`) requires two things:

### 8a. System Thermal Sensors (IPMI)

Install `ipmitool` to read chassis inlet/exhaust temperatures and fan data
from an IPMI-capable system on the same network:

```bash
sudo apt install -y ipmitool
```

Test connectivity to the target system:

```bash
ipmitool -I lanplus -H <BMC_IP> -U <USER> -P <PASS> sdr type Temperature
```

You will need to implement the `collect_system()` stub in
`pia_server/collectors/real.py` to parse this output (or use a Python IPMI
library such as `python-ipmi`).

### 8b. NVIDIA NVML (Spark GPU Metrics)

`nvidia-ml-py` wraps NVML calls, which requires `libnvidia-ml.so` at runtime.
On a Pi (no local NVIDIA GPU) you have two options:

**Option A — Remote NVML via SSH/API proxy**
Run a small sidecar on the machine with the NVIDIA Spark GPUs that exposes
NVML data over HTTP or a Unix socket, then implement `collect_spark()` to call
that sidecar.

**Option B — nvidia-ml-py stub / mock**
Keep `COLLECTOR_TYPE=mock` on the Pi and only enable `real` on a host that
has an NVIDIA driver installed (`libnvidia-ml.so` in `/usr/lib`).

To install on a host that **does** have NVIDIA drivers:

```bash
pip install -e ".[real]"
# libnvidia-ml.so is provided by the NVIDIA driver package, not pip
```

---

## 9. Run as a systemd Service

Create the service unit:

```bash
sudo nano /etc/systemd/system/pia-server.service
```

Paste:

```ini
[Unit]
Description=PIA Metrics Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/pia_server
Environment="PATH=/home/pi/pia_server/.venv/bin"
ExecStart=/home/pi/pia_server/.venv/bin/python -m pia_server.main
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pia-server
sudo systemctl start pia-server
sudo systemctl status pia-server
```

View live logs:

```bash
journalctl -u pia-server -f
```

---

## 10. Firewall / Port Access

If you want to reach the server from other machines on the network, open the
ports in the Pi's firewall (if `ufw` is active):

```bash
sudo ufw allow 8000/tcp comment "PIA REST + GraphQL"
sudo ufw allow 8001/tcp comment "PIA MCP"
```

---

## 11. Verify Installation

```bash
# REST
curl http://<PI_IP>:8000/health
curl http://<PI_IP>:8000/system/current
curl http://<PI_IP>:8000/spark/current

# GraphQL
curl -X POST http://<PI_IP>:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"{ systemCurrent { airInletTemp btuTransfer } sparkAllCurrent { serverId sparkGpuTempCelsius } }"}'
```

---

## 12. Optional: Install uv (faster package manager)

[uv](https://github.com/astral-sh/uv) has ARM64 Linux binaries and can
replace pip + venv for faster installs:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env   # or restart shell

# Then instead of steps 4–5 above:
uv venv && uv sync
uv run python -m pia_server.main
```

---

## Summary Checklist

- [ ] Raspberry Pi OS Bookworm 64-bit
- [ ] Python 3.11+ (`python3 --version`)
- [ ] System packages installed (`apt install` block above)
- [ ] Repo cloned
- [ ] `.venv` created and project installed
- [ ] `.env` configured (especially `DB_PATH`)
- [ ] Server starts and `/health` returns `{"status":"ok"}`
- [ ] *(optional)* systemd service enabled
- [ ] *(optional)* IPMI / NVML access configured for real collector
