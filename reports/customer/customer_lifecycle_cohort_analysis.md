| 时间 | 修改人 | 版本号 | 备注 |
|---|---|---|---|
| 2026-08-10 | Hong Shucham | V1.0 | 完成Cohort留存、短期复购留存及用户生命周期分析；建立相关SQL、CSV输出及Cohort留存热力图 |

# Cohort留存与用户生命周期分析 （阶段三 Member 2）

## 1. 识别每位用户基本信息
   - 首次购买日期；
   - 首次购买月份；
   - 最近购买日期；
   - 累计有效订单数；
   - 累计GMV；
   - 用户生命周期长度。

产出：
- outputs/data/03_customer_analysis/customer_profile.csv 
- outputs/data/03_customer_analysis/customer_order_base.csv

customer_order_base.csv详细描述：
- customer_unique_id：TEXT，用户全局唯一标识，原始数据集用户唯一编号
- customer_id：TEXT，订单关联的客户ID，用于关联 customer_profile表
- order_id：TEXT，订单唯一编号，每笔订单不重复
- order_purchase_timestamp：TEXT，订单下单完整时间戳，精确到时分秒
- purchase_date：TEXT，下单日期，格式yyyy‑mm‑dd
- purchase_month：TEXT，下单年月，格式yyyy‑mm
- purchase_hour：INTEGER，下单小时 (0‑23)，分析下单时段分布
- weekday_number：INTEGER，下单是星期几的数字编码，用于周度行为分析
- customer_state：TEXT，用户所在州，直接从订单源提取
- customer_city：TEXT，用户所在城市
- order_gmv：REAL，该笔订单 GMV；0 代表无效 / 取消订单
- is_paid_order：INTEGER，是否为有效付费订单；1 = 有效可统计，0 = 取消、未支付，计算指标时过滤 is_paid_order=0

customer_profile.csv详细描述：
- customer_unique_id：TEXT，用户全局唯一标识，原始数据集用户唯一编号
- first_purchase_timestamp：TEXT，用户首次有效付费订单完整时间戳，包含日期与时分秒
- last_purchase_timestamp：TEXT，用户最近一次有效付费订单完整时间戳；仅下单 1 次时与首次时间相等
- first_purchase_month：TEXT，用户首购月份，格式May‑18，作为 Cohort 分析的队列月份 (cohort month)
- latest_purchase_month：TEXT，用户最后一笔有效订单所属月份，格式May‑18
- valid_order_count：INTEGER，用户全部有效订单数量（经过数据清洗过滤异常订单后的订单总数）
- paid_order_count：INTEGER，用户实际付费订单数量；筛选参与 GMV、复购指标计算的订单
- lifetime_gmv：REAL，用户全生命周期累计 GMV，所有付费订单金额汇总
- average_order_value：REAL，用户个人平均客单价 = lifetime_gmv /paid_order_count
- customer_lifecycle_days：REAL，用户生命周期天数：末次下单时间 − 首次下单时间；仅 1 笔订单时值为 0
- active_purchase_months：INTEGER，用户产生过付费订单的不同自然月的总个数，用于判断跨月复购行为
- is_repeat_customer：INTEGER，是否复购用户；1 = 付费订单数≥2，0 = 仅 1 笔付费订单
- customer_state：TEXT，用户收货地址所属巴西州缩写（如 SP、RJ）
- customer_city：TEXT，用户收货所在城市名称

---
根据sql/05_customer_analysis/03_customer_lifecycle_cohort_analysis.sql来制作以下产出的csv
---

## 2. 建立月度Cohort
   - 首购月份；
   - 后续活跃月份；
   - Cohort Month；
   - 初始用户数；
   - 各月活跃用户数；
   - 各月留存率；
   - 不同首购月份的留存差异。

产出：
- outputs/data/03_customer_analysis/
cohort_monthly_retention.csv
- src/customer_analysis/customer_analysis/cohort_retention_heatmap_log.py
- src/customer_analysis/customer_analysis/cohort_retention_heatmap_log.png

观察图片大致推断：
- 整体跨月复购留存极低：除偏移 0（首购当月）颜色很深代表 100% 留存外，只要向后推移 1 个月及以上，热力颜色迅速变浅，留存普遍落在\(10^{-2} \sim 10^{-3}\)量级，说明绝大部分用户在完成首次下单之后，不会再回来跨月下单
- 没有明显随时间改善的留存趋势：对比不同首购队列（Y 轴各个月份），不管是 2016 年底、2017 全年还是 2018 年的新用户队列，后续月份留存都维持在很低水平，后期新增用户并没有表现出更好的用户忠诚度
- 少数队列存在微弱的长期活跃信号：少数单元格存在淡淡的蓝色，代表还是存在极少量用户，在首购之后很久依然会回来下单，但这部分用户占整体队列的比例微乎其微
- 业务推断：该平台用户大多属于一次性消费用户，平台难以把新用户转化为长期复购客户，用户生命周期价值主要由首次订单贡献

