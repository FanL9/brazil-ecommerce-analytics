# 平台核心指标定义手册

本文档统一定义项目阶段一的 18 项正式核心指标。指标名称、顺序和口径必须与以下文件保持一致：

- `docs/metric_dictionary.csv`
- `sql/03_metrics/core_metrics.sql`
- `sql/03_metrics/derived_metrics.sql`
- `outputs/metric_validation.csv`

## 统一基础口径

- 默认有效订单状态为：`orders.order_status = 'delivered'`。
- 默认订单时间字段为：`orders.order_purchase_timestamp`。
- 订单唯一标识为：`orders.order_id`。
- 用户唯一标识为：`customers.customer_unique_id`。
- 支付记录有效条件为：`payment_value IS NOT NULL AND payment_value > 0`。
- 支付表必须先按 `order_id` 聚合到订单级。
- 一对多明细表必须先聚合到目标统计粒度，禁止直接同时连接后汇总。
- 所有比例指标必须使用 `NULLIF` 或等价逻辑处理分母为 0。
- 所有时间差指标必须处理时间缺失与负时间差。
- 文档、指标字典、SQL 和验证结果必须使用完全一致的中文名与英文名。

---

## 1. GMV

### 1.1 中文名与英文名

- 中文名：GMV
- 英文名：Gross Merchandise Value (GMV)

### 1.2 业务定义

在指定时间窗口内，所有有效支付且已送达订单的订单级支付金额总和，用于衡量平台成交金额规模。

### 1.3 计算公式

先筛选 payment_value > 0 的支付记录并按 order_id 汇总得到 order_payment_amount；GMV = SUM(order_payment_amount)。

### 1.4 数据来源

`orders.order_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`order_payments.order_id`、`order_payments.payment_value`。

### 1.5 时间字段

`orders.order_purchase_timestamp`。

### 1.6 统计粒度

支付明细先聚合到订单级，再按统计周期汇总。

### 1.7 订单状态范围

`orders.order_status = 'delivered'`，且订单级有效支付金额大于 0。

### 1.8 去重字段

`orders.order_id`。

### 1.9 空值和异常处理

排除 `payment_value` 为空、等于 0 或小于 0 的记录；没有有效支付记录的订单不产生 GMV。

### 1.10 对应 SQL

`sql/03_metrics/core_metrics.sql`。

### 1.11 使用限制

不得将支付表与订单明细、评论等其他一对多表直接连接后汇总，否则会放大金额。GMV 与商品销售额不是同一口径。

---

## 2. 有效订单量

### 2.1 中文名与英文名

- 中文名：有效订单量
- 英文名：Valid Order Count

### 2.2 业务定义

在指定时间窗口内，状态为 delivered 的去重订单数量。

### 2.3 计算公式

`COUNT(DISTINCT orders.order_id)`。

### 2.4 数据来源

`orders.order_id`、`orders.order_status`、`orders.order_purchase_timestamp`。

### 2.5 时间字段

`orders.order_purchase_timestamp`。

### 2.6 统计粒度

订单级。

### 2.7 订单状态范围

`orders.order_status = 'delivered'`。

### 2.8 去重字段

`orders.order_id`。

### 2.9 空值和异常处理

`order_id` 为空的记录不计入；不受支付、商品明细或评论记录是否存在影响。

### 2.10 对应 SQL

`sql/03_metrics/core_metrics.sql`。

### 2.11 使用限制

不能使用支付记录数、商品明细行数或评论行数代替订单数。

---

## 3. 客单价

### 3.1 中文名与英文名

- 中文名：客单价
- 英文名：Average Order Value (AOV)

### 3.2 业务定义

在指定时间窗口内，有效支付且已送达订单的支付金额总和除以有效支付订单量。

### 3.3 计算公式

`SUM(order_payment_amount) / COUNT(DISTINCT paid_order_id)`。

### 3.4 数据来源

`orders.order_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`order_payments.order_id`、`order_payments.payment_value`。

### 3.5 时间字段

`orders.order_purchase_timestamp`。

### 3.6 统计粒度

支付明细先聚合到订单级，再整体或按统计周期汇总。

### 3.7 订单状态范围

`orders.order_status = 'delivered'`，且订单级有效支付金额大于 0。

### 3.8 去重字段

`orders.order_id`。

### 3.9 空值和异常处理

排除无有效支付、支付金额为空或非正的订单；分母为 0 时返回 NULL。

### 3.10 对应 SQL

`sql/03_metrics/derived_metrics.sql`。

### 3.11 使用限制

