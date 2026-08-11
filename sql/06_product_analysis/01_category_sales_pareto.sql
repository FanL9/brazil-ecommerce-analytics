/*
| 日期 | 修改人 | 版本号 | 备注 |
|---|---|---|---|
| 2026-08-11 | FL | v1.0 | 建立阶段四品类销售额帕累托结果表 |

Stage 4 category sales Pareto analysis (SQLite).

Upstream source:
  - category_sales_base

Grain:
  - category_pareto: one row per category_name.

The threshold rule compares the cumulative sales amount before the current
row with 80% of total sales. Therefore the first category that reaches or
crosses 80% is included in head, while subsequent categories are long_tail.
*/

DROP TABLE IF EXISTS category_pareto;

CREATE TABLE category_pareto AS
WITH ranked_categories AS (
    SELECT
        category_name,
        sales_amount,
        ROW_NUMBER() OVER (
            ORDER BY sales_amount DESC, category_name ASC
        ) AS sales_rank,
        SUM(sales_amount) OVER () AS total_sales_amount,
        SUM(sales_amount) OVER (
            ORDER BY sales_amount DESC, category_name ASC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_sales_amount
    FROM category_sales_base
),
pareto_metrics AS (
    SELECT
        category_name,
        sales_amount,
        sales_amount * 1.0 / NULLIF(total_sales_amount, 0) AS sales_share,
        cumulative_sales_amount,
        cumulative_sales_amount * 1.0
            / NULLIF(total_sales_amount, 0) AS cumulative_sales_share,
        sales_rank,
        CASE
            WHEN cumulative_sales_amount - sales_amount
                    < total_sales_amount * 0.80
                THEN 'head'
            ELSE 'long_tail'
        END AS category_type
    FROM ranked_categories
)
SELECT
    category_name,
    sales_amount,
    sales_share,
    cumulative_sales_amount,
    cumulative_sales_share,
    sales_rank,
    category_type
FROM pareto_metrics;

CREATE UNIQUE INDEX idx_category_pareto_category
    ON category_pareto (category_name);
