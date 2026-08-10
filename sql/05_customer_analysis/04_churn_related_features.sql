-- ============================================================
-- Stage 3 - Member 3
-- Churn Related Features Analysis
-- ============================================================
-- Unified standard:
--   docs/unified_analysis_standards.md
--
-- Observation cutoff:
--   order_purchase_timestamp < 2018-08-01 00:00:00
--
-- User:
--   customer_unique_id
--
-- Churn:
--   recency_days > 90 as of 2018-07-31
--
-- Important:
--   Results describe associations / structural differences.
--   They must NOT be interpreted as causal effects.
-- ============================================================


-- ============================================================
-- 1. PRIMARY PAYMENT TYPE × CHURN
-- ============================================================
-- Rules:
--   1. Positive payment only.
--   2. Aggregate to order_id + payment_type first.
--   3. Primary payment type = largest aggregated amount.
--   4. Tie-break: payment_type ASC.
-- ============================================================

WITH observation_orders AS (
    SELECT
        customer_unique_id,
        order_id,
        order_purchase_timestamp
    FROM customer_order_base
    WHERE DATETIME(order_purchase_timestamp) IS NOT NULL
      AND DATETIME(order_purchase_timestamp)
          < DATETIME('2018-08-01 00:00:00')
),

user_churn AS (
    SELECT
        customer_unique_id,

        CASE
            WHEN CAST(
                JULIANDAY(DATE('2018-07-31'))
                - JULIANDAY(
                    DATE(MAX(order_purchase_timestamp))
                )
                AS INTEGER
            ) > 90
            THEN 1
            ELSE 0
        END AS churn_flag

    FROM observation_orders
    GROUP BY customer_unique_id
),

payment_by_type AS (
    SELECT
        p.order_id,
        p.payment_type,
        SUM(p.payment_value) AS payment_type_amount

    FROM vw_order_payments_clean AS p

    INNER JOIN observation_orders AS o
        ON p.order_id = o.order_id

    WHERE p.payment_value IS NOT NULL
      AND p.payment_value > 0

    GROUP BY
        p.order_id,
        p.payment_type
),

payment_ranked AS (
    SELECT
        order_id,
        payment_type,
        payment_type_amount,

        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY
                payment_type_amount DESC,
                payment_type ASC
        ) AS payment_rank

    FROM payment_by_type
),

primary_payment AS (
    SELECT
        order_id,
        payment_type AS primary_payment_type

    FROM payment_ranked

    WHERE payment_rank = 1
),

group_totals AS (
    SELECT
        uc.churn_flag,
        COUNT(*) AS paid_order_count

    FROM observation_orders AS o

    INNER JOIN primary_payment AS p
        ON o.order_id = p.order_id

    INNER JOIN user_churn AS uc
        ON o.customer_unique_id
         = uc.customer_unique_id

    GROUP BY uc.churn_flag
)

SELECT
    CASE
        WHEN uc.churn_flag = 1
        THEN 'Churned'
        ELSE 'Non-churned'
    END AS churn_status,

    p.primary_payment_type,

    COUNT(*) AS order_count,

    ROUND(
        100.0 * COUNT(*)
        / NULLIF(g.paid_order_count, 0),
        2
    ) AS order_share_pct,

    COUNT(DISTINCT o.customer_unique_id)
        AS users_using_payment_type

FROM observation_orders AS o

INNER JOIN primary_payment AS p
    ON o.order_id = p.order_id

INNER JOIN user_churn AS uc
    ON o.customer_unique_id
     = uc.customer_unique_id

INNER JOIN group_totals AS g
    ON uc.churn_flag = g.churn_flag

GROUP BY
    uc.churn_flag,
    p.primary_payment_type,
    g.paid_order_count

ORDER BY
    uc.churn_flag DESC,
    order_count DESC,
    p.primary_payment_type ASC;



-- ============================================================
-- 2. STATE × CHURN
-- ============================================================
-- User-level representative geography:
--   latest delivered order before cutoff.
--
-- Tie-break:
--   purchase timestamp DESC
--   order_id DESC
--   customer_id DESC
-- ============================================================

