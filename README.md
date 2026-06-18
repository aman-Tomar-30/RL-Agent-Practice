# AI-Based MAC Learning Policies

An AI-driven network management system that applies Reinforcement Learning (RL) to optimize MAC address learning policies in a simulated Dragonfly network topology. The RL agent observes network state, takes routing/forwarding actions, and is monitored in real-time via a Grafana dashboard backed by Prometheus metrics. Results are evaluated by comparing RL-driven behavior against a baseline environment with no RL.

---

## Project Structure

```
RL-AGENT-PRACTICE/
├── project/
│   ├── .venv/                          # Python virtual environment
│   ├── eval/
│   │   └── compare.py                  # Compares RL vs non-RL output states
│   ├── final/
│   │   ├── learn/
│   │   │   ├── with_rl.csv             # Learning metrics with RL agent
│   │   │   └── without_rl.csv          # Learning metrics without RL agent
│   │   └── rebalance/
│   │       ├── with_rl.csv             # Rebalance metrics with RL agent
│   │       └── without_rl.csv          # Rebalance metrics without RL agent
│   ├── network_stats/
│   │   └── stat.csv                    # Raw network statistics
│   ├── output/
│   │   └── network_stats.csv           # Processed network output stats
│   ├── results/
│   │   ├── eval/
│   │   │   ├── learn/
│   │   │   │   ├── avg_metrics.png         # Avg metrics plot (learn phase, RL)
│   │   │   │   ├── improvements.png        # Improvement trends (learn phase)
│   │   │   │   └── state_distribution.png  # State distribution (learn phase)
│   │   │   └── rebalance/
│   │   │       ├── avg_metrics.png         # Avg metrics plot (rebalance phase)
│   │   │       ├── improvements.png        # Improvement trends (rebalance phase)
│   │   │       └── state_distribution.png  # State distribution (rebalance phase)
│   │   ├── avg_metrics_comparison.png      # Side-by-side RL vs non-RL metrics
│   │   ├── improvement_summary.png         # Overall improvement summary
│   │   └── state_distribution.png          # Global state distribution
│   ├── logs/
│   │   ├── episode_log.csv             # Per-episode training logs
│   │   └── live_step_log.csv           # Per-step live reward/action logs
│   ├── qtable/
│   │   ├── q_table.csv                 # Live Q-table (updated during training)
│   │   └── final_q_table.csv           # Final Q-table snapshot after training
│   ├── rl/
│   │   ├── __init__.py
│   │   ├── action_definition.py        # Formal action space definitions
│   │   ├── actions.py                  # Action execution logic
│   │   ├── agent.py                    # RL agent (Q-learning) implementation
│   │   ├── env.py                      # Gym-compatible network environment
│   │   ├── main.py                     # RL training entry point
│   │   ├── policy.py                   # Policy logic (epsilon-greedy, etc.)
│   │   ├── reward.py                   # Reward function definitions
│   │   ├── states.py                   # State space definitions
│   │   └── train.py                    # Training loop
│   ├── __init__.py
│   ├── auto_traffic.py                 # Legacy traffic generation strategy
│   ├── data_sync.py                    # Pandas-based CSV sync/processing utility
│   ├── dragonfly.py                    # Dragonfly topology builder
│   ├── generate_csv.py                 # CSV log generation helper
│   ├── get_data.py                     # Data extraction utility
│   ├── network_run.py                  # Mininet network launcher
│   ├── ovs_stats.py                    # OVS switch statistics collector
│   ├── traffic.py                      # New traffic generation strategy
│   ├── watch.py                        # Live watcher utility
│   └── without_rl.csv                  # Baseline CSV (no RL)
├── grafana/
│   └── provisioning/
│       └── dashboards/
│           └── mac-step-logs-dashboard.json   # Pre-built Grafana dashboard
├── prometheus/
│   └── prometheus.yml                  # Prometheus scrape configuration
├── .gitignore
├── docker-compose.yml                  # Orchestrates monitoring stack
├── Dockerfile
├── episode_exporter.py                 # Exports episode logs → Prometheus (port 8001)
├── fdb_exporter.py                     # Exports OVS MAC/FDB table → Prometheus (port 8000)
├── redis_exporter.py                   # Exports Redis MAC DB metrics → Prometheus
├── steps_exporter.py                   # Exports step/reward logs → Prometheus (port 8002)
├── README.md
└── requirements.txt
```

---

## Flow of Execution

```
network_run.py
     │
     ▼
Generate Dragonfly topology + traffic in Mininet
(traffic.py — new strategy)
     │
     ▼
main.py (RL Agent)
  - Interacts with network environment
  - Observes network state
  - Takes actions (MAC learning policy decisions)
  - Logs per-episode and per-step data
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
  - fdb_exporter       (port 8000)  ← OVS MAC/FDB table from switches
  - redis_exporter                  ← MAC table stored/optimized in Redis DB
     │
     ▼
Prometheus
  - Scrapes all exporters
     │
     ▼
Grafana
  - Uses Prometheus as datasource
  - Loads provisioned dashboard JSON
  - Displays real-time metrics on port 3000
```

---

## Prerequisites

