-- ============================================================
-- Stage 3 - Member 3
-- Churn User Analysis
-- ============================================================
-- Unified standard:
--   docs/unified_analysis_standards.md
--
-- Purpose:
--   Identify behavior-based churn users as of 2018-07-31
--   and compare churned vs non-churned users.
--
-- Observation window:
--   Only delivered orders with:
--   order_purchase_timestamp < 2018-08-01 00:00:00
--
-- Churn definition:
--   recency_days > 90
--
-- Important:
--   This is a behavioral churn definition within a fixed
--   observation window. It does not mean the user permanently
--   left or closed their account.
-- ============================================================


-- ------------------------------------------------------------
-- 1. Analysis parameters
-- ------------------------------------------------------------

WITH params AS (
    SELECT
        DATE('2018-07-31') AS observation_date,
        DATETIME('2018-08-01 00:00:00') AS observation_end_exclusive,
        90 AS churn_threshold_days
),


-- ------------------------------------------------------------
-- 2. Delivered orders within the fixed observation window
-- ------------------------------------------------------------
-- customer_order_base:
--   one row per delivered order
--   payment already aggregated to order_id
-- ------------------------------------------------------------

observation_orders AS (
    SELECT
        o.customer_unique_id,
        o.customer_id,
        o.order_id,
        o.order_purchase_timestamp,

        DATE(o.order_purchase_timestamp) AS purchase_date,

        CAST(
            STRFTIME('%H', o.order_purchase_timestamp)
            AS INTEGER
        ) AS purchase_hour,

        -- Unified weekday definition:
        -- Monday = 1 ... Sunday = 7
        CASE
            WHEN CAST(
                STRFTIME('%w', o.order_purchase_timestamp)
                AS INTEGER
            ) = 0
            THEN 7

            ELSE CAST(
                STRFTIME('%w', o.order_purchase_timestamp)
                AS INTEGER
            )
        END AS weekday_number,

        o.customer_state,
        o.customer_city,

        o.order_gmv,
        o.is_paid_order

    FROM customer_order_base AS o

    CROSS JOIN params AS p

    WHERE DATETIME(o.order_purchase_timestamp) IS NOT NULL
      AND DATETIME(o.order_purchase_timestamp)
          < p.observation_end_exclusive
),


-- ------------------------------------------------------------
-- 3. User-level purchase summary
-- ------------------------------------------------------------
-- Grain:
--   one row per customer_unique_id
-- ------------------------------------------------------------

user_purchase_summary AS (
    SELECT
        customer_unique_id,

        MIN(order_purchase_timestamp)
            AS first_purchase_timestamp,

        MAX(order_purchase_timestamp)
            AS last_purchase_timestamp,

        COUNT(DISTINCT order_id)
            AS valid_order_count,

        SUM(is_paid_order)
            AS paid_order_count,

        SUM(order_gmv)
            AS lifetime_gmv,

        CASE
            WHEN SUM(is_paid_order) > 0
            THEN
                SUM(order_gmv) * 1.0
                / NULLIF(SUM(is_paid_order), 0)

            ELSE NULL
        END AS average_order_value

    FROM observation_orders

    GROUP BY customer_unique_id
),


-- ------------------------------------------------------------
-- 4. Calculate recency
-- ------------------------------------------------------------

user_recency AS (
    SELECT
        u.*,

        p.observation_date,
        p.churn_threshold_days,

        CAST(
            JULIANDAY(p.observation_date)
            - JULIANDAY(DATE(u.last_purchase_timestamp))
            AS INTEGER
        ) AS recency_days

    FROM user_purchase_summary AS u

    CROSS JOIN params AS p
),


-- ------------------------------------------------------------
-- 5. Churn flag, lifecycle and repeat-purchase flag
-- ------------------------------------------------------------

user_churn AS (
    SELECT
        r.*,

        -- Unified lifecycle definition:
        -- last valid purchase date - first valid purchase date
        CAST(
            JULIANDAY(DATE(r.last_purchase_timestamp))
            - JULIANDAY(DATE(r.first_purchase_timestamp))
            AS INTEGER
        ) AS customer_lifecycle_days,

        -- Unified repeat-purchase definition:
        -- at least 2 distinct delivered orders
        CASE
            WHEN r.valid_order_count >= 2 THEN 1
            ELSE 0
        END AS is_repeat_customer,

        -- Unified churn definition:
        -- strictly greater than 90 days
        CASE
            WHEN r.recency_days > r.churn_threshold_days
            THEN 1
            ELSE 0
        END AS churn_flag

    FROM user_recency AS r
),


