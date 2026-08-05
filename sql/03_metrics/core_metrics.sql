/*
Core metrics M01, M02, M04, M05, M06, M07, M13 and M15.
Source of truth (read-only): docs/metric_definition.md and
docs/metric_dictionary.csv. SQLite cleaning views must be created first by
sql/02_data_cleaning/data_cleaning_rules.sql.

Unified rules: delivered is the valid-order status; order time is
order_purchase_timestamp; users are deduplicated with customer_unique_id;
payments are aggregated to order_id before joining; IQR long tails are retained.
*/

-- metric: M01
-- GMV / Gross Merchandise Value: delivered orders' positive cleaned payments.
-- Grain: full observation period; time field: order_purchase_timestamp.
WITH payment_by_order AS (
    SELECT
        order_id,
        SUM(payment_value) AS order_payment_amount
    FROM vw_order_payments_clean
    GROUP BY order_id
)
SELECT
    ROUND(SUM(p.order_payment_amount), 2) AS gmv
FROM vw_orders_clean AS o
INNER JOIN payment_by_order AS p
    ON p.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND p.order_payment_amount > 0;

-- metric: M02
-- 有效订单量 / Valid Order Count: distinct delivered order_id.
-- Grain: full observation period; independent of payment/review/item presence.
SELECT
    COUNT(DISTINCT order_id) AS valid_order_count
FROM vw_orders_clean
WHERE order_status = 'delivered'
  AND order_id IS NOT NULL;

-- metric: M04
-- 支付订单量 / Paid Order Count: delivered orders with positive order payment.
-- Payment detail is aggregated before the order join to prevent amplification.
WITH payment_by_order AS (
    SELECT
        order_id,
        SUM(payment_value) AS order_payment_amount
    FROM vw_order_payments_clean
    GROUP BY order_id
)
SELECT
    COUNT(DISTINCT o.order_id) AS paid_order_count
FROM vw_orders_clean AS o
INNER JOIN payment_by_order AS p
    ON p.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND p.order_payment_amount > 0;

-- metric: M05
-- 活跃用户数 / Active Customer Count: users with >=1 delivered order.
-- User key is customer_unique_id, never customer_id.
SELECT
    COUNT(DISTINCT c.customer_unique_id) AS active_customer_count
FROM vw_orders_clean AS o
INNER JOIN customers AS c
    ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered'
  AND c.customer_unique_id IS NOT NULL;

-- metric: M06
-- 新增用户数 / New Customer Count: users grouped by their first delivered month.
-- First purchase is calculated from the complete observed delivered history.
WITH first_purchase AS (
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
)
SELECT
    STRFTIME('%Y-%m', first_purchase_timestamp) AS first_purchase_month,
    COUNT(*) AS new_customer_count
FROM first_purchase
GROUP BY first_purchase_month
ORDER BY first_purchase_month;

-- metric: M07
-- 复购用户数 / Repeat Customer Count: users with >=2 distinct delivered orders.
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
    COUNT(*) AS repeat_customer_count
FROM user_orders
WHERE valid_order_count >= 2;

-- metric: M13
-- 平均配送时长 / Average Delivery Time: purchase to customer delivery in days.
-- Excludes only missing/unparseable endpoints and delivery before purchase.
-- Intermediate chronology errors and valid IQR long tails remain with flags.
-- Grain: delivered order; time: order_purchase_timestamp.
SELECT
    COUNT(DISTINCT order_id) AS valid_delivery_order_count,
    AVG(delivery_days) AS average_delivery_days
FROM vw_delivery_analysis_clean
WHERE order_status = 'delivered';

-- metric: M15
-- 平均评论分数 / Average Review Score: one representative review per order.
-- The order-level cleaned review view applies the dictionary's deterministic
-- answer-time, creation-time and review_id rule; only scores 1..5 remain.
SELECT
    COUNT(DISTINCT r.order_id) AS reviewed_order_count,
    AVG(r.review_score) AS average_review_score
FROM vw_order_reviews_order_level AS r
INNER JOIN vw_orders_clean AS o
    ON o.order_id = r.order_id
WHERE o.order_status = 'delivered';
