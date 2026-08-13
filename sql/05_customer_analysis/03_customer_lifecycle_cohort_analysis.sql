------ Cohort留存与用户生命周期分析 ------

--- 1.部分三识别每位用户的：
   -- 首次购买日期；
   --首次购买月份；
   -- 最近购买日期；
   -- 累计有效订单数；
   -- 累计GMV；
   -- 用户生命周期长度
-- 两张产出如下，后续的2-5分析均根据这两张表展开： 
-- outputs/data/03_customer_analysis/customer_profile.csv
-- outputs/data/03_customer_analysis/customer_order_base.csv

--- 2.建立月度Cohort：
   -- 首购月份；
   -- 后续活跃月份；
   -- Cohort Month；
   -- 初始用户数；
   -- 各月活跃用户数；
   -- 各月留存率；
   -- 不同首购月份的留存差异。
-- 输出 outputs/data/03_customer_analysis/cohort_monthly_retention.csv
-- 此表用于后续的heatmap分析，制作visualizations/customer/cohort_retention_heatmap_log.png
WITH order_month AS (
SELECT
customer_unique_id,
substr(purchase_date,1,7) AS purchase_month
FROM customer_order_base
WHERE is_paid_order=1
),
user_first_month AS (
SELECT
customer_unique_id,
MIN(purchase_month) AS cohort_month
FROM order_month
GROUP BY customer_unique_id
),
cohort_data AS (
SELECT
f.customer_unique_id,
f.cohort_month,
o.purchase_month AS active_month
FROM user_first_month f
JOIN order_month o
ON f.customer_unique_id=o.customer_unique_id
),
cohort_count AS (
SELECT
cohort_month,
active_month,
COUNT(DISTINCT customer_unique_id) AS active_users
FROM cohort_data
GROUP BY cohort_month,active_month
),
cohort_size AS (
SELECT
cohort_month,
COUNT(*) AS initial_users
FROM user_first_month
GROUP BY cohort_month
)
SELECT
c.cohort_month,
c.active_month,
(
CAST(substr(c.active_month,1,4) AS INTEGER)-CAST(substr(c.cohort_month,1,4) AS INTEGER)
)*12+
(
CAST(substr(c.active_month,6,2) AS INTEGER)-CAST(substr(c.cohort_month,6,2) AS INTEGER)
) AS cohort_index,
s.initial_users,
c.active_users,
ROUND(
CAST(c.active_users AS FLOAT)/s.initial_users,
4
) AS retention_rate
FROM cohort_count c
JOIN cohort_size s
ON c.cohort_month=s.cohort_month
ORDER BY c.cohort_month,c.active_month;

--- 3. 计算短期复购留存：
   -- 7日内再次购买比例；
   -- 30日内再次购买比例；
   -- 90日内再次购买比例；
   -- 完整观察窗口用户数；
   -- 因观察窗口不足而排除的用户数。
