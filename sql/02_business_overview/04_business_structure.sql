-- ============================================================================
-- Member 3: Business Structure Analysis
-- File: sql/02_business_overview/04_business_structure.sql
-- Database: SQLite
--
-- Analysis scope:
--   1. Payment method structure
--   2. Order value band structure
--   3. Customer state structure
--   4. Structural risks and opportunities
--
-- Unified metric rules:
--   - Clean order source: vw_orders_clean
--   - Clean payment source: vw_order_payments_clean
--   - Valid order status: order_status = 'delivered'
--   - Order time field: order_purchase_timestamp
--   - GMV: sum of positive payment values aggregated to order_id
--   - Paid order count: distinct delivered orders with order payment amount > 0
--   - Average order value: GMV / paid order count
--   - Geography: customers.customer_state
--
-- Mixed-payment rule:
--   - Payment-method GMV is split by the actual amount paid with each method.
--   - Order count and AOV use one primary payment type per order.
--   - Primary payment type is the type with the largest aggregated amount.
--   - The checked data contains no ties for the largest payment amount.
--
-- Order value bands:
--   - 0-50
--   - 50-100
--   - 100-200
--   - 200-500
--   - 500+
--
-- Comparable period:
--   - 2017-01 through 2017-08
--   - 2018-01 through 2018-08
--   - 2016 and 2018 must not be treated as complete calendar years.
--
-- Important:
--   - Never join raw payment rows directly to other one-to-many tables
--     before aggregating payments to the order level.
--   - All final results must remain reproducible from the local database.
-- ============================================================================


-- ============================================================================
-- 1. Order-level business structure base
--    Grain: one row per order
-- ============================================================================

DROP TABLE IF EXISTS business_structure_order_base;

