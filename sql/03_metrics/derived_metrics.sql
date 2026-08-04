/*
Brazil Olist 衍生指标（SQLite）

统一口径：
1. 有效订单为 orders.order_status = 'delivered'。
2. 用户以 customers.customer_unique_id 去重；订单以 orders.order_id 去重。
3. 默认时间字段为 orders.order_purchase_timestamp。
4. 支付先聚合至 order_id；评论先按规则去重至 order_id，避免一对多连接放大。
5. 比率使用浮点除法，分母为 0 时返回 NULL。

本文件包含十个可独立执行的最终 SELECT（D09 分总体与月度两个结果集），
不会创建永久表或修改业务数据。
*/

-- metric: D01
/*
D01 复购用户数与复购率 / Repeat Purchasers and Repeat Purchase Rate
业务定义：观察窗口（本查询为数据库完整观察期）内，至少有 1 笔 delivered
去重订单的用户为购买用户，至少有 2 笔的用户为复购用户。
公式：repeat_purchase_rate = repeat_users / purchasing_users。
时间字段：order_purchase_timestamp；粒度：全观察期汇总。
分子/分母：复购用户数 / 购买用户数；用户按 customer_unique_id 去重，
订单按 order_id 去重。排除空用户、空订单、空购买时间；仅 delivered。
限制：结果受数据观察期截止影响，不代表用户完整生命周期复购率。
*/
WITH user_order_counts AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS delivered_order_count
    FROM orders AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_id IS NOT NULL
      AND o.order_purchase_timestamp IS NOT NULL
      AND c.customer_unique_id IS NOT NULL
    GROUP BY c.customer_unique_id
),
summary AS (
    SELECT
        COUNT(*) AS purchasing_users,
        SUM(CASE WHEN delivered_order_count >= 2 THEN 1 ELSE 0 END) AS repeat_users
    FROM user_order_counts
)
SELECT
    purchasing_users,
    repeat_users,
    1.0 * repeat_users / NULLIF(purchasing_users, 0) AS repeat_purchase_rate
FROM summary;

-- metric: D02
/*
D02 月度 Cohort 留存率 / Monthly Cohort Retention Rate
业务定义：用户历史首笔 delivered 订单自然月为 cohort_month；同一用户每个
活动自然月只计一次，month_number 为活动月与首购月的自然月差。
公式：retention_rate = retained_users / cohort_size。
时间字段：order_purchase_timestamp；粒度：cohort_month × month_number。
分子/分母：相应活动月活跃用户 / cohort 用户；均按 customer_unique_id 去重，
订单按 order_id 去重。排除空用户、订单、购买时间；仅 delivered。
右截尾：使用 delivered 历史的最大购买月份确定观察截止月；为每个 cohort 生成
截至该月的已观察单元（无活跃月份补 0），不生成尚未经历的未来月份，Month 0 为 100%。
限制：截止月若为不完整自然月，其已发生行为仍是观察事实，但未来月份不补零；
首购月始终依据完整 delivered 历史，而不是局部窗口。
*/
WITH RECURSIVE delivered_user_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_purchase_timestamp,
        DATE(o.order_purchase_timestamp, 'start of month') AS activity_month_date
    FROM orders AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_id IS NOT NULL
      AND o.order_purchase_timestamp IS NOT NULL
      AND c.customer_unique_id IS NOT NULL
    GROUP BY c.customer_unique_id, o.order_id, o.order_purchase_timestamp
),
first_purchase AS (
    SELECT
        customer_unique_id,
        DATE(MIN(order_purchase_timestamp), 'start of month') AS cohort_month_date
    FROM delivered_user_orders
    GROUP BY customer_unique_id
),
cohort_sizes AS (
    SELECT
        cohort_month_date,
        COUNT(*) AS cohort_size
    FROM first_purchase
    GROUP BY cohort_month_date
),
monthly_activity AS (
    SELECT
        customer_unique_id,
        activity_month_date
    FROM delivered_user_orders
    GROUP BY customer_unique_id, activity_month_date
),
observation_limit AS (
    SELECT MAX(activity_month_date) AS last_observed_month
    FROM delivered_user_orders
),
cohort_observed_months AS (
    SELECT
        cs.cohort_month_date,
        cs.cohort_month_date AS activity_month_date,
        ol.last_observed_month
    FROM cohort_sizes AS cs
    CROSS JOIN observation_limit AS ol
    WHERE cs.cohort_month_date <= ol.last_observed_month

    UNION ALL

    SELECT
        cohort_month_date,
        DATE(activity_month_date, '+1 month'),
        last_observed_month
    FROM cohort_observed_months
    WHERE activity_month_date < last_observed_month
),
retained AS (
    SELECT
        fp.cohort_month_date,
        ma.activity_month_date,
        COUNT(*) AS retained_users
    FROM monthly_activity AS ma
    INNER JOIN first_purchase AS fp
        ON fp.customer_unique_id = ma.customer_unique_id
    WHERE ma.activity_month_date >= fp.cohort_month_date
    GROUP BY fp.cohort_month_date, ma.activity_month_date
)
SELECT
    STRFTIME('%Y-%m', com.cohort_month_date) AS cohort_month,
    CAST(
        (CAST(STRFTIME('%Y', com.activity_month_date) AS INTEGER)
         - CAST(STRFTIME('%Y', com.cohort_month_date) AS INTEGER)) * 12
        + CAST(STRFTIME('%m', com.activity_month_date) AS INTEGER)
        - CAST(STRFTIME('%m', com.cohort_month_date) AS INTEGER)
        AS INTEGER
    ) AS month_number,
    cs.cohort_size,
    COALESCE(r.retained_users, 0) AS retained_users,
    1.0 * COALESCE(r.retained_users, 0) / NULLIF(cs.cohort_size, 0) AS retention_rate
