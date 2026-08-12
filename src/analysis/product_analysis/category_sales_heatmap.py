import pandas as pd
import matplotlib.pyplot as plt

# ==========================
# 1. 读取数据
# ==========================

file_path = r"outputs\data\06_ptoduct_analysis\category_monthly_growth.csv"

df = pd.read_csv(file_path)

print(df.head())
print(df.columns)

# ==========================
# 2. 只保留 2017-01 至 2018-07
# ==========================

df = df[
    (df["purchase_month"] >= "2017-01") &
    (df["purchase_month"] <= "2018-07")
].copy()

# ==========================
# 3. 选择 Top 15 品类
# 按整个观察期累计销售额排序
# ==========================

top_categories = (
    df.groupby("category_name")["monthly_sales_amount"]
    .sum()
    .sort_values(ascending=False)
    .head(15)
    .index
)

heatmap_data = df[
    df["category_name"].isin(top_categories)
]

# ==========================
# 4. 转换为 Heatmap 格式
# 行：Category
# 列：Month
# 值：Monthly Sales Amount
# ==========================

heatmap_table = heatmap_data.pivot(
    index="category_name",
    columns="purchase_month",
    values="monthly_sales_amount"
)

# 按整个观察期累计销售额排序
category_order = (
    heatmap_table.sum(axis=1)
    .sort_values(ascending=False)
    .index
)

heatmap_table = heatmap_table.loc[category_order]

# 按时间排序月份
heatmap_table = heatmap_table.reindex(
    sorted(heatmap_table.columns),
    axis=1
)

# ==========================
# 5. 绘制 Heatmap
# ==========================

plt.figure(figsize=(16, 8))

plt.imshow(
    heatmap_table,
    aspect="auto",
    interpolation="nearest"
)

plt.colorbar(
    label="Monthly Sales Amount"
)

plt.xticks(
    range(len(heatmap_table.columns)),
    heatmap_table.columns,
    rotation=90
)

plt.yticks(
    range(len(heatmap_table.index)),
    heatmap_table.index
)

plt.xlabel("Purchase Month")
plt.ylabel("Category")

plt.title(
    "Monthly Sales Heatmap of Top 15 Categories (2017-01 to 2018-07)"
)

plt.tight_layout()

plt.show()
