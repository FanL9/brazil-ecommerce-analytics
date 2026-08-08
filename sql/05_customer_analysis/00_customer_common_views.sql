/*
Stage 3 customer common layers (SQLite).

Metric source of truth:
  - docs/metric_definition.md
  - docs/metric_dictionary.csv

Run sql/02_data_cleaning/data_cleaning_rules.sql first.

Grains:
  - customer_order_base: one row per delivered order.
  - customer_profile: one row per customer_unique_id.

Payment rows are filtered and aggregated to order_id before joining orders.
The only delivered order without a positive payment is retained with order_gmv = 0
and is excluded from paid_order_count / average_order_value denominators.

Representative geography rule for customer_profile:
  use the address on the customer's most recent delivered order. If timestamps
  tie, choose the lexicographically greatest order_id, then customer_id. This
  deterministic rule is used only for the user-level representative geography;
  customer_order_base retains the address recorded on each individual order.
*/

DROP TABLE IF EXISTS customer_profile;
DROP TABLE IF EXISTS customer_order_base;

CREATE TABLE customer_order_base AS
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
)
SELECT
    c.customer_unique_id,
    o.customer_id,
    o.order_id,
    o.order_purchase_timestamp,
    DATE(o.order_purchase_timestamp) AS purchase_date,
    STRFTIME('%Y-%m', o.order_purchase_timestamp) AS purchase_month,
    CAST(STRFTIME('%H', o.order_purchase_timestamp) AS INTEGER) AS purchase_hour,
    CASE CAST(STRFTIME('%w', o.order_purchase_timestamp) AS INTEGER)
        WHEN 0 THEN 7
        ELSE CAST(STRFTIME('%w', o.order_purchase_timestamp) AS INTEGER)
    END AS weekday_number,
    c.customer_state,
    c.customer_city,
    COALESCE(p.order_payment_amount, 0.0) AS order_gmv,
    CASE WHEN p.order_payment_amount > 0 THEN 1 ELSE 0 END AS is_paid_order
FROM vw_orders_clean AS o
INNER JOIN customers AS c
    ON c.customer_id = o.customer_id
LEFT JOIN payment_by_order AS p
    ON p.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND o.order_id IS NOT NULL
  AND o.order_purchase_timestamp IS NOT NULL
  AND DATETIME(o.order_purchase_timestamp) IS NOT NULL
  AND c.customer_unique_id IS NOT NULL
  AND TRIM(c.customer_unique_id) <> '';

CREATE INDEX idx_customer_order_base_customer_unique_id
    ON customer_order_base (customer_unique_id);
CREATE UNIQUE INDEX idx_customer_order_base_order_id
    ON customer_order_base (order_id);
CREATE INDEX idx_customer_order_base_purchase_month
    ON customer_order_base (purchase_month);
CREATE INDEX idx_customer_order_base_state_city
    ON customer_order_base (customer_state, customer_city);

CREATE TABLE customer_profile AS
WITH user_summary AS (
    SELECT
        customer_unique_id,
        MIN(order_purchase_timestamp) AS first_purchase_timestamp,
        MAX(order_purchase_timestamp) AS last_purchase_timestamp,
        COUNT(*) AS valid_order_count,
        SUM(is_paid_order) AS paid_order_count,
        SUM(order_gmv) AS lifetime_gmv,
        COUNT(DISTINCT purchase_month) AS active_purchase_months
    FROM customer_order_base
    GROUP BY customer_unique_id
),
latest_address AS (
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
        ) AS address_rank
    FROM customer_order_base
)
SELECT
    s.customer_unique_id,
    s.first_purchase_timestamp,
    s.last_purchase_timestamp,
    STRFTIME('%Y-%m', s.first_purchase_timestamp) AS first_purchase_month,
    STRFTIME('%Y-%m', s.last_purchase_timestamp) AS latest_purchase_month,
    s.valid_order_count,
    s.paid_order_count,
    s.lifetime_gmv,
    CASE
        WHEN s.paid_order_count = 0 THEN NULL
        ELSE 1.0 * s.lifetime_gmv / s.paid_order_count
    END AS average_order_value,
    JULIANDAY(s.last_purchase_timestamp) - JULIANDAY(s.first_purchase_timestamp)
        AS customer_lifecycle_days,
    s.active_purchase_months,
    CASE WHEN s.valid_order_count >= 2 THEN 1 ELSE 0 END AS is_repeat_customer,
    a.customer_state,
    a.customer_city
FROM user_summary AS s
INNER JOIN latest_address AS a
    ON a.customer_unique_id = s.customer_unique_id
   AND a.address_rank = 1;

CREATE UNIQUE INDEX idx_customer_profile_customer_unique_id
    ON customer_profile (customer_unique_id);
CREATE INDEX idx_customer_profile_state_city
    ON customer_profile (customer_state, customer_city);
