def get_reward(
    old_fill,
    new_fill,
    old_flood,
    new_flood,
    old_age,
    new_age,
    action
):
    reward = 0

    HIGH_FILL = 1.0
    CRITICAL_FILL = 1.75
    HEATHY_FILL = 0.60

    HIGH_FLOOD = 0.4

    stale_age_threshold = 0.05
    fresh_age_threshold = 0.01


    fill_reduction = old_fill - new_fill
    new_mac_rate_reduction = old_flood - new_flood
    age_reduction = old_age - new_age


    if action == "LEARN_MAC":

        # flooding existed and reduced
        if new_fill < HEATHY_FILL:
                reward += 8

        elif new_fill > HIGH_FILL and new_fill < CRITICAL_FILL:
                reward -= 8

        # table was already critically full
        elif new_fill >= CRITICAL_FILL:
            reward -= 15



    elif action == "EVICT_ENTRY":

        # eviction should reduce fill
        if old_fill > CRITICAL_FILL:

            if fill_reduction > 0:
                reward += 8

            elif fill_reduction < 0:
                reward -= 8

        elif old_fill > HIGH_FILL:

            if fill_reduction > 0:
                reward += 5

        # stale entries removed
        if old_flood == 0:

            if new_flood > 0:
                reward -= 10

        # unnecessary eviction
        if old_fill < 0.5:
            reward -= 10

        if old_age < fresh_age_threshold:
            reward -= 5

    elif action == "INCREASE_AGING":

        # useful when flooding exists
        if old_fill > HEATHY_FILL:
            if new_fill >= CRITICAL_FILL:
                reward -= 15
            elif new_fill >= HIGH_FILL:
                reward -= 7

            if new_mac_rate_reduction < 0:
                reward -= 5
            elif new_mac_rate_reduction > 0:
                reward += 3

        # keeping already-fresh entries longer
        if new_age < fresh_age_threshold:
            reward += 3

        # no flood + empty table
        if new_fill < HEATHY_FILL:
            reward += 5



    elif action == "DECREASE_AGING":

        # should remove stale entries
        if old_age > stale_age_threshold:

            if age_reduction > 0:

                if old_fill < HIGH_FILL:
                    reward += 7
                else:
                    reward += 5

            elif age_reduction < 0:
                reward -= 5

        # bad when table already crowded
        if old_fill > CRITICAL_FILL:
            reward -= 7

        # bad when flooding already high
        if old_flood > HIGH_FLOOD:
            reward -= 5


    reward += (
        15 * fill_reduction +
        5 * new_mac_rate_reduction +
        2 * age_reduction
    )



    if new_fill >= CRITICAL_FILL:
        situation = "CRITICAL"

    elif new_fill >= HIGH_FILL:
        situation = "PREVENTIVE"

    else:
        situation = "NORMAL"

    if (
        fill_reduction > 0 or
        new_mac_rate_reduction > 0 or
        age_reduction > 0
    ):
        outcome = "improved"

    elif (
        fill_reduction < 0 or
        new_mac_rate_reduction < 0 or
        age_reduction < 0
    ):
        outcome = "degraded"

    else:
        outcome = "neutral"

    return reward, outcome, situation