FROM cohort_observed_months AS com
INNER JOIN cohort_sizes AS cs
    ON cs.cohort_month_date = com.cohort_month_date
LEFT JOIN retained AS r
    ON r.cohort_month_date = com.cohort_month_date
   AND r.activity_month_date = com.activity_month_date
ORDER BY com.cohort_month_date, month_number;

-- metric: D03
/*
D03 观察期历史 LTV / Observed Historical LTV
业务定义：每位用户在观察期内所有 delivered、且订单级有效支付合计大于 0 的
订单收入之和；仅计 payment_value > 0 的有效支付记录。
公式：observed_ltv = total_customer_revenue / paying_users。
时间字段：order_purchase_timestamp；粒度：全观察期汇总。
分子/分母：有效客户收入 / 有效付费购买用户；用户按 customer_unique_id 去重，
支付先按 order_id 聚合。排除空用户、空订单及无正支付订单。
限制：这是数据观察期内已实现的历史 LTV，受右截尾影响，不是预测的完整生命周期价值。
*/
WITH order_payments_agg AS (
    SELECT
        order_id,
        SUM(CASE WHEN payment_value > 0 THEN payment_value ELSE 0 END) AS order_payment_value
    FROM order_payments
    WHERE order_id IS NOT NULL
    GROUP BY order_id
),
valid_user_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        p.order_payment_value
    FROM orders AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    INNER JOIN order_payments_agg AS p
        ON p.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_id IS NOT NULL
      AND o.order_purchase_timestamp IS NOT NULL
      AND c.customer_unique_id IS NOT NULL
      AND p.order_payment_value > 0
),
summary AS (
    SELECT
        COUNT(DISTINCT customer_unique_id) AS paying_users,
        SUM(order_payment_value) AS total_customer_revenue
    FROM valid_user_orders
)
SELECT
    paying_users,
    total_customer_revenue,
    1.0 * total_customer_revenue / NULLIF(paying_users, 0) AS observed_ltv
FROM summary;

-- metric: D04
/*
D04 平均购买频次 / Average Purchase Frequency
业务定义：观察期内 delivered 去重订单数除以至少购买一次的去重用户数。
公式：average_purchase_frequency = delivered_orders / purchasing_users。
时间字段：order_purchase_timestamp；粒度：全观察期汇总。
分子/分母：delivered 订单 / 购买用户；order_id、customer_unique_id 分别去重。
排除空订单、空用户、空购买时间；仅 delivered。分母为 0 返回 NULL。
限制：观察期频次，不代表年化频次或完整生命周期频次。
*/
WITH valid_orders AS (
    SELECT
        o.order_id,
        c.customer_unique_id
    FROM orders AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_id IS NOT NULL
      AND o.order_purchase_timestamp IS NOT NULL
      AND c.customer_unique_id IS NOT NULL
    GROUP BY o.order_id, c.customer_unique_id
),
summary AS (
    SELECT
        COUNT(*) AS delivered_orders,
        COUNT(DISTINCT customer_unique_id) AS purchasing_users
    FROM valid_orders
)
SELECT
    delivered_orders,
    purchasing_users,
    1.0 * delivered_orders / NULLIF(purchasing_users, 0) AS average_purchase_frequency
FROM summary;

