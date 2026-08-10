import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

# ==========================
# 1. 读取数据
# ==========================

df = pd.read_csv(
    r"outputs/data/03_customer_analysis/cohort_monthly_retention.csv"
    )

# ==========================
# 2. 月份转换用于排序
# ==========================

df["cohort_month_date"] = pd.to_datetime(
    df["cohort_month"],
    format="%b-%y"
)

# ==========================
# 3. 生成 Cohort Matrix
# ==========================

cohort_heatmap = df.pivot(
    index="cohort_month",
    columns="cohort_index",
    values="retention_rate"
)

# ==========================
# 4. 最新 Cohort 在上方
# ==========================

cohort_order = (
    df[["cohort_month", "cohort_month_date"]]
    .drop_duplicates()
    .sort_values(
        "cohort_month_date",
        ascending=False
    )["cohort_month"]
)

cohort_heatmap = cohort_heatmap.loc[cohort_order]

# ==========================
# 5. 画 Heatmap
# ==========================

plt.figure(figsize=(12,10))

# 避免0导致log错误
heatmap_data = cohort_heatmap.fillna(0.0001)

img = plt.imshow(
    heatmap_data,
    aspect="auto",
    cmap="Blues",
    norm=LogNorm(
        vmin=0.001,
        vmax=1
    )
)

plt.colorbar(
    img,
    label="Retention Rate (Log Scale)"
)

plt.xticks(
    range(len(cohort_heatmap.columns)),
    cohort_heatmap.columns
)

plt.yticks(
    range(len(cohort_heatmap.index)),
    cohort_heatmap.index
)

plt.xlabel(
    "Cohort Index (Months Since First Purchase)"
)

plt.ylabel(
    "Cohort Month"
)

plt.title(
    "Monthly Cohort Retention Heatmap"
)

plt.savefig(
    r"C:\Users\Hongshucham\Desktop\8.10\cohort_retention_heatmap_log.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()