不得使用 GMV 除以全部 delivered 订单量；分母必须与“支付订单量”完全一致。

---

## 4. 支付订单量

### 4.1 中文名与英文名

- 中文名：支付订单量
- 英文名：Paid Order Count

### 4.2 业务定义

在指定时间窗口内，状态为 delivered，且订单级有效支付金额大于 0 的去重订单数量。

### 4.3 计算公式

先筛选 `payment_value > 0` 并按 `order_id` 汇总；支付订单量 = `COUNT(DISTINCT order_id)`。

### 4.4 数据来源

`orders.order_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`order_payments.order_id`、`order_payments.payment_value`。

### 4.5 时间字段

`orders.order_purchase_timestamp`。

### 4.6 统计粒度

支付明细先聚合到订单级。

### 4.7 订单状态范围

`orders.order_status = 'delivered'`，且订单级有效支付金额大于 0。

### 4.8 去重字段

`orders.order_id`。

### 4.9 空值和异常处理

排除 `payment_value` 为空、等于 0 或小于 0 的记录；订单级金额必须大于 0。

### 4.10 对应 SQL

`sql/03_metrics/core_metrics.sql`。

### 4.11 使用限制

不得直接使用支付明细行数作为支付订单量。

---

## 5. 活跃用户数

### 5.1 中文名与英文名

- 中文名：活跃用户数
- 英文名：Active Customer Count

### 5.2 业务定义

在指定时间窗口内，至少产生 1 笔有效订单的去重用户数量。

### 5.3 计算公式

`COUNT(DISTINCT customers.customer_unique_id)`。

### 5.4 数据来源

`orders.customer_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`customers.customer_id`、`customers.customer_unique_id`。

### 5.5 时间字段

`orders.order_purchase_timestamp`。

### 5.6 统计粒度

用户级。

### 5.7 订单状态范围

`orders.order_status = 'delivered'`。

### 5.8 去重字段

`customers.customer_unique_id`。

### 5.9 空值和异常处理

先通过 `customer_id` 连接，再按 `customer_unique_id` 去重；用户标识为空的记录不计入。

### 5.10 对应 SQL

`sql/03_metrics/core_metrics.sql`。

### 5.11 使用限制

不代表平台注册用户数；不得使用 `customer_id` 作为最终用户去重字段。

---

## 6. 新增用户数

### 6.1 中文名与英文名

- 中文名：新增用户数
- 英文名：New Customer Count

### 6.2 业务定义

在指定自然月内，首次产生有效订单的去重用户数量。

### 6.3 计算公式

用户首购时间 = `MIN(order_purchase_timestamp)`；新增用户数 = 首购月份等于统计月份的用户数。

### 6.4 数据来源

`orders.order_id`、`orders.customer_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`customers.customer_id`、`customers.customer_unique_id`。

### 6.5 时间字段

`orders.order_purchase_timestamp`。

### 6.6 统计粒度

自然月 × 用户首购。

### 6.7 订单状态范围

仅使用 `orders.order_status = 'delivered'` 的订单确定首购时间。

### 6.8 去重字段

`customers.customer_unique_id`。

### 6.9 空值和异常处理

用户标识或下单时间为空的不计入；首购时间必须基于完整历史计算；同一用户只属于一个首购月份。

### 6.10 对应 SQL

`sql/03_metrics/core_metrics.sql`。

### 6.11 使用限制

不代表注册用户数；观察期开始前的历史缺失可能导致存量用户被误判为新增用户。

---

## 7. 复购用户数

### 7.1 中文名与英文名

- 中文名：复购用户数
- 英文名：Repeat Customer Count

### 7.2 业务定义

在指定时间窗口内，拥有至少 2 笔有效订单的去重用户数量。

### 7.3 计算公式

按用户统计 `COUNT(DISTINCT order_id)`；订单数大于等于 2 的用户计为复购用户。

### 7.4 数据来源

`orders.order_id`、`orders.customer_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`customers.customer_id`、`customers.customer_unique_id`。

### 7.5 时间字段

`orders.order_purchase_timestamp`。

### 7.6 统计粒度

用户级汇总后整体或按统计周期汇总。

### 7.7 订单状态范围

`orders.order_status = 'delivered'`。

### 7.8 去重字段

`customers.customer_unique_id`；订单使用 `orders.order_id` 去重。

### 7.9 空值和异常处理

用户标识为空的不计入；同一订单只计 1 次。

### 7.10 对应 SQL

`sql/03_metrics/core_metrics.sql`。

