/*
Stage 3 Member 1 customer profile and behavior analysis views (SQLite).

Prerequisite: sql/05_customer_analysis/00_customer_common_views.sql.

Geographic profile views assign each customer's complete observed history to
the deterministic representative state/city stored in customer_profile. This
keeps one user in exactly one geography and makes user, order, and GMV totals
reconcile to the customer-level common layer.

Time-distribution and growth views use customer_order_base, retaining the
geography recorded on each order. AOV always divides GMV by paid_order_count,
not by all delivered orders.
*/

DROP VIEW IF EXISTS potential_regional_market_base;
DROP VIEW IF EXISTS customer_growth_periods;
DROP VIEW IF EXISTS customer_day_type_behavior;
DROP VIEW IF EXISTS customer_weekday_behavior;
DROP VIEW IF EXISTS customer_hourly_behavior;
DROP VIEW IF EXISTS customer_city_profile;
DROP VIEW IF EXISTS customer_state_profile;

CREATE VIEW customer_state_profile AS
WITH state_summary AS (
    SELECT
        customer_state,
        COUNT(*) AS unique_user_count,
        SUM(valid_order_count) AS valid_order_count,
        SUM(paid_order_count) AS paid_order_count,
        SUM(lifetime_gmv) AS gmv
    FROM customer_profile
    GROUP BY customer_state
)
SELECT
    customer_state,
    unique_user_count,
    1.0 * unique_user_count / SUM(unique_user_count) OVER () AS user_share,
    valid_order_count,
    paid_order_count,
    gmv,
    1.0 * gmv / NULLIF(SUM(gmv) OVER (), 0) AS gmv_share,
    1.0 * gmv / NULLIF(unique_user_count, 0) AS spend_per_user,
    1.0 * gmv / NULLIF(paid_order_count, 0) AS average_order_value,
    RANK() OVER (ORDER BY unique_user_count DESC) AS user_rank,
    RANK() OVER (ORDER BY gmv DESC) AS gmv_rank
FROM state_summary;

CREATE VIEW customer_city_profile AS
WITH city_summary AS (
    SELECT
        customer_city,
        customer_state,
        COUNT(*) AS unique_user_count,
        SUM(valid_order_count) AS valid_order_count,
        SUM(paid_order_count) AS paid_order_count,
        SUM(lifetime_gmv) AS gmv
    FROM customer_profile
    GROUP BY customer_state, customer_city
)
SELECT
    customer_city,
    customer_state,
    unique_user_count,
    1.0 * unique_user_count / SUM(unique_user_count) OVER () AS user_share,
    valid_order_count,
    paid_order_count,
    gmv,
    1.0 * gmv / NULLIF(SUM(gmv) OVER (), 0) AS gmv_share,
    1.0 * gmv / NULLIF(unique_user_count, 0) AS spend_per_user,
    1.0 * gmv / NULLIF(paid_order_count, 0) AS average_order_value,
    RANK() OVER (ORDER BY unique_user_count DESC) AS user_rank,
    RANK() OVER (ORDER BY gmv DESC) AS gmv_rank
FROM city_summary;

CREATE VIEW customer_hourly_behavior AS
WITH RECURSIVE hours(hour) AS (
    SELECT 0
    UNION ALL
    SELECT hour + 1 FROM hours WHERE hour < 23
),
hour_summary AS (
    SELECT
        purchase_hour AS hour,
        COUNT(*) AS valid_order_count,
        COUNT(DISTINCT customer_unique_id) AS unique_user_count,
        SUM(is_paid_order) AS paid_order_count,
        SUM(order_gmv) AS gmv
    FROM customer_order_base
    GROUP BY purchase_hour
),
totals AS (
    SELECT COUNT(*) AS total_orders, SUM(order_gmv) AS total_gmv
    FROM customer_order_base
)
SELECT
    h.hour,
    COALESCE(s.valid_order_count, 0) AS valid_order_count,
    1.0 * COALESCE(s.valid_order_count, 0) / NULLIF(t.total_orders, 0) AS order_share,
    COALESCE(s.unique_user_count, 0) AS unique_user_count,
    COALESCE(s.paid_order_count, 0) AS paid_order_count,
    COALESCE(s.gmv, 0.0) AS gmv,
    1.0 * COALESCE(s.gmv, 0.0) / NULLIF(t.total_gmv, 0) AS gmv_share,
    1.0 * COALESCE(s.gmv, 0.0) / NULLIF(s.paid_order_count, 0) AS average_order_value
