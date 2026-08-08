import pandas as pd
import matplotlib.pyplot as plt
file_path = r"monthly_kpi.csv的所在路径"
df = pd.read_csv(file_path)

df["month"] = pd.to_datetime(df["month"])

#我们排除异常月份2016‑09，2016‑10，2016‑12，2017‑01
exclude_month_list = ["2016-09", "2016-10", "2016-12", "2017-01"]
df = df[~df["month"].dt.strftime("%Y-%m").isin(exclude_month_list)]

df = df.sort_values("month").reset_index(drop=True)

plt.figure(figsize=(12, 5), dpi=110)
plt.plot(df["month"], df["gmv"], marker='o', linewidth=2, color="#1f77b4")

plt.title("Monthly GMV Trend (Excluding Early Incomplete Months)")
plt.xlabel("Month")
plt.ylabel("GMV")
plt.xticks(rotation=30)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()