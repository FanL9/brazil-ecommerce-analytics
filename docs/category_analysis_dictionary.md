| 日期 | 修改人 | 版本号 | 备注 |
|---|---|---|---|
| 2026-08-10 | FL | v1.0 | 建立阶段四品类公共数据层字段字典与质量校验规则 |
| 2026-08-10 | FL | v1.1 | 按更新分工移除评论和经济性代理字段，无法映射英文的品类统一标记为 unknown |

# 阶段四品类公共数据层说明

## 1. 用途与执行依赖

阶段四 Member 1 提供两个可复用的 SQLite 派生表：

- `category_item_base`：订单商品级公共层，一行一个 delivered 订单商品。
- `category_order_base`：订单—品类级公共层，一行一个 delivered“订单—品类”组合。

两个表由 `sql/06_product_analysis/00_category_common_layer.sql` 创建。运行前必须先创建以下清洗 View：

- `vw_orders_clean`；
- `vw_order_items_clean`；

评论字段不进入这两个公共层。Member 3 进行满意度分析时，应以 `category_order_base` 为基础，再通过 `order_id` 连接 `vw_order_reviews_order_level`；后者已将评论稳定收敛为一单一条，避免多评论记录放大订单—品类样本。

统一口径以 `docs/unified_analysis_standards.md` 为准。公共层保留全部观察期 delivered 订单；`2016-09` 和 `2018-08` 是否排除，由下游正式增长分析按统一时间规则处理。

## 2. 品类名称规则

使用 `product_category_name_translation.product_category_name_english` 作为统一品类名称。原始品类为空、翻译表没有匹配记录或英文翻译为空时，均标记为 `unknown`。

`unknown` 属于正式分析分类，必须保留在商品销售额、订单量、商品件数和销售额占比分母中。

## 3. `category_item_base`

粒度：一行一个 `order_id + order_item_id`；该组合有唯一索引。

| 字段 | 含义 |
|---|---|
| `order_id` | delivered 订单唯一标识 |
| `order_item_id` | 商品在订单内的明细序号，与 `order_id` 共同构成业务键 |
| `product_id` | 商品唯一标识 |
| `category_name` | 英文翻译名称；缺失或无法映射英文时为 `unknown` |
| `purchase_timestamp` | 订单购买时间，来自 `orders.order_purchase_timestamp` |
| `purchase_month` | 购买月份，格式为 `YYYY-MM` |
| `price` | 商品售价，单位 BRL；不含运费，不得称为 GMV |
| `freight_value` | 订单商品行对应的运费金额，单位 BRL；保留原始字段，不作为本阶段经济性或利润指标使用 |

## 4. `category_order_base`

粒度：一行一个 `order_id + category_name`；该组合有唯一索引。同一订单含多个品类时会有多行，但同一订单的同一品类只保留一行。

| 字段 | 含义 |
|---|---|
| `order_id` | delivered 订单唯一标识 |
| `category_name` | 英文翻译名称；缺失或无法映射英文时为 `unknown` |
| `purchase_month` | 购买月份，格式为 `YYYY-MM` |
| `category_item_count` | 该订单中属于该品类的商品明细行数 |
| `category_sales_amount` | 该订单该品类的 `SUM(price)`，不含运费，不得称为 GMV |

下游计算规则：

```text
品类商品销售额 = SUM(category_sales_amount)
品类订单量 = COUNT(DISTINCT order_id)
品类商品件数 = SUM(category_item_count)
平均商品单价 = SUM(category_sales_amount) / SUM(category_item_count)
每单件数 = SUM(category_item_count) / COUNT(DISTINCT order_id)
```

所有比率在分母为 0 时返回 `NULL`。同一订单可能属于多个品类，因此各品类订单量之和不要求等于平台去重订单量。

## 5. 金额与利润边界

- `price` 及其汇总是商品销售额，不是基于支付金额的 GMV。
- 原始数据不包含商品成本、采购成本、佣金、营销成本或利润字段。因此本阶段不输出任何利润、毛利、毛利率、高毛利品类、利润空间或经济性代理指标。
- `freight_value` 仅作为订单商品原始字段保留在 `category_item_base`，不用于本阶段正式分析结论。

## 6. 重跑命令

在项目根目录依次执行：

```powershell
python -c "from pathlib import Path; import sqlite3; c=sqlite3.connect(r'database/brazil_ecommerce.db'); c.executescript(Path(r'sql/02_data_cleaning/data_cleaning_rules.sql').read_text(encoding='utf-8-sig')); c.close()"

python -c "from pathlib import Path; import sqlite3; c=sqlite3.connect(r'database/brazil_ecommerce.db'); c.executescript(Path(r'sql/06_product_analysis/00_category_common_layer.sql').read_text(encoding='utf-8-sig')); c.close()"
```

第二条命令可重复执行，会重建两个派生表及其索引，不修改原始表。

## 7. 发布前质量校验

1. `category_item_base` 的 `order_id + order_item_id` 是否唯一；
2. `category_order_base` 的 `order_id + category_name` 是否唯一；
3. 公共层是否仅包含 delivered 订单；
4. 商品层行数、商品销售额和运费是否与相同清洗口径的 delivered 商品明细总体一致；
5. 订单—品类层的商品件数、商品销售额和运费是否与商品层一致；
6. 原始品类缺失或无法映射英文的记录是否统一为 `unknown` 并保留；
7. 是否把商品销售额误写成 GMV，或出现任何无数据支持的利润、毛利率或经济性代理指标。
