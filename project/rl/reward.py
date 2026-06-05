def get_reward(
    action,
    old_fill,
    new_fill,
    old_flood,
    new_flood,
    old_age,
    new_age,
    all_ports_blocked=False
):

    mac_gain = old_fill - new_fill
    flood_gain = old_flood - new_flood
    age_gain = old_age - new_age

    reward = (
        3.0 * flood_gain +
        2.0 * mac_gain +
        1.0 * age_gain
    )

    action_cost = {
    0: 0.01,
    1: 0.05,
    2: 0.10,
    3: 0.20,
    4: 0.10,
    5: 0.05,
    6: 0.05
    }

    reward -= action_cost[action]

    outcome = "neutral"

    if reward > 0.2:
        outcome = "improved"

    elif reward < -0.2:
        outcome = "degraded"

    situation = "NORMAL"

    if new_fill >= 0.95:
        reward -= 5
        situation = "CRITICAL"

    elif new_fill >= 0.80:
        situation = "PREVENTIVE"

    if all_ports_blocked:
        reward -= 10
        outcome = "isolation"

    return reward, outcome, situation