### 7.11 使用限制

当前口径为统计窗口内复购用户数，不等同于历史累计复购用户数。

---

## 8. 复购率

### 8.1 中文名与英文名

- 中文名：复购率
- 英文名：Repeat Purchase Rate

### 8.2 业务定义

在指定时间窗口内，复购用户数占至少拥有 1 笔有效订单用户数的比例。

### 8.3 计算公式

`复购用户数 / 活跃用户数`。

### 8.4 数据来源

`orders.order_id`、`orders.customer_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`customers.customer_id`、`customers.customer_unique_id`。

### 8.5 时间字段

`orders.order_purchase_timestamp`。

### 8.6 统计粒度

用户级汇总后整体或按统计周期汇总。

### 8.7 订单状态范围

`orders.order_status = 'delivered'`。

### 8.8 去重字段

`customers.customer_unique_id`；订单使用 `orders.order_id` 去重。

### 8.9 空值和异常处理

用户标识为空的不计入；分母为 0 时返回 NULL。

### 8.10 对应 SQL

`sql/03_metrics/derived_metrics.sql`。

### 8.11 使用限制

统计窗口内复购率与历史累计复购率不可混用。

---

## 9. 用户留存率

### 9.1 中文名与英文名

- 中文名：用户留存率
- 英文名：Customer Retention Rate

### 9.2 业务定义

以用户首购自然月为 cohort，衡量该 cohort 在第 N 个自然月再次产生有效订单的用户比例。

### 9.3 计算公式

`第 N 月留存用户数 / cohort 用户总数`。

### 9.4 数据来源

`orders.customer_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`customers.customer_id`、`customers.customer_unique_id`。

### 9.5 时间字段

`orders.order_purchase_timestamp`。

### 9.6 统计粒度

首购月份 × 留存月序号。

### 9.7 订单状态范围

`orders.order_status = 'delivered'`。

### 9.8 去重字段

`customers.customer_unique_id`；同一用户在同一自然月只计 1 次。

### 9.9 空值和异常处理

用户标识或时间为空的不计入；首购月基于完整历史；仅纳入已完整经历 N 个月的 cohort；分母为 0 时返回 NULL。

### 9.10 对应 SQL

`sql/03_metrics/derived_metrics.sql`。

### 9.11 使用限制

本指标为自然月 cohort 留存，不得与 7 日、30 日或 90 日留存混用；较新 cohort 存在右截尾。

---

## 10. 用户生命周期价值（LTV）

### 10.1 中文名与英文名

- 中文名：用户生命周期价值（LTV）
- 英文名：Customer Lifetime Value (LTV)

### 10.2 业务定义

在当前数据观察期内，每名用户累计贡献的有效支付金额的平均值，属于收入型观察期 LTV。

### 10.3 计算公式

先按用户汇总其全部有效支付订单金额得到 `customer_lifetime_revenue`；LTV = `AVG(customer_lifetime_revenue)`。

### 10.4 数据来源

`orders.order_id`、`orders.customer_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`order_payments.order_id`、`order_payments.payment_value`；`customers.customer_id`、`customers.customer_unique_id`。

### 10.5 时间字段

`orders.order_purchase_timestamp`，用于限定观察期；用户累计价值在观察期内汇总。

### 10.6 统计粒度

支付明细先聚合到订单级，再聚合到用户级，最后整体汇总。

### 10.7 订单状态范围

`orders.order_status = 'delivered'`，且订单级有效支付金额大于 0。

### 10.8 去重字段

`customers.customer_unique_id`；订单使用 `orders.order_id` 去重。

### 10.9 空值和异常处理

排除无有效支付、用户标识为空的记录；支付金额先按订单聚合；分母为 0 时返回 NULL。

### 10.10 对应 SQL

`sql/03_metrics/derived_metrics.sql`。

### 10.11 使用限制

该指标是收入型、观察期 LTV，不是利润型 LTV；未扣除成本、退款和获客成本，且受数据观察期右截尾影响。

---

## 11. 平均购买频次

### 11.1 中文名与英文名

- 中文名：平均购买频次
- 英文名：Average Purchase Frequency

### 11.2 业务定义

在指定时间窗口内，每名活跃用户平均产生的有效订单数量。

### 11.3 计算公式

`有效订单量 / 活跃用户数`。

### 11.4 数据来源

`orders.order_id`、`orders.customer_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`customers.customer_id`、`customers.customer_unique_id`。

### 11.5 时间字段

`orders.order_purchase_timestamp`。

### 11.6 统计粒度

