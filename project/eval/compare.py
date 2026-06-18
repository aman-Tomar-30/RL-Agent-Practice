import os
import pandas as pd
import matplotlib.pyplot as plt


BASE_DIR = "project/final"
OUTPUT_ROOT = "project/results/eval"

os.makedirs(OUTPUT_ROOT, exist_ok=True)


def evaluate(folder_name):

    RL_FILE = os.path.join(
        BASE_DIR,
        folder_name,
        "with_rl.csv"
    )

    BASE_FILE = os.path.join(
        BASE_DIR,
        folder_name,
        "without_rl.csv"
    )

    OUTPUT_DIR = os.path.join(
        OUTPUT_ROOT,
        folder_name
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ==========================
    # LOAD DATA
    # ==========================

    rl = pd.read_csv(RL_FILE)
    base = pd.read_csv(BASE_FILE)

    rows = min(len(rl), len(base))

    rl = rl.head(rows)
    base = base.head(rows)

    print(f"\nComparing {rows} rows [{folder_name}]")

    # ==========================
    # BASIC METRICS
    # ==========================

    rl_fill = rl["mac_fill"].mean()
    base_fill = base["mac_fill"].mean()

    rl_flood = rl["flood_pressure"].mean()
    base_flood = base["flood_pressure"].mean()

    rl_age = rl["avg_age"].mean()
    base_age = base["avg_age"].mean()

    # ==========================
    # STATES
    # ==========================

    def count_states(df):

        critical = (df["mac_fill"] >= 0.95).sum()

        preventive = (
            (df["mac_fill"] >= 0.80)
            & (df["mac_fill"] < 0.95)
        ).sum()

        normal = (
            df["mac_fill"] < 0.80
        ).sum()

        return critical, preventive, normal

    base_critical, base_preventive, base_normal = count_states(base)
    rl_critical, rl_preventive, rl_normal = count_states(rl)

    # ==========================
    # IMPROVEMENTS
    # ==========================

    def pct_improvement(old, new):

        if old == 0:
            return 0

        return ((old - new) / old) * 100

    flood_reduction = pct_improvement(
        base_flood,
        rl_flood
    )

    critical_reduction = pct_improvement(
        base_critical,
        rl_critical
    )

    normal_coverage = (
        rl_normal / rows
    ) * 100

    fill_reduction = (
        ((base_fill - rl_fill) / base_fill) * 100
        if base_fill > 0
        else 0
    )

    base_stability = (
        (1 - base_flood) * 50
        + (1 - min(base_fill, 1)) * 25
        + (1 - base_age) * 25
    )

    rl_stability = (
        (1 - rl_flood) * 50
        + (1 - min(rl_fill, 1)) * 25
        + (1 - rl_age) * 25
    )

    stability_gain = (
        ((rl_stability - base_stability)
         / base_stability)
        * 100
        if base_stability != 0
        else 0
    )

    # ==========================
    # REPORT
    # ==========================

    print("\n" + "=" * 65)
    print(f"      RL EVALUATION : {folder_name.upper()}")
    print("=" * 65)

    print(f"MAC Utilization Reduction : {fill_reduction:.2f}%")
    print(f"Flood Reduction           : {flood_reduction:.2f}%")
    print(f"Critical Reduction        : {critical_reduction:.2f}%")
    print(f"Normal State Coverage     : {normal_coverage:.2f}%")
    print(f"Network Stability Gain    : {stability_gain:.2f}%")

    print("=" * 65)

    # ==========================
    # CHART 1
    # ==========================

    metrics = [
        "MAC Fill",
        "Flood",
        "Avg Age"
    ]

    base_values = [
        base_fill,
        base_flood,
        base_age
    ]

    rl_values = [
        rl_fill,
        rl_flood,
        rl_age
    ]

    width = 0.35
    x = range(len(metrics))

    plt.figure(figsize=(8, 5))

    plt.bar(
        [i - width/2 for i in x],
        base_values,
        width,
        label="Baseline"
    )

    plt.bar(
        [i + width/2 for i in x],
        rl_values,
        width,
        label="RL"
    )

    plt.xticks(x, metrics)
    plt.title(f"{folder_name.upper()} Metrics")
    plt.legend()

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            OUTPUT_DIR,
            "avg_metrics.png"
        )
    )

    plt.close()

    # ==========================
    # CHART 2
    # ==========================

    states = [
        "Critical",
        "Preventive",
        "Normal"
    ]

    base_states = [
        base_critical,
        base_preventive,
        base_normal
    ]

    rl_states = [
        rl_critical,
        rl_preventive,
        rl_normal
    ]

    x = range(len(states))

    plt.figure(figsize=(8, 5))

    plt.bar(
        [i - width/2 for i in x],
        base_states,
        width,
        label="Baseline"
    )

    plt.bar(
        [i + width/2 for i in x],
        rl_states,
        width,
        label="RL"
    )

    plt.xticks(x, states)
    plt.title(f"{folder_name.upper()} State Distribution")
    plt.legend()

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            OUTPUT_DIR,
            "state_distribution.png"
        )
    )

    plt.close()

    # ==========================
    # CHART 3
    # ==========================

    labels = [
        "MAC\nReduction",
        "Flood\nReduction",
        "Critical\nReduction",
        "Normal\nCoverage",
        "Stability\nGain"
    ]

    values = [
        fill_reduction,
        flood_reduction,
        critical_reduction,
        normal_coverage,
        stability_gain
    ]

    plt.figure(figsize=(8, 5))

    plt.bar(labels, values)

    plt.ylabel("Percentage (%)")
    plt.title(f"{folder_name.upper()} Improvements")

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            OUTPUT_DIR,
            "improvements.png"
        )
    )

    plt.close()

    print(f"Charts saved in {OUTPUT_DIR}")


# ===================================
# RUN BOTH APPROACHES
# ===================================

evaluate("learn")
evaluate("rebalance")
