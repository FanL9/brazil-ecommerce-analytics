-- SQLite database is selected by the client connection; USE is not valid SQLite syntax.

---- 1. OVERALL ----
SELECT 'customers' AS table_name, COUNT(*) total_rows FROM customers
UNION ALL
SELECT 'geolocation', COUNT(*) FROM geolocation
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL
SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL
SELECT 'order_reviews', COUNT(*) FROM order_reviews
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'product_category_name_translation', COUNT(*) FROM product_category_name_translation
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'sellers', COUNT(*) FROM sellers;

---- 2. NULL DETECTION ----

-- 2.1 olist_customers_dataset
SELECT 'customer_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(customer_id IS NULL OR customer_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(customer_id IS NULL OR customer_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM customers
UNION all
SELECT 'customer_unique_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(customer_unique_id IS NULL OR customer_unique_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(customer_unique_id IS NULL OR customer_unique_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM customers
UNION ALL
SELECT 'customer_zip_code_prefix' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(customer_zip_code_prefix IS NULL OR customer_zip_code_prefix = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(customer_zip_code_prefix IS NULL OR customer_zip_code_prefix = '', 1, 0)) / COUNT(*) *100, 2) AS missing_pct
FROM customers
UNION ALL
SELECT 'customer_city' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(customer_city IS NULL OR customer_city = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(customer_city IS NULL OR customer_city = '', 1, 0)) / COUNT(*) *100, 2) AS missing_pct
FROM customers
UNION ALL
SELECT 'customer_state' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(customer_state IS NULL OR customer_state = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(customer_state IS NULL OR customer_state = '', 1, 0)) / COUNT(*) *100, 2) AS missing_pct
FROM customers;
-- no missing value

