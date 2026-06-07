import sys, os
sys.path.append(os.path.dirname(__file__))
from project.rl.train import run_live_training
# from project.rl.states import LiveStateEncoder

if __name__ == "__main__":
    # make sure dragonfly.py is already running in another terminal
    # and Mininet topology is up before running this

    SWITCH   = 'g0_s1'
    EPISODES = 200
    STEPS    = 30

    agent, encoder, rewards_history = run_live_training(
        switch=SWITCH,
        episodes=EPISODES,
        steps_per_ep=STEPS
    )

    # # Test - BINS
    # encoder = LiveStateEncoder()
    # encoder.display_bins_with_intervals()
