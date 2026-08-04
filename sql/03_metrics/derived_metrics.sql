/*
Derived metrics M03, M08-M12, M14, M16-M18.
Source of truth (read-only): docs/metric_definition.md and
docs/metric_dictionary.csv. Execute the cleaning-view SQL first.

All queries are standalone SQLite SELECT statements. Rates use floating-point
division and return NULL for a zero denominator. No source table is modified.
*/

-- metric: M03
-- 客单价 / Average Order Value (AOV).
-- Numerator: delivered positive order payments; denominator: those same paid
-- delivered orders. Payment records are cleaned and aggregated before joining.
WITH payment_by_order AS (
    SELECT
        order_id,
        SUM(payment_value) AS order_payment_amount
    FROM vw_order_payments_clean
    GROUP BY order_id
),
paid_delivered_orders AS (
    SELECT
        o.order_id,
        p.order_payment_amount
    FROM vw_orders_clean AS o
    INNER JOIN payment_by_order AS p
        ON p.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND p.order_payment_amount > 0
)
SELECT
    COUNT(*) AS paid_order_count,
    ROUND(SUM(order_payment_amount), 2) AS paid_order_revenue,
    1.0 * SUM(order_payment_amount) / NULLIF(COUNT(*), 0) AS average_order_value
FROM paid_delivered_orders;

-- metric: M08
-- 复购率 / Repeat Purchase Rate.
-- Numerator: users with >=2 delivered orders; denominator: active users with >=1.
WITH user_orders AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS valid_order_count
    FROM vw_orders_clean AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_id IS NOT NULL
      AND c.customer_unique_id IS NOT NULL
    GROUP BY c.customer_unique_id
)
SELECT
    COUNT(*) AS active_customer_count,
    SUM(CASE WHEN valid_order_count >= 2 THEN 1 ELSE 0 END) AS repeat_customer_count,
    1.0 * SUM(CASE WHEN valid_order_count >= 2 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0) AS repeat_purchase_rate
FROM user_orders;

-- metric: M09
-- 用户留存率 / Customer Retention Rate.
-- Natural-month cohort from complete delivered history. The dense grid includes
-- observed zero-retention months and excludes future right-censored months.
WITH RECURSIVE user_month_activity AS (
    SELECT
        c.customer_unique_id,
        DATE(o.order_purchase_timestamp, 'start of month') AS activity_month
    FROM vw_orders_clean AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp IS NOT NULL
      AND c.customer_unique_id IS NOT NULL
    GROUP BY c.customer_unique_id, activity_month
),
user_cohort AS (
    SELECT
        customer_unique_id,
        MIN(activity_month) AS cohort_month
    FROM user_month_activity
    GROUP BY customer_unique_id
),
cohort_size AS (
    SELECT
        cohort_month,
        COUNT(*) AS cohort_customer_count
    FROM user_cohort
    GROUP BY cohort_month
),
observation_limit AS (
    SELECT MAX(activity_month) AS last_observed_month
    FROM user_month_activity
),
cohort_month_grid AS (
    SELECT
        c.cohort_month,
        c.cohort_month AS activity_month,
        o.last_observed_month
    FROM cohort_size AS c
    CROSS JOIN observation_limit AS o

    UNION ALL

    SELECT
        cohort_month,
        DATE(activity_month, '+1 month'),
        last_observed_month
    FROM cohort_month_grid
    WHERE activity_month < last_observed_month
),
retained AS (
    SELECT
        u.cohort_month,
        a.activity_month,
        COUNT(*) AS retained_customer_count
    FROM user_month_activity AS a
    INNER JOIN user_cohort AS u
        ON u.customer_unique_id = a.customer_unique_id
    GROUP BY u.cohort_month, a.activity_month
)
SELECT
    STRFTIME('%Y-%m', g.cohort_month) AS cohort_month,
    CAST(
        (CAST(STRFTIME('%Y', g.activity_month) AS INTEGER)
         - CAST(STRFTIME('%Y', g.cohort_month) AS INTEGER)) * 12
        + CAST(STRFTIME('%m', g.activity_month) AS INTEGER)
        - CAST(STRFTIME('%m', g.cohort_month) AS INTEGER)
        AS INTEGER
    ) AS retention_month_number,
    c.cohort_customer_count,
    COALESCE(r.retained_customer_count, 0) AS retained_customer_count,
    1.0 * COALESCE(r.retained_customer_count, 0)
        / NULLIF(c.cohort_customer_count, 0) AS customer_retention_rate