-- metric: D05
/*
D05 平均复购间隔 / Average Repurchase Interval
业务定义：按用户和购买时间排列 delivered 去重订单，以 LAG 计算相邻间隔；
先求每位有有效复购间隔用户的平均值，再对用户等权平均。
公式：average_repurchase_interval_days = AVG(用户平均相邻购买间隔天数)。
时间字段：order_purchase_timestamp；粒度：全观察期汇总。
分子/分母：用户平均间隔之和 / 有有效间隔复购用户数；同时输出有效相邻区间数。
按 order_id 去重、用户按 customer_unique_id；排除首单 NULL 间隔及负间隔，保留 0。
限制：右截尾会低估尚未发生的未来复购；等权用户口径不按间隔数加权。
*/
WITH valid_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_purchase_timestamp
    FROM orders AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_id IS NOT NULL
      AND o.order_purchase_timestamp IS NOT NULL
      AND c.customer_unique_id IS NOT NULL
    GROUP BY c.customer_unique_id, o.order_id, o.order_purchase_timestamp
),
sequenced AS (
    SELECT
        customer_unique_id,
        order_id,
        order_purchase_timestamp,
        LAG(order_purchase_timestamp) OVER (
            PARTITION BY customer_unique_id
            ORDER BY order_purchase_timestamp, order_id
        ) AS previous_purchase_timestamp
    FROM valid_orders
),
valid_intervals AS (
    SELECT
        customer_unique_id,
        JULIANDAY(order_purchase_timestamp) - JULIANDAY(previous_purchase_timestamp) AS interval_days
    FROM sequenced
    WHERE previous_purchase_timestamp IS NOT NULL
      AND JULIANDAY(order_purchase_timestamp) - JULIANDAY(previous_purchase_timestamp) >= 0
),
per_user AS (
    SELECT
        customer_unique_id,
        COUNT(*) AS interval_count,
        AVG(interval_days) AS user_average_interval_days
    FROM valid_intervals
    GROUP BY customer_unique_id
)
SELECT
    COUNT(*) AS repeat_users_with_valid_interval,
    COALESCE(SUM(interval_count), 0) AS valid_repeat_intervals,
    AVG(user_average_interval_days) AS average_repurchase_interval_days
FROM per_user;

-- metric: D06
/*
D06 平均配送时长 / Average Delivery Duration
业务定义：delivered 订单从下单到实际签收的天数。
公式：delivery_days = JULIANDAY(delivered_customer_date) - JULIANDAY(purchase_timestamp)。
时间字段：order_purchase_timestamp（归属）及 order_delivered_customer_date；粒度：全期汇总。
分子/分母：合法配送天数总和 / 合法配送订单数；订单按 order_id 去重。
两个时间非空且可解析，排除负时长，合法长尾保留；并统计超过 60/90/180 天订单。
限制：只反映已签收订单，未签收及进行中订单不进入分母。
*/
WITH valid_deliveries AS (
    SELECT
        order_id,
        JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp) AS delivery_days
    FROM orders
    WHERE order_status = 'delivered'
      AND order_id IS NOT NULL
      AND order_purchase_timestamp IS NOT NULL
      AND order_delivered_customer_date IS NOT NULL
      AND JULIANDAY(order_purchase_timestamp) IS NOT NULL
      AND JULIANDAY(order_delivered_customer_date) IS NOT NULL
      AND JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp) >= 0
    GROUP BY order_id, order_purchase_timestamp, order_delivered_customer_date
)
SELECT
    COUNT(*) AS valid_delivery_orders,
    AVG(delivery_days) AS average_delivery_days,
    SUM(CASE WHEN delivery_days > 60 THEN 1 ELSE 0 END) AS orders_over_60_days,
    SUM(CASE WHEN delivery_days > 90 THEN 1 ELSE 0 END) AS orders_over_90_days,
    SUM(CASE WHEN delivery_days > 180 THEN 1 ELSE 0 END) AS orders_over_180_days
FROM valid_deliveries;

-- metric: D07
/*
D07 延迟送达率 / Delayed Delivery Rate
业务定义：delivered 且实际签收、预计签收均有效，实际签收晚于预计签收为延迟。
公式：delayed_delivery_rate = delayed_orders / evaluable_orders。
时间字段：order_purchase_timestamp（归属）、实际及预计签收时间；粒度：全期汇总。
分子/分母：延迟订单 / 可评估订单；order_id 去重。
排除空/不可解析时间以及实际签收早于下单的异常；分母为 0 返回 NULL。
限制：仅与采用完全相同分母的准时送达率互为补集。
*/
WITH evaluable AS (
    SELECT
        order_id,
        order_delivered_customer_date,
        order_estimated_delivery_date
    FROM orders
    WHERE order_status = 'delivered'
      AND order_id IS NOT NULL
      AND order_purchase_timestamp IS NOT NULL
      AND order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
      AND JULIANDAY(order_purchase_timestamp) IS NOT NULL
      AND JULIANDAY(order_delivered_customer_date) IS NOT NULL
      AND JULIANDAY(order_estimated_delivery_date) IS NOT NULL
      AND JULIANDAY(order_delivered_customer_date) >= JULIANDAY(order_purchase_timestamp)
    GROUP BY order_id, order_delivered_customer_date, order_estimated_delivery_date
),
summary AS (
    SELECT
        COUNT(*) AS evaluable_orders,
        SUM(CASE
                WHEN JULIANDAY(order_delivered_customer_date) > JULIANDAY(order_estimated_delivery_date)
                THEN 1 ELSE 0
            END) AS delayed_orders
    FROM evaluable
)
SELECT
    evaluable_orders,
    delayed_orders,
    1.0 * delayed_orders / NULLIF(evaluable_orders, 0) AS delayed_delivery_rate
