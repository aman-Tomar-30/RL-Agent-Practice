import time
import pandas as pd
from prometheus_client import start_http_server, Gauge

# Define Prometheus Gauges matching train.py output format
STEP_MAC_FILL = Gauge("rl_step_mac_fill", "MAC Table Fill Ratio per step")
STEP_NEW_MAC_RATE = Gauge("rl_step_new_mac_rate", "New MAC Rate per step")
STEP_AVG_AGE = Gauge("rl_step_avg_age", "Average MAC Entry Age per step")
STEP_REWARD = Gauge("rl_step_reward", "Reward obtained in the current step")
STEP_TOTAL_EP_REWARD = Gauge("rl_step_total_ep_reward", "Running total reward inside current episode")
STEP_EPSILON = Gauge("rl_step_epsilon", "Current Epsilon Exploration Rate")

STEP_Q_VALS = Gauge("rl_step_q_value", "Live Q-Value for a specific action", ["action"])
STEP_SITUATION = Gauge("rl_step_situation", "Categorical network situation tag", ["situation"])
STEP_OUTCOME = Gauge("rl_step_outcome", "Categorical action outcome tag", ["outcome"])

LOG_PATH = "project/results/logs/live_step_log.csv"

def export_buffer():
    try:
        # Read the live training log CSV file
        df = pd.read_csv(LOG_PATH)
        if df.empty:
            return
        
        # Grab the absolute latest step row written by train.py
        row = df.iloc[-1]
        
        # Update gauges with exact case-sensitive matching headers from train.py
        STEP_MAC_FILL.set(float(row["mac_fill"]))
        STEP_NEW_MAC_RATE.set(float(row["new_mac_rate"]))
        STEP_AVG_AGE.set(float(row["avg_age"]))
        STEP_REWARD.set(float(row["Reward"]))
        STEP_TOTAL_EP_REWARD.set(float(row["Total_Ep_Reward"]))
        STEP_EPSILON.set(float(row["Epsilon"]))
        
        # Update discrete Q-Values using matching REBALANCE syntax
        STEP_Q_VALS.labels(action="EVICT").set(float(row["Q_EVICT"]))
        STEP_Q_VALS.labels(action="INC_AGE").set(float(row["Q_INC_AGE"]))
        STEP_Q_VALS.labels(action="DEC_AGE").set(float(row["Q_DEC_AGE"]))
        STEP_Q_VALS.labels(action="LEARN_MAC").set(float(row["Q_LEARN_MAC"]))
        
        # Clear old labels and update categories safely
        STEP_SITUATION.clear()
        STEP_OUTCOME.clear()
        STEP_SITUATION.labels(situation=str(row["Situation"])).set(1)
        STEP_OUTCOME.labels(outcome=str(row["Outcome"])).set(1)
        
    except Exception as e:
        # Catch file read locks gracefully when train.py is writing
        pass

def main():
    # Start the HTTP server on Port 8002 for Prometheus scraping
    start_http_server(8002)
    print("[PROMETHEUS] Running on :8002")
    
    while True:
        export_buffer()
        time.sleep(1) # Check for file updates every 1 second

if __name__ == "__main__":
    main()