FROM hours AS h
LEFT JOIN hour_summary AS s
    ON s.hour = h.hour
CROSS JOIN totals AS t;

CREATE VIEW customer_weekday_behavior AS
WITH weekdays(weekday_number, weekday_name) AS (
    VALUES
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
        (7, 'Sunday')
),
weekday_summary AS (
    SELECT
        weekday_number,
        COUNT(*) AS valid_order_count,
        COUNT(DISTINCT customer_unique_id) AS unique_user_count,
        SUM(is_paid_order) AS paid_order_count,
        SUM(order_gmv) AS gmv
    FROM customer_order_base
    GROUP BY weekday_number
),
totals AS (
    SELECT COUNT(*) AS total_orders, SUM(order_gmv) AS total_gmv
    FROM customer_order_base
)
SELECT
    w.weekday_number,
    w.weekday_name,
    COALESCE(s.valid_order_count, 0) AS valid_order_count,
    1.0 * COALESCE(s.valid_order_count, 0) / NULLIF(t.total_orders, 0) AS order_share,
    COALESCE(s.unique_user_count, 0) AS unique_user_count,
    COALESCE(s.paid_order_count, 0) AS paid_order_count,
    COALESCE(s.gmv, 0.0) AS gmv,
    1.0 * COALESCE(s.gmv, 0.0) / NULLIF(t.total_gmv, 0) AS gmv_share,
    1.0 * COALESCE(s.gmv, 0.0) / NULLIF(s.paid_order_count, 0) AS average_order_value
FROM weekdays AS w
LEFT JOIN weekday_summary AS s
    ON s.weekday_number = w.weekday_number
CROSS JOIN totals AS t;

CREATE VIEW customer_day_type_behavior AS
WITH RECURSIVE calendar(calendar_date, max_date) AS (
    SELECT
        DATE(MIN(order_purchase_timestamp)),
        DATE(MAX(order_purchase_timestamp))
    FROM customer_order_base
    UNION ALL
    SELECT DATE(calendar_date, '+1 day'), max_date
    FROM calendar
    WHERE calendar_date < max_date
),
calendar_summary AS (
    SELECT
        CASE
            WHEN CAST(STRFTIME('%w', calendar_date) AS INTEGER) IN (0, 6)
                THEN 'Weekend'
            ELSE 'Weekday'
        END AS day_type,
        COUNT(*) AS calendar_day_count
    FROM calendar
    GROUP BY day_type
),
order_summary AS (
    SELECT
        CASE WHEN weekday_number IN (6, 7) THEN 'Weekend' ELSE 'Weekday' END AS day_type,
        COUNT(*) AS valid_order_count,
        COUNT(DISTINCT customer_unique_id) AS unique_user_count,
        SUM(is_paid_order) AS paid_order_count,
        SUM(order_gmv) AS gmv
    FROM customer_order_base
    GROUP BY day_type
),
totals AS (
    SELECT COUNT(*) AS total_orders, SUM(order_gmv) AS total_gmv
    FROM customer_order_base
)
SELECT
    CASE WHEN o.day_type = 'Weekday' THEN 1 ELSE 2 END AS day_type_order,
    o.day_type,
    o.valid_order_count,
    1.0 * o.valid_order_count / NULLIF(t.total_orders, 0) AS order_share,
    o.unique_user_count,
    o.paid_order_count,
    o.gmv,
    1.0 * o.gmv / NULLIF(t.total_gmv, 0) AS gmv_share,
    1.0 * o.gmv / NULLIF(o.paid_order_count, 0) AS average_order_value,
    c.calendar_day_count,
    1.0 * o.valid_order_count / NULLIF(c.calendar_day_count, 0) AS average_daily_orders
FROM order_summary AS o
INNER JOIN calendar_summary AS c
    ON c.day_type = o.day_type
CROSS JOIN totals AS t;