FROM summary;

-- metric: D08
/*
D08 好评率 / Positive Review Rate
业务定义：delivered 订单的代表评论中，review_score >= 4 为好评。
代表评论按 review_answer_timestamp、review_creation_date、review_id 依次降序选取。
公式：positive_review_rate = positive_review_orders / reviewed_orders。
时间字段：order_purchase_timestamp；粒度：全期订单汇总。
分子/分母：好评订单 / 有 1–5 分有效代表评分订单；order_id 去重。
先去重评论，再排除无评论、空分及范围外评分；分母为 0 返回 NULL。
限制：只描述已评论订单，不能解释为全部 delivered 订单满意率。
*/
WITH ranked_reviews AS (
    SELECT
        review_id,
        order_id,
        review_score,
        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY review_answer_timestamp DESC,
                     review_creation_date DESC,
                     review_id DESC
        ) AS review_rank
    FROM order_reviews
    WHERE order_id IS NOT NULL
),
representative_reviews AS (
    SELECT
        order_id,
        review_score
    FROM ranked_reviews
    WHERE review_rank = 1
),
reviewed AS (
    SELECT
        o.order_id,
        r.review_score
    FROM orders AS o
    INNER JOIN representative_reviews AS r
        ON r.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_id IS NOT NULL
      AND o.order_purchase_timestamp IS NOT NULL
      AND r.review_score BETWEEN 1 AND 5
),
summary AS (
    SELECT
        COUNT(*) AS reviewed_orders,
        SUM(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END) AS positive_review_orders
    FROM reviewed
)
SELECT
    reviewed_orders,
    positive_review_orders,
    1.0 * positive_review_orders / NULLIF(reviewed_orders, 0) AS positive_review_rate
FROM summary;

-- metric: D09_OVERALL
/*
D09 取消率（总体）/ Cancellation Rate (Overall)
业务定义：全部状态去重订单中 order_status = 'canceled' 的占比（不是 cancelled）。
公式：cancellation_rate = canceled_orders / total_orders。
时间字段：总体指标覆盖完整订单历史；粒度：全期汇总。
分子/分母：canceled 去重订单 / 全部状态去重订单；按 order_id 去重。
总体仅排除空 order_id；状态空值仍属于全部订单但不属于 canceled。分母为 0 返回 NULL。
限制：总体口径与月度口径的时间非空筛选不同，比较汇总时须使用相同有效范围。
*/
WITH unique_orders AS (
    SELECT
        order_id,
        MAX(CASE WHEN order_status = 'canceled' THEN 1 ELSE 0 END) AS is_canceled
    FROM orders
    WHERE order_id IS NOT NULL
    GROUP BY order_id
),
summary AS (
    SELECT
        COUNT(*) AS total_orders,
        SUM(is_canceled) AS canceled_orders
    FROM unique_orders
)
SELECT
    total_orders,
    canceled_orders,
    1.0 * canceled_orders / NULLIF(total_orders, 0) AS cancellation_rate
FROM summary;

-- metric: D09_MONTHLY
/*
D09 取消率（月度）/ Cancellation Rate (Monthly)
业务定义及公式同总体，按购买自然月 YYYY-MM 输出。
时间字段：order_purchase_timestamp；粒度：order_month。
分子/分母：当月 canceled 去重订单 / 当月全部状态去重订单；order_id 去重。
排除空 order_id 或空/不可解析购买时间；分母为 0 返回 NULL。
限制：右端 2018-09/10 为不完整尾期，月率应结合订单量谨慎解释。
*/
WITH unique_monthly_orders AS (
    SELECT
        STRFTIME('%Y-%m', order_purchase_timestamp) AS order_month,
        order_id,
        MAX(CASE WHEN order_status = 'canceled' THEN 1 ELSE 0 END) AS is_canceled
    FROM orders
    WHERE order_id IS NOT NULL
      AND order_purchase_timestamp IS NOT NULL
      AND STRFTIME('%Y-%m', order_purchase_timestamp) IS NOT NULL
    GROUP BY order_month, order_id
),
monthly_summary AS (
    SELECT
        order_month,
        COUNT(*) AS total_orders,
        SUM(is_canceled) AS canceled_orders
    FROM unique_monthly_orders
    GROUP BY order_month
)
SELECT
    order_month,
    total_orders,
    canceled_orders,
    1.0 * canceled_orders / NULLIF(total_orders, 0) AS cancellation_rate
FROM monthly_summary
ORDER BY order_month;
