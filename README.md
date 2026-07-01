# AI-Based MAC Learning Policies

> An AI-driven MAC learning framework that leverages Q-Learning (Reinforcement Learning) to optimize MAC address management in real time. The system continuously monitors MAC table occupancy, new MAC address arrival rate, and entry age to make intelligent decisions on MAC learning, entry eviction, and aging time adjustment.
 
---
 
## Table of Contents
 
- [Overview](#overview)
- [Project Structure](#project-structure)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Setup & Running — 7 Terminals](#setup--running--7-terminals)
- [Grafana Dashboard](#grafana-dashboard)
- [Evaluation — RL vs No-RL](#evaluation--rl-vs-no-rl)
- [Key Components](#key-components)
- [License](#license)
---
 
## Overview
 
Traditional L2 switches learn MAC addresses reactively — when an unknown destination is encountered, the packet is **flooded to every port**. This wastes bandwidth, causes MAC table overflow, and leads to MAC flapping instability, especially in large topologies like Dragonfly used in data centers.
 
This project replaces reactive flooding with an **RL agent that learns which port a MAC address is likely to be on** — making smarter forwarding decisions, evicting stale entries intelligently, and adjusting aging timers dynamically. The entire system is observable in real time via a Prometheus + Grafana monitoring stack.
 

---

## Project Structure
 
```
RL-AGENT-PRACTICE/
├── project/
│   ├── .venv/                          # Python virtual environment
│   ├── rl/
│   │   ├── __init__.py
│   │   ├── action_definition.py        # Formal action space definitions
│   │   ├── actions.py                  # Action execution logic
│   │   ├── agent.py                    # RL agent (Q-Learning / DQN) implementation
│   │   ├── env.py                      # Gym-compatible Mininet environment
│   │   ├── main.py                     # RL training entry point  ← Terminal 7
│   │   ├── policy.py                   # Epsilon-greedy policy logic
│   │   ├── reward.py                   # Reward function
│   │   ├── states.py                   # State space definitions
│   │   └── train.py                    # Training loop
│   ├── results/
│   │   ├── logs/
│   │   │   ├── episode_log.csv             # Per-episode training logs
│   │   │   └── live_step_log.csv           # Per-step live reward/action logs
│   │   └── qtable/
│   │       ├── q_table.csv                 # Live Q-table (updated during training)
│   │       └── final_q_table.csv           # Final Q-table after training
│   ├── network_stats/
│   │   └── stat.csv
│   ├── output/
│   │   └── network_stats.csv
│   ├── __init__.py
│   ├── auto_traffic.py                 # Legacy traffic generation
│   ├── compare.py                      # RL vs No-RL comparison script
│   ├── data_sync.py                    # CSV sync / Pandas utility
│   ├── dragonfly.py                    # Dragonfly topology builder
│   ├── generate_csv.py                 # CSV log generation helper
│   ├── get_data.py                     # Data extraction utility
│   ├── network_run.py                  # Mininet network launcher  ← Terminal 1
│   ├── ovs_stats.py                    # OVS switch statistics collector
│   ├── traffic.py                      # Current traffic generation strategy
│   ├── watch.py                        # Live watcher utility
│   └── without_rl.csv                  # Baseline CSV (no RL)
├── grafana/
│   └── provisioning/
│       └── dashboards/
│           └── Full-dashboard.yaml            # Pre-built Grafana dashboard
│           └── mac-step-logs-dashboard.json   # Pre-built Grafana dashboard
│           └── dashboard.yaml                 # Pre-built Grafana dashboard
│           └── episode-logs-dashboard.json    # Pre-built Grafana dashboard
│           └── mac-table-dashboard.json       # Pre-built Grafana dashboard
│           └── step-logs-dashboard.json       # Pre-built Grafana dashboard
├── prometheus/
│   └── prometheus.yml                  # Prometheus scrape config
├── .gitignore
├── docker-compose.yml                  # Prometheus + Grafana orchestration
├── Dockerfile
├── episode_exporter.py                 # Episode logs → Prometheus   ← Terminal 2
├── steps_exporter.py                   # Step/reward logs → Prometheus ← Terminal 3
├── fdb_exporter.py                     # OVS MAC/FDB table → Prometheus ← Terminal 4
├── redis_exporter.py                   # Redis MAC DB → Prometheus    ← Terminal 5
├── rl_telemetry_exporter.py            # RL live telemetry → Prometheus ← Terminal 6
├── requirements.txt
└── README.md
```
 
---

## System Architecture
 
```
┌─────────────────────────────────────────────────────────────────┐
│              Mininet — Dragonfly Topology                       │
│         network_run.py · OVS switches · traffic.py              │
│                       [ Terminal 1 ]                            │
└──────────────────────────────┬──────────────────────────────────┘
                               │ network state / reward signal
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│              RL Agent — Q-Learning / Deep Q-Learning             │
│          agent.py · policy.py · env.py · reward.py               │
│                       [ Terminal 7 ]                             │
│                                                                  │
│   State: MAC table occupancy · new MAC arrival rate · entry age  │
│   Action: learn entry · evict entry · adjust aging timer         │
│   Reward: +delivery · +MAC hit · −flooding · −loop               │
└───────────────────────────┬──────────────────────────────────────┘
                            │ read / write policy
                            ▼
                  ┌─────────────────────┐
                  │      Redis DB       │
                  │  MAC table storage  │
                  │  optimized policy   │
                  └──────────┬──────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐
  │episode_export │  │steps_exporter │  │  fdb_exporter         │
  │Port 8001 [T2] │  │Port 8002 [T3] │  │  OVS MAC/FDB [T4]     │
  └───────┬───────┘  └───────┬───────┘  └──────────┬────────────┘
          │                  │                     │
  ┌───────────────┐  ┌────────────────────────────────┐
  │redis_exporter │  │   rl_telemetry_exporter        │
  │Port 8003 [T5] │  │   RL live telemetry [T6]       │
  └───────┬───────┘  └───────────────┬────────────────┘
          │                          │
          └──────────────┬───────────┘
                         ▼
              ┌─────────────────────┐
              │     Prometheus      │
              │   Scrapes all 5     │
              │   Port 8080         │
              │  (docker-compose)   │
              └──────────┬──────────┘
                         ▼
              ┌──────────────────────┐
              │  Grafana Dashboard   │
              │  localhost:3000      │
              │  Q-table · episodes  │
              │  MAC table · Redis   │
              └──────────────────────┘
```
 
---
 
## Prerequisites
 
- Python 3.8+
- [Mininet](http://mininet.org/) with OVS support
- Docker and Docker Compose
- Redis server
- `sudo` privileges (required for Mininet and OVS)
---
 
## Setup & Running — 7 Terminals
 
The full system runs across **7 terminals simultaneously**. Start them in order.
 
---
 
### Terminal 1 — Launch Mininet Network
 
```bash
cd project
source .venv/bin/activate
sudo python3 network_run.py
```
 
Builds the Dragonfly topology in Mininet and starts traffic generation. Keep this running throughout.
 
---
 
### Terminal 2 — Episode Exporter
 
```bash
cd project
source .venv/bin/activate
cd ..
sudo python3 episode_exporter.py
```
 
Reads `logs/episode_log.csv` and exposes per-episode RL training metrics to Prometheus on port **8001**.
 
---
 
### Terminal 3 — Steps Exporter
 
```bash
cd project
source .venv/bin/activate
cd ..
sudo python3 steps_exporter.py
```
 
Reads `logs/live_step_log.csv` and exposes per-step reward and action metrics to Prometheus on port **8002**.
 
---
 
### Terminal 4 — FDB Exporter
 
```bash
cd project
source .venv/bin/activate
cd ..
sudo python3 fdb_exporter.py
```
 
Reads the OVS switch FDB (Forwarding Database) directly from the Mininet switches and exposes live MAC table entries to Prometheus on port **8000**.
 
---
 
### Terminal 5 — Redis Exporter
 
```bash
cd project
source .venv/bin/activate
cd ..
sudo python3 redis_exporter.py
```
 
Reads the optimized MAC table from Redis and exposes it to Prometheus on port **8003**.
 
---
 
### Terminal 6 — RL Telemetry Exporter
 
```bash
cd project
source .venv/bin/activate
cd ..
sudo python3 rl_telemetry_exporter.py
```
 
Exposes live RL agent telemetry (Q-values, epsilon, episode count) to Prometheus in real time.
 
---
 
### Terminal 7 — Run the RL Agent
 
```bash
cd project
source .venv/bin/activate
cd ..
sudo python3 -m project.rl.main
```
 
Launches the RL agent. It observes network state from Mininet, selects actions based on the Q-table policy, writes decisions to Redis, and logs all training data to `logs/`.
 
---



## Grafana Dashboard
 
Once all terminals and Docker services are running:
 
1. Open [http://localhost:3000](http://localhost:3000)
2. Log in — default credentials: `admin` / `admin`
3. Go to **Configuration → Data Sources → Add data source**
4. Choose **Prometheus** and set the URL to `http://localhost:8080`
5. Click **Save & Test**
6. Import the pre-built dashboard:
   - Go to **Dashboards → Import**
   - Upload `grafana/provisioning/dashboards/Full-dashboard.yaml`
   - Click **Import**

## Evaluation — RL vs No-RL
 
Run the comparison script after training to generate side-by-side plots:
 
```bash
cd project
source .venv/bin/activate
python3 compare.py
```

---

## Key Components
 
| File | Description |
|------|-------------|
| `project/network_run.py` | Builds and runs Dragonfly topology in Mininet |
| `project/traffic.py` | Current traffic generation strategy |
| `project/dragonfly.py` | Dragonfly topology builder |
| `project/rl/env.py` | Gym-compatible environment wrapping Mininet |
| `project/rl/agent.py` | Q-Learning / DQN agent implementation |
| `project/rl/action_definition.py` | Formal action space — learn, evict, adjust aging |
| `project/rl/policy.py` | Epsilon-greedy exploration policy |
| `project/rl/reward.py` | Reward function — delivery, flooding penalty, MAC hit |
| `project/rl/states.py` | State: MAC occupancy, arrival rate, entry age |
| `project/ovs_stats.py` | OVS switch statistics collector |
| `project/data_sync.py` | Pandas CSV sync utility |
| `episode_exporter.py` | Episode logs → Prometheus (port 8001) |
| `steps_exporter.py` | Step/reward logs → Prometheus (port 8002) |
| `fdb_exporter.py` | OVS FDB/MAC table → Prometheus (port 8000) |
| `redis_exporter.py` | Redis MAC state → Prometheus (port 8003) |
| `rl_telemetry_exporter.py` | Live RL telemetry → Prometheus |
| `docker-compose.yml` | Prometheus + Grafana orchestration |
| `project/compare.py` | RL vs No-RL statistical comparison |

---

## License

This project is for research and educational purposes — HPE Career Preview Program FY26