FROM cohort_month_grid AS g
INNER JOIN cohort_size AS c
    ON c.cohort_month = g.cohort_month
LEFT JOIN retained AS r
    ON r.cohort_month = g.cohort_month
   AND r.activity_month = g.activity_month
ORDER BY g.cohort_month, retention_month_number;

-- metric: M10
-- 用户生命周期价值 / Customer Lifetime Value (observed revenue LTV).
-- Positive cleaned payments -> order -> delivered user revenue -> average user
-- revenue. This is observation-period revenue, not forecast lifetime profit.
WITH payment_by_order AS (
    SELECT
        order_id,
        SUM(payment_value) AS order_payment_amount
    FROM vw_order_payments_clean
    GROUP BY order_id
),
customer_revenue AS (
    SELECT
        c.customer_unique_id,
        SUM(p.order_payment_amount) AS customer_lifetime_revenue
    FROM vw_orders_clean AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    INNER JOIN payment_by_order AS p
        ON p.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND c.customer_unique_id IS NOT NULL
      AND p.order_payment_amount > 0
    GROUP BY c.customer_unique_id
)
SELECT
    COUNT(*) AS paying_customer_count,
    ROUND(SUM(customer_lifetime_revenue), 2) AS total_customer_revenue,
    AVG(customer_lifetime_revenue) AS customer_lifetime_value
FROM customer_revenue;

-- metric: M11
-- 平均购买频次 / Average Purchase Frequency.
-- Formula: distinct delivered orders / active customer_unique_id users.
WITH valid_orders AS (
    SELECT
        o.order_id,
        c.customer_unique_id
    FROM vw_orders_clean AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_id IS NOT NULL
      AND c.customer_unique_id IS NOT NULL
)
SELECT
    COUNT(DISTINCT order_id) AS valid_order_count,
    COUNT(DISTINCT customer_unique_id) AS active_customer_count,
    1.0 * COUNT(DISTINCT order_id)
        / NULLIF(COUNT(DISTINCT customer_unique_id), 0) AS average_purchase_frequency
FROM valid_orders;

-- metric: M12
-- 平均复购间隔 / Average Repurchase Interval.
-- Dictionary rule: every valid adjacent order interval has equal weight (not an
-- equal-weight average of per-user averages). Negative intervals are excluded.
WITH valid_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_purchase_timestamp
    FROM vw_orders_clean AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_id IS NOT NULL
      AND o.order_purchase_timestamp IS NOT NULL
      AND c.customer_unique_id IS NOT NULL
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
        JULIANDAY(order_purchase_timestamp)
            - JULIANDAY(previous_purchase_timestamp) AS interval_days
    FROM sequenced
    WHERE previous_purchase_timestamp IS NOT NULL
      AND JULIANDAY(order_purchase_timestamp)
          - JULIANDAY(previous_purchase_timestamp) >= 0
)
SELECT
    COUNT(DISTINCT customer_unique_id) AS repeat_customer_count,
    COUNT(*) AS valid_interval_count,
    AVG(interval_days) AS average_repurchase_interval_days
FROM valid_intervals;

