/*
Monthly KPI common data layer (SQLite).

Source of truth (read-only): docs/metric_definition.md and
docs/metric_dictionary.csv. Run sql/02_data_cleaning/data_cleaning_rules.sql
before this file so that the referenced cleaning views exist.

Grain: one row per observed natural month containing delivered orders.
Payments are filtered and aggregated to order_id before any order join.
*/

DROP VIEW IF EXISTS monthly_kpi;

CREATE VIEW monthly_kpi AS
WITH payment_by_order AS (
    SELECT
        order_id,
        SUM(payment_value) AS order_payment_amount
    FROM vw_order_payments_clean
    WHERE order_id IS NOT NULL
      AND payment_value IS NOT NULL
      AND payment_value > 0
    GROUP BY order_id
    HAVING SUM(payment_value) > 0
),
monthly_orders AS (
    SELECT
        STRFTIME('%Y-%m', order_purchase_timestamp) AS month,
        COUNT(DISTINCT order_id) AS order_count
    FROM vw_orders_clean
    WHERE order_status = 'delivered'
      AND order_id IS NOT NULL
      AND order_purchase_timestamp IS NOT NULL
      AND STRFTIME('%Y-%m', order_purchase_timestamp) IS NOT NULL
    GROUP BY STRFTIME('%Y-%m', order_purchase_timestamp)
),
monthly_paid_orders AS (
    SELECT
        STRFTIME('%Y-%m', o.order_purchase_timestamp) AS month,
        SUM(p.order_payment_amount) AS gmv,
        COUNT(DISTINCT o.order_id) AS paid_order_count
    FROM vw_orders_clean AS o
    INNER JOIN payment_by_order AS p
        ON p.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_id IS NOT NULL
      AND o.order_purchase_timestamp IS NOT NULL
      AND STRFTIME('%Y-%m', o.order_purchase_timestamp) IS NOT NULL
      AND p.order_payment_amount > 0
    GROUP BY STRFTIME('%Y-%m', o.order_purchase_timestamp)
),
first_purchase AS (
    SELECT
        c.customer_unique_id,
        MIN(o.order_purchase_timestamp) AS first_purchase_timestamp
    FROM vw_orders_clean AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp IS NOT NULL
      AND c.customer_unique_id IS NOT NULL
    GROUP BY c.customer_unique_id
),
monthly_new_users AS (
    SELECT
        STRFTIME('%Y-%m', first_purchase_timestamp) AS month,
        COUNT(*) AS new_users
    FROM first_purchase
    WHERE first_purchase_timestamp IS NOT NULL
      AND STRFTIME('%Y-%m', first_purchase_timestamp) IS NOT NULL
    GROUP BY STRFTIME('%Y-%m', first_purchase_timestamp)
),
monthly_active_users AS (
    SELECT
        STRFTIME('%Y-%m', o.order_purchase_timestamp) AS month,
        COUNT(DISTINCT c.customer_unique_id) AS active_users
    FROM vw_orders_clean AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp IS NOT NULL
      AND STRFTIME('%Y-%m', o.order_purchase_timestamp) IS NOT NULL
      AND c.customer_unique_id IS NOT NULL
    GROUP BY STRFTIME('%Y-%m', o.order_purchase_timestamp)
)
SELECT
    m.month AS month,
    COALESCE(p.gmv, 0.0) AS gmv,
    m.order_count AS order_count,
    CASE
        WHEN COALESCE(p.paid_order_count, 0) = 0 THEN NULL
        ELSE 1.0 * p.gmv / p.paid_order_count
    END AS average_order_value,
    COALESCE(n.new_users, 0) AS new_users,
    COALESCE(a.active_users, 0) AS active_users
FROM monthly_orders AS m
LEFT JOIN monthly_paid_orders AS p
    ON p.month = m.month
LEFT JOIN monthly_new_users AS n
    ON n.month = m.month
LEFT JOIN monthly_active_users AS a
    ON a.month = m.month;
