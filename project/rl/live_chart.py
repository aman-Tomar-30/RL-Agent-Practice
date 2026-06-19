import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

LOG_FILE = "project/results/logs/episode_log.csv"

plt.style.use("default")

fig, ax = plt.subplots(figsize=(10, 5))
ax2 = ax.twinx()

def update(frame):

    try:
        df = pd.read_csv(LOG_FILE)

        ax.clear()
        ax2.clear()

        # Total Reward
        ax.plot(
            df["Episode"],
            df["Total_Reward"],
            label="Total Reward"
        )

        # Discounted Return
        ax.plot(
            df["Episode"],
            df["Discounted_G"],
            label="Discounted Return G"
        )

        # Moving Average
        if len(df) >= 10:
            moving_avg = (
                df["Total_Reward"]
                .rolling(window=10)
                .mean()
            )

            ax.plot(
                df["Episode"],
                moving_avg,
                linewidth=2,
                label="Reward MA(10)"
            )

        # Epsilon
        ax2.plot(
            df["Episode"],
            df["Epsilon"],
            linestyle="--",
            label="Epsilon"
        )

        ax.set_title("RL Training Progress")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Reward")
        ax2.set_ylabel("Epsilon")

        # Merge legends
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()

        ax.legend(
            lines1 + lines2,
            labels1 + labels2,
            loc="best"
        )

        ax.grid(True)

    except Exception as e:
        print(e)
        
ani = FuncAnimation(
    fig,
    update,
    interval=1000,   # update every second
    cache_frame_data=False
)

plt.show()