WITH observation_orders AS (
    SELECT
        customer_unique_id,
        customer_id,
        order_id,
        order_purchase_timestamp,
        customer_state,
        customer_city

    FROM customer_order_base

    WHERE DATETIME(order_purchase_timestamp) IS NOT NULL
      AND DATETIME(order_purchase_timestamp)
          < DATETIME('2018-08-01 00:00:00')
),

user_churn AS (
    SELECT
        customer_unique_id,

        CASE
            WHEN CAST(
                JULIANDAY(DATE('2018-07-31'))
                - JULIANDAY(
                    DATE(MAX(order_purchase_timestamp))
                )
                AS INTEGER
            ) > 90
            THEN 1
            ELSE 0
        END AS churn_flag

    FROM observation_orders

    GROUP BY customer_unique_id
),

geo_ranked AS (
    SELECT
        customer_unique_id,
        customer_state,
        customer_city,

        ROW_NUMBER() OVER (
            PARTITION BY customer_unique_id
            ORDER BY
                DATETIME(order_purchase_timestamp) DESC,
                order_id DESC,
                customer_id DESC
        ) AS geo_rank

    FROM observation_orders
),

user_geo AS (
    SELECT
        customer_unique_id,
        customer_state,
        customer_city

    FROM geo_ranked

    WHERE geo_rank = 1
),

user_base AS (
    SELECT
        uc.customer_unique_id,
        uc.churn_flag,
        ug.customer_state,
        ug.customer_city

    FROM user_churn AS uc

    INNER JOIN user_geo AS ug
        ON uc.customer_unique_id
         = ug.customer_unique_id
),

overall AS (
    SELECT
        COUNT(*) AS total_users,

        100.0 * SUM(churn_flag)
        / NULLIF(COUNT(*), 0)
            AS overall_churn_rate

    FROM user_base
)

SELECT
    b.customer_state,

    COUNT(*) AS user_count,

    SUM(b.churn_flag)
        AS churned_users,

    COUNT(*) - SUM(b.churn_flag)
        AS non_churned_users,

    ROUND(
        100.0 * SUM(b.churn_flag)
        / NULLIF(COUNT(*), 0),
        2
    ) AS churn_rate_pct,

    ROUND(
        100.0 * COUNT(*)
        / NULLIF(o.total_users, 0),
        2
    ) AS user_share_pct,

    ROUND(
        (
            100.0 * SUM(b.churn_flag)
            / NULLIF(COUNT(*), 0)
        )
        - o.overall_churn_rate,
        2
    ) AS churn_rate_vs_overall_pct_point

FROM user_base AS b

CROSS JOIN overall AS o

GROUP BY
    b.customer_state,
    o.total_users,
    o.overall_churn_rate

ORDER BY
    user_count DESC,
    b.customer_state ASC;



-- ============================================================
-- 3. CITY + STATE × CHURN
-- ============================================================
-- City must always be combined with state.
-- Output only Top 30 cities by user scale for interpretation.
-- ============================================================

WITH observation_orders AS (
    SELECT
        customer_unique_id,
        customer_id,
        order_id,
        order_purchase_timestamp,
        customer_state,
        customer_city

    FROM customer_order_base

    WHERE DATETIME(order_purchase_timestamp) IS NOT NULL
      AND DATETIME(order_purchase_timestamp)
          < DATETIME('2018-08-01 00:00:00')
),

user_churn AS (
    SELECT
        customer_unique_id,

        CASE
            WHEN CAST(
                JULIANDAY(DATE('2018-07-31'))
                - JULIANDAY(
                    DATE(MAX(order_purchase_timestamp))
                )
                AS INTEGER
            ) > 90
            THEN 1
            ELSE 0
        END AS churn_flag

    FROM observation_orders

    GROUP BY customer_unique_id
),

geo_ranked AS (
    SELECT
        customer_unique_id,
        customer_state,
        customer_city,

        ROW_NUMBER() OVER (
            PARTITION BY customer_unique_id
            ORDER BY
                DATETIME(order_purchase_timestamp) DESC,
                order_id DESC,
                customer_id DESC
        ) AS geo_rank

    FROM observation_orders
),

