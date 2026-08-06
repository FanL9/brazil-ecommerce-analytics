# 阶段三用户公共数据层说明

## 1. 用途与执行依赖

阶段三 Member 1 提供两个可复用的 SQLite 派生表：

- `customer_order_base`：订单级用户行为基础层，一行一个 delivered 订单。
- `customer_profile`：用户级公共层，一行一个 `customer_unique_id`。

两个表由 `sql/05_customer_analysis/00_customer_common_views.sql` 创建；州、城市、小时、星期、工作日/周末和潜力区域市场 View 由 `sql/05_customer_analysis/01_customer_profile_analysis.sql` 创建。运行前必须已创建 `vw_orders_clean` 与 `vw_order_payments_clean`。

统一口径来自 `docs/metric_definition.md` 和 `docs/metric_dictionary.csv`：

- 用户唯一标识：`customers.customer_unique_id`。
- 有效订单：`orders.order_status = 'delivered'`。
- 业务时间：`orders.order_purchase_timestamp`。
- GMV：只保留正 `payment_value`，先按 `order_id` 汇总，再连接订单。
- 客单价：GMV / 正支付 delivered 订单数；不是 GMV / 全部 delivered 订单数。

## 2. `customer_order_base`

粒度：一行一个 delivered `order_id`；`order_id` 有唯一索引。

| 字段 | 含义 |
|---|---|
| `customer_unique_id` | 真实用户唯一标识 |
| `customer_id` | 订单与客户维表的连接键，不可替代唯一用户标识 |
| `order_id` | 订单唯一标识 |
| `order_purchase_timestamp` | 订单购买时间 |
| `purchase_date` | 购买日期 `YYYY-MM-DD` |
| `purchase_month` | 购买月份 `YYYY-MM` |
| `purchase_hour` | 购买小时，0—23 |
| `weekday_number` | 星期序号，Monday=1，Sunday=7 |
| `customer_state` | 该订单客户记录中的州 |
| `customer_city` | 该订单客户记录中的城市 |
| `order_gmv` | 订单级正支付金额之和；无正支付的 delivered 订单为 0 |
| `is_paid_order` | 订单级金额大于 0 时为 1，否则为 0 |

注意：当前数据有一个 delivered 订单没有正支付。该订单仍属于“有效订单量”，但不产生 GMV，也不进入客单价分母。

## 3. `customer_profile`

粒度：一行一个 `customer_unique_id`；该字段有唯一索引。

| 字段 | 含义 |
|---|---|
| `customer_unique_id` | 用户唯一标识 |
| `first_purchase_timestamp` | 观察期内首次 delivered 订单购买时间 |
| `last_purchase_timestamp` | 观察期内最近 delivered 订单购买时间 |
| `first_purchase_month` | 首购月份 `YYYY-MM` |
| `latest_purchase_month` | 最近购买月份 `YYYY-MM` |
| `valid_order_count` | 用户 delivered 订单数 |
| `paid_order_count` | 用户正支付 delivered 订单数 |
| `lifetime_gmv` | 用户观察期累计 GMV（BRL） |
| `average_order_value` | `lifetime_gmv / paid_order_count` |
| `customer_lifecycle_days` | 最近购买与首次购买的时间差（天） |
| `active_purchase_months` | 至少发生一次 delivered 订单的不同月份数 |
| `is_repeat_customer` | delivered 订单数不少于 2 时为 1 |
| `customer_state` | 用户代表州 |
| `customer_city` | 用户代表城市 |

代表地域规则：使用用户最近一次 delivered 订单对应的客户地址。如果多笔订单购买时间相同，按 `order_id DESC`、`customer_id DESC` 依次确定。该规则保证每名用户只进入一个州和一个“城市 + 州”组合，且选择结果稳定可重复。

## 4. 分析 View

| View | 粒度与用途 |
|---|---|
| `customer_state_profile` | 一州一行；用户数、占比、订单、GMV、人均消费、客单价和排名 |
| `customer_city_profile` | 城市 + 州一行；禁止只按城市名聚合 |
| `customer_hourly_behavior` | 0—23 时各一行；无订单小时也保留 0 |
| `customer_weekday_behavior` | Monday—Sunday 各一行，并保留稳定星期序号 |
| `customer_day_type_behavior` | Weekday / Weekend；含自然日数和日均订单数 |
| `customer_growth_periods` | 最近 6 个完整月与此前 6 个完整月的边界 |
| `potential_regional_market_base` | 州级前后期用户、订单、GMV、人均消费和增长率基础表 |

州/城市画像使用 `customer_profile` 的代表地域，并将用户完整观察期订单与 GMV 归入该地域，因此用户数、订单数和 GMV 均可与总体严格对账。时段与增长 View 使用 `customer_order_base`，保留订单发生时地域。

## 5. 潜力区域市场筛选

Python 脚本从 `potential_regional_market_base` 导出最终结果，并公开写入全部阈值：

1. 前期与近期用户数都不低于各自州级正样本分布的 P25，才进入潜力判断。
2. “规模较大但人均消费较低”：合格市场近期用户数不低于中位数，且人均消费低于中位数。
3. “当前规模中等但增长较快”：近期用户数位于 P25—P75，且用户增长率和 GMV 增长率都不低于各自中位数。
4. “人均消费较高但渗透规模较小”：人均消费不低于 P75，且用户占比低于中位数。
5. 分母为 0 的增长率保留为 `NULL`；不生成无限大或强制写 0。

这些标签是历史数据筛选结果，不代表因果关系，也不等于城市等级或“下沉市场”。

## 6. 重跑命令

从项目根目录执行：

```powershell
.venv\Scripts\python.exe src\analysis\customer_analysis\customer_profile_analysis.py
```

脚本会重建派生表和 View、导出最终 CSV、从最终 CSV 生成 300 DPI 图表、更新报告并运行 14 项验证。