-- 2.2 olist_geolocation_dataset
SELECT 'geolocation_zip_code_prefix' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(geolocation_zip_code_prefix IS NULL OR geolocation_zip_code_prefix = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(geolocation_zip_code_prefix IS NULL OR geolocation_zip_code_prefix = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM geolocation
UNION ALL
SELECT 'geolocation_lat' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(geolocation_lat IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(geolocation_lat IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM geolocation
UNION ALL
SELECT 'geolocation_lng' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(geolocation_lng IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(geolocation_lng IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM geolocation
UNION ALL
SELECT 'geolocation_city' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(geolocation_city IS NULL OR geolocation_city = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(geolocation_city IS NULL OR geolocation_city = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM geolocation
UNION ALL
SELECT 'geolocation_state' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(geolocation_state IS NULL OR geolocation_state = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(geolocation_state IS NULL OR geolocation_state = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM geolocation;
-- no missing value

-- 2.3 olist_order_items_dataset
SELECT 'order_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(order_id IS NULL OR order_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(order_id IS NULL OR order_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items
UNION ALL
SELECT 'order_item_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(order_item_id IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(order_item_id IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items
UNION ALL
SELECT 'product_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(product_id IS NULL OR product_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(product_id IS NULL OR product_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items
UNION ALL
SELECT 'seller_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(seller_id IS NULL OR seller_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(seller_id IS NULL OR seller_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items
UNION ALL
SELECT 'shipping_limit_date' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(shipping_limit_date IS NULL OR shipping_limit_date = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(shipping_limit_date IS NULL OR shipping_limit_date = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items
UNION ALL
SELECT 'price' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(price IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(price IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items
UNION ALL
SELECT 'freight_value' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(freight_value IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(freight_value IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items;
-- no missing value

-- 2.4 olist_order_payments_dataset
SELECT 'order_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(order_id IS NULL OR order_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(order_id IS NULL OR order_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_payments
UNION ALL
SELECT 'payment_sequential' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(payment_sequential IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(payment_sequential IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_payments
UNION ALL
SELECT 'payment_type' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(payment_type IS NULL OR payment_type = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(payment_type IS NULL OR payment_type = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_payments
UNION ALL
SELECT 'payment_installments' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(payment_installments IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(payment_installments IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_payments
UNION ALL
SELECT 'payment_value' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(payment_value IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(payment_value IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_payments;
-- no missing value

-- 2.5 olist_order_review_dataset
SELECT 'review_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(review_id IS NULL OR review_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(review_id IS NULL OR review_id = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews
UNION all
SELECT 'order_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(order_id IS NULL OR order_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(order_id IS NULL OR order_id = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews
UNION ALL
SELECT 'review_score' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(review_score IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(review_score IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews
UNION ALL
SELECT 'review_comment_title' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(review_comment_title IS NULL OR review_comment_title = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(review_comment_title IS NULL OR review_comment_title = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews
UNION ALL
SELECT 'review_comment_message' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(review_comment_message IS NULL OR review_comment_message = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(review_comment_message IS NULL OR review_comment_message = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews
UNION ALL 
SELECT 'review_creation_date' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(review_creation_date IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(review_creation_date IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews
UNION ALL
SELECT 'review_answer_timestamp' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(review_answer_timestamp IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(review_answer_timestamp IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews;
-- have missing value

-- 2.6 olist_orders_dataset
SELECT 'order_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(order_id IS NULL OR order_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(order_id IS NULL OR order_id = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'customer_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(customer_id IS NULL OR customer_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(customer_id IS NULL OR customer_id = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'order_status' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(order_status IS NULL OR order_status = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(order_status IS NULL OR order_status = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'order_purchase_timestamp' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(order_purchase_timestamp IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(order_purchase_timestamp IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'order_approved_at' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(order_approved_at IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(order_approved_at IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'order_delivered_carrier_date' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(order_delivered_carrier_date IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(order_delivered_carrier_date IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'order_delivered_customer_date' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(order_delivered_customer_date IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(order_delivered_customer_date IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'order_estimated_delivery_date' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(order_estimated_delivery_date IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(order_estimated_delivery_date IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders;
-- have missing value

-- 2.7 olist_products_dataset
SELECT 'product_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(product_id IS NULL OR product_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(product_id IS NULL OR product_id = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_category_name' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(product_category_name IS NULL OR product_category_name = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(product_category_name IS NULL OR product_category_name = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_name_lenght' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(product_name_lenght IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(product_name_lenght IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_description_lenght' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(product_description_lenght IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(product_description_lenght IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_photos_qty' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(product_photos_qty IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(product_photos_qty IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_weight_g' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(product_weight_g IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(product_weight_g IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_length_cm' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(product_length_cm IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(product_length_cm IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_height_cm' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(product_height_cm IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(product_height_cm IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_width_cm' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(product_width_cm IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IIF(product_width_cm IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products;
-- have missing value

-- 2.8 olist_sellers_dataset
SELECT 'seller_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(seller_id IS NULL OR seller_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(seller_id IS NULL OR seller_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM sellers
UNION ALL
SELECT 'seller_zip_code_prefix' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(seller_zip_code_prefix IS NULL OR seller_zip_code_prefix = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(seller_zip_code_prefix IS NULL OR seller_zip_code_prefix = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM sellers
UNION ALL
SELECT 'seller_city' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(seller_city IS NULL OR seller_city = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(seller_city IS NULL OR seller_city = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM sellers
UNION ALL
SELECT 'seller_state' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(seller_state IS NULL OR seller_state = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(seller_state IS NULL OR seller_state = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM sellers;
-- no missing value 

-- 2.9 product_category_name_translation
SELECT 'product_category_name' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(product_category_name IS NULL OR product_category_name = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(product_category_name IS NULL OR product_category_name = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM product_category_name_translation
UNION ALL
SELECT 'product_category_name_english' AS variable,
       COUNT(*) AS total_records,
       SUM(IIF(product_category_name_english IS NULL OR product_category_name_english = '', 1, 0)) AS missing_count,
       ROUND(SUM(IIF(product_category_name_english IS NULL OR product_category_name_english = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM product_category_name_translation;
-- no missing value

---- 3. Duplicate Record Detection ----

-- 3.1 olist_customers_dataset
SELECT
customer_id,
customer_unique_id,
customer_zip_code_prefix,
customer_city,
customer_state,
COUNT(*) dup_count
FROM customers
GROUP BY customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state
HAVING COUNT(*) > 1;
-- no duplicate

-- 3.2 geolocation
SELECT
    geolocation_zip_code_prefix,
    geolocation_lat,
    geolocation_lng,
    geolocation_state,
    COUNT(*) AS dup_count
FROM geolocation
GROUP BY
    geolocation_zip_code_prefix,
    geolocation_lat,
    geolocation_lng,
    geolocation_state
HAVING COUNT(*) > 1;
-- duplicate

-- 3.3 olist_order_items_dataset
SELECT
    order_id,
    order_item_id,
    product_id,
    seller_id,
    shipping_limit_date,
    price,
    freight_value,
    COUNT(*) AS cnt
FROM order_items
GROUP BY
    order_id,
    order_item_id,
    product_id,
    seller_id,
    shipping_limit_date,
    price,
    freight_value
HAVING cnt > 1;
-- no duplicate

-- 3.4 order_payments
SELECT
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value,
    COUNT(*) AS cnt
FROM order_payments
GROUP BY
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value
HAVING cnt > 1;
-- no duplicate

-- 3.5 olist_order_review_dataset
SELECT
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date,
    review_answer_timestamp,
    COUNT(*) AS cnt
FROM order_reviews
GROUP BY
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date,
    review_answer_timestamp
HAVING cnt > 1;
-- no duplicate

-- 3.6 orders
SELECT
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    COUNT(*) AS cnt
FROM orders
GROUP BY
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date
HAVING cnt > 1;
-- no duplicate

-- 3.7 olist_products_dataset
SELECT
    product_id,
    product_category_name,
    product_name_lenght,
    product_description_lenght,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm,
    COUNT(*) AS cnt
FROM products
GROUP BY
    product_id,
    product_category_name,
    product_name_lenght,
    product_description_lenght,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm
HAVING cnt > 1;
-- no duplicate

-- 3.8 sellers
SELECT
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state,
    COUNT(*) AS cnt
FROM sellers
GROUP BY
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state
HAVING cnt > 1;
-- no duplicate

-- 3.9 product_category_name_translation
SELECT
    product_category_name,
    product_category_name_english,
    COUNT(*) AS cnt
FROM product_category_name_translation
GROUP BY
    product_category_name,
    product_category_name_english
HAVING cnt > 1;
-- no duplicate

---- 4. Check for duplicates of primary keys and business keys ----

-- 4.1 Detect duplicate orders
SELECT order_id, COUNT(*) AS cnt
FROM orders
GROUP BY order_id
HAVING COUNT(*) > 1;
-- no duplicate

-- 4.2 Detect duplicate customers
SELECT customer_id, COUNT(*) cnt
FROM orders
GROUP BY customer_id
HAVING COUNT(*)>1;
-- no duplicate

-- 4.3 Detect duplicate order-item records
SELECT order_id, order_item_id, COUNT(*) AS repeat_cnt
FROM order_items
GROUP BY order_id, order_item_id
HAVING COUNT(*) > 1;
-- no duplicate

-- 4.4 Detect duplicate payment sequential entries
SELECT order_id, payment_sequential, COUNT(*) AS repeat_cnt
FROM order_payments
GROUP BY order_id, payment_sequential
HAVING COUNT(*) >1;
-- no duplicate

-- 4.5 Detect duplicate review records
WITH dup_review AS (
SELECT review_id
FROM order_reviews
GROUP BY review_id
HAVING COUNT(*) > 1
)
SELECT
    r.review_id,
    r.review_comment_title,
    r.review_comment_message,
    COUNT(*) AS row_count
FROM order_reviews r
INNER JOIN dup_review d ON r.review_id = d.review_id
GROUP BY r.review_id, r.review_comment_title, r.review_comment_message
ORDER BY r.review_id;
-- duplicate

---- 5. Check referential integrity between tables ----

-- 5.1 Orders cannot be linked to customers
SELECT o.*
FROM orders o
LEFT JOIN customers c 
  ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;
-- normal

-- 5.2 Order-items cannot be linked to orders
SELECT oi.*
FROM order_items oi
LEFT JOIN orders o 
  ON oi.order_id = o.order_id
WHERE o.order_id IS NULL;
-- normal

-- 5.3 Products cannot be linked to product information
SELECT oi.*
FROM order_items oi
LEFT JOIN products p 
  ON oi.product_id = p.product_id
WHERE p.product_id IS NULL;
-- normal

-- 5.4 Payments cannot be linked to orders;
SELECT op.*
FROM order_payments op
LEFT JOIN orders o 
  ON op.order_id = o.order_id
WHERE o.order_id IS NULL;
-- normal

-- 5.5 Reviews cannot be linked to orders;
SELECT rv.*
FROM order_reviews rv
LEFT JOIN orders o 
  ON rv.order_id = o.order_id
WHERE o.order_id IS NULL;
-- normal

---- 6. Check monetary value anomalies ----

-- 6.1 Check NULL monetary values
SELECT *
FROM order_items
WHERE price IS NULL OR freight_value IS NULL;
-- normal

-- 6.2 Check zero monetary values
SELECT *
FROM order_items
WHERE price = 0 ;
-- normal

-- 6.3 Check negative monetary values
SELECT *
FROM order_items
WHERE price < 0 OR freight_value < 0;
-- normal

---- 7. Check time‑related anomalies ----

-- 7.1 Check time NULL values
SELECT *
FROM orders
WHERE
    order_purchase_timestamp IS NULL
    OR order_approved_at IS NULL
    OR order_delivered_carrier_date IS NULL
    OR order_delivered_customer_date IS NULL
    OR order_estimated_delivery_date IS NULL;
-- have missing values

-- 7.2 Check untranslatable / invalid timestamps
SELECT *
FROM orders
WHERE
    (order_purchase_timestamp IS NOT NULL AND datetime(order_purchase_timestamp) IS NULL)
 OR (order_approved_at IS NOT NULL AND datetime(order_approved_at) IS NULL)
 OR (order_delivered_carrier_date IS NOT NULL AND datetime(order_delivered_carrier_date) IS NULL)
 OR (order_delivered_customer_date IS NOT NULL AND datetime(order_delivered_customer_date) IS NULL)
 OR (order_estimated_delivery_date IS NOT NULL AND datetime(order_estimated_delivery_date) IS NULL);
-- normal

-- 7.3 Check wrong chronological order 
-- proper order：order_purchase_timestamp → order_approved_at → order_delivered_customer_date → order_purchase_timestamp
SELECT *
FROM orders
WHERE
    -- 审核早于下单
    datetime(order_approved_at) < datetime(order_purchase_timestamp)
    -- 交给物流早于审核
    OR datetime(order_delivered_carrier_date) < datetime(order_approved_at)
    -- 用户签收早于交给物流
    OR datetime(order_delivered_customer_date) < datetime(order_delivered_carrier_date)
    -- 实际签收早于下单
    OR datetime(order_delivered_customer_date) < datetime(order_purchase_timestamp);
-- have chronological error

---- 8. Check null‑key identifiers ----

-- 8.1 order_id
SELECT *
FROM orders
WHERE
    order_id IS NULL
    OR customer_id IS NULL;
-- no missing value

-- 8.2 customer_id and customer_unique_id
SELECT *
FROM customers
WHERE
    customer_id IS NULL
    OR customer_unique_id IS NULL;
-- no missing value

-- 8.3 product_id
-- 8.3 Check key ID null in order_items table
SELECT *
FROM order_items
WHERE
    order_id IS NULL
    OR product_id IS NULL;
-- no missing value

---- 9. IQR extreme-value detection (SQLite, nearest-rank quartiles) ----
-- Quantile rule: after removing NULL/unparseable values, sort by
-- (actual_value, record_key). Q1, median, and Q3 use deterministic nearest-rank
-- positions ceil(0.25*n), ceil(0.50*n), and ceil(0.75*n), respectively.
-- These TEMP views only identify/flag observations; they never change source rows.
DROP VIEW IF EXISTS temp.dq_numeric_values;
CREATE TEMP VIEW dq_numeric_values AS
SELECT
    'order_payments' AS source_table,
    'payment_value' AS field_name,
    order_id || ':' || payment_sequential AS record_key,
    CAST(payment_value AS REAL) AS actual_value
FROM order_payments
WHERE payment_value IS NOT NULL
UNION ALL
SELECT
    'order_payments',
    'payment_installments',
    order_id || ':' || payment_sequential,
    CAST(payment_installments AS REAL)
FROM order_payments
WHERE payment_installments IS NOT NULL
UNION ALL
SELECT
    'order_items',
    'price',
    order_id || ':' || order_item_id,
    CAST(price AS REAL)
FROM order_items
WHERE price IS NOT NULL
UNION ALL
SELECT
    'order_items',
    'freight_value',
    order_id || ':' || order_item_id,
    CAST(freight_value AS REAL)
FROM order_items
WHERE freight_value IS NOT NULL
UNION ALL
SELECT
    'orders',
    'actual_delivery_days',
    order_id,
    JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp)
FROM orders
WHERE order_purchase_timestamp IS NOT NULL
  AND order_delivered_customer_date IS NOT NULL
  AND JULIANDAY(order_purchase_timestamp) IS NOT NULL
  AND JULIANDAY(order_delivered_customer_date) IS NOT NULL;

DROP VIEW IF EXISTS temp.dq_numeric_ranked;
CREATE TEMP VIEW dq_numeric_ranked AS
SELECT
    source_table,
    field_name,
    record_key,
    actual_value,
    ROW_NUMBER() OVER (
        PARTITION BY source_table, field_name
        ORDER BY actual_value, record_key
    ) AS value_rank,
    COUNT(*) OVER (
        PARTITION BY source_table, field_name
    ) AS valid_count
FROM dq_numeric_values;

DROP VIEW IF EXISTS temp.dq_iqr_bounds;
CREATE TEMP VIEW dq_iqr_bounds AS
WITH quartiles AS (
    SELECT
        source_table,
        field_name,
        MAX(valid_count) AS valid_count,
        MIN(actual_value) AS min_value,
        MAX(CASE
                WHEN value_rank = CAST((valid_count + 3) / 4 AS INTEGER)
                THEN actual_value
            END) AS q1,
        MAX(CASE
                WHEN value_rank = CAST((valid_count + 1) / 2 AS INTEGER)
                THEN actual_value
            END) AS median,
        MAX(CASE
                WHEN value_rank = CAST((3 * valid_count + 3) / 4 AS INTEGER)
                THEN actual_value
            END) AS q3,
        MAX(actual_value) AS max_value
    FROM dq_numeric_ranked
    GROUP BY source_table, field_name
)
SELECT
    source_table,
    field_name,
    valid_count,
    min_value,
    q1,
    median,
    q3,
    max_value,
    q1 - 1.5 * (q3 - q1) AS lower_bound,
    q3 + 1.5 * (q3 - q1) AS upper_bound
FROM quartiles;

DROP VIEW IF EXISTS temp.dq_iqr_extreme_records;
CREATE TEMP VIEW dq_iqr_extreme_records AS
SELECT
    r.source_table,
    r.field_name,
    r.record_key,
    r.actual_value,
    b.lower_bound,
    b.upper_bound,
    CASE
        WHEN r.actual_value < b.lower_bound THEN 'lower'
        WHEN r.actual_value > b.upper_bound THEN 'upper'
    END AS extreme_direction
FROM dq_numeric_ranked AS r
INNER JOIN dq_iqr_bounds AS b
    ON b.source_table = r.source_table
   AND b.field_name = r.field_name
WHERE r.actual_value < b.lower_bound
   OR r.actual_value > b.upper_bound;

-- 9.1 Required field-level IQR summary.
SELECT
    b.source_table,
    b.field_name,
    b.valid_count,
    b.min_value,
    b.q1,
    b.median,
    b.q3,
    b.max_value,
    b.lower_bound,
    b.upper_bound,
    SUM(CASE WHEN e.extreme_direction = 'lower' THEN 1 ELSE 0 END) AS lower_extreme_count,
    SUM(CASE WHEN e.extreme_direction = 'upper' THEN 1 ELSE 0 END) AS upper_extreme_count
FROM dq_iqr_bounds AS b
LEFT JOIN dq_iqr_extreme_records AS e
    ON e.source_table = b.source_table
   AND e.field_name = b.field_name
GROUP BY
    b.source_table,
    b.field_name,
    b.valid_count,
    b.min_value,
    b.q1,
    b.median,
    b.q3,
    b.max_value,
    b.lower_bound,
    b.upper_bound
ORDER BY b.source_table, b.field_name;

-- 9.2 Record-level extreme inspection. Long-tail records remain unchanged.
SELECT
    source_table,
    field_name,
    record_key,
    actual_value,
    lower_bound,
    upper_bound,
    extreme_direction
FROM dq_iqr_extreme_records
ORDER BY source_table, field_name, extreme_direction, actual_value, record_key;

---- 10. Distinguish data errors, true extremes, and records needing review ----
-- Classification is evidence-based. IQR membership alone never means data_error.
DROP VIEW IF EXISTS temp.dq_classified_numeric_issues;
CREATE TEMP VIEW dq_classified_numeric_issues AS
-- Classify every IQR extreme record.
SELECT
    e.source_table,
    e.field_name,
    e.record_key,
    e.actual_value,
    CASE
        WHEN e.actual_value < 0 THEN 'data_error'
        WHEN e.source_table = 'orders'
         AND EXISTS (
             SELECT 1
             FROM orders AS o
             WHERE o.order_id = e.record_key
               AND (
                    DATETIME(o.order_approved_at) < DATETIME(o.order_purchase_timestamp)
                 OR DATETIME(o.order_delivered_carrier_date) < DATETIME(o.order_approved_at)
                 OR DATETIME(o.order_delivered_customer_date) < DATETIME(o.order_delivered_carrier_date)
                 OR DATETIME(o.order_delivered_customer_date) < DATETIME(o.order_purchase_timestamp)
               )
         ) THEN 'data_error'
        WHEN e.source_table = 'orders'
         AND EXISTS (
             SELECT 1
             FROM orders AS o
             WHERE o.order_id = e.record_key
               AND (o.order_approved_at IS NULL OR o.order_delivered_carrier_date IS NULL)
         ) THEN 'needs_review'
        WHEN e.source_table = 'order_items'
         AND e.field_name = 'freight_value'
         AND e.actual_value = 0 THEN 'needs_review'
        ELSE 'true_extreme'
    END AS classification
FROM dq_iqr_extreme_records AS e

UNION ALL

-- payment_value <= 0 is invalid for paid-order revenue analysis. These nine
-- zero-value rows are outside the IQR fences, so add them explicitly.
SELECT
    'order_payments',
    'payment_value',
    order_id || ':' || payment_sequential,
    CAST(payment_value AS REAL),
    'data_error'
FROM order_payments
WHERE payment_value <= 0
  AND NOT EXISTS (
      SELECT 1
      FROM dq_iqr_extreme_records AS e
      WHERE e.source_table = 'order_payments'
        AND e.field_name = 'payment_value'
        AND e.record_key = order_payments.order_id || ':' || order_payments.payment_sequential
  )

UNION ALL

-- Zero credit-card installments conflict with the semantic meaning of an
-- installment count, but the source alone cannot prove the intended value.
SELECT
    'order_payments',
    'payment_installments',
    order_id || ':' || payment_sequential,
    CAST(payment_installments AS REAL),
    'needs_review'
FROM order_payments
WHERE payment_installments <= 0
  AND NOT EXISTS (
      SELECT 1
      FROM dq_iqr_extreme_records AS e
      WHERE e.source_table = 'order_payments'
        AND e.field_name = 'payment_installments'
        AND e.record_key = order_payments.order_id || ':' || order_payments.payment_sequential
  )

UNION ALL

-- A delivered order must have an actual delivery timestamp to support delivery
-- analysis; no replacement value can be inferred, so exclude only from that view.
SELECT
    'orders',
    'actual_delivery_days',
    order_id,
    NULL,
    'data_error'
FROM orders
WHERE order_status = 'delivered'
  AND (
       order_purchase_timestamp IS NULL
    OR order_delivered_customer_date IS NULL
    OR JULIANDAY(order_purchase_timestamp) IS NULL
    OR JULIANDAY(order_delivered_customer_date) IS NULL
  );

-- 10.1 Required classification summary. Zero-count rows are retained so every
-- numeric field has all three controlled classifications represented.
WITH fields(source_table, field_name) AS (
    VALUES
        ('order_payments', 'payment_value'),
        ('order_payments', 'payment_installments'),
        ('order_items', 'price'),
        ('order_items', 'freight_value'),
        ('orders', 'actual_delivery_days')
),
classes(classification) AS (
    VALUES ('data_error'), ('true_extreme'), ('needs_review')
),
counts AS (
    SELECT
        source_table,
        field_name,
        classification,
        COUNT(*) AS record_count
    FROM dq_classified_numeric_issues
    GROUP BY source_table, field_name, classification
)
SELECT
    f.source_table,
    f.field_name,
    c.classification,
    COALESCE(n.record_count, 0) AS record_count,
    CASE
        WHEN c.classification = 'true_extreme'
            THEN 'Outside an IQR fence, but keys, relationships, sign, and available chronology are valid.'
        WHEN c.classification = 'needs_review' AND f.field_name = 'freight_value'
            THEN 'Zero freight can represent free shipping, but this cannot be proven from the source alone.'
        WHEN c.classification = 'needs_review' AND f.field_name = 'payment_installments'
            THEN 'Zero installments has no uniquely inferable correction.'
        WHEN c.classification = 'needs_review' AND f.field_name = 'actual_delivery_days'
            THEN 'Long delivery is plausible, but an intermediate timestamp is missing.'
        WHEN c.classification = 'data_error' AND f.field_name = 'payment_value'
            THEN 'Non-positive payment is invalid for paid-order revenue analysis.'
        WHEN c.classification = 'data_error' AND f.field_name = 'actual_delivery_days'
            THEN 'Delivered timestamp is missing/invalid or the available chronology is impossible.'
        ELSE 'No records met this classification rule.'
    END AS reason,
    CASE
        WHEN c.classification = 'data_error' THEN 'exclude'
        WHEN c.classification = 'true_extreme' THEN 'retain'
        ELSE 'flag'
    END AS recommended_action
FROM fields AS f
CROSS JOIN classes AS c
LEFT JOIN counts AS n
    ON n.source_table = f.source_table
   AND n.field_name = f.field_name
   AND n.classification = c.classification
ORDER BY f.source_table, f.field_name, c.classification;
