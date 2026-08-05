/*
11. Data-cleaning rules for downstream analysis (SQLite)

The nine source tables are immutable. This script only recreates analysis views,
uses deterministic rules, and is safe to run repeatedly.
*/

-- Drop dependent views before their bases so repeated execution is deterministic.
DROP VIEW IF EXISTS vw_order_reviews_order_level;
DROP VIEW IF EXISTS vw_order_reviews_clean;
DROP VIEW IF EXISTS vw_delivery_analysis_clean;
DROP VIEW IF EXISTS vw_orders_clean;
DROP VIEW IF EXISTS vw_order_payments_clean;
DROP VIEW IF EXISTS vw_order_items_clean;
DROP VIEW IF EXISTS vw_geolocation_deduplicated;

/*
View: vw_orders_clean
处理的问题：关键 ID、核心购买时间、客户关联错误，以及可选时间缺失/时序异常。
处理方式：明确错误从通用订单视图排除；不影响通用订单分析的可选时间缺失仅标记。
去重或排除条件：排除空 order_id/customer_id、不可解析购买/预计时间及孤立 customer_id；
订单主键已由数据库保证唯一，因此不额外去重。
保留条件：所有关键字段及客户关联有效的订单，包括尚未签收订单和长配送订单。
影响指标：订单量、取消率使用本视图；配送类指标使用更严格的专用视图。
*/
CREATE VIEW vw_orders_clean AS
SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    CASE WHEN o.order_approved_at IS NULL THEN 1 ELSE 0 END AS is_missing_approval_timestamp,
    CASE WHEN o.order_delivered_carrier_date IS NULL THEN 1 ELSE 0 END AS is_missing_carrier_timestamp,
    CASE WHEN o.order_delivered_customer_date IS NULL THEN 1 ELSE 0 END AS is_missing_delivery_timestamp,
    CASE
        WHEN DATETIME(o.order_approved_at) < DATETIME(o.order_purchase_timestamp)
          OR DATETIME(o.order_delivered_carrier_date) < DATETIME(o.order_approved_at)
          OR DATETIME(o.order_delivered_customer_date) < DATETIME(o.order_delivered_carrier_date)
          OR DATETIME(o.order_delivered_customer_date) < DATETIME(o.order_purchase_timestamp)
        THEN 1 ELSE 0
    END AS has_chronology_error
FROM orders AS o
WHERE o.order_id IS NOT NULL
  AND o.customer_id IS NOT NULL
  AND o.order_purchase_timestamp IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL
  AND DATETIME(o.order_purchase_timestamp) IS NOT NULL
  AND DATETIME(o.order_estimated_delivery_date) IS NOT NULL
  AND EXISTS (
      SELECT 1
      FROM customers AS c
      WHERE c.customer_id = o.customer_id
  );

/*
View: vw_delivery_analysis_clean
处理的问题：配送日期缺失/不可解析、签收早于下单，以及中间环节时序异常。
处理方式：只排除会使首尾配送时长无效的记录；中间时序异常保留并标记；
合法长尾保留并标记 IQR 极端值。
去重或排除条件：order_id 已唯一；只排除无法计算或 delivery_days<0。
保留条件：签收不早于下单的可计算订单，包括中间时序异常和合法长尾。
影响指标：平均配送时长、延迟送达率及物流长尾分析。
*/
CREATE VIEW vw_delivery_analysis_clean AS
WITH all_computable_values AS (
    SELECT
        order_id,
        JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp) AS delivery_days,
        has_chronology_error
    FROM vw_orders_clean
    WHERE order_delivered_customer_date IS NOT NULL
      AND JULIANDAY(order_delivered_customer_date) IS NOT NULL
      AND JULIANDAY(order_purchase_timestamp) IS NOT NULL
),
valid_values AS (
    SELECT
        order_id,
        delivery_days,
        has_chronology_error
    FROM all_computable_values
    WHERE delivery_days >= 0
),
ranked AS (
    SELECT
        order_id,
        delivery_days,
        ROW_NUMBER() OVER (ORDER BY delivery_days, order_id) AS value_rank,
        COUNT(*) OVER () AS valid_count
    FROM valid_values
),
quartiles AS (
    SELECT
        MAX(CASE WHEN value_rank = CAST((valid_count + 3) / 4 AS INTEGER) THEN delivery_days END) AS q1,
        MAX(CASE WHEN value_rank = CAST((3 * valid_count + 3) / 4 AS INTEGER) THEN delivery_days END) AS q3
    FROM ranked
)
SELECT
    o.order_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    r.delivery_days,
    r.has_chronology_error AS has_intermediate_chronology_error,
    CASE
        WHEN r.delivery_days < q.q1 - 1.5 * (q.q3 - q.q1)
          OR r.delivery_days > q.q3 + 1.5 * (q.q3 - q.q1)
        THEN 1 ELSE 0
    END AS is_delivery_iqr_extreme