CREATE VIEW customer_growth_periods AS
WITH observed_months AS (
    SELECT DISTINCT purchase_month AS month
    FROM customer_order_base
    WHERE purchase_month IS NOT NULL
),
interior_months AS (
    SELECT month
    FROM observed_months
    WHERE month > (SELECT MIN(month) FROM observed_months)
      AND month < (SELECT MAX(month) FROM observed_months)
),
ranked AS (
    SELECT month, ROW_NUMBER() OVER (ORDER BY month DESC) AS reverse_month_rank
    FROM interior_months
),
selected AS (
    SELECT month, reverse_month_rank
    FROM ranked
    WHERE reverse_month_rank <= 12
)
SELECT
    MIN(CASE WHEN reverse_month_rank BETWEEN 1 AND 6 THEN month END) AS recent_start_month,
    MAX(CASE WHEN reverse_month_rank BETWEEN 1 AND 6 THEN month END) AS recent_end_month,
    MIN(CASE WHEN reverse_month_rank BETWEEN 7 AND 12 THEN month END) AS prior_start_month,
    MAX(CASE WHEN reverse_month_rank BETWEEN 7 AND 12 THEN month END) AS prior_end_month,
    SUM(CASE WHEN reverse_month_rank BETWEEN 1 AND 6 THEN 1 ELSE 0 END) AS recent_month_count,
    SUM(CASE WHEN reverse_month_rank BETWEEN 7 AND 12 THEN 1 ELSE 0 END) AS prior_month_count
FROM selected;

CREATE VIEW potential_regional_market_base AS
WITH periods AS (
    SELECT * FROM customer_growth_periods
),
state_period_summary AS (
    SELECT
        b.customer_state,
        COUNT(DISTINCT CASE
            WHEN b.purchase_month BETWEEN p.prior_start_month AND p.prior_end_month
                THEN b.customer_unique_id END) AS prior_unique_users,
        COUNT(DISTINCT CASE
            WHEN b.purchase_month BETWEEN p.recent_start_month AND p.recent_end_month
                THEN b.customer_unique_id END) AS recent_unique_users,
        SUM(CASE
            WHEN b.purchase_month BETWEEN p.prior_start_month AND p.prior_end_month
                THEN 1 ELSE 0 END) AS prior_valid_orders,
        SUM(CASE
            WHEN b.purchase_month BETWEEN p.recent_start_month AND p.recent_end_month
                THEN 1 ELSE 0 END) AS recent_valid_orders,
        SUM(CASE
            WHEN b.purchase_month BETWEEN p.prior_start_month AND p.prior_end_month
                THEN b.is_paid_order ELSE 0 END) AS prior_paid_orders,
        SUM(CASE
            WHEN b.purchase_month BETWEEN p.recent_start_month AND p.recent_end_month
                THEN b.is_paid_order ELSE 0 END) AS recent_paid_orders,
        SUM(CASE
            WHEN b.purchase_month BETWEEN p.prior_start_month AND p.prior_end_month
                THEN b.order_gmv ELSE 0.0 END) AS prior_gmv,
        SUM(CASE
            WHEN b.purchase_month BETWEEN p.recent_start_month AND p.recent_end_month
                THEN b.order_gmv ELSE 0.0 END) AS recent_gmv
    FROM customer_order_base AS b
    CROSS JOIN periods AS p
    WHERE b.purchase_month BETWEEN p.prior_start_month AND p.recent_end_month
    GROUP BY b.customer_state
)
SELECT
    s.customer_state,
    p.prior_start_month,
    p.prior_end_month,
    p.recent_start_month,
    p.recent_end_month,
    s.prior_unique_users,
    s.recent_unique_users,
    s.prior_valid_orders,
    s.recent_valid_orders,
    s.prior_paid_orders,
    s.recent_paid_orders,
    s.prior_gmv,
    s.recent_gmv,
    1.0 * s.recent_gmv / NULLIF(s.recent_unique_users, 0)
        AS recent_spend_per_user,
    CASE
        WHEN s.prior_unique_users = 0 THEN NULL
        ELSE 1.0 * (s.recent_unique_users - s.prior_unique_users)
             / s.prior_unique_users
    END AS user_growth_rate,
    CASE
        WHEN s.prior_gmv = 0 THEN NULL
        ELSE 1.0 * (s.recent_gmv - s.prior_gmv) / s.prior_gmv
    END AS gmv_growth_rate,
    1.0 * s.recent_unique_users
        / NULLIF(SUM(s.recent_unique_users) OVER (), 0)
        AS recent_user_share,
    1.0 * s.recent_gmv
        / NULLIF(SUM(s.recent_gmv) OVER (), 0)
        AS recent_gmv_share
FROM state_period_summary AS s
CROSS JOIN periods AS p
;
