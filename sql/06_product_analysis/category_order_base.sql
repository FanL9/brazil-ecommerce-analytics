/*
| 日期 | 修改人 | 版本号 | 备注 |
|---|---|---|---|
| 2026-08-10 | FL | v1.0 | 建立阶段四品类公共数据层 |

Stage 4 category common layers (SQLite).

Source of truth:
  - docs/unified_analysis_standards.md
  - docs/category_analysis_dictionary.md

Run sql/02_data_cleaning/data_cleaning_rules.sql first.

Grains:
  - category_item_base: one row per delivered order item
    (order_id + order_item_id).
  - category_order_base: one row per delivered order-category combination
    (order_id + category_name).

Category resolution:
  use the English translation when it exists; otherwise use "unknown". This
  includes source categories that are missing from the translation table.
*/

DROP TABLE IF EXISTS category_order_base;
DROP TABLE IF EXISTS category_item_base;

CREATE TABLE category_item_base AS
SELECT
    i.order_id,
    i.order_item_id,
    i.product_id,
    COALESCE(
        NULLIF(TRIM(t.product_category_name_english), ''),
        'unknown'
    ) AS category_name,
    o.order_purchase_timestamp AS purchase_timestamp,
    STRFTIME('%Y-%m', o.order_purchase_timestamp) AS purchase_month,
    CAST(i.price AS REAL) AS price,
    CAST(i.freight_value AS REAL) AS freight_value
FROM vw_orders_clean AS o
INNER JOIN vw_order_items_clean AS i
    ON i.order_id = o.order_id
INNER JOIN products AS p
    ON p.product_id = i.product_id
LEFT JOIN product_category_name_translation AS t
    ON t.product_category_name = p.product_category_name
WHERE o.order_status = 'delivered'
  AND o.order_id IS NOT NULL
  AND o.order_purchase_timestamp IS NOT NULL
  AND DATETIME(o.order_purchase_timestamp) IS NOT NULL;

CREATE UNIQUE INDEX idx_category_item_base_order_item
    ON category_item_base (order_id, order_item_id);
CREATE INDEX idx_category_item_base_category
    ON category_item_base (category_name);
CREATE INDEX idx_category_item_base_purchase_month
    ON category_item_base (purchase_month);
CREATE INDEX idx_category_item_base_product
    ON category_item_base (product_id);

CREATE TABLE category_order_base AS
SELECT
    order_id,
    category_name,
    purchase_month,
    COUNT(*) AS category_item_count,
    SUM(price) AS category_sales_amount
FROM category_item_base
GROUP BY
    order_id,
    category_name,
    purchase_month;

CREATE UNIQUE INDEX idx_category_order_base_order_category
    ON category_order_base (order_id, category_name);
CREATE INDEX idx_category_order_base_category
    ON category_order_base (category_name);
CREATE INDEX idx_category_order_base_order
    ON category_order_base (order_id);
