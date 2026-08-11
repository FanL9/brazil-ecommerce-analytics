| 日期 | 修改人 | 版本号 | 备注 |
|---|---|---|---|
| 2026-08-10 | FL | v1.0 | 建立阶段四品类公共数据层字段字典与质量校验规则 |
| 2026-08-10 | FL | v1.1 | 按更新分工移除评论和经济性代理字段，无法映射英文的品类统一标记为 unknown |
| 2026-08-11 | FL | v1.2 | 新增品类总体与月度销售汇总基础表及导出、回算说明 |

# 阶段四品类公共数据层说明

## 1. 用途与执行依赖

阶段四公共层提供四个可复用的 SQLite 派生表：

- `category_item_base`：订单商品级公共层，一行一个 delivered 订单商品。
- `category_order_base`：订单—品类级公共层，一行一个 delivered“订单—品类”组合。
- `category_sales_base`：品类总体销售汇总层，一行一个品类，供 Member 1 帕累托分析和最终整合复用。
- `category_monthly_sales_base`：月份—品类销售汇总层，一行一个实际发生销售的“月份—品类”组合，供 Member 2 增长趋势分析复用。

四个表由 `sql/06_product_analysis/category_order_base.sql` 创建。运行前必须先创建以下清洗 View：

- `vw_orders_clean`；
- `vw_order_items_clean`；

评论字段不进入这四个公共层。Member 3 进行满意度分析时，应以 `category_order_base` 为基础，再通过 `order_id` 连接 `vw_order_reviews_order_level`；后者已将评论稳定收敛为一单一条，避免多评论记录放大订单—品类样本。本次新增汇总表不改动 Member 2 的增长计算或 Member 3 的满意度、关联规则实现。

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

## 5. `category_sales_base`

用途：提供全观察期、口径统一的品类销售表现汇总。下游使用者为 Member 1 的帕累托分析和阶段四最终整合。

粒度：一行一个 `category_name`；`category_name` 有唯一索引。

上游来源：直接汇总 `category_order_base`；该订单—品类层来自 `category_item_base`，因此商品销售额和件数可以回算至商品明细层，品类订单量不会重复计算同一订单中的多个同品类商品。

| 字段 | 含义与计算口径 |
|---|---|
| `category_name` | 英文翻译名称；缺失或无法映射英文时为 `unknown` |
| `sales_amount` | 该品类全部 delivered 订单的商品销售额，即 `SUM(category_order_base.category_sales_amount)`，等价于该品类商品明细的 `SUM(price)`；不含运费，不得称为 GMV |
| `sales_share` | `sales_amount / 全部品类 sales_amount`；分母包含 `unknown` |
| `category_order_count` | 包含该品类的去重订单数；在唯一的订单—品类粒度上按行计数 |
| `item_count` | 该品类订单商品件数，即 `SUM(category_item_count)` |
| `avg_item_price` | `sales_amount / item_count` |
| `items_per_order` | `item_count / category_order_count` |
| `sales_rank` | 按 `sales_amount DESC` 排序；金额相同时按 `category_name ASC` 稳定排序后生成连续名次 |

表内金额不预先四舍五入；CSV 仅按货币展示精度输出金额，比例和均值保留更高精度。`item_count` 或 `category_order_count` 理论上不会为 0；实现仍使用安全除法，若分母为 0 则返回 `NULL`。

## 6. `category_monthly_sales_base`

用途：提供 Member 2 可直接计算环比、CMGR 和增长分类的月度品类基础数据；本表不写入任何增长率或增长分类结果。

粒度：一行一个 `purchase_month + category_name`；该组合有唯一索引。只保留实际出现订单商品的“月份—品类”组合，不补齐无销售组合，也不人为填充 0 行。

上游来源：按 `purchase_month + category_name` 汇总 `category_order_base`。`2016-09` 和 `2018-08` 保留用于边界展示，是否纳入正式增长分析由下游按统一时间窗口处理。

| 字段 | 含义与计算口径 |
|---|---|
| `purchase_month` | 订单购买月份，来自 `orders.order_purchase_timestamp`，格式为 `YYYY-MM` |
| `category_name` | 英文翻译名称；缺失或无法映射英文时为 `unknown` |
| `monthly_sales_amount` | 该月该品类的商品销售额，即 `SUM(category_sales_amount)`；不含运费，不得称为 GMV |
| `monthly_order_count` | 该月包含该品类的去重订单数；在唯一的订单—品类粒度上按行计数 |
| `monthly_item_count` | 该月该品类的订单商品件数，即 `SUM(category_item_count)` |
| `avg_item_price` | `monthly_sales_amount / monthly_item_count` |
| `items_per_order` | `monthly_item_count / monthly_order_count` |

`monthly_item_count` 或 `monthly_order_count` 理论上不会为 0；实现仍使用安全除法，若分母为 0 则返回 `NULL`。

## 7. 金额与利润边界

- `price` 及其汇总是商品销售额，不是基于支付金额的 GMV。
- 原始数据不包含商品成本、采购成本、佣金、营销成本或利润字段。因此本阶段不输出任何利润、毛利、毛利率、高毛利品类、利润空间或经济性代理指标。
- `freight_value` 仅作为订单商品原始字段保留在 `category_item_base`，不用于本阶段正式分析结论。

## 8. 重跑与导出命令

数据库首次构建或需要从原始 CSV 完整重建时，先执行：

```powershell
python src\data_processing\build_sqlite_database.py
```

随后在项目根目录执行阶段四公共层的清洗 View、SQL、验证和 CSV 导出流程：

```powershell
python src\analysis\product_analysis\category_common_layer.py
```

该脚本可重复执行，会重建四个派生表及其索引、运行严格回算，并按项目惯例以 UTF-8 BOM、无行索引格式导出：

- `outputs/data/06_product_analysis/category_sales_base.csv`
- `outputs/data/06_product_analysis/category_monthly_sales_base.csv`

## 9. 发布前质量校验

1. `category_item_base` 的 `order_id + order_item_id` 是否唯一；
2. `category_order_base` 的 `order_id + category_name` 是否唯一；
3. `category_sales_base.category_name` 是否非空且唯一；
4. `category_monthly_sales_base.purchase_month + category_name` 是否唯一；
5. 总体和月度汇总的商品销售额是否逐层回算至 `category_item_base.price`；
6. 总体与月度汇总的商品件数是否回算至 `category_item_base` 行数；
7. `category_order_count` 是否逐品类等于 `category_order_base` 行数，且同订单同品类没有重复；
8. 原始品类缺失或无法映射英文的记录是否统一为 `unknown`，并保留在销售额、订单量、件数和占比分母中；
9. `sales_share` 合计是否在浮点容差内等于 1；
10. 基础指标是否不存在 `NULL`、空品类或除零异常；
11. 公共层是否仅包含 delivered 订单，且购买时间来自 `orders.order_purchase_timestamp`；
12. 是否把商品销售额误写成 GMV，或出现任何无数据支持的利润、毛利率或经济性代理指标。
