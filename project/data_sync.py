import pandas as pd

# df = pd.read_csv("without_rl_stats.csv")
# # Set all values greater than 1 in mac_fill to 1
# df['mac_fill'] = df['mac_fill'].clip(upper=1)

# # Reorder columns
# df = df[['mac_fill', 'flood_pressure', 'age_score']]
# print(df)

# df.to_csv("without_rl.csv", index=False)

# df = pd.read_csv("results/logs/live_step_log.csv")
# df = df[['mac_fill', 'flood_pressure', 'avg_age']]
# #print(df)
# df.to_csv("with_rl_rebalance.csv", index=False)