-- ------------------------------------------------------------
-- 6. Order-level review and delivery experience
-- ------------------------------------------------------------
-- Review:
--   only valid representative review scores 1-5
--
-- Delivery duration:
--   actual delivery - purchase timestamp
--   only when timestamps are non-null, parseable,
--   and actual delivery >= purchase timestamp
--
-- Delay:
--   actual delivery strictly later than estimated delivery
--   using the same valid delivery logic
-- ------------------------------------------------------------

order_experience AS (
    SELECT
        o.customer_unique_id,
        o.customer_id,
        o.order_id,

        o.order_purchase_timestamp,
        o.purchase_date,

        o.customer_state,
        o.customer_city,

        o.order_gmv,

        -- Unified valid review-score rule
        CASE
            WHEN r.review_score BETWEEN 1 AND 5
            THEN r.review_score
            ELSE NULL
        END AS valid_review_score,

        -- Unified valid delivery-duration rule
        CASE
            WHEN oc.order_delivered_customer_date IS NULL
            THEN NULL

            WHEN DATETIME(
                oc.order_delivered_customer_date
            ) IS NULL
            THEN NULL

            WHEN DATETIME(
                o.order_purchase_timestamp
            ) IS NULL
            THEN NULL

            WHEN DATETIME(
                oc.order_delivered_customer_date
            ) < DATETIME(
                o.order_purchase_timestamp
            )
            THEN NULL

            ELSE ROUND(
                JULIANDAY(
                    oc.order_delivered_customer_date
                )
                - JULIANDAY(
                    o.order_purchase_timestamp
                ),
                4
            )
        END AS delivery_days,

        -- Unified delay-delivery rule
        CASE
            WHEN oc.order_delivered_customer_date IS NULL
              OR oc.order_estimated_delivery_date IS NULL
            THEN NULL

            WHEN DATETIME(
                oc.order_delivered_customer_date
            ) IS NULL
              OR DATETIME(
                oc.order_estimated_delivery_date
            ) IS NULL
              OR DATETIME(
                o.order_purchase_timestamp
            ) IS NULL
            THEN NULL

            WHEN DATETIME(
                oc.order_delivered_customer_date
            ) < DATETIME(
                o.order_purchase_timestamp
            )
            THEN NULL

            WHEN DATETIME(
                oc.order_delivered_customer_date
            ) > DATETIME(
                oc.order_estimated_delivery_date
            )
            THEN 1

            ELSE 0
        END AS is_delayed

    FROM observation_orders AS o

    LEFT JOIN vw_orders_clean AS oc
        ON o.order_id = oc.order_id

    LEFT JOIN vw_order_reviews_order_level AS r
        ON o.order_id = r.order_id
),


-- ------------------------------------------------------------
-- 7. Rank orders within each user
-- ------------------------------------------------------------
-- Used for:
--   latest order amount
--   representative customer geography
--
-- Unified tie-break rule:
--   purchase timestamp DESC
--   order_id DESC
--   customer_id DESC
-- ------------------------------------------------------------

order_experience_ranked AS (
    SELECT
        oe.*,

        ROW_NUMBER() OVER (
            PARTITION BY oe.customer_unique_id

            ORDER BY
                DATETIME(
                    oe.order_purchase_timestamp
                ) DESC,

                oe.order_id DESC,

                oe.customer_id DESC
        ) AS latest_order_rank

    FROM order_experience AS oe
),


-- ------------------------------------------------------------
-- 8. Latest-order / representative-geography user layer
-- ------------------------------------------------------------
-- Grain:
--   one row per customer_unique_id
-- ------------------------------------------------------------

user_latest_order AS (
    SELECT
        customer_unique_id,

        MAX(
            CASE
                WHEN latest_order_rank = 1
                THEN order_gmv
                ELSE NULL
            END
        ) AS latest_order_amount,

        MAX(
            CASE
                WHEN latest_order_rank = 1
                THEN customer_state
                ELSE NULL
            END
        ) AS latest_customer_state,

        MAX(
            CASE
                WHEN latest_order_rank = 1
                THEN customer_city
                ELSE NULL
            END
        ) AS latest_customer_city

    FROM order_experience_ranked

    GROUP BY customer_unique_id
),


-- ------------------------------------------------------------
-- 9. Core business metrics by churn status
-- ------------------------------------------------------------

