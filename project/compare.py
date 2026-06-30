import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# df = pd.read_csv("without_rl_stats.csv")
# # # Set all values greater than 1 in mac_fill to 1
# df['mac_fill'] = round((df['mac_fill'] / 15) * 10, 3)

# # Reorder columns
# df = df[['mac_fill', 'new_mac_rate', 'age_score']]
# #print(df)

# df.to_csv("without_rl.csv", index=False)

#df = pd.read_csv("results/logs/live_step_log.csv")
#df = df[['mac_fill', 'new_mac_rate', 'avg_age']]
#  #print(df)
#df.to_csv("with_rl.csv", index=False)

df1 = pd.read_csv("without_rl.csv")
df2 = pd.read_csv("with_rl.csv")

comparison = pd.Series({
    'MAC Table Ulitilization':
        abs(((df2['mac_fill'].mean() - df1['mac_fill'].mean())
         / df1['mac_fill'].mean()) * 100),

    # 'Learning Improvements':
    #     abs(((df2['new_mac_rate'].mean() - df1['new_mac_rate'].mean())
    #      / df1['new_mac_rate'].mean()) * 100),

    'AVG Age Reduction':
        abs(((df2['avg_age'].mean() - df1['age_score'].mean())
         / df1['age_score'].mean()) * 100)
}).round(2)

#print(comparison)


window = 30

fig, axes = plt.subplots(3, 1, figsize=(14, 10))


(df1['mac_fill'].rolling(window).mean()).plot(ax=axes[0], label='Traditional')
(df2['mac_fill'].rolling(window).mean()).plot(ax=axes[0], label='RL')
axes[0].set_title('MAC Table Ulitilization')

(df1['new_mac_rate'].rolling(window).mean()).plot(ax=axes[1], label='Traditional')
(df2['new_mac_rate'].rolling(window).mean()).plot(ax=axes[1], label='RL')
axes[1].set_title('Learning Improvement (New MAC Learn)')

(df1['age_score'].rolling(window).mean()).plot(ax=axes[2], label='Traditional')
(df2['avg_age'].rolling(window).mean()).plot(ax=axes[2], label='RL')
axes[2].set_title('AVG Age Reduction')

for ax in axes:
    ax.legend()

plt.tight_layout()
plt.show()