user_geo AS (
    SELECT
        customer_unique_id,

        customer_city || ' | ' || customer_state
            AS city_state

    FROM geo_ranked

    WHERE geo_rank = 1
),

user_base AS (
    SELECT
        uc.customer_unique_id,
        uc.churn_flag,
        ug.city_state

    FROM user_churn AS uc

    INNER JOIN user_geo AS ug
        ON uc.customer_unique_id
         = ug.customer_unique_id
),

overall AS (
    SELECT
        COUNT(*) AS total_users,

        100.0 * SUM(churn_flag)
        / NULLIF(COUNT(*), 0)
            AS overall_churn_rate

    FROM user_base
)

SELECT
    b.city_state,

    COUNT(*) AS user_count,

    SUM(b.churn_flag)
        AS churned_users,

    COUNT(*) - SUM(b.churn_flag)
        AS non_churned_users,

    ROUND(
        100.0 * SUM(b.churn_flag)
        / NULLIF(COUNT(*), 0),
        2
    ) AS churn_rate_pct,

    ROUND(
        100.0 * COUNT(*)
        / NULLIF(o.total_users, 0),
        2
    ) AS user_share_pct,

    ROUND(
        (
            100.0 * SUM(b.churn_flag)
            / NULLIF(COUNT(*), 0)
        )
        - o.overall_churn_rate,
        2
    ) AS churn_rate_vs_overall_pct_point

FROM user_base AS b

CROSS JOIN overall AS o

GROUP BY
    b.city_state,
    o.total_users,
    o.overall_churn_rate

ORDER BY
    user_count DESC,
    b.city_state ASC

LIMIT 30;



-- ============================================================
-- 4. WEEKDAY / WEEKEND × CHURN
-- ============================================================
-- Monday-Friday = Weekday
-- Saturday-Sunday = Weekend
--
-- Calendar denominator includes zero-order dates.
-- ============================================================

WITH RECURSIVE

params AS (
    SELECT
        DATE('2016-09-15') AS start_date,
        DATE('2018-07-31') AS end_date
),

calendar(date_value) AS (
    SELECT start_date
    FROM params

    UNION ALL

    SELECT DATE(date_value, '+1 day')

    FROM calendar, params

    WHERE date_value < end_date
),

calendar_days AS (
    SELECT
        CASE
            WHEN CAST(
                STRFTIME('%w', date_value)
                AS INTEGER
            ) BETWEEN 1 AND 5
            THEN 'Weekday'
            ELSE 'Weekend'
        END AS day_type,

        COUNT(*) AS calendar_day_count

    FROM calendar

    GROUP BY day_type
),

observation_orders AS (
    SELECT
        customer_unique_id,
        order_id,
        order_purchase_timestamp,
        order_gmv,
        is_paid_order,

        CASE
            WHEN CAST(
                STRFTIME(
                    '%w',
                    order_purchase_timestamp
                )
                AS INTEGER
            ) BETWEEN 1 AND 5
            THEN 'Weekday'
            ELSE 'Weekend'
        END AS day_type

    FROM customer_order_base

    WHERE DATETIME(order_purchase_timestamp) IS NOT NULL
      AND DATETIME(order_purchase_timestamp)
          < DATETIME('2018-08-01 00:00:00')
),

user_churn AS (
    SELECT
        customer_unique_id,

        CASE
            WHEN CAST(
                JULIANDAY(DATE('2018-07-31'))
                - JULIANDAY(
                    DATE(MAX(order_purchase_timestamp))
                )
                AS INTEGER
            ) > 90
            THEN 1
            ELSE 0
        END AS churn_flag

    FROM observation_orders

    GROUP BY customer_unique_id
),

group_totals AS (
    SELECT
        uc.churn_flag,
        COUNT(*) AS total_orders

    FROM observation_orders AS o

    INNER JOIN user_churn AS uc
        ON o.customer_unique_id
         = uc.customer_unique_id

    GROUP BY uc.churn_flag
)

