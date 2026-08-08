/*
Stage 3 Member 1 RFM customer value analysis (SQLite).

Prerequisite:
  customer_order_base created by 00_customer_common_views.sql.

Fixed observation date: 2018-07-31.
Only rows whose purchase_date is on or before the observation date are used.
The common order table is already one row per delivered order and order_gmv is
already aggregated to order_id, so this script never rejoins payment detail.

R/M percentiles use the empirical nearest-rank method on the complete customer
distribution. Repeated boundary values may leave score bands uneven or empty;
identical raw values always receive the same score.

F scoring first extracts distinct frequency values, applies NTILE(5) only to
those distinct values, and maps the result back to customers. Therefore the
same frequency can never be split across scores.
*/

DROP TABLE IF EXISTS rfm_segment_summary;
DROP TABLE IF EXISTS rfm_score_distribution;
DROP TABLE IF EXISTS rfm_customer_detail;
DROP TABLE IF EXISTS rfm_frequency_score_mapping;
DROP TABLE IF EXISTS rfm_scoring_boundaries;
DROP TABLE IF EXISTS rfm_customer_base;

CREATE TABLE rfm_customer_base AS
WITH eligible_orders AS (
    SELECT *
    FROM customer_order_base
    WHERE DATE(order_purchase_timestamp) <= DATE('2018-07-31')
),
user_summary AS (
    SELECT
        customer_unique_id,
        MIN(purchase_date) AS first_purchase_date,
        MAX(purchase_date) AS last_purchase_date,
        CAST(
            JULIANDAY('2018-07-31') - JULIANDAY(MAX(purchase_date))
            AS INTEGER
        ) AS recency_days,
        COUNT(*) AS frequency,
        SUM(is_paid_order) AS paid_order_count,
        SUM(order_gmv) AS monetary
    FROM eligible_orders
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
    FROM eligible_orders
)
SELECT
    s.customer_unique_id,
    a.customer_state,
    a.customer_city,
    s.first_purchase_date,
    s.last_purchase_date,
    s.recency_days,
    s.frequency,
    s.paid_order_count,
    s.monetary,
    CASE WHEN s.frequency >= 2 THEN 1 ELSE 0 END AS is_repeat_customer,
    '2018-07-31' AS observation_date
FROM user_summary AS s
INNER JOIN latest_address AS a
    ON a.customer_unique_id = s.customer_unique_id
   AND a.address_rank = 1;

CREATE UNIQUE INDEX idx_rfm_customer_base_customer_unique_id
    ON rfm_customer_base (customer_unique_id);

