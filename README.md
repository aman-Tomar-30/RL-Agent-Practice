# AI-Based MAC Learning Policies

An AI-driven network management system that applies Reinforcement Learning (RL) to optimize MAC address learning policies in a simulated Dragonfly network topology. The RL agent observes network state, takes routing/forwarding actions, and is monitored in real-time via a Grafana dashboard backed by Prometheus metrics.

---

## Project Structure

```
RL-AGENT-PRACTICE/
├── project/
│   ├── .venv/                    # Python virtual environment
│   ├── output/                   # Training output files
│   ├── results/                  # Experiment results
│   ├── rl/
│   │   ├── __init__.py
│   │   ├── actions.py            # Action space definitions
│   │   ├── agent.py              # RL agent implementation
│   │   ├── env.py                # Network environment (Gym-compatible)
│   │   ├── main.py               # RL training entry point
│   │   ├── requirements.txt      # Python dependencies
│   │   ├── reward.py             # Reward function definitions
│   │   ├── states.py             # State space definitions
│   │   └── train.py              # Training loop logic
│   ├── __init__.py
│   ├── auto_traffic.py           # Automated traffic generation
│   ├── dragonfly.py              # Dragonfly topology builder
│   ├── generate_csv.py           # CSV log generation
│   ├── monitor.py                # Network monitoring utilities
│   ├── network_run.py            # Mininet network launcher
│   ├── rl_watcher.py             # RL training watcher/logger
│   └── watch.py                  # Live watcher utility
├── grafana/
│   └── mac-step-logs-dashboard.json   # Pre-built Grafana dashboard
├── prometheus/                   # Prometheus configuration
├── docker-compose.yml            # Orchestrates monitoring stack
├── Dockerfile
├── episode_exporter.py           # Prometheus exporter: episode metrics (port 8001)
├── fdb_exporter.py               # Prometheus exporter: FDB/MAC table metrics (port 8000)
├── steps_exporter.py             # Prometheus exporter: step/reward metrics (port 8002)
└── requirements.txt              # Top-level Python dependencies
```

---

## Flow of Execution

```
network_run.py
     │
     ▼
Generate Dragonfly topology + traffic in Mininet
     │
     ▼
main.py (RL Agent)
  - Interacts with environment
  - Observes network state
  - Takes actions
  - Maintains training logs
     │
     ▼
Docker Compose
  - Prometheus         (port 8080)
  - Grafana            (port 3000)
  - episode_exporter   (port 8001)
  - steps_exporter     (port 8002)
     │
     ▼
Exporters
  - fdb_exporter       (port 8000)
     │
     ▼
Prometheus
  - Scrapes all exporters
     │
     ▼
Grafana
  - Uses Prometheus as datasource
  - Loads dashboard JSON
  - Displays real-time metrics on port 3000
```

---

## Prerequisites

- Python 3.8+
- [Mininet](http://mininet.org/)
- Docker & Docker Compose
- `sudo` privileges (required for Mininet)

---

## Setup & Running

The system requires **4 terminal sessions** running simultaneously.

### Terminal 1 — Launch Mininet Network

```bash
cd project
source .venv/bin/activate
sudo python3 network_run.py
```

Starts the Dragonfly topology in Mininet and generates network traffic.

---

### Terminal 2 — Run the RL Agent

```bash
cd project
source .venv/bin/activate
cd ..
sudo python3 -m project.rl.main
```

Launches the RL agent. It observes the network environment, selects actions, and logs per-episode and per-step metrics.

---

### Terminal 3 — Start Monitoring Stack (Docker Compose)

```bash
docker compose up -d
```

Starts the following services:

| Service           | Port  | Description                        |
|-------------------|-------|------------------------------------|
| Prometheus        | 8080  | Metrics scraper & time-series DB   |
| Grafana           | 3000  | Visualization dashboard            |
| episode_exporter  | 8001  | Exports per-episode RL metrics     |
| steps_exporter    | 8002  | Exports per-step reward metrics    |

---

### Terminal 4 — Run FDB Exporter

```bash
cd project
source .venv/bin/activate
cd ..
sudo python3 fdb_exporter.py
```

Exports MAC/FDB table metrics from the simulated switches to Prometheus on port **8000**.

---

## Grafana Dashboard Setup

Once all terminals are running:

1. Open Grafana in your browser: [http://localhost:3000](http://localhost:3000)
2. Log in (default credentials: `admin` / `admin`)
3. Go to **Configuration → Data Sources → Add data source**
4. Select **Prometheus** and set the URL to:
   ```
   http://localhost:8080
   ```
5. Click **Save & Test**
6. To load the pre-built dashboard:
   - Go to **Dashboards → Import**
   - Upload `grafana/mac-step-logs-dashboard.json`
   - Click **Import**

### Dashboard Panels

The imported dashboard displays:

- **RL Agent Q-Table** — current Q-values per state-action pair
- **Episode & Step Logs** — reward curves, episode lengths, and training progress
- **MAC Table of `g0_s1` switch** — live FDB entries showing learned MAC addresses

---

## Key Components

| File | Description |
|------|-------------|
| `network_run.py` | Builds and runs the Dragonfly topology in Mininet |
| `rl/env.py` | Custom Gym environment wrapping the Mininet network |
| `rl/agent.py` | Q-learning (or other RL) agent implementation |
| `rl/reward.py` | Reward signal based on network performance metrics |
| `rl/states.py` | State representation (link utilization, queue depths, etc.) |
| `fdb_exporter.py` | Reads FDB/MAC tables from switches; exposes to Prometheus |
| `episode_exporter.py` | Exposes per-episode RL training metrics |
| `steps_exporter.py` | Exposes per-step reward/action metrics |
| `docker-compose.yml` | Defines Prometheus, Grafana, and exporter services |

---

## Architecture Overview

```
 Mininet (Dragonfly Topology)
        │  network state
        ▼
  RL Agent (Q-Learning)
        │  actions (routing decisions)
        ▼
  Environment Feedback (reward)
        │
        ├── episode_exporter ──► Prometheus ──► Grafana Dashboard
        ├── steps_exporter   ──►     │
        └── fdb_exporter     ──►     │
                                     └── Real-time visualization
                                         on localhost:3000
```

---

## License

This project is for research and educational purposes.