FROM valid_values AS r
INNER JOIN vw_orders_clean AS o
    ON o.order_id = r.order_id
CROSS JOIN quartiles AS q;

/*
View: vw_order_payments_clean
处理的问题：非正支付金额、无效业务键/订单关联，以及支付金额长尾和零分期疑点。
处理方式：payment_value<=0 从付费金额分析排除；零分期保留并标记；长尾保留并标记。
去重或排除条件：按真实业务键 (order_id,payment_sequential)；数据库已保证唯一，
不把同订单多次合法支付错误去重。
保留条件：订单关联有效、payment_value>0、payment_installments>=0 的支付记录。
影响指标：GMV、客单价、历史 LTV；零分期仅影响分期行为分析。
*/
CREATE VIEW vw_order_payments_clean AS
WITH values_ranked AS (
    SELECT
        order_id,
        payment_sequential,
        CAST(payment_value AS REAL) AS actual_value,
        ROW_NUMBER() OVER (ORDER BY payment_value, order_id, payment_sequential) AS value_rank,
        COUNT(*) OVER () AS valid_count
    FROM order_payments
    WHERE payment_value IS NOT NULL
),
quartiles AS (
    SELECT
        MAX(CASE WHEN value_rank = CAST((valid_count + 3) / 4 AS INTEGER) THEN actual_value END) AS q1,
        MAX(CASE WHEN value_rank = CAST((3 * valid_count + 3) / 4 AS INTEGER) THEN actual_value END) AS q3
    FROM values_ranked
)
SELECT
    p.order_id,
    p.payment_sequential,
    p.payment_type,
    p.payment_installments,
    p.payment_value,
    CASE WHEN p.payment_installments = 0 THEN 1 ELSE 0 END AS needs_installment_review,
    CASE
        WHEN p.payment_value < q.q1 - 1.5 * (q.q3 - q.q1)
          OR p.payment_value > q.q3 + 1.5 * (q.q3 - q.q1)
        THEN 1 ELSE 0
    END AS is_payment_value_iqr_extreme
FROM order_payments AS p
CROSS JOIN quartiles AS q
WHERE p.order_id IS NOT NULL
  AND p.payment_sequential IS NOT NULL
  AND p.payment_value > 0
  AND p.payment_installments >= 0
  AND EXISTS (
      SELECT 1
      FROM orders AS o
      WHERE o.order_id = p.order_id
  );

/*
View: vw_order_items_clean
处理的问题：金额空值/负值、关键关联错误，以及价格和运费 IQR 长尾。
处理方式：明确金额/关联错误排除；合法低运费、高运费和高价格全部保留并标记。
去重或排除条件：按业务键 (order_id,order_item_id)，不删除同订单的多商品行。
保留条件：order/product/seller 关联有效，price>=0、freight_value>=0。
影响指标：商品销售额、品类分析、运费分析。
*/
CREATE VIEW vw_order_items_clean AS
WITH price_ranked AS (
    SELECT
        order_id,
        order_item_id,
        CAST(price AS REAL) AS actual_value,
        ROW_NUMBER() OVER (ORDER BY price, order_id, order_item_id) AS value_rank,
        COUNT(*) OVER () AS valid_count
    FROM order_items
    WHERE price IS NOT NULL
),
price_quartiles AS (
    SELECT
        MAX(CASE WHEN value_rank = CAST((valid_count + 3) / 4 AS INTEGER) THEN actual_value END) AS q1,
        MAX(CASE WHEN value_rank = CAST((3 * valid_count + 3) / 4 AS INTEGER) THEN actual_value END) AS q3
    FROM price_ranked
),
freight_ranked AS (
    SELECT
        order_id,
        order_item_id,
        CAST(freight_value AS REAL) AS actual_value,
        ROW_NUMBER() OVER (ORDER BY freight_value, order_id, order_item_id) AS value_rank,
        COUNT(*) OVER () AS valid_count
    FROM order_items
    WHERE freight_value IS NOT NULL
),
freight_quartiles AS (
    SELECT
        MAX(CASE WHEN value_rank = CAST((valid_count + 3) / 4 AS INTEGER) THEN actual_value END) AS q1,
        MAX(CASE WHEN value_rank = CAST((3 * valid_count + 3) / 4 AS INTEGER) THEN actual_value END) AS q3
    FROM freight_ranked
)
SELECT
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    i.shipping_limit_date,
    i.price,
    i.freight_value,
    CASE
        WHEN i.price < pq.q1 - 1.5 * (pq.q3 - pq.q1)
          OR i.price > pq.q3 + 1.5 * (pq.q3 - pq.q1)
        THEN 1 ELSE 0
    END AS is_price_iqr_extreme,
    CASE
        WHEN i.freight_value < fq.q1 - 1.5 * (fq.q3 - fq.q1)
          OR i.freight_value > fq.q3 + 1.5 * (fq.q3 - fq.q1)
        THEN 1 ELSE 0
    END AS is_freight_iqr_extreme,
    CASE WHEN i.freight_value = 0 THEN 1 ELSE 0 END AS needs_zero_freight_review
