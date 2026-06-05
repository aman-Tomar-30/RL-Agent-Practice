class LiveStateEncoder:
    def __init__(self, bins=8):
        self.bins = bins

    def get_state_index(self, state_info):
        mac_bin   = min(int(state_info["mac_fill"]        * self.bins), self.bins - 1)
        flood_bin = min(int(state_info["flood_pressure"]  * self.bins), self.bins - 1)
        age_bin   = min(int(state_info["age_score"]       * self.bins), self.bins - 1)
        return (mac_bin * self.bins * self.bins) + (flood_bin * self.bins) + age_bin

    def total_states(self):
        return self.bins ** 3    # 5x5x5 = 125 states