df = pd.read_csv('outputs/data/02_business_overview/monthly_growth_rates.csv')
import pandas as pd
import matplotlib.pyplot as plt

df['month']=pd.to_datetime(df['month'])
df=df.sort_values('month')

cols=['gmv_mom','order_count_mom','aov_mom','new_users_mom','active_users_mom']

outliers={}

for c in cols:
    q1,q3=df[c].quantile([.25,.75])
    low,up=q1-1.5*(q3-q1),q3+1.5*(q3-q1)
    outliers[c]=df[(df[c]<low)|(df[c]>up)][['month',c]]
    df.loc[(df[c]<low)|(df[c]>up),c]=None

plt.figure(figsize=(14,6))

for c in cols:
    plt.plot(df['month'],df[c],marker='o',label=c)

plt.title('MoM Growth Rate (Outliers Removed)')
plt.xlabel('Month')
plt.ylabel('Growth Rate')
plt.xticks(df['month'],df['month'].dt.strftime('%Y-%m'),rotation=90)
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