-- 复购定义：在同一统计窗口内，拥有至少2笔去重有效订单的唯一用户，且只看每个用户第一次购买后的第一次复购时间（第二笔订单），若有多笔复购，则只根据第一次的复购记录来计算比例
-- 7/30/90 日短期留存定义：
-- 起点为用户第一笔有效订单的购买时间。
-- 短期留存定义：只看第一笔订单之后的第一次复购，也就是第二笔订单。
-- 同一用户 `customer_unique_id` 若在区间内有多笔订单，则只考虑第一笔订单与第二笔订单作为衡量短期留存率标准。
-- 第三笔及之后的订单不参与 7/30/90 日复购判断。
-- 复购时间按实际时间差计算，即按照 24 小时计算，而不是自然日或自然月。
-- N 日留存用户：首购后 `> 0` 且 `<= N × 24 小时` 内至少再次产生 1 笔有效订单的用户。
-- N 日留存率：`N 日内再次购买用户数 / 具备完整 N 日观察窗口的首购用户数`。
-- 完整观察窗口要求首购时间不晚于观察截止日减 N 日；窗口不足用户必须排除，并同时报告纳入人数和排除人数。
-- 指标之间的关系 7 日复购用户 ⊆ 30 日复购用户 ⊆ 90 日复购用户。
-- 7/30/90 日留存不得与自然月 Cohort 留存混称。
-- 输出 outputs/data/03_customer_analysis/short_term_repeat_retention.csv
WITH t AS (
    SELECT
        customer_unique_id,
        datetime(order_purchase_timestamp) AS order_time,
        ROW_NUMBER() OVER(
            PARTITION BY customer_unique_id
            ORDER BY datetime(order_purchase_timestamp)
        ) AS rn
    FROM customer_order_base
    WHERE is_paid_order = 1
),
r AS (
    SELECT
        customer_unique_id,
        MAX(CASE WHEN rn = 1 THEN order_time END) AS first_time,
        MAX(CASE WHEN rn = 2 THEN order_time END) AS second_time
    FROM t
    GROUP BY customer_unique_id
),
x AS (
    SELECT
        customer_unique_id,
        first_time,
        second_time,
        (
            julianday(second_time) - julianday(first_time)
        ) AS days_to_repeat
    FROM r
),
e AS (
    SELECT
        datetime('2018-07-31 23:59:59') AS end_date
)
SELECT
    COUNT(*) AS total_users,
    SUM(
        CASE
            WHEN julianday(e.end_date) - julianday(first_time) >= 7
            THEN 1
            ELSE 0
        END
    ) AS obs_7d,
    SUM(
        CASE
            WHEN days_to_repeat > 0
             AND days_to_repeat <= 7
            THEN 1
            ELSE 0
        END
    ) AS repeat_7d,
    ROUND(
        CAST(
            SUM(
                CASE
                    WHEN days_to_repeat > 0
                     AND days_to_repeat <= 7
                    THEN 1
                    ELSE 0
                END
            ) AS FLOAT
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN julianday(e.end_date) - julianday(first_time) >= 7
                    THEN 1
                    ELSE 0
                END
            ),
            0
        ),
        4
    ) AS repeat_rate_7d,
    SUM(
        CASE
            WHEN julianday(e.end_date) - julianday(first_time) >= 30
            THEN 1
            ELSE 0
        END
    ) AS obs_30d,
    SUM(
        CASE
            WHEN days_to_repeat > 0
             AND days_to_repeat <= 30
            THEN 1
            ELSE 0
        END
    ) AS repeat_30d,
    ROUND(
        CAST(
            SUM(
                CASE
                    WHEN days_to_repeat > 0
                     AND days_to_repeat <= 30
                    THEN 1
                    ELSE 0
                END
            ) AS FLOAT
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN julianday(e.end_date) - julianday(first_time) >= 30
                    THEN 1
                    ELSE 0
                END
            ),
            0
        ),
        4
    ) AS repeat_rate_30d,
    SUM(
        CASE
            WHEN julianday(e.end_date) - julianday(first_time) >= 90
            THEN 1
            ELSE 0
        END
    ) AS obs_90d,
    SUM(
        CASE
            WHEN days_to_repeat > 0
             AND days_to_repeat <= 90
            THEN 1
            ELSE 0
        END
    ) AS repeat_90d,
    ROUND(
        CAST(
            SUM(
                CASE
                    WHEN days_to_repeat > 0
                     AND days_to_repeat <= 90
                    THEN 1
                    ELSE 0
                END
            ) AS FLOAT
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN julianday(e.end_date) - julianday(first_time) >= 90
                    THEN 1
                    ELSE 0
                END
            ),
            0
        ),
        4
    ) AS repeat_rate_90d
FROM x
CROSS JOIN e;

-- 三个时间窗口
SELECT
    '7d' AS window,
    '2018-07-31 23:59:59' AS observation_end,
    datetime('2018-07-31 23:59:59', '-7 days') AS latest_eligible_first_purchase,
    7 AS window_days
UNION ALL
SELECT
    '30d' AS window,
    '2018-07-31 23:59:59' AS observation_end,
    datetime('2018-07-31 23:59:59', '-30 days') AS latest_eligible_first_purchase,
    30 AS window_days
UNION ALL
SELECT
    '90d' AS window,
    '2018-07-31 23:59:59' AS observation_end,
    datetime('2018-07-31 23:59:59', '-90 days') AS latest_eligible_first_purchase,
    90 AS window_days;

   
--- 4. 建立生命周期阶段
   -- 首购用户；
   -- 早期用户；
   -- 成长用户；
   -- 成熟用户；
   -- 沉默用户。
