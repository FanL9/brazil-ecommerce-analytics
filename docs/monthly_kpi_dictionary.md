# 月度 KPI 公共数据层字段说明

## 1. 数据层用途

`monthly_kpi` 是阶段二 Member 1 提供给 Member 2 和 Member 3 统一使用的支付型月度公共数据层。它集中计算同一批“正支付且已送达”订单的 GMV、订单量、客单价、新增用户数和活跃用户数，避免一张公共表混合全部 delivered 与正支付 delivered 两种订单范围。本层仅提供公共指标结果，不包含趋势、增长率、季节性、地域、品类、留存或可视化分析。

数据层粒度为“存在正支付 delivered 订单的自然月”，每月最多一行。`month` 采用 `YYYY-MM` 格式，底层时间字段统一为 `orders.order_purchase_timestamp`（实际通过 `vw_orders_clean.order_purchase_timestamp` 使用）。未支付或订单级正支付金额不大于 0 的 delivered 订单仍保留在有效订单基础指标中，但不进入本支付型公共层。

## 2. 字段说明

### `month`

- 中文名称：月份
- 业务定义：正支付 delivered 订单按购买时间归属的自然月，是本公共层的唯一维度。
- 计算公式：`STRFTIME('%Y-%m', vw_orders_clean.order_purchase_timestamp)`。
- 数据来源：`vw_orders_clean`（来源于 `orders`）。
- 时间字段：`orders.order_purchase_timestamp`。
- 统计粒度：自然月，格式为 `YYYY-MM`。
- 订单状态范围：`orders.order_status = 'delivered'`，且订单级正支付金额大于 0。
- 去重字段：按月份分组；月内订单以 `orders.order_id` 去重。
- 空值及异常处理：购买时间为空、不可解析或无法生成 `YYYY-MM` 的记录不计入；`vw_orders_clean` 已排除关键时间无效记录。
- 适用范围：作为五项月度 KPI 的统一月份键。
- 使用限制：仅输出存在正支付 delivered 订单的月份，不人为补月；只有未支付 delivered 订单的月份不会出现在本表中，缺失月份应结合全部 delivered 订单另行检查和披露。

### `gmv`

- 中文名称：GMV（成交总额）
- 业务定义：当月所有有效支付且已送达订单的订单级支付金额总和。
- 计算公式：先从 `vw_order_payments_clean` 筛选 `payment_value > 0`，按 `order_id` 计算 `order_payment_amount = SUM(payment_value)`；保留订单级金额大于 0 且状态为 delivered 的订单；`gmv = SUM(order_payment_amount)`。
- 数据来源：`vw_order_payments_clean`（来源于 `order_payments`）和 `vw_orders_clean`（来源于 `orders`）。
- 时间字段：`orders.order_purchase_timestamp`。
- 统计粒度：支付明细先聚合至订单级，再按自然月汇总。
- 订单状态范围：`orders.order_status = 'delivered'`，且订单级有效支付金额大于 0。
- 去重字段：支付先按 `orders.order_id` 聚合，订单连接后仍以 `order_id` 为粒度。
- 空值及异常处理：排除 `payment_value` 为 NULL、0 或负数的支付记录；没有订单级正支付金额的 delivered 订单不进入本公共层。
- 适用范围：衡量月度平台支付金额口径的成交规模。
- 使用限制：不得将支付表与商品、评论等其他一对多表直接连接后汇总；GMV 与基于 `order_items.price` 的商品销售额不是同一口径。

### `order_count`

- 中文名称：正支付已送达订单量
- 业务定义：当月订单级正支付金额大于 0 且状态为 delivered 的去重订单数量。
- 计算公式：`COUNT(DISTINCT orders.order_id)`。
- 数据来源：`vw_orders_clean`（来源于 `orders`）和按 `order_id` 汇总后的 `vw_order_payments_clean`（来源于 `order_payments`）。
- 时间字段：`orders.order_purchase_timestamp`。
- 统计粒度：自然月 × 订单级。
- 订单状态范围：`orders.order_status = 'delivered'`，且订单级正支付金额大于 0。
- 去重字段：`orders.order_id`。
- 空值及异常处理：`order_id` 为空、购买时间无效或订单级正支付金额不大于 0 的记录不计入；该字段不为 NULL。
- 适用范围：衡量月度正支付且已送达的成交订单规模。
- 使用限制：不能用支付明细数、商品明细数、评论数或全部 delivered 有效订单量替代；字段名继续固定为 `order_count`，但其范围由本公共层的正支付 delivered 过滤条件限定。

### `average_order_value`

- 中文名称：客单价
- 业务定义：当月有效支付且已送达订单的支付金额总和，除以同口径有效支付订单量。
- 计算公式：`average_order_value = gmv / order_count`；本表的 `order_count` 已限定为状态 delivered、订单级正支付金额大于 0、按 `order_id` 去重的订单量。
- 数据来源：`vw_order_payments_clean`（来源于 `order_payments`）和 `vw_orders_clean`（来源于 `orders`）。GMV 与 AOV 共用同一个订单级支付 CTE。
- 时间字段：`orders.order_purchase_timestamp`。
- 统计粒度：自然月；底层支付先聚合至订单级。
- 订单状态范围：`orders.order_status = 'delivered'`，且订单级有效支付金额大于 0。
- 去重字段：分母按 `orders.order_id` 去重。
- 空值及异常处理：排除无有效支付、支付金额为空或非正的订单；`order_count = 0` 时返回 NULL。
- 适用范围：衡量月度有效支付订单的平均支付金额。
- 使用限制：分母不是平台全部 delivered 有效订单量，而是本支付型公共层中的 `order_count`。