- Python 3.8+
- [Mininet](http://mininet.org/)
- Docker & Docker Compose
- Redis (for MAC table storage and optimization)
- `sudo` privileges (required for Mininet and OVS)

---

## Setup & Running

The system requires **4 terminal sessions** running simultaneously.

---

### Terminal 1 — Launch Mininet Network

```bash
cd project
source .venv/bin/activate
sudo python3 network_run.py
```

Builds the Dragonfly topology in Mininet and starts traffic generation using the new `traffic.py` strategy.

---

### Terminal 2 — Run the RL Agent

```bash
cd project
source .venv/bin/activate
cd ..
sudo python3 -m project.rl.main
```

Launches the RL agent. It interacts with the Mininet environment, selects actions based on the current policy, updates the Q-table, and writes logs to `logs/episode_log.csv` and `logs/live_step_log.csv`.

---

### Terminal 3 — Start Monitoring Stack (Docker Compose)

```bash
docker compose up -d
```

Starts the following services:

| Service          | Port | Description                              |
|------------------|------|------------------------------------------|
| Prometheus       | 8080 | Metrics scraper & time-series DB         |
| Grafana          | 3000 | Visualization dashboard                  |
| episode_exporter | 8001 | Exports per-episode RL training metrics  |
| steps_exporter   | 8002 | Exports per-step reward/action metrics   |

---

### Terminal 4 — Run Exporters

**FDB Exporter** (OVS MAC table from switches → Prometheus):
```bash
cd project
source .venv/bin/activate
cd ..
sudo python3 fdb_exporter.py
```

**Redis Exporter** (Redis MAC DB metrics → Prometheus):
```bash
sudo python3 redis_exporter.py
```

> Both exporters can be run in the same terminal sequentially or in separate terminals as needed.

---

## Grafana Dashboard Setup

Once all terminals are running:

1. Open Grafana: [http://localhost:3000](http://localhost:3000)
2. Log in (default: `admin` / `admin`)
3. Go to **Configuration → Data Sources → Add data source**
4. Select **Prometheus** and set the URL to:
   ```
   http://localhost:8080
   ```
5. Click **Save & Test**
6. Import the pre-built dashboard:
   - Go to **Dashboards → Import**
   - Upload `grafana/provisioning/dashboards/mac-step-logs-dashboard.json`
   - Click **Import**

### Dashboard Panels

| Panel | Description |
|-------|-------------|
| **RL Agent Q-Table** | Live Q-values per state-action pair |
| **Episode & Step Logs** | Reward curves, episode lengths, training progress |
| **MAC Table (`g0_s1`)** | Live FDB entries from OVS switch |
| **Redis MAC Table** | MAC entries stored and optimized inside Redis DB |

---

## Evaluation — RL vs Non-RL Comparison

The `eval/compare.py` script compares output states generated by:
- The environment **without RL** (baseline, reactive MAC learning)
- The environment **with RL** acting on it (optimized MAC learning policy)

```bash
cd project
source .venv/bin/activate
python3 eval/compare.py
```

Comparison results and plots are saved under `results/eval/`:

| Output File | Description |
|-------------|-------------|
| `learn/avg_metrics.png` | Average metrics during the learn phase |
| `learn/improvements.png` | Improvement trends during learning |
| `learn/state_distribution.png` | State visit distribution during learning |
| `rebalance/avg_metrics.png` | Average metrics during the rebalance phase |
| `rebalance/improvements.png` | Improvement trends during rebalancing |
| `rebalance/state_distribution.png` | State visit distribution during rebalancing |
| `avg_metrics_comparison.png` | Side-by-side RL vs non-RL metric comparison |
| `improvement_summary.png` | Overall improvement summary across phases |
| `state_distribution.png` | Global state distribution across all runs |

---

## Key Components

| File | Description |
|------|-------------|
| `network_run.py` | Builds and runs the Dragonfly topology in Mininet |
| `traffic.py` | New traffic generation strategy for the network |
| `auto_traffic.py` | Legacy traffic generation (superseded by `traffic.py`) |
| `rl/env.py` | Custom Gym environment wrapping the Mininet network |
| `rl/agent.py` | Q-learning agent implementation |
| `rl/action_definition.py` | Formal definitions of the RL action space |
| `rl/policy.py` | Policy logic (e.g., epsilon-greedy exploration) |
| `rl/reward.py` | Reward signal based on network performance metrics |
| `rl/states.py` | State representation (link utilization, queue depths, etc.) |
| `data_sync.py` | Pandas-based utility to sync and process CSV log files |
| `ovs_stats.py` | Collects OVS switch statistics |
| `get_data.py` | Data extraction utility for analysis |
| `fdb_exporter.py` | Reads OVS FDB/MAC tables from switches; exposes to Prometheus (8000) |
| `episode_exporter.py` | Exposes per-episode RL training metrics to Prometheus (8001) |
| `steps_exporter.py` | Exposes per-step reward/action metrics to Prometheus (8002) |
| `redis_exporter.py` | Exports Redis-stored MAC table metrics to Prometheus |
| `eval/compare.py` | Compares RL vs non-RL environment output states |
| `docker-compose.yml` | Defines Prometheus, Grafana, and exporter services |

---

## Architecture Overview

```
 Mininet (Dragonfly Topology)
   └── traffic.py (traffic generation)
          │  network state
          ▼
    RL Agent (Q-Learning)
          │  MAC learning policy actions
          ▼
    Environment Feedback (reward signal)
          │
          ├── episode_exporter ──►
          ├── steps_exporter   ──► Prometheus ──► Grafana Dashboard
          ├── fdb_exporter     ──►  (8080)         (localhost:3000)
          └── redis_exporter   ──►

    Redis DB ◄──── MAC Table (stored & optimized by RL)
          │
          └── redis_exporter ──► Prometheus

    eval/compare.py
          ├── with_rl.csv    ──► Statistical comparison
          └── without_rl.csv ──► & visualization plots
```

---

## License

This project is for research and educational purposes.