--- construct daily_kpi for further sesonality analysis ---
-- 只包含delivered的订单
-- 产出：outputs/data/02_business_overview/daily_kpi.csv
WITH b AS (
    SELECT
        DATE(o.order_purchase_timestamp) AS d,
        o.order_id,
        o.customer_id,
        p.payment_value
    FROM vw_orders_clean o
    JOIN vw_order_payments_clean p
        ON o.order_id = p.order_id
    WHERE o.order_status = 'delivered'
),
f AS (
    SELECT
        customer_id,
        MIN(d) AS fd
    FROM b
    GROUP BY customer_id
),
s AS (
    SELECT
        d,
        SUM(payment_value) AS gmv,
        COUNT(DISTINCT order_id) AS order_count,
        ROUND(
            SUM(payment_value) * 1.0 / COUNT(DISTINCT order_id),
            2
        ) AS average_order_value,
        COUNT(DISTINCT customer_id) AS active_users_per_day
    FROM b
    GROUP BY d
),
n AS (
    SELECT
        fd AS d,
        COUNT(*) AS new_users
    FROM f
    GROUP BY fd
)
SELECT
    s.d AS order_date,
    s.gmv,
    s.order_count,
    s.average_order_value,
    COALESCE(n.new_users, 0) AS new_users,
    s.active_users_per_day
FROM s
LEFT JOIN n
    ON s.d = n.d
ORDER BY order_date;