## 3. 计算短期复购留存
   - 7日内再次购买比例；
   - 30日内再次购买比例；
   - 90日内再次购买比例；
   - 完整观察窗口用户数；
   - 因观察窗口不足而排除的用户数。

产出：
- outputs/data/03_customer_analysis/short_term_repeat_retention.csv

|total_users|obs_7d|repeat_7d|repeat_rate_7d|obs_30d|repeat_30d|repeat_rate_30d|obs_90d|repeat_90d|repeat_rate_90d|
|---|---|---|---|---|---|---|---|---|---|
|93358|92801|1015|0.0109|86772|1412|0.0163|75320|1907|0.0253|

7/30/90 日短期留存定义：
- 起点为用户第一笔有效订单的购买时间。
- N 日留存用户：首购后 > 0 且 <= N × 24 小时 内至少再次产生1 笔有效订单的用户。
- N 日留存率：N 日内再次购买用户数 / 具备完整 N 日观察窗口的首购用户数。
- 完整观察窗口要求首购时间不晚于观察截止日减 N 日；窗口不足用户必须排除，并同时报告纳入人数和排除人数。
- 7/30/90 日留存不得与自然月 Cohort 留存混称。

大致推断：
- 平台整体短期复购水平极低：7 日复购率仅 1.09%，30 日复购率 1.63%，90 日复购率仅 2.53%
- 随着观测周期拉长，复购率有小幅提升，但整体仍处于极低水平，说明绝大多数用户在首购后不会产生复购行为，平台用户粘性差
- 9 万 + 总用户中，90 天内产生复购的用户不足 2000 人，平台营收高度依赖首购订单，老用户复购贡献极小

## 4. 建立生命周期阶段
   - 首购用户；
   - 早期用户；
   - 成长用户；
   - 成熟用户；
   - 沉默用户。

产出：
- outputs/data/03_customer_analysis/customer_lifecycle_segment.csv

定义：
- 用户生命周期长度：截止日前最近一笔有效订单日期减首次有效订单日期，单位为天；单次购买用户为 0 天
- 使用以下互斥顺序：    
    1. 沉默用户：recency_days > 90
    2. 首购用户：未沉默、有效订单数为 1，且 recency_days <= 30
    3. 早期用户：未沉默、有效订单数为 1，且 30 < recency_days <= 90
    4. 成长用户：未沉默、有效订单数不少于 2，且生命周期长度 <= 180 天
    5. 成熟用户：未沉默、有效订单数不少于 2，且生命周期长度 > 180 天
- 上述顺序先判断沉默，再判断订单数和生命周期，保证每位用户只进入一类

## 5. 对比各生命周期阶段的数值
   - 用户数及占比；
   - 订单数；
   - GMV；
   - 人均消费；
   - 客单价；
   - 平均购买频次；
   - 复购用户数；
   - 复购率；
   - 平均生命周期长度；
   - 平均最近消费间隔。

产出：
- outputs/data/03_customer_analysis/lifecycle_stage_comparison.csv

|lifecycle_stage|user_count|user_percentage|order_count|gmv|avg_customer_spend|avg_order_value|avg_purchase_frequency|repeat_users|repeat_rate|avg_lifecycle_days|avg_recency_days|
|---|---|---|---|---|---|---|---|---|---|---|---|
|Dormant Customer|74899|0.8023|77304|12308397.4|164.33|159.22|1.03|2187|0.0292|2.06|289.42|
|Early Customer|11298|0.121|11298|1894571.12|167.69|167.69|1.0|0|0.0|0.0|64.12|
|Growing Customer|391|0.0042|807|122755.35|313.95|152.11|2.06|391|1.0|55.57|50.64|
|Mature Customer|223|0.0024|522|75040.51|336.5|143.76|2.34|223|1.0|318.58|48.31|
|New Customer|6547|0.0701|6547|1021697.39|156.06|156.06|1.0|0|0.0|0.0|22.22|

大致推断：
- 用户结构失衡：休眠用户占比高达 80.23%，是平台绝对主体；新用户 + 早期用户合计占 19.11%，而高价值的成长用户 + 成熟用户合计仅占 0.66%，平台用户结构呈现 “倒金字塔” 形态，高价值用户规模极小
- 复购能力分层极端明显：成长、成熟用户复购率 100%，但用户总量仅 614 人；而占比 99% 以上的休眠、早期、新用户复购率几乎为 0，绝大多数用户仅完成 1 笔订单就不再活跃，平台完全无法完成新客到复购用户的转化
- 用户价值与生命周期阶段强正相关：成熟用户人均累计消费 336.5 元，是休眠用户的 2 倍，人均下单频次也远超其他群体，用户生命周期价值随阶段提升显著增长
- 平台核心增长隐患：平台超 80% 的用户处于休眠状态，营收高度依赖首购订单，高价值复购用户规模极小，用户生命周期价值挖掘不足，缺乏可持续的老用户营收增长动力