CREATE TABLE business_structure_order_base AS
WITH payment_by_order AS (
    SELECT
        order_id,
        ROUND(SUM(CAST(payment_value AS REAL)), 2)
            AS order_payment_amount,
        COUNT(*) AS payment_row_count,
        COUNT(DISTINCT payment_type) AS payment_type_count
    FROM vw_order_payments_clean
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.customer_state,

    o.order_status,
    o.order_purchase_timestamp,

    SUBSTR(o.order_purchase_timestamp, 1, 7)
        AS purchase_month,

    CAST(
        SUBSTR(o.order_purchase_timestamp, 1, 4)
        AS INTEGER
    ) AS purchase_year,

    p.order_payment_amount,

    COALESCE(p.payment_row_count, 0)
        AS payment_row_count,

    COALESCE(p.payment_type_count, 0)
        AS payment_type_count,

    CASE
        WHEN COALESCE(p.payment_type_count, 0) > 1
        THEN 1
        ELSE 0
    END AS is_mixed_payment,

    CASE
        WHEN o.order_status = 'delivered'
        THEN 1
        ELSE 0
    END AS is_delivered_order,

    CASE
        WHEN o.order_status = 'delivered'
         AND p.order_payment_amount > 0
        THEN 1
        ELSE 0
    END AS is_paid_delivered_order,

    CASE
        WHEN p.order_payment_amount >= 0
         AND p.order_payment_amount < 50
        THEN '0-50'

        WHEN p.order_payment_amount >= 50
         AND p.order_payment_amount < 100
        THEN '50-100'

        WHEN p.order_payment_amount >= 100
         AND p.order_payment_amount < 200
        THEN '100-200'

        WHEN p.order_payment_amount >= 200
         AND p.order_payment_amount < 500
        THEN '200-500'

        WHEN p.order_payment_amount >= 500
        THEN '500+'

        ELSE NULL
    END AS order_value_band,

    CASE
        WHEN SUBSTR(o.order_purchase_timestamp, 1, 7)
             BETWEEN '2017-01' AND '2017-08'
        THEN '2017-01_to_2017-08'

        WHEN SUBSTR(o.order_purchase_timestamp, 1, 7)
             BETWEEN '2018-01' AND '2018-08'
        THEN '2018-01_to_2018-08'

        ELSE NULL
    END AS comparable_period

FROM vw_orders_clean AS o

INNER JOIN customers AS c
    ON c.customer_id = o.customer_id

LEFT JOIN payment_by_order AS p
    ON p.order_id = o.order_id;


-- Indexes for repeated structure analysis queries.

CREATE UNIQUE INDEX IF NOT EXISTS
    idx_business_structure_base_order_id
ON business_structure_order_base(order_id);

CREATE INDEX IF NOT EXISTS
    idx_business_structure_base_month
ON business_structure_order_base(purchase_month);

CREATE INDEX IF NOT EXISTS
    idx_business_structure_base_state
ON business_structure_order_base(customer_state);

CREATE INDEX IF NOT EXISTS
    idx_business_structure_base_paid
ON business_structure_order_base(is_paid_delivered_order);


-- Validation result expected:
-- 99,441 rows and 99,441 distinct order IDs.

SELECT
    COUNT(*) AS base_rows,
    COUNT(DISTINCT order_id) AS distinct_orders,
    COUNT(*) - COUNT(DISTINCT order_id) AS duplicate_rows,

    SUM(is_delivered_order) AS delivered_orders,
    SUM(is_paid_delivered_order) AS paid_delivered_orders,

    ROUND(
        SUM(
            CASE
                WHEN is_paid_delivered_order = 1
                THEN order_payment_amount
                ELSE 0
            END
        ),
        2
    ) AS paid_delivered_gmv,

    SUM(
        CASE
            WHEN is_paid_delivered_order = 1
             AND customer_state IS NULL
            THEN 1
            ELSE 0
        END
    ) AS paid_orders_without_state

FROM business_structure_order_base;

-- ============================================================================
-- 2. Payment attribution layers
-- ============================================================================

-- 2.1 Order + payment type grain.
-- One order may have multiple rows here when mixed payment is used.
-- Payment-method GMV uses the actual amount paid by each payment type.

DROP TABLE IF EXISTS business_structure_order_payment_type;

CREATE TABLE business_structure_order_payment_type AS
SELECT
    p.order_id,
    p.payment_type,

    ROUND(
        SUM(CAST(p.payment_value AS REAL)),
        2
    ) AS payment_type_amount

FROM vw_order_payments_clean AS p

INNER JOIN business_structure_order_base AS b
    ON b.order_id = p.order_id

WHERE b.is_paid_delivered_order = 1

GROUP BY
    p.order_id,
    p.payment_type;


CREATE UNIQUE INDEX IF NOT EXISTS
    idx_business_structure_order_payment_type
ON business_structure_order_payment_type(
    order_id,
    payment_type
);


-- 2.2 Primary payment type.
-- One row per paid delivered order.
-- The payment type with the largest amount receives the order attribution.
-- payment_type is used as a deterministic secondary sort key.

DROP TABLE IF EXISTS business_structure_primary_payment;

CREATE TABLE business_structure_primary_payment AS
WITH ranked_payment_types AS (
    SELECT
        opt.order_id,
        opt.payment_type,
        opt.payment_type_amount,

        ROW_NUMBER() OVER (
            PARTITION BY opt.order_id
            ORDER BY
                opt.payment_type_amount DESC,
                opt.payment_type ASC
        ) AS payment_type_rank

    FROM business_structure_order_payment_type AS opt
)
SELECT
    r.order_id,

    r.payment_type
        AS primary_payment_type,

    r.payment_type_amount
        AS primary_payment_type_amount,

    b.order_payment_amount,
    b.payment_type_count,
    b.is_mixed_payment

FROM ranked_payment_types AS r

INNER JOIN business_structure_order_base AS b
    ON b.order_id = r.order_id

WHERE r.payment_type_rank = 1;


CREATE UNIQUE INDEX IF NOT EXISTS
    idx_business_structure_primary_payment_order
ON business_structure_primary_payment(order_id);

CREATE INDEX IF NOT EXISTS
    idx_business_structure_primary_payment_type
ON business_structure_primary_payment(primary_payment_type);


-- Validation expected:
-- 96,477 rows and 96,477 distinct orders.
-- 2,182 mixed-payment orders.
-- Split payment amount and order-level GMV should both equal 15,422,461.77.

SELECT
    COUNT(*) AS primary_payment_rows,
    COUNT(DISTINCT order_id) AS distinct_orders,
    COUNT(*) - COUNT(DISTINCT order_id) AS duplicate_rows,

    SUM(is_mixed_payment)
        AS mixed_payment_orders,

    ROUND(
        SUM(order_payment_amount),
        2
    ) AS primary_attribution_gmv

FROM business_structure_primary_payment;


SELECT
    COUNT(*) AS order_payment_type_rows,
    COUNT(DISTINCT order_id) AS distinct_orders,
    COUNT(DISTINCT payment_type) AS distinct_payment_types,

    ROUND(
        SUM(payment_type_amount),
        2
    ) AS split_payment_gmv

FROM business_structure_order_payment_type;


-- Confirm that no mixed-payment order has a tie for the largest amount.

WITH payment_type_maximum AS (
    SELECT
        order_id,
        MAX(payment_type_amount) AS maximum_amount
    FROM business_structure_order_payment_type
    GROUP BY order_id
),
top_amount_counts AS (
    SELECT
        opt.order_id,
        COUNT(*) AS top_type_count
    FROM business_structure_order_payment_type AS opt
    INNER JOIN payment_type_maximum AS m
        ON m.order_id = opt.order_id
       AND m.maximum_amount = opt.payment_type_amount
    GROUP BY opt.order_id
)
SELECT
    COUNT(*) AS orders_with_top_amount_tie
FROM top_amount_counts
WHERE top_type_count > 1;


-- ============================================================================
-- 3. Payment method structure summary
--
-- GMV rule:
--   split_gmv uses the actual amount paid with each payment method.
--
-- Order and AOV rule:
--   primary_order_count assigns each order to its largest payment method.
--   attributed_order_gmv assigns the full order GMV to that primary method.
--   average_order_value = attributed_order_gmv / primary_order_count.
--
-- Periods:
--   ALL_DATA
--   2017-01_to_2017-08
--   2018-01_to_2018-08
-- ============================================================================

DROP TABLE IF EXISTS business_structure_payment_summary;

CREATE TABLE business_structure_payment_summary AS
WITH periods AS (
    SELECT
        1 AS period_order,
        'ALL_DATA' AS period

    UNION ALL

    SELECT
        2 AS period_order,
        '2017-01_to_2017-08' AS period

    UNION ALL

    SELECT
        3 AS period_order,
        '2018-01_to_2018-08' AS period
),

payment_types AS (
    SELECT DISTINCT
        payment_type
    FROM business_structure_order_payment_type
),

split_payment_gmv AS (
    SELECT
        'ALL_DATA' AS period,
        opt.payment_type,

        ROUND(
            SUM(opt.payment_type_amount),
            2
        ) AS split_gmv

    FROM business_structure_order_payment_type AS opt

    INNER JOIN business_structure_order_base AS b
        ON b.order_id = opt.order_id

    WHERE b.is_paid_delivered_order = 1

    GROUP BY
        opt.payment_type

    UNION ALL

    SELECT
        b.comparable_period AS period,
        opt.payment_type,

        ROUND(
            SUM(opt.payment_type_amount),
            2
        ) AS split_gmv

    FROM business_structure_order_payment_type AS opt

    INNER JOIN business_structure_order_base AS b
        ON b.order_id = opt.order_id

    WHERE b.is_paid_delivered_order = 1
      AND b.comparable_period IS NOT NULL

    GROUP BY
        b.comparable_period,
        opt.payment_type
),

primary_payment_stats AS (
    SELECT
        'ALL_DATA' AS period,
        p.primary_payment_type AS payment_type,

        COUNT(*) AS primary_order_count,

        ROUND(
            SUM(p.order_payment_amount),
            2
        ) AS attributed_order_gmv,

        SUM(p.is_mixed_payment)
            AS mixed_payment_orders

    FROM business_structure_primary_payment AS p

    GROUP BY
        p.primary_payment_type

    UNION ALL

    SELECT
        b.comparable_period AS period,
        p.primary_payment_type AS payment_type,

        COUNT(*) AS primary_order_count,

        ROUND(
            SUM(p.order_payment_amount),
            2
        ) AS attributed_order_gmv,

        SUM(p.is_mixed_payment)
            AS mixed_payment_orders

    FROM business_structure_primary_payment AS p

    INNER JOIN business_structure_order_base AS b
        ON b.order_id = p.order_id

    WHERE b.comparable_period IS NOT NULL

    GROUP BY
        b.comparable_period,
        p.primary_payment_type
),

period_totals AS (
    SELECT
        'ALL_DATA' AS period,

        COUNT(*) AS total_paid_orders,

        ROUND(
            SUM(order_payment_amount),
            2
        ) AS total_gmv

    FROM business_structure_order_base

    WHERE is_paid_delivered_order = 1

    UNION ALL

    SELECT
        comparable_period AS period,

        COUNT(*) AS total_paid_orders,

        ROUND(
            SUM(order_payment_amount),
            2
        ) AS total_gmv

    FROM business_structure_order_base

    WHERE is_paid_delivered_order = 1
      AND comparable_period IS NOT NULL

    GROUP BY
        comparable_period
)

SELECT
    periods.period_order,
    periods.period,
    payment_types.payment_type,

    COALESCE(
        split_payment_gmv.split_gmv,
        0
    ) AS split_gmv,

    COALESCE(
        primary_payment_stats.attributed_order_gmv,
        0
    ) AS attributed_order_gmv,

    COALESCE(
        primary_payment_stats.primary_order_count,
        0
    ) AS primary_order_count,

    CASE
        WHEN COALESCE(
            primary_payment_stats.primary_order_count,
            0
        ) > 0
        THEN ROUND(
            primary_payment_stats.attributed_order_gmv
            / primary_payment_stats.primary_order_count,
            2
        )
        ELSE NULL
    END AS average_order_value,

    ROUND(
        COALESCE(
            split_payment_gmv.split_gmv,
            0
        ) / NULLIF(period_totals.total_gmv, 0),
        6
    ) AS gmv_share,

    ROUND(
        CAST(
            COALESCE(
                primary_payment_stats.primary_order_count,
                0
            ) AS REAL
        ) / NULLIF(period_totals.total_paid_orders, 0),
        6
    ) AS order_share,

    COALESCE(
        primary_payment_stats.mixed_payment_orders,
        0
    ) AS mixed_payment_orders,

    CASE
        WHEN COALESCE(
            primary_payment_stats.primary_order_count,
            0
        ) > 0
        THEN ROUND(
            CAST(
                primary_payment_stats.mixed_payment_orders
                AS REAL
            ) / primary_payment_stats.primary_order_count,
            6
        )
        ELSE 0
    END AS mixed_payment_order_share,

    period_totals.total_gmv,
    period_totals.total_paid_orders

FROM periods

CROSS JOIN payment_types

INNER JOIN period_totals
    ON period_totals.period = periods.period

LEFT JOIN split_payment_gmv
    ON split_payment_gmv.period = periods.period
   AND split_payment_gmv.payment_type
       = payment_types.payment_type

LEFT JOIN primary_payment_stats
    ON primary_payment_stats.period = periods.period
   AND primary_payment_stats.payment_type
       = payment_types.payment_type;


CREATE UNIQUE INDEX IF NOT EXISTS
    idx_business_structure_payment_summary
ON business_structure_payment_summary(
    period,
    payment_type
);


-- Validation:
-- For each period:
--   sum(split_gmv) = total GMV
--   sum(primary_order_count) = total paid orders
--   sum(gmv_share) should be approximately 1
--   sum(order_share) should be approximately 1

SELECT
    period,

    ROUND(
        SUM(split_gmv),
        2
    ) AS summed_split_gmv,

    MAX(total_gmv)
        AS expected_total_gmv,

    SUM(primary_order_count)
        AS summed_primary_orders,

    MAX(total_paid_orders)
        AS expected_total_paid_orders,

    ROUND(
        SUM(gmv_share),
        6
    ) AS summed_gmv_share,

    ROUND(
        SUM(order_share),
        6
    ) AS summed_order_share

FROM business_structure_payment_summary

GROUP BY
    period_order,
    period

ORDER BY
    period_order;


-- Preview payment structure results.

SELECT
    period,
    payment_type,
    split_gmv,
    primary_order_count,
    average_order_value,
    gmv_share,
    order_share,
    mixed_payment_orders

FROM business_structure_payment_summary

ORDER BY
    period_order,
    split_gmv DESC;


-- ============================================================================
-- 4. Order value band structure summary
--
-- Grain:
--   one row per period and order value band
--
-- Value band rule:
--   based on the total positive payment amount at the order level
--
-- Periods:
--   ALL_DATA
--   2017-01_to_2017-08
--   2018-01_to_2018-08
-- ============================================================================

DROP TABLE IF EXISTS business_structure_order_value_summary;

CREATE TABLE business_structure_order_value_summary AS
WITH periods AS (
    SELECT
        1 AS period_order,
        'ALL_DATA' AS period

    UNION ALL

    SELECT
        2 AS period_order,
        '2017-01_to_2017-08' AS period

    UNION ALL

    SELECT
        3 AS period_order,
        '2018-01_to_2018-08' AS period
),

value_bands AS (
    SELECT
        1 AS band_order,
        '0-50' AS order_value_band

    UNION ALL

    SELECT
        2 AS band_order,
        '50-100' AS order_value_band

    UNION ALL

    SELECT
        3 AS band_order,
        '100-200' AS order_value_band

    UNION ALL

    SELECT
        4 AS band_order,
        '200-500' AS order_value_band

    UNION ALL

    SELECT
        5 AS band_order,
        '500+' AS order_value_band
),

band_stats AS (
    SELECT
        'ALL_DATA' AS period,
        order_value_band,

        COUNT(*) AS order_count,

        ROUND(
            SUM(order_payment_amount),
            2
        ) AS gmv

    FROM business_structure_order_base

    WHERE is_paid_delivered_order = 1
      AND order_value_band IS NOT NULL

    GROUP BY
        order_value_band

    UNION ALL

    SELECT
        comparable_period AS period,
        order_value_band,

        COUNT(*) AS order_count,

        ROUND(
            SUM(order_payment_amount),
            2
        ) AS gmv

    FROM business_structure_order_base

    WHERE is_paid_delivered_order = 1
      AND comparable_period IS NOT NULL
      AND order_value_band IS NOT NULL

    GROUP BY
        comparable_period,
        order_value_band
),

period_totals AS (
    SELECT
        'ALL_DATA' AS period,

        COUNT(*) AS total_paid_orders,

        ROUND(
            SUM(order_payment_amount),
            2
        ) AS total_gmv

    FROM business_structure_order_base

    WHERE is_paid_delivered_order = 1

    UNION ALL

    SELECT
        comparable_period AS period,

        COUNT(*) AS total_paid_orders,

        ROUND(
            SUM(order_payment_amount),
            2
        ) AS total_gmv

    FROM business_structure_order_base

    WHERE is_paid_delivered_order = 1
      AND comparable_period IS NOT NULL

    GROUP BY
        comparable_period
)

SELECT
    periods.period_order,
    periods.period,

    value_bands.band_order,
    value_bands.order_value_band,

    COALESCE(
        band_stats.order_count,
        0
    ) AS order_count,

    COALESCE(
        band_stats.gmv,
        0
    ) AS gmv,

    CASE
        WHEN COALESCE(
            band_stats.order_count,
            0
        ) > 0
        THEN ROUND(
            band_stats.gmv
            / band_stats.order_count,
            2
        )
        ELSE NULL
    END AS average_order_value,

    ROUND(
        CAST(
            COALESCE(
                band_stats.order_count,
                0
            ) AS REAL
        ) / NULLIF(period_totals.total_paid_orders, 0),
        6
    ) AS order_share,

    ROUND(
        COALESCE(
            band_stats.gmv,
            0
        ) / NULLIF(period_totals.total_gmv, 0),
        6
    ) AS gmv_share,

    period_totals.total_paid_orders,
    period_totals.total_gmv

FROM periods

CROSS JOIN value_bands

INNER JOIN period_totals
    ON period_totals.period = periods.period

LEFT JOIN band_stats
    ON band_stats.period = periods.period
   AND band_stats.order_value_band
       = value_bands.order_value_band;


CREATE UNIQUE INDEX IF NOT EXISTS
    idx_business_structure_order_value_summary
ON business_structure_order_value_summary(
    period,
    order_value_band
);


-- Validation:
-- For each period:
--   sum(order_count) = total paid orders
--   sum(gmv) = total GMV
--   sum(order_share) should be approximately 1
--   sum(gmv_share) should be approximately 1

SELECT
    period,

    SUM(order_count)
        AS summed_order_count,

    MAX(total_paid_orders)
        AS expected_total_paid_orders,

    ROUND(
        SUM(gmv),
        2
    ) AS summed_gmv,

    MAX(total_gmv)
        AS expected_total_gmv,

    ROUND(
        SUM(order_share),
        6
    ) AS summed_order_share,

    ROUND(
        SUM(gmv_share),
        6
    ) AS summed_gmv_share

FROM business_structure_order_value_summary

GROUP BY
    period_order,
    period

ORDER BY
    period_order;


-- Preview order value band results.

SELECT
    period,
    order_value_band,
    order_count,
    gmv,
    average_order_value,
    order_share,
    gmv_share

FROM business_structure_order_value_summary

ORDER BY
    period_order,
    band_order;


-- ============================================================================
-- 5. Customer state structure summary
--
-- Geography rule:
--   use customers.customer_state, not seller state
--
-- Customer count:
--   distinct customer_unique_id among paid delivered orders
--
-- Periods:
--   ALL_DATA
--   2017-01_to_2017-08
--   2018-01_to_2018-08
-- ============================================================================

DROP TABLE IF EXISTS business_structure_state_summary;

CREATE TABLE business_structure_state_summary AS
WITH periods AS (
    SELECT
        1 AS period_order,
        'ALL_DATA' AS period

    UNION ALL

    SELECT
        2 AS period_order,
        '2017-01_to_2017-08' AS period

    UNION ALL

    SELECT
        3 AS period_order,
        '2018-01_to_2018-08' AS period
),

states AS (
    SELECT DISTINCT
        customer_state
    FROM business_structure_order_base
    WHERE is_paid_delivered_order = 1
      AND customer_state IS NOT NULL
      AND TRIM(customer_state) <> ''
),

state_stats AS (
    SELECT
        'ALL_DATA' AS period,
        customer_state,

        COUNT(*) AS order_count,

        COUNT(
            DISTINCT customer_unique_id
        ) AS customer_count,

        ROUND(
            SUM(order_payment_amount),
            2
        ) AS gmv

    FROM business_structure_order_base

    WHERE is_paid_delivered_order = 1
      AND customer_state IS NOT NULL
      AND TRIM(customer_state) <> ''

    GROUP BY
        customer_state

    UNION ALL

    SELECT
        comparable_period AS period,
        customer_state,

        COUNT(*) AS order_count,

        COUNT(
            DISTINCT customer_unique_id
        ) AS customer_count,

        ROUND(
            SUM(order_payment_amount),
            2
        ) AS gmv

    FROM business_structure_order_base

    WHERE is_paid_delivered_order = 1
      AND comparable_period IS NOT NULL
      AND customer_state IS NOT NULL
      AND TRIM(customer_state) <> ''

    GROUP BY
        comparable_period,
        customer_state
),

period_totals AS (
    SELECT
        'ALL_DATA' AS period,

        COUNT(*) AS total_paid_orders,

        ROUND(
            SUM(order_payment_amount),
            2
        ) AS total_gmv

    FROM business_structure_order_base

    WHERE is_paid_delivered_order = 1

    UNION ALL

    SELECT
        comparable_period AS period,

        COUNT(*) AS total_paid_orders,

        ROUND(
            SUM(order_payment_amount),
            2
        ) AS total_gmv

    FROM business_structure_order_base

    WHERE is_paid_delivered_order = 1
      AND comparable_period IS NOT NULL

    GROUP BY
        comparable_period
),

combined AS (
    SELECT
        periods.period_order,
        periods.period,
        states.customer_state,

        COALESCE(
            state_stats.order_count,
            0
        ) AS order_count,

        COALESCE(
            state_stats.customer_count,
            0
        ) AS customer_count,

        COALESCE(
            state_stats.gmv,
            0
        ) AS gmv,

        CASE
            WHEN COALESCE(
                state_stats.order_count,
                0
            ) > 0
            THEN ROUND(
                state_stats.gmv
                / state_stats.order_count,
                2
            )
            ELSE NULL
        END AS average_order_value,

        ROUND(
            CAST(
                COALESCE(
                    state_stats.order_count,
                    0
                ) AS REAL
            ) / NULLIF(
                period_totals.total_paid_orders,
                0
            ),
            6
        ) AS order_share,

        ROUND(
            COALESCE(
                state_stats.gmv,
                0
            ) / NULLIF(
                period_totals.total_gmv,
                0
            ),
            6
        ) AS gmv_share,

        period_totals.total_paid_orders,
        period_totals.total_gmv

    FROM periods

    CROSS JOIN states

    INNER JOIN period_totals
        ON period_totals.period = periods.period

    LEFT JOIN state_stats
        ON state_stats.period = periods.period
       AND state_stats.customer_state
           = states.customer_state
)

SELECT
    period_order,
    period,
    customer_state,
    order_count,
    customer_count,
    gmv,
    average_order_value,
    order_share,
    gmv_share,

    ROW_NUMBER() OVER (
        PARTITION BY period
        ORDER BY
            gmv DESC,
            customer_state ASC
    ) AS gmv_rank,

    total_paid_orders,
    total_gmv

FROM combined;


CREATE UNIQUE INDEX IF NOT EXISTS
    idx_business_structure_state_summary
ON business_structure_state_summary(
    period,
    customer_state
);


CREATE INDEX IF NOT EXISTS
    idx_business_structure_state_rank
ON business_structure_state_summary(
    period,
    gmv_rank
);


-- Validation:
-- For each period:
--   sum(order_count) = total paid orders
--   sum(gmv) = total GMV
--   sum(order_share) should be approximately 1
--   sum(gmv_share) should be approximately 1

SELECT
    period,

    COUNT(*) AS state_count,

    SUM(order_count)
        AS summed_order_count,

    MAX(total_paid_orders)
        AS expected_total_paid_orders,

    ROUND(
        SUM(gmv),
        2
    ) AS summed_gmv,

    MAX(total_gmv)
        AS expected_total_gmv,

    ROUND(
        SUM(order_share),
        6
    ) AS summed_order_share,

    ROUND(
        SUM(gmv_share),
        6
    ) AS summed_gmv_share

FROM business_structure_state_summary

GROUP BY
    period_order,
    period

ORDER BY
    period_order;


-- Preview state structure results.

SELECT
    period,
    customer_state,
    order_count,
    customer_count,
    gmv,
    average_order_value,
    order_share,
    gmv_share,
    gmv_rank

FROM business_structure_state_summary

ORDER BY
    period_order,
    gmv_rank;


-- ============================================================================
-- 6. State concentration and comparable-period structural change
-- ============================================================================

-- 6.1 Geographic concentration indicators.

DROP TABLE IF EXISTS business_structure_state_concentration;

CREATE TABLE business_structure_state_concentration AS
SELECT
    period_order,
    period,

    ROUND(
        SUM(
            CASE
                WHEN gmv_rank <= 5
                THEN gmv_share
                ELSE 0
            END
        ),
        6
    ) AS top_5_gmv_share,

    ROUND(
        SUM(
            CASE
                WHEN gmv_rank <= 10
                THEN gmv_share
                ELSE 0
            END
        ),
        6
    ) AS top_10_gmv_share,

    ROUND(
        SUM(
            CASE
                WHEN gmv_rank <= 5
                THEN order_share
                ELSE 0
            END
        ),
        6
    ) AS top_5_order_share,

    ROUND(
        SUM(
            CASE
                WHEN gmv_rank <= 10
                THEN order_share
                ELSE 0
            END
        ),
        6
    ) AS top_10_order_share,

    -- HHI based on state GMV shares.
    -- Multiplying by 10,000 makes the index easier to interpret.
    ROUND(
        SUM(gmv_share * gmv_share) * 10000,
        2
    ) AS state_gmv_hhi,

    ROUND(
        SUM(order_share * order_share) * 10000,
        2
    ) AS state_order_hhi,

    COUNT(*) AS state_count

FROM business_structure_state_summary

GROUP BY
    period_order,
    period;


CREATE UNIQUE INDEX IF NOT EXISTS
    idx_business_structure_state_concentration
ON business_structure_state_concentration(period);


-- 6.2 Comparable-period state change.
--
-- High scale:
--   2018 GMV share is at least the equal-share benchmark, 1 / 27.
--
-- High growth:
--   state GMV growth is at least the platform-wide GMV growth rate
--   between the two comparable periods.

DROP TABLE IF EXISTS business_structure_state_change;

CREATE TABLE business_structure_state_change AS
WITH state_2017 AS (
    SELECT
        customer_state,

        order_count
            AS order_count_2017,

        customer_count
            AS customer_count_2017,

        gmv
            AS gmv_2017,

        average_order_value
            AS average_order_value_2017,

        order_share
            AS order_share_2017,

        gmv_share
            AS gmv_share_2017,

        gmv_rank
            AS gmv_rank_2017,

        total_paid_orders
            AS total_paid_orders_2017,

        total_gmv
            AS total_gmv_2017

    FROM business_structure_state_summary

    WHERE period = '2017-01_to_2017-08'
),

state_2018 AS (
    SELECT
        customer_state,

        order_count
            AS order_count_2018,

        customer_count
            AS customer_count_2018,

        gmv
            AS gmv_2018,

        average_order_value
            AS average_order_value_2018,

        order_share
            AS order_share_2018,

        gmv_share
            AS gmv_share_2018,

        gmv_rank
            AS gmv_rank_2018,

        total_paid_orders
            AS total_paid_orders_2018,

        total_gmv
            AS total_gmv_2018

    FROM business_structure_state_summary

    WHERE period = '2018-01_to_2018-08'
),

state_change AS (
    SELECT
        state_2018.customer_state,

        state_2017.order_count_2017,
        state_2018.order_count_2018,

        state_2017.customer_count_2017,
        state_2018.customer_count_2018,

        state_2017.gmv_2017,
        state_2018.gmv_2018,

        state_2017.average_order_value_2017,
        state_2018.average_order_value_2018,

        state_2017.order_share_2017,
        state_2018.order_share_2018,

        state_2017.gmv_share_2017,
        state_2018.gmv_share_2018,

        state_2017.gmv_rank_2017,
        state_2018.gmv_rank_2018,

        CASE
            WHEN state_2017.gmv_2017 > 0
            THEN ROUND(
                state_2018.gmv_2018
                / state_2017.gmv_2017
                - 1,
                6
            )
            ELSE NULL
        END AS gmv_growth_rate,

        CASE
            WHEN state_2017.order_count_2017 > 0
            THEN ROUND(
                CAST(state_2018.order_count_2018 AS REAL)
                / state_2017.order_count_2017
                - 1,
                6
            )
            ELSE NULL
        END AS order_growth_rate,

        CASE
            WHEN state_2017.customer_count_2017 > 0
            THEN ROUND(
                CAST(state_2018.customer_count_2018 AS REAL)
                / state_2017.customer_count_2017
                - 1,
                6
            )
            ELSE NULL
        END AS customer_growth_rate,

        CASE
            WHEN state_2017.average_order_value_2017 > 0
            THEN ROUND(
                state_2018.average_order_value_2018
                / state_2017.average_order_value_2017
                - 1,
                6
            )
            ELSE NULL
        END AS average_order_value_growth_rate,

        ROUND(
            state_2018.gmv_share_2018
            - state_2017.gmv_share_2017,
            6
        ) AS gmv_share_change,

        ROUND(
            state_2018.order_share_2018
            - state_2017.order_share_2017,
            6
        ) AS order_share_change,

        state_2018.total_gmv_2018
            / state_2017.total_gmv_2017
            - 1
            AS platform_gmv_growth_rate,

        1.0 / 27
            AS equal_state_share_benchmark

    FROM state_2018

    INNER JOIN state_2017
        ON state_2017.customer_state
           = state_2018.customer_state
)

SELECT
    customer_state,

    order_count_2017,
    order_count_2018,

    customer_count_2017,
    customer_count_2018,

    gmv_2017,
    gmv_2018,

    average_order_value_2017,
    average_order_value_2018,

    order_share_2017,
    order_share_2018,

    gmv_share_2017,
    gmv_share_2018,

    gmv_rank_2017,
    gmv_rank_2018,

    gmv_growth_rate,
    order_growth_rate,
    customer_growth_rate,
    average_order_value_growth_rate,

    gmv_share_change,
    order_share_change,

    ROUND(
        platform_gmv_growth_rate,
        6
    ) AS platform_gmv_growth_rate,

    ROUND(
        gmv_growth_rate
        - platform_gmv_growth_rate,
        6
    ) AS growth_gap_vs_platform,

    ROUND(
        equal_state_share_benchmark,
        6
    ) AS equal_state_share_benchmark,

    CASE
        WHEN gmv_share_2018 >= equal_state_share_benchmark
         AND gmv_growth_rate >= platform_gmv_growth_rate
        THEN 'HIGH_SCALE_HIGH_GROWTH'

        WHEN gmv_share_2018 >= equal_state_share_benchmark
         AND gmv_growth_rate < platform_gmv_growth_rate
        THEN 'HIGH_SCALE_LOW_GROWTH'

        WHEN gmv_share_2018 < equal_state_share_benchmark
         AND gmv_growth_rate >= platform_gmv_growth_rate
        THEN 'LOW_SCALE_HIGH_GROWTH'

        ELSE 'LOW_SCALE_LOW_GROWTH'
    END AS state_structure_segment

FROM state_change;


CREATE UNIQUE INDEX IF NOT EXISTS
    idx_business_structure_state_change
ON business_structure_state_change(customer_state);


CREATE INDEX IF NOT EXISTS
    idx_business_structure_state_segment
ON business_structure_state_change(state_structure_segment);


-- Preview geographic concentration.

SELECT
    period,
    top_5_gmv_share,
    top_10_gmv_share,
    top_5_order_share,
    top_10_order_share,
    state_gmv_hhi,
    state_order_hhi

FROM business_structure_state_concentration

ORDER BY period_order;


-- Preview state comparable-period changes.

SELECT
    customer_state,
    gmv_2017,
    gmv_2018,
    gmv_growth_rate,
    platform_gmv_growth_rate,
    growth_gap_vs_platform,
    gmv_share_2017,
    gmv_share_2018,
    gmv_share_change,
    state_structure_segment

FROM business_structure_state_change

ORDER BY
    gmv_2018 DESC;


-- Count states in each structural segment.

SELECT
    state_structure_segment,
    COUNT(*) AS state_count

FROM business_structure_state_change

GROUP BY state_structure_segment

ORDER BY state_structure_segment;