CREATE TABLE rfm_scoring_boundaries AS
WITH percentile_targets(percentile_label, percentile_value) AS (
    VALUES ('P20', 0.2), ('P40', 0.4), ('P60', 0.6), ('P80', 0.8)
),
recency_distribution AS (
    SELECT recency_days AS metric_value, COUNT(*) AS value_user_count
    FROM rfm_customer_base
    GROUP BY recency_days
),
recency_cumulative AS (
    SELECT
        metric_value,
        value_user_count,
        SUM(value_user_count) OVER (
            ORDER BY metric_value
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_users,
        SUM(value_user_count) OVER () AS total_users
    FROM recency_distribution
),
monetary_distribution AS (
    SELECT monetary AS metric_value, COUNT(*) AS value_user_count
    FROM rfm_customer_base
    GROUP BY monetary
),
monetary_cumulative AS (
    SELECT
        metric_value,
        value_user_count,
        SUM(value_user_count) OVER (
            ORDER BY metric_value
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_users,
        SUM(value_user_count) OVER () AS total_users
    FROM monetary_distribution
)
SELECT
    'recency_days' AS metric,
    p.percentile_label,
    p.percentile_value,
    MIN(r.metric_value) AS boundary_value,
    'lower_is_better' AS scoring_direction,
    'empirical_nearest_rank_on_customer_distribution' AS boundary_method
FROM percentile_targets AS p
CROSS JOIN recency_cumulative AS r
WHERE r.cumulative_users >= r.total_users * p.percentile_value
GROUP BY p.percentile_label, p.percentile_value

UNION ALL

SELECT
    'monetary' AS metric,
    p.percentile_label,
    p.percentile_value,
    MIN(m.metric_value) AS boundary_value,
    'higher_is_better' AS scoring_direction,
    'empirical_nearest_rank_on_customer_distribution' AS boundary_method
FROM percentile_targets AS p
CROSS JOIN monetary_cumulative AS m
WHERE m.cumulative_users >= m.total_users * p.percentile_value
GROUP BY p.percentile_label, p.percentile_value;

CREATE TABLE rfm_frequency_score_mapping AS
WITH distinct_frequency AS (
    SELECT DISTINCT frequency
    FROM rfm_customer_base
),
scored_frequency AS (
    SELECT
        frequency,
        NTILE(5) OVER (ORDER BY frequency) AS f_score
    FROM distinct_frequency
)
SELECT
    frequency,
    f_score,
    COUNT(*) OVER (PARTITION BY f_score) AS distinct_values_in_score,
    'NTILE(5) applied to distinct frequency values only' AS scoring_method
FROM scored_frequency;

CREATE UNIQUE INDEX idx_rfm_frequency_mapping_frequency
    ON rfm_frequency_score_mapping (frequency);

CREATE TABLE rfm_customer_detail AS
WITH boundaries AS (
    SELECT
        MAX(CASE WHEN metric = 'recency_days' AND percentile_label = 'P20'
            THEN boundary_value END) AS r_p20,
        MAX(CASE WHEN metric = 'recency_days' AND percentile_label = 'P40'
            THEN boundary_value END) AS r_p40,
        MAX(CASE WHEN metric = 'recency_days' AND percentile_label = 'P60'
            THEN boundary_value END) AS r_p60,
        MAX(CASE WHEN metric = 'recency_days' AND percentile_label = 'P80'
            THEN boundary_value END) AS r_p80,
        MAX(CASE WHEN metric = 'monetary' AND percentile_label = 'P20'
            THEN boundary_value END) AS m_p20,
        MAX(CASE WHEN metric = 'monetary' AND percentile_label = 'P40'
            THEN boundary_value END) AS m_p40,
        MAX(CASE WHEN metric = 'monetary' AND percentile_label = 'P60'
            THEN boundary_value END) AS m_p60,
        MAX(CASE WHEN metric = 'monetary' AND percentile_label = 'P80'
            THEN boundary_value END) AS m_p80
    FROM rfm_scoring_boundaries
),
scored AS (
    SELECT
        b.*,
        CASE
            WHEN b.recency_days <= x.r_p20 THEN 5
            WHEN b.recency_days <= x.r_p40 THEN 4
            WHEN b.recency_days <= x.r_p60 THEN 3
            WHEN b.recency_days <= x.r_p80 THEN 2
            ELSE 1
        END AS r_score,
        f.f_score,
        CASE
            WHEN b.monetary <= x.m_p20 THEN 1
            WHEN b.monetary <= x.m_p40 THEN 2
            WHEN b.monetary <= x.m_p60 THEN 3
            WHEN b.monetary <= x.m_p80 THEN 4
            ELSE 5
        END AS m_score
    FROM rfm_customer_base AS b
    CROSS JOIN boundaries AS x
    INNER JOIN rfm_frequency_score_mapping AS f
        ON f.frequency = b.frequency
),
coded AS (
    SELECT
        *,
        r_score + f_score + m_score AS rfm_score,
        CAST(r_score AS TEXT) || CAST(f_score AS TEXT) || CAST(m_score AS TEXT)
            AS rfm_code
    FROM scored
)
SELECT
    customer_unique_id,
    customer_state,
    customer_city,
    first_purchase_date,
    last_purchase_date,
    recency_days,
    frequency,
    paid_order_count,
    monetary,
    is_repeat_customer,
    r_score,
    f_score,
    m_score,
    rfm_score,
    rfm_code,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4
            THEN '重要价值用户'
        WHEN r_score >= 4 AND f_score <= 3 AND m_score >= 4
            THEN '重要发展用户'
        WHEN r_score <= 3 AND f_score >= 4 AND m_score >= 4
            THEN '重要保持用户'
        WHEN r_score <= 3 AND f_score <= 3 AND m_score >= 4
            THEN '重要挽留用户'
        ELSE '一般用户'
    END AS rfm_segment,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 1
        WHEN r_score >= 4 AND f_score <= 3 AND m_score >= 4 THEN 2
        WHEN r_score <= 3 AND f_score >= 4 AND m_score >= 4 THEN 3
        WHEN r_score <= 3 AND f_score <= 3 AND m_score >= 4 THEN 4
        ELSE 5
    END AS rfm_segment_order,
    observation_date
FROM coded;

CREATE UNIQUE INDEX idx_rfm_customer_detail_customer_unique_id
    ON rfm_customer_detail (customer_unique_id);
CREATE INDEX idx_rfm_customer_detail_segment
    ON rfm_customer_detail (rfm_segment_order, rfm_segment);

CREATE TABLE rfm_score_distribution AS
WITH scores(score) AS (VALUES (1), (2), (3), (4), (5)),
metrics(metric, metric_order) AS (
    VALUES ('R', 1), ('F', 2), ('M', 3)
),
score_counts AS (
    SELECT 'R' AS metric, r_score AS score, COUNT(*) AS user_count
    FROM rfm_customer_detail GROUP BY r_score
    UNION ALL
    SELECT 'F', f_score, COUNT(*)
    FROM rfm_customer_detail GROUP BY f_score
    UNION ALL
    SELECT 'M', m_score, COUNT(*)
    FROM rfm_customer_detail GROUP BY m_score
),
totals AS (SELECT COUNT(*) AS total_users FROM rfm_customer_detail)
SELECT
    m.metric,
    m.metric_order,
    s.score,
    COALESCE(c.user_count, 0) AS user_count,
    1.0 * COALESCE(c.user_count, 0) / NULLIF(t.total_users, 0) AS user_share
FROM metrics AS m
CROSS JOIN scores AS s
CROSS JOIN totals AS t
LEFT JOIN score_counts AS c
    ON c.metric = m.metric
   AND c.score = s.score;

CREATE TABLE rfm_segment_summary AS
WITH segments(rfm_segment_order, rfm_segment) AS (
    VALUES
        (1, '重要价值用户'),
        (2, '重要发展用户'),
        (3, '重要保持用户'),
        (4, '重要挽留用户'),
        (5, '一般用户')
),
segment_values AS (
    SELECT
        rfm_segment_order,
        rfm_segment,
        COUNT(*) AS user_count,
        SUM(frequency) AS valid_order_count,
        SUM(paid_order_count) AS paid_order_count,
        SUM(monetary) AS gmv,
        SUM(is_repeat_customer) AS repeat_customer_count,
        AVG(recency_days) AS average_recency,
        AVG(frequency) AS average_frequency,
        AVG(monetary) AS average_monetary,
        AVG(r_score) AS average_r_score,
        AVG(f_score) AS average_f_score,
        AVG(m_score) AS average_m_score
    FROM rfm_customer_detail
    GROUP BY rfm_segment_order, rfm_segment
),
totals AS (
    SELECT
        COUNT(*) AS total_users,
        SUM(frequency) AS total_orders,
        SUM(monetary) AS total_gmv
    FROM rfm_customer_detail
)
SELECT
    s.rfm_segment_order,
    s.rfm_segment,
    COALESCE(v.user_count, 0) AS user_count,
    1.0 * COALESCE(v.user_count, 0) / NULLIF(t.total_users, 0) AS user_share,
    COALESCE(v.valid_order_count, 0) AS valid_order_count,
    1.0 * COALESCE(v.valid_order_count, 0) / NULLIF(t.total_orders, 0) AS order_share,
    COALESCE(v.paid_order_count, 0) AS paid_order_count,
    COALESCE(v.gmv, 0.0) AS gmv,
    1.0 * COALESCE(v.gmv, 0.0) / NULLIF(t.total_gmv, 0) AS gmv_share,
    1.0 * COALESCE(v.gmv, 0.0) / NULLIF(v.user_count, 0) AS spend_per_user,
    1.0 * COALESCE(v.gmv, 0.0) / NULLIF(v.paid_order_count, 0)
        AS average_order_value,
    1.0 * COALESCE(v.gmv, 0.0) / NULLIF(v.valid_order_count, 0)
        AS gmv_per_valid_order,
    1.0 * COALESCE(v.valid_order_count, 0) / NULLIF(v.user_count, 0)
        AS average_purchase_frequency,
    COALESCE(v.repeat_customer_count, 0) AS repeat_customer_count,
    1.0 * COALESCE(v.repeat_customer_count, 0) / NULLIF(v.user_count, 0)
        AS repeat_purchase_rate,
    v.average_recency,
    v.average_frequency,
    v.average_monetary,
    v.average_r_score,
    v.average_f_score,
    v.average_m_score
FROM segments AS s
CROSS JOIN totals AS t
LEFT JOIN segment_values AS v
    ON v.rfm_segment_order = s.rfm_segment_order
   AND v.rfm_segment = s.rfm_segment;