统计周期整体，底层为订单级和用户级。

### 11.7 订单状态范围

`orders.order_status = 'delivered'`。

### 11.8 去重字段

订单使用 `orders.order_id`；用户使用 `customers.customer_unique_id`。

### 11.9 空值和异常处理

用户标识为空的不计入活跃用户；活跃用户数为 0 时返回 NULL。

### 11.10 对应 SQL

`sql/03_metrics/derived_metrics.sql`。

### 11.11 使用限制

必须明确统计窗口；不得与用户完整生命周期累计购买频次混用。

---

## 12. 平均复购间隔

### 12.1 中文名与英文名

- 中文名：平均复购间隔
- 英文名：Average Repurchase Interval

### 12.2 业务定义

复购用户相邻两笔有效订单之间时间间隔的平均值，单位为天。

### 12.3 计算公式

按用户和购买时间排序，使用 `LAG(order_purchase_timestamp)` 获得上一笔订单；平均复购间隔 = 所有合法相邻订单间隔的平均值。

### 12.4 数据来源

`orders.order_id`、`orders.customer_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`customers.customer_id`、`customers.customer_unique_id`。

### 12.5 时间字段

`orders.order_purchase_timestamp`。

### 12.6 统计粒度

用户相邻订单对，再整体汇总。

### 12.7 订单状态范围

`orders.order_status = 'delivered'`。

### 12.8 去重字段

`customers.customer_unique_id`；订单使用 `orders.order_id` 去重。

### 12.9 空值和异常处理

用户标识或时间为空的不计入；首笔订单没有间隔记录；负间隔排除并单独披露。

### 12.10 对应 SQL

`sql/03_metrics/derived_metrics.sql`。

### 12.11 使用限制

本口径对所有相邻订单间隔等权平均，不是先计算每名用户均值再对用户等权平均。

---

## 13. 平均配送时长

### 13.1 中文名与英文名

- 中文名：平均配送时长
- 英文名：Average Delivery Time

### 13.2 业务定义

从用户下单到实际签收的平均总时长，单位为天。

### 13.3 计算公式

`AVG(JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp))`。

### 13.4 数据来源

`orders.order_id`、`orders.order_status`、`orders.order_purchase_timestamp`、`orders.order_delivered_customer_date`。

### 13.5 时间字段

`orders.order_purchase_timestamp`。

### 13.6 统计粒度

订单级计算后整体或按统计周期汇总。

### 13.7 订单状态范围

`orders.order_status = 'delivered'`。

### 13.8 去重字段

`orders.order_id`。

### 13.9 空值和异常处理

两个时间字段均需非空；负时长排除；合法长尾记录保留并单独披露。

### 13.10 对应 SQL

`sql/03_metrics/core_metrics.sql`。

### 13.11 使用限制

不等于承运商运输时长；如采用截尾、缩尾或异常排除，必须单独披露。

---

## 14. 延迟配送率

### 14.1 中文名与英文名

- 中文名：延迟配送率
- 英文名：Late Delivery Rate

### 14.2 业务定义

在可评估的 delivered 订单中，实际签收时间晚于预计送达时间的订单比例。

### 14.3 计算公式

`延迟送达订单数 / 可评估 delivered 订单数`。

### 14.4 数据来源

`orders.order_id`、`orders.order_status`、`orders.order_purchase_timestamp`、`orders.order_delivered_customer_date`、`orders.order_estimated_delivery_date`。

### 14.5 时间字段

`orders.order_purchase_timestamp`。

### 14.6 统计粒度

订单级判断后整体或按统计周期汇总。

### 14.7 订单状态范围

`orders.order_status = 'delivered'`。

### 14.8 去重字段

`orders.order_id`。

### 14.9 空值和异常处理

实际或预计送达时间为空的不进入分母；实际签收时间早于下单时间的异常记录排除；分母为 0 时返回 NULL。

### 14.10 对应 SQL

`sql/03_metrics/derived_metrics.sql`。

### 14.11 使用限制

延迟配送率与准时送达率互为补集的前提是二者使用完全相同的分母。

---

## 15. 平均评论分数

### 15.1 中文名与英文名

- 中文名：平均评论分数
- 英文名：Average Review Score

### 15.2 业务定义

在指定时间窗口内，去重后的 delivered 订单有效评论分数平均值。

### 15.3 计算公式

每个订单选取 1 条代表评论后，`AVG(review_score)`。

### 15.4 数据来源

`orders.order_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`order_reviews.order_id`、`order_reviews.review_score`、`order_reviews.review_answer_timestamp`、`order_reviews.review_creation_date`、`order_reviews.review_id`。