FROM order_items AS i
CROSS JOIN price_quartiles AS pq
CROSS JOIN freight_quartiles AS fq
WHERE i.order_id IS NOT NULL
  AND i.order_item_id IS NOT NULL
  AND i.product_id IS NOT NULL
  AND i.seller_id IS NOT NULL
  AND i.price >= 0
  AND i.freight_value >= 0
  AND EXISTS (SELECT 1 FROM orders AS o WHERE o.order_id = i.order_id)
  AND EXISTS (SELECT 1 FROM products AS p WHERE p.product_id = i.product_id)
  AND EXISTS (SELECT 1 FROM sellers AS s WHERE s.seller_id = i.seller_id);

/*
View: vw_geolocation_deduplicated
处理的问题：完全相同的地理业务记录重复；邮编的一对多坐标不是错误。
处理方式：deduplicate。
去重或排除条件：按邮编、经纬度、城市、州分区，ROW_NUMBER 按 geolocation_id 升序保留首行。
保留条件：同一邮编但经纬度/城市/州不同的合法一对多记录全部保留。
影响指标：邮编地域映射与地图聚合，避免完全重复点获得额外权重。
*/
CREATE VIEW vw_geolocation_deduplicated AS
WITH ranked AS (
    SELECT
        geolocation_id,
        geolocation_zip_code_prefix,
        geolocation_lat,
        geolocation_lng,
        geolocation_city,
        geolocation_state,
        ROW_NUMBER() OVER (
            PARTITION BY
                geolocation_zip_code_prefix,
                geolocation_lat,
                geolocation_lng,
                geolocation_city,
                geolocation_state
            ORDER BY geolocation_id
        ) AS duplicate_rank
    FROM geolocation
)
SELECT
    geolocation_id,
    geolocation_zip_code_prefix,
    geolocation_lat,
    geolocation_lng,
    geolocation_city,
    geolocation_state
FROM ranked
WHERE duplicate_rank = 1;

/*
View: vw_order_reviews_clean
处理的问题：评论关键字段、评分范围和订单关联错误。
处理方式：明确错误排除；同订单多条合法评论全部保留，不在基础视图误删。
去重或排除条件：以数据库真实复合键 (review_id,order_id) 为准；不按 order_id 强行去重。
保留条件：订单存在且评分在 1 至 5；标题/正文缺失属于可选文本，不填补也不排除。
影响指标：评论明细分析；好评率应使用下方订单级代表评论视图。
*/
CREATE VIEW vw_order_reviews_clean AS
SELECT
    r.review_id,
    r.order_id,
    r.review_score,
    r.review_comment_title,
    r.review_comment_message,
    r.review_creation_date,
    r.review_answer_timestamp
FROM order_reviews AS r
WHERE r.review_id IS NOT NULL
  AND r.order_id IS NOT NULL
  AND r.review_score BETWEEN 1 AND 5
  AND DATETIME(r.review_creation_date) IS NOT NULL
  AND DATETIME(r.review_answer_timestamp) IS NOT NULL
  AND EXISTS (
      SELECT 1
      FROM orders AS o
      WHERE o.order_id = r.order_id
  );

/*
View: vw_order_reviews_order_level
处理的问题：好评率需要一单一条代表评论，但同订单多评论可以是合法历史。
处理方式：deduplicate only for the order-level analytical projection。
去重或排除条件：ROW_NUMBER 按有效评分优先、回答时间降序、创建时间降序、review_id 降序；
order_id 是分区键，排序字段构成确定性选择规则。
保留条件：基础评论视图中的所有订单各保留一条代表评论；原始及基础评论明细不删除。
影响指标：有评论订单数、好评订单数和好评率。
*/
CREATE VIEW vw_order_reviews_order_level AS
WITH ranked AS (
    SELECT
        review_id,
        order_id,
        review_score,
        review_comment_title,
        review_comment_message,
        review_creation_date,
        review_answer_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY
                CASE WHEN review_score BETWEEN 1 AND 5 THEN 0 ELSE 1 END,
                review_answer_timestamp DESC,
                review_creation_date DESC,
                review_id DESC
        ) AS review_rank
    FROM vw_order_reviews_clean
)
SELECT
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date,
    review_answer_timestamp
FROM ranked
WHERE review_rank = 1;