-- 生命周期长度与阶段定义：
-- 用户生命周期长度：截止日前最近一笔有效订单日期减首次有效订单日期，单位为天；单次购买用户为 0 天。
-- 使用以下互斥顺序：
-- 沉默用户：recency_days > 90；
-- 首购用户：未沉默、有效订单数为 1，且 recency_days <= 30；
-- 早期用户：未沉默、有效订单数为 1，且 30 < recency_days <= 90；
-- 成长用户：未沉默、有效订单数不少于 2，且生命周期长度 <= 180 天；
-- 成熟用户：未沉默、有效订单数不少于 2，且生命周期长度 > 180 天。
-- 上述顺序先判断沉默，再判断订单数和生命周期，保证每位用户只进入一类。首次正式使用前必须在 SQL 中实现并完成互斥、完整性验证。
-- 输出 outputs/data/03_customer_analysis/customer_lifecycle_segment.csv
WITH data_end AS (
    SELECT
        MAX(datetime(last_purchase_timestamp)) AS cutoff_date
    FROM customer_profile
),
base AS (
    SELECT
        c.customer_unique_id,
        c.valid_order_count,
        c.customer_lifecycle_days,
        julianday(d.cutoff_date)
        -
        julianday(c.last_purchase_timestamp)
        AS recency_days
    FROM customer_profile c
    CROSS JOIN data_end d
)
SELECT
    customer_unique_id,
    CASE
        WHEN recency_days > 90
        THEN 'Dormant Customer'
        WHEN recency_days <= 30
             AND valid_order_count = 1
        THEN 'New Customer'
        WHEN recency_days > 30
             AND recency_days <= 90
             AND valid_order_count = 1
        THEN 'Early Customer'
        WHEN valid_order_count >= 2
             AND customer_lifecycle_days <= 180
        THEN 'Growing Customer'
        WHEN valid_order_count >= 2
             AND customer_lifecycle_days > 180
        THEN 'Mature Customer'
        ELSE 'Unclassified'
    END AS lifecycle_stage,
    valid_order_count,
    customer_lifecycle_days,
    recency_days
FROM base;
   
--- 5. 对比各生命周期阶段的：
   -- 用户数及占比；
   -- 订单数；
   -- GMV；
   -- 人均消费；
   -- 客单价；
   -- 平均购买频次；
   -- 复购用户数；
   -- 复购率；
   -- 平均生命周期长度；
   -- 平均最近消费间隔。
--根据：outputs/data/03_customer_analysis/customer_profile.csv
--     outputs/data/03_customer_analysis/customer_lifecycle_segment.csv
--输出：outputs/data/03_customer_analysis/lifecycle_stage_comparison.csv
WITH lifecycle_base AS (
SELECT
    s.lifecycle_stage,
    c.customer_unique_id,
    c.valid_order_count,
    c.lifetime_gmv,
    c.average_order_value,
    c.customer_lifecycle_days,
    julianday(
        '2018-09-03'
    ) - julianday(c.last_purchase_timestamp) AS recency_days
FROM customer_profile c
JOIN customer_lifecycle_segment s
ON c.customer_unique_id = s.customer_unique_id
),
total AS (
SELECT COUNT(*) AS total_users
FROM lifecycle_base
)
SELECT
lifecycle_stage,
COUNT(customer_unique_id) AS user_count,
ROUND(
    COUNT(customer_unique_id)*1.0/
    (SELECT total_users FROM total),
    4
) AS user_percentage,
SUM(valid_order_count) AS order_count,
ROUND(
    SUM(lifetime_gmv),
    2
) AS gmv,
ROUND(
    AVG(lifetime_gmv),
    2
) AS avg_customer_spend,
ROUND(
    SUM(lifetime_gmv)/
    SUM(valid_order_count),
    2
) AS avg_order_value,
ROUND(
    AVG(valid_order_count),
    2
) AS avg_purchase_frequency,
SUM(
    CASE 
    WHEN valid_order_count>=2 
    THEN 1 ELSE 0 
    END
) AS repeat_users,
ROUND(
    SUM(
        CASE 
        WHEN valid_order_count>=2 
        THEN 1 ELSE 0 
        END
    )*1.0/
    COUNT(customer_unique_id),
    4
) AS repeat_rate,
ROUND(
    AVG(customer_lifecycle_days),
    2
) AS avg_lifecycle_days,
ROUND(
    AVG(recency_days),
    2
) AS avg_recency_days
FROM lifecycle_base
GROUP BY lifecycle_stage;  
