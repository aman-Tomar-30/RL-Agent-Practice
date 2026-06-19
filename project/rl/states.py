class LiveStateEncoder:
    def __init__(self, bins=5):
        self.bins = bins
        self.interval = 1.0 / bins
        self.mac_edges = [0.5, 1.0, 1.5, 2.5]


    def mac_binning(self, value):
        for i, edge in enumerate(self.mac_edges):
            if value < edge:
                return i
        return len(self.mac_edges)  # bucket 4

    # Flood/Age Bucketing
    def normal_binning(self, value):
        bin_index = int(value / self.interval)
        return min(bin_index, self.bins - 1)


    def get_state_index(self, state_info):

        mac_bin = self.mac_binning(state_info["mac_fill"])
        flood_bin = self.normal_binning(state_info["flood_pressure"])
        age_bin = self.normal_binning(state_info["avg_age"])

        state_index = (
            mac_bin * self.bins * self.bins
            + flood_bin * self.bins
            + age_bin
        )

        return state_index


    def total_states(self):
        return self.bins ** 3

    def show_mac_buckets(self):
        print("MAC Fill Buckets:")
        print("Bucket 0 : < 0.5")
        print("Bucket 1 : 0.5 - 1.0")
        print("Bucket 2 : 1.0 - 1.5")
        print("Bucket 3 : 1.5 - 2.5")
        print("Bucket 4 : >= 2.5")

    def show_normal_buckets(self):
        print("\nFlood/Age Buckets:")
        for i in range(self.bins):
            start = i * self.interval
            end = 1.0 if i == self.bins - 1 else (i + 1) * self.interval
            print(f"Bucket {i} : {start:.2f} - {end:.2f}")