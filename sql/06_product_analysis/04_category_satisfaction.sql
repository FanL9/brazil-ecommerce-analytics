-- Stage 4 - Member 3
-- Category satisfaction analysis
-- Highest-priority standard:
-- docs/unified_analysis_standards.md
--
-- Grain of upstream category data:
--   category_order_base = one row per order_id + category_name
--
-- Review source:
--   vw_order_reviews_order_level = one representative review per order
--
-- Important:
--   The same order may belong to multiple categories.
--   Therefore category review-order counts overlap across categories and
--   must not be summed to reconcile to platform-level unique review orders.

DROP TABLE IF EXISTS category_satisfaction;

CREATE TABLE category_satisfaction AS

WITH order_category_review AS (
    SELECT
        cob.order_id,
        cob.category_name,
        r.review_score,
        r.review_comment_message
    FROM category_order_base AS cob
    LEFT JOIN vw_order_reviews_order_level AS r
        ON cob.order_id = r.order_id
),

category_agg AS (
    SELECT
        category_name,

        COUNT(
            DISTINCT CASE
                WHEN review_score BETWEEN 1 AND 5
                THEN order_id
            END
        ) AS valid_review_orders,

        AVG(
            CASE
                WHEN review_score BETWEEN 1 AND 5
                THEN CAST(review_score AS REAL)
            END
        ) AS avg_review_score,

        COUNT(
            DISTINCT CASE
                WHEN review_score = 1
                THEN order_id
            END
        ) AS one_star_review_orders,

        COUNT(
            DISTINCT CASE
                WHEN review_score IN (4, 5)
                THEN order_id
            END
        ) AS positive_4_5_review_orders,

        COUNT(
            DISTINCT CASE
                WHEN review_score = 1
                     AND review_comment_message IS NOT NULL
                     AND TRIM(review_comment_message) <> ''
                THEN order_id
            END
        ) AS negative_text_review_orders

    FROM order_category_review
    GROUP BY category_name
)

SELECT
    category_name,
    valid_review_orders,
    avg_review_score,
    one_star_review_orders,

    CASE
        WHEN valid_review_orders = 0 THEN NULL
        ELSE CAST(one_star_review_orders AS REAL)
             / valid_review_orders
    END AS one_star_rate,

    positive_4_5_review_orders,

    CASE
        WHEN valid_review_orders = 0 THEN NULL
        ELSE CAST(positive_4_5_review_orders AS REAL)
             / valid_review_orders
    END AS positive_4_5_rate,

    negative_text_review_orders,

    CASE
        WHEN valid_review_orders >= 30 THEN 'eligible'
        ELSE 'small_sample'
    END AS sample_status

FROM category_agg
ORDER BY
    CASE WHEN valid_review_orders >= 30 THEN 0 ELSE 1 END,
    avg_review_score ASC,
    one_star_rate DESC,
    category_name ASC
;

CREATE UNIQUE INDEX IF NOT EXISTS
idx_category_satisfaction_category
ON category_satisfaction(category_name);
