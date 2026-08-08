--- construct daily_kpi for further sesonality analysis ---
WITH b AS (
SELECT 
    DATE(o.order_purchase_timestamp) d,
    o.order_id,
    o.customer_id,
    p.payment_value
FROM vw_orders_clean o
JOIN vw_order_payments_clean p 
ON o.order_id=p.order_id
),
f AS (
SELECT 
    customer_id,
    MIN(d) fd
FROM b
GROUP BY customer_id
),
s AS (
SELECT
    d,
    SUM(payment_value) AS gmv,
    COUNT(DISTINCT order_id) AS order_count,
    ROUND(SUM(payment_value)*1.0/COUNT(DISTINCT order_id),2) AS average_order_value,
    COUNT(DISTINCT customer_id) AS active_users_per_day
FROM b
GROUP BY d
),
n AS (
SELECT
    fd d,
    COUNT(*) AS new_users
FROM f
GROUP BY fd
)
SELECT
    s.d AS order_date,
    s.gmv,
    s.order_count,
    s.average_order_value,
    COALESCE(n.new_users,0) AS new_users,
    s.active_users_per_day
FROM s
LEFT JOIN n
ON s.d=n.d
ORDER BY order_date;
