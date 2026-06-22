import time
import json
import redis
from prometheus_client import start_http_server, Gauge

# Connect to the local Redis instance
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Define Prometheus Gauges for Step-Level Metrics
RL_MAC_FILL = Gauge("rl_mac_fill", "Live MAC Table Fill Ratio")
RL_MAC_COUNT = Gauge("rl_mac_count", "Live MAC Entry Count in OVS")
RL_FLOOD_PRESSURE = Gauge("rl_flood_pressure", "Live Network Flood Pressure")
RL_AVG_AGE = Gauge("rl_avg_age", "Live Average MAC Entry Age")
RL_STEP_REWARD = Gauge("rl_step_reward", "Reward obtained in the current step")
RL_TOTAL_EP_REWARD = Gauge("rl_total_ep_reward", "Running total reward inside current episode")

# Define Prometheus Gauges for Categorical Labels (Action and Strategy tracking)
RL_ACTION_DIST = Gauge("rl_action_execution", "Tracking executed actions", ["action_name"])
RL_POLICY_MODE = Gauge("rl_policy_mode", "Exploration vs Exploitation choice", ["mode"])

# Define Prometheus Gauges for Episode-Level Metrics
RL_EPISODE_REWARD = Gauge("rl_episode_total_reward", "Total accumulated reward per completed episode")
RL_DISCOUNTED_G = Gauge("rl_discounted_g", "Calculated Discounted Return G")
RL_EPSILON = Gauge("rl_epsilon", "Current Epsilon Exploration Rate")

def process_telemetry():
    # Initialize Redis PubSub and subscribe to the channels configured in train.py
    pubsub = r.pubsub()
    pubsub.subscribe(["rl_step_channel", "rl_episode_channel"])
    
    print("[TELEMETRY] Listening for live training variables from Redis...")
    
    for message in pubsub.listen():
        if message["type"] != "message":
            continue
            
        channel = message["channel"]
        data = json.loads(message["data"])
        
        if channel == "rl_step_channel":
            # Update step metrics in RAM
            RL_MAC_FILL.set(data["mac_fill"])
            RL_FLOOD_PRESSURE.set(data["flood_pressure"])
            RL_AVG_AGE.set(data["avg_age"])
            RL_STEP_REWARD.set(data["reward"])
            RL_EPSILON.set(data["epsilon"])
            
            # Reset and flag active actions/modes for discrete categorical charts
            RL_ACTION_DIST.clear()
            RL_POLICY_MODE.clear()
            RL_ACTION_DIST.labels(action_name=data["action_name"]).set(1)
            RL_POLICY_MODE.labels(mode=data["chosen_by"]).set(1)
            
        elif channel == "rl_episode_channel":
            # Update episode historical metrics
            RL_EPISODE_REWARD.set(data["total_reward"])
            RL_DISCOUNTED_G.set(data["discounted_g"])

if __name__ == "__main__":
    # Start the Prometheus scraping HTTP server on port 8004
    start_http_server(8004)
    print("[PROMETHEUS] Standalone RL Exporter serving on http://localhost:8004/metrics")
    
    try:
        process_telemetry()
    except KeyboardInterrupt:
        print("\n[STOP] Telemetry exporter shutting down cleanly.")