### `new_users`

- 中文名称：新增用户数
- 业务定义：完整数据观察期内首次产生正支付 delivered 订单，且首次正支付购买自然月等于统计月份的去重用户数量。
- 计算公式：先按 `customers.customer_unique_id` 计算完整正支付 delivered 历史中的 `MIN(orders.order_purchase_timestamp)`，再按首购月份 `COUNT(*)`。
- 数据来源：`vw_orders_clean`（来源于 `orders`）和原始维表 `customers`；连接条件为 `orders.customer_id = customers.customer_id`。
- 时间字段：`orders.order_purchase_timestamp`。
- 统计粒度：自然月 × 用户首购。
- 订单状态范围：仅使用 `orders.order_status = 'delivered'` 且订单级正支付金额大于 0 的订单确定首购。
- 去重字段：`customers.customer_unique_id`。
- 空值及异常处理：用户唯一标识或购买时间为空的记录不计入；首购时间先基于完整历史计算；同一用户只归属一个首购月份；无新增用户的结果月份返回 0。
- 适用范围：衡量数据观察期口径下的月度首次购买用户规模。
- 使用限制：这里是“首次正支付购买用户”，不是注册用户，也不等同于基于全部 delivered 订单定义的新增用户；观察期开始前历史缺失可能将存量用户误判为新增用户，不能在每个月内部重新计算首购。

### `active_users`

- 中文名称：活跃用户数
- 业务定义：当月至少产生一笔正支付 delivered 订单的去重用户数量。
- 计算公式：`COUNT(DISTINCT customers.customer_unique_id)`。
- 数据来源：`vw_orders_clean`（来源于 `orders`）和原始维表 `customers`；连接条件为 `orders.customer_id = customers.customer_id`。
- 时间字段：`orders.order_purchase_timestamp`。
- 统计粒度：自然月 × 用户级。
- 订单状态范围：`orders.order_status = 'delivered'`，且订单级正支付金额大于 0。
- 去重字段：`customers.customer_unique_id`；不得使用 `customer_id` 作为最终去重字段。
- 空值及异常处理：用户唯一标识为空的记录不计入；无活跃用户的结果月份返回 0。
- 适用范围：衡量月度产生正支付 delivered 订单的唯一用户规模。
- 使用限制：不代表平台注册用户；不同月份的活跃用户可能重复，不能跨月直接相加解释为整个观察期的唯一活跃用户数。

## 3. 数据来源和连接关系

- 订单来源：清洗 View `vw_orders_clean`，底层表为 `orders`。该 View 保留有效关键 ID、可解析购买时间且客户关联有效的订单。
- 支付来源：清洗 View `vw_order_payments_clean`，底层表为 `order_payments`。该 View 已排除空值和非正支付；月度 SQL 仍显式筛选 `payment_value > 0`，随后按 `order_id` 聚合为一行一个订单，再连接订单。
- 客户来源：原始维表 `customers`。阶段一没有建立客户清洗 View；订单通过 `vw_orders_clean.customer_id = customers.customer_id` 连接，最终用户按 `customers.customer_unique_id` 去重。
- 支付连接：`vw_order_payments_clean.order_id = vw_orders_clean.order_id`，且连接发生在支付按 `order_id` 聚合之后。
- 时间口径：`orders.order_purchase_timestamp`，按自然月统计，输出格式为 `YYYY-MM`。
- 用户口径：`customers.customer_unique_id`，连接路径为 `orders.customer_id = customers.customer_id`。
- 本公共层订单口径：`orders.order_status = 'delivered'` 且订单级正支付金额大于 0，订单按 `orders.order_id` 去重。
- 地域口径：阶段一指标定义手册未明确地域口径。本次不自行新增地域字段，也不生成地域分析结果。

## 4. 使用限制与数据覆盖披露

- GMV 不能通过支付表与商品、评论或其他一对多表直接连接后汇总，否则金额会被放大。
- GMV 是支付金额口径，与商品销售额不是同一口径。
- `order_count` 是正支付 delivered 去重订单量；平台全部 delivered 有效订单量仍应使用独立核心指标查询。
- AOV 分母就是本表同口径的 `order_count`。
- 新增用户基于完整观察历史中的首次正支付 delivered 订单，且不代表注册用户。
- 活跃用户按 `customer_unique_id` 去重；月度活跃用户不能跨月直接相加得到观察期唯一用户数。
- 当前全部 delivered 订单购买时间从 `2016-09-15 12:16:38` 开始，但 `2016-09` 唯一 delivered 订单没有正支付，因此本支付型公共层从 `2016-10` 开始；末月 `2018-08` 仍不是完整自然月。本层不增加 `is_complete_month` 字段。
- 当前公共层观察范围 `2016-10` 至 `2018-08` 的自然月序列中缺少 `2016-11`；本层只披露缺月，不人为补月。
- 地域口径仅做缺失定义记录，本次不生成任何地域汇总或分析。
