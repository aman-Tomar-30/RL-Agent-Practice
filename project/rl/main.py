import sys, os
sys.path.append(os.path.dirname(__file__))
from project.rl.train import run_live_training
import redis

r = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)

if __name__ == "__main__":

    SWITCH   = 'g0_s1'
    EPISODES = 200
    STEPS    = 30

    try:
        # Signal experiment start
        r.set("rl_running", "1")

        agent, encoder, rewards_history = run_live_training(
            switch=SWITCH,
            episodes=EPISODES,
            steps_per_ep=STEPS
        )
    except KeyboardInterrupt:
        print("\nTraining interrupted by user.")
    finally:

        # Signal experiment end
        r.delete("rl_running")

        print("[SYNC] RL experiment ended")