### 15.5 时间字段

`orders.order_purchase_timestamp`。

### 15.6 统计粒度

评论先去重到订单级，再整体或按统计周期汇总。

### 15.7 订单状态范围

`orders.order_status = 'delivered'`。

### 15.8 去重字段

`order_reviews.order_id`；优先按最新 `review_answer_timestamp`，其次 `review_creation_date`，最后 `review_id` 选择代表评论。

### 15.9 空值和异常处理

无评论或评分为空的不进入计算；评分必须在 1 至 5 范围内。

### 15.10 对应 SQL

`sql/03_metrics/core_metrics.sql`。

### 15.11 使用限制

不得直接对评论明细行求平均，否则多评论订单会获得更高权重。

---

## 16. 好评率

### 16.1 中文名与英文名

- 中文名：好评率
- 英文名：Positive Review Rate

### 16.2 业务定义

去重后好评订单数占去重后有有效评分的 delivered 订单数的比例；好评定义为 `review_score >= 4`。

### 16.3 计算公式

`好评订单数 / 有有效评分的订单数`。

### 16.4 数据来源

`orders.order_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`order_reviews.order_id`、`order_reviews.review_score`、`order_reviews.review_answer_timestamp`、`order_reviews.review_creation_date`、`order_reviews.review_id`。

### 16.5 时间字段

`orders.order_purchase_timestamp`。

### 16.6 统计粒度

评论先去重到订单级，再整体或按统计周期汇总。

### 16.7 订单状态范围

`orders.order_status = 'delivered'`。

### 16.8 去重字段

`order_reviews.order_id`；使用与平均评论分数相同的代表评论规则。

### 16.9 空值和异常处理

无评论或评分为空的不进入分母；评分必须在 1 至 5 范围内；分母为 0 时返回 NULL。

### 16.10 对应 SQL

`sql/03_metrics/derived_metrics.sql`。

### 16.11 使用限制

好评阈值固定为 4 分及以上；不得使用评论创建时间作为默认订单归属周期。

---

## 17. 取消率

### 17.1 中文名与英文名

- 中文名：取消率
- 英文名：Cancellation Rate

### 17.2 业务定义

在指定时间窗口内，状态为 canceled 的订单数占全部订单数的比例。

### 17.3 计算公式

`canceled 订单数 / 全部订单数`。

### 17.4 数据来源

`orders.order_id`、`orders.order_status`、`orders.order_purchase_timestamp`。

### 17.5 时间字段

`orders.order_purchase_timestamp`。

### 17.6 统计粒度

默认按自然月，也可按完整观察期汇总。

### 17.7 订单状态范围

分母包含全部订单状态；分子仅包含 `orders.order_status = 'canceled'`。

### 17.8 去重字段

`orders.order_id`。

### 17.9 空值和异常处理

`order_id` 或时间为空的不计入月度计算；分母为 0 时返回 NULL。

### 17.10 对应 SQL

`sql/03_metrics/derived_metrics.sql`。

### 17.11 使用限制

状态值使用 `canceled`，不是 `cancelled`；首尾小样本月份的比例不宜直接与完整月份比较。

---

## 18. 品类销售占比

### 18.1 中文名与英文名

- 中文名：品类销售占比
- 英文名：Category Sales Share

### 18.2 业务定义

指定时间窗口内，各商品品类销售额占全部商品品类销售额的比例。

### 18.3 计算公式

`某品类 SUM(order_items.price) / 全部品类 SUM(order_items.price)`。

### 18.4 数据来源

`orders.order_id`、`orders.order_status`、`orders.order_purchase_timestamp`；`order_items.order_id`、`order_items.product_id`、`order_items.price`；`products.product_id`、`products.product_category_name`。

### 18.5 时间字段

`orders.order_purchase_timestamp`。

### 18.6 统计粒度

商品明细先关联品类，再按品类汇总。

### 18.7 订单状态范围

`orders.order_status = 'delivered'`。

### 18.8 去重字段

商品明细使用 `order_items.order_id + order_items.order_item_id`。

### 18.9 空值和异常处理

`price` 为空或小于 0 的记录不计入；品类为空时统一标记为 `unknown` 并保留在分母中；分母为 0 时返回 NULL。

### 18.10 对应 SQL

`sql/03_metrics/derived_metrics.sql`。

### 18.11 使用限制

销售额仅使用 `order_items.price`，不包含运费；不得与基于支付金额的 GMV 口径混用。