SELECT
    CASE
        WHEN uc.churn_flag = 1
        THEN 'Churned'
        ELSE 'Non-churned'
    END AS churn_status,

    o.day_type,

    cd.calendar_day_count,

    COUNT(*) AS order_count,

    ROUND(
        COUNT(*) * 1.0
        / NULLIF(cd.calendar_day_count, 0),
        2
    ) AS orders_per_calendar_day,

    ROUND(
        100.0 * COUNT(*)
        / NULLIF(gt.total_orders, 0),
        2
    ) AS order_share_pct,

    COUNT(DISTINCT o.customer_unique_id)
        AS users_with_orders,

    SUM(o.is_paid_order)
        AS paid_order_count,

    ROUND(
        SUM(o.order_gmv),
        2
    ) AS gmv,

    ROUND(
        SUM(o.order_gmv) * 1.0
        / NULLIF(SUM(o.is_paid_order), 0),
        2
    ) AS average_order_value

FROM observation_orders AS o

INNER JOIN user_churn AS uc
    ON o.customer_unique_id
     = uc.customer_unique_id

INNER JOIN calendar_days AS cd
    ON o.day_type = cd.day_type

INNER JOIN group_totals AS gt
    ON uc.churn_flag = gt.churn_flag

GROUP BY
    uc.churn_flag,
    o.day_type,
    cd.calendar_day_count,
    gt.total_orders

ORDER BY
    uc.churn_flag DESC,
    o.day_type ASC;



-- ============================================================
-- 5. FIRST PURCHASE MONTH × CHURN
-- ============================================================
-- WARNING:
-- Newer cohorts have insufficient opportunity to satisfy
-- recency_days > 90.
--
-- users_with_full_90d_opportunity indicates whether the
-- cohort had enough time to potentially satisfy churn rule.
-- ============================================================

WITH observation_orders AS (
    SELECT
        customer_unique_id,
        order_id,
        order_purchase_timestamp

    FROM customer_order_base

    WHERE DATETIME(order_purchase_timestamp) IS NOT NULL
      AND DATETIME(order_purchase_timestamp)
          < DATETIME('2018-08-01 00:00:00')
),

user_base AS (
    SELECT
        customer_unique_id,

        MIN(order_purchase_timestamp)
            AS first_purchase_timestamp,

        MAX(order_purchase_timestamp)
            AS last_purchase_timestamp,

        STRFTIME(
            '%Y-%m',
            MIN(order_purchase_timestamp)
        ) AS first_purchase_month,

        CAST(
            JULIANDAY(DATE('2018-07-31'))
            - JULIANDAY(
                DATE(MAX(order_purchase_timestamp))
            )
            AS INTEGER
        ) AS recency_days

    FROM observation_orders

    GROUP BY customer_unique_id
),

user_churn AS (
    SELECT
        *,

        CASE
            WHEN recency_days > 90
            THEN 1
            ELSE 0
        END AS churn_flag,

        CASE
            WHEN DATE(first_purchase_timestamp)
                 <= DATE('2018-05-01')
            THEN 1
            ELSE 0
        END AS has_full_90d_churn_opportunity

    FROM user_base
),

overall AS (
    SELECT
        COUNT(*) AS total_users
    FROM user_churn
)

SELECT
    u.first_purchase_month,

    COUNT(*) AS cohort_users,

    SUM(u.churn_flag)
        AS churned_users,

    COUNT(*) - SUM(u.churn_flag)
        AS non_churned_users,

    ROUND(
        100.0 * SUM(u.churn_flag)
        / NULLIF(COUNT(*), 0),
        2
    ) AS churn_rate_pct,

    SUM(u.has_full_90d_churn_opportunity)
        AS users_with_full_90d_opportunity,

    ROUND(
        100.0 * COUNT(*)
        / NULLIF(o.total_users, 0),
        2
    ) AS user_share_pct

FROM user_churn AS u

CROSS JOIN overall AS o

GROUP BY
    u.first_purchase_month,
    o.total_users

ORDER BY
    u.first_purchase_month ASC;