-- metric: M14
-- 延迟配送率 / Late Delivery Rate.
-- Numerator: actual delivery after estimate; denominator: cleaned delivered
-- orders with usable actual and estimated dates and delivery not before purchase.
-- Intermediate chronology errors stay flagged but are not excluded. The same
-- denominator defines the complementary on-time rate.
WITH evaluable AS (
    SELECT
        order_id,
        order_delivered_customer_date,
        order_estimated_delivery_date
    FROM vw_delivery_analysis_clean
    WHERE order_status = 'delivered'
      AND order_estimated_delivery_date IS NOT NULL
      AND JULIANDAY(order_estimated_delivery_date) IS NOT NULL
),
summary AS (
    SELECT
        COUNT(*) AS evaluable_order_count,
        SUM(CASE
                WHEN JULIANDAY(order_delivered_customer_date)
                   > JULIANDAY(order_estimated_delivery_date)
                THEN 1 ELSE 0
            END) AS late_order_count
    FROM evaluable
)
SELECT
    evaluable_order_count,
    late_order_count,
    1.0 * late_order_count / NULLIF(evaluable_order_count, 0) AS late_delivery_rate
FROM summary;

-- metric: M16
-- 好评率 / Positive Review Rate. Positive means representative score >=4.
-- Denominator: delivered orders with one valid order-level review.
WITH reviewed AS (
    SELECT
        r.order_id,
        r.review_score
    FROM vw_order_reviews_order_level AS r
    INNER JOIN vw_orders_clean AS o
        ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
      AND r.review_score BETWEEN 1 AND 5
)
SELECT
    COUNT(*) AS reviewed_order_count,
    SUM(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END) AS positive_review_order_count,
    1.0 * SUM(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0) AS positive_review_rate
FROM reviewed;

-- metric: M17_OVERALL
-- 取消率 / Cancellation Rate (overall): canceled distinct orders / all statuses.
SELECT
    COUNT(DISTINCT order_id) AS total_order_count,
    COUNT(DISTINCT CASE WHEN order_status = 'canceled' THEN order_id END) AS canceled_order_count,
    1.0 * COUNT(DISTINCT CASE WHEN order_status = 'canceled' THEN order_id END)
        / NULLIF(COUNT(DISTINCT order_id), 0) AS cancellation_rate
FROM vw_orders_clean
WHERE order_id IS NOT NULL;

-- metric: M17_MONTHLY
-- Monthly cancellation rate; purchase timestamp defines YYYY-MM attribution.
SELECT
    STRFTIME('%Y-%m', order_purchase_timestamp) AS order_month,
    COUNT(DISTINCT order_id) AS total_order_count,
    COUNT(DISTINCT CASE WHEN order_status = 'canceled' THEN order_id END) AS canceled_order_count,
    1.0 * COUNT(DISTINCT CASE WHEN order_status = 'canceled' THEN order_id END)
        / NULLIF(COUNT(DISTINCT order_id), 0) AS cancellation_rate
FROM vw_orders_clean
WHERE order_id IS NOT NULL
  AND order_purchase_timestamp IS NOT NULL
  AND STRFTIME('%Y-%m', order_purchase_timestamp) IS NOT NULL
GROUP BY order_month
ORDER BY order_month;

-- metric: M18
-- 品类销售占比 / Category Sales Share.
-- Sales uses cleaned item price only (not freight/payment GMV); NULL/empty category
-- is retained as unknown. Item business key is (order_id, order_item_id).
WITH category_sales AS (
    SELECT
        CASE
            WHEN p.product_category_name IS NULL OR p.product_category_name = ''
            THEN 'unknown'
            ELSE p.product_category_name
        END AS product_category,
        SUM(i.price) AS category_sales_amount
    FROM vw_order_items_clean AS i
    INNER JOIN vw_orders_clean AS o
        ON o.order_id = i.order_id
    INNER JOIN products AS p
        ON p.product_id = i.product_id
    WHERE o.order_status = 'delivered'
      AND i.price IS NOT NULL
      AND i.price >= 0
    GROUP BY product_category
),
with_total AS (
    SELECT
        product_category,
        category_sales_amount,
        SUM(category_sales_amount) OVER () AS total_category_sales_amount
    FROM category_sales
)
SELECT
    product_category,
    category_sales_amount,
    total_category_sales_amount,
    1.0 * category_sales_amount
        / NULLIF(total_category_sales_amount, 0) AS category_sales_share
FROM with_total
ORDER BY category_sales_amount DESC, product_category;