core_metrics_by_churn AS (
    SELECT
        churn_flag,

        COUNT(*) AS user_count,

        ROUND(
            100.0 * COUNT(*)
            / NULLIF(
                (SELECT COUNT(*) FROM user_churn),
                0
            ),
            2
        ) AS user_share_pct,

        SUM(valid_order_count)
            AS total_valid_orders,

        SUM(paid_order_count)
            AS total_paid_orders,

        ROUND(
            SUM(lifetime_gmv),
            2
        ) AS total_gmv,

        -- Unified spend per user
        ROUND(
            SUM(lifetime_gmv) * 1.0
            / NULLIF(COUNT(*), 0),
            2
        ) AS spend_per_user,

        -- Unified average purchase frequency
        ROUND(
            SUM(valid_order_count) * 1.0
            / NULLIF(COUNT(*), 0),
            4
        ) AS avg_purchase_frequency,

        SUM(is_repeat_customer)
            AS repeat_users,

        -- Unified repeat rate
        ROUND(
            100.0 * SUM(is_repeat_customer)
            / NULLIF(COUNT(*), 0),
            2
        ) AS repeat_rate_pct,

        ROUND(
            AVG(customer_lifecycle_days),
            2
        ) AS avg_lifecycle_days,

        -- Unified AOV:
        -- GMV / paid order count
        ROUND(
            SUM(lifetime_gmv) * 1.0
            / NULLIF(SUM(paid_order_count), 0),
            2
        ) AS average_order_value

    FROM user_churn

    GROUP BY churn_flag
),


-- ------------------------------------------------------------
-- 10. Latest-order metrics by churn status
-- ------------------------------------------------------------

latest_order_metrics_by_churn AS (
    SELECT
        uc.churn_flag,

        COUNT(ul.latest_order_amount)
            AS users_with_latest_order_amount,

        ROUND(
            AVG(ul.latest_order_amount),
            2
        ) AS avg_latest_order_amount

    FROM user_churn AS uc

    LEFT JOIN user_latest_order AS ul
        ON uc.customer_unique_id
         = ul.customer_unique_id

    GROUP BY uc.churn_flag
),


-- ------------------------------------------------------------
-- 11. Order-level experience metrics by churn status
-- ------------------------------------------------------------

order_experience_by_churn AS (
    SELECT
        uc.churn_flag,

        COUNT(oe.order_id)
            AS order_count,

        -- Valid review sample
        COUNT(oe.valid_review_score)
            AS review_order_count,

        COUNT(oe.order_id)
        - COUNT(oe.valid_review_score)
            AS excluded_review_orders,

        ROUND(
            AVG(oe.valid_review_score),
            3
        ) AS avg_review_score,

        -- Valid delivery-duration sample
        COUNT(oe.delivery_days)
            AS delivery_order_count,

        COUNT(oe.order_id)
        - COUNT(oe.delivery_days)
            AS excluded_delivery_orders,

        ROUND(
            AVG(oe.delivery_days),
            2
        ) AS avg_delivery_days,

        -- Valid delay-evaluation sample
        COUNT(oe.is_delayed)
            AS delay_eligible_orders,

        COUNT(oe.order_id)
        - COUNT(oe.is_delayed)
            AS excluded_delay_orders,

        SUM(
            CASE
                WHEN oe.is_delayed = 1 THEN 1
                ELSE 0
            END
        ) AS delayed_orders,

        ROUND(
            100.0
            * SUM(
                CASE
                    WHEN oe.is_delayed = 1
                    THEN 1
                    ELSE 0
                END
            )
            / NULLIF(
                COUNT(oe.is_delayed),
                0
            ),
            2
        ) AS delay_rate_pct

    FROM order_experience AS oe

    INNER JOIN user_churn AS uc
        ON oe.customer_unique_id
         = uc.customer_unique_id

    GROUP BY uc.churn_flag
)


-- ------------------------------------------------------------
-- 12. Final churn vs non-churn comparison
-- ------------------------------------------------------------

SELECT
    CASE
        WHEN c.churn_flag = 1
        THEN 'Churned'

        ELSE 'Non-churned'
    END AS churn_status,

    -- User scale
    c.user_count,
    c.user_share_pct,

    -- Orders and GMV
    c.total_valid_orders,
    c.total_paid_orders,
    c.total_gmv,

    -- User value
    c.spend_per_user,
    c.avg_purchase_frequency,
    c.repeat_users,
    c.repeat_rate_pct,
    c.avg_lifecycle_days,
    c.average_order_value,

    -- Latest order
    l.users_with_latest_order_amount,
    l.avg_latest_order_amount,

    -- Experience order sample
    e.order_count,

    -- Review
    e.review_order_count,
    e.excluded_review_orders,
    e.avg_review_score,

    -- Delivery
    e.delivery_order_count,
    e.excluded_delivery_orders,
    e.avg_delivery_days,

    -- Delay
    e.delay_eligible_orders,
    e.excluded_delay_orders,
    e.delayed_orders,
    e.delay_rate_pct

FROM core_metrics_by_churn AS c

INNER JOIN latest_order_metrics_by_churn AS l
    ON c.churn_flag = l.churn_flag

INNER JOIN order_experience_by_churn AS e
    ON c.churn_flag = e.churn_flag

ORDER BY c.churn_flag DESC;
