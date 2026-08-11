
import pandas as pd
import matplotlib.pyplot as plt

# ==========================
# 1. 读取数据
# ==========================

file_path = r"outputs\data\06_product_analysis\category_monthly_growth.csv"
df = pd.read_csv(file_path)

# 查看字段
print(df.head())

# ==========================
# 2. 选择Top品类（避免类别太多看不清）
# Top 15 是按照整个观察期内累计销售额（total sales amount）最高的15个品类选出来的，不是按照某一个月份。
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
# 3. 转换为热力图格式
# 行：category
# 列：month
# 值：monthly_sales_amount
# ==========================
heatmap_table = heatmap_data.pivot(
    index="category_name",
    columns="purchase_month",
    values="monthly_sales_amount"
)

# 按总销售额排序
category_order = (
    heatmap_table.sum(axis=1)
    .sort_values(ascending=False)
    .index
)

heatmap_table = heatmap_table.loc[category_order]

# ==========================
# 4. 绘制 Heatmap
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
    "Monthly Sales Heatmap of Top Categories"
)

plt.tight_layout()

plt.show()
