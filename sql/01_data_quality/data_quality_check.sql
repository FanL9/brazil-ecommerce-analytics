USE brazil_ecommerce_db;

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
       SUM(IF(customer_id IS NULL OR customer_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(customer_id IS NULL OR customer_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM customers
UNION all
SELECT 'customer_unique_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(customer_unique_id IS NULL OR customer_unique_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(customer_unique_id IS NULL OR customer_unique_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM customers
UNION ALL
SELECT 'customer_zip_code_prefix' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(customer_zip_code_prefix IS NULL OR customer_zip_code_prefix = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(customer_zip_code_prefix IS NULL OR customer_zip_code_prefix = '', 1, 0)) / COUNT(*) *100, 2) AS missing_pct
FROM customers
UNION ALL
SELECT 'customer_city' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(customer_city IS NULL OR customer_city = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(customer_city IS NULL OR customer_city = '', 1, 0)) / COUNT(*) *100, 2) AS missing_pct
FROM customers
UNION ALL
SELECT 'customer_state' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(customer_state IS NULL OR customer_state = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(customer_state IS NULL OR customer_state = '', 1, 0)) / COUNT(*) *100, 2) AS missing_pct
FROM customers;
-- no missing value

-- 2.2 olist_geolocation_dataset
SELECT 'geolocation_zip_code_prefix' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(geolocation_zip_code_prefix IS NULL OR geolocation_zip_code_prefix = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(geolocation_zip_code_prefix IS NULL OR geolocation_zip_code_prefix = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM geolocation
UNION ALL
SELECT 'geolocation_lat' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(geolocation_lat IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(geolocation_lat IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM geolocation
UNION ALL
SELECT 'geolocation_lng' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(geolocation_lng IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(geolocation_lng IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM geolocation
UNION ALL
SELECT 'geolocation_city' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(geolocation_city IS NULL OR geolocation_city = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(geolocation_city IS NULL OR geolocation_city = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM geolocation
UNION ALL
SELECT 'geolocation_state' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(geolocation_state IS NULL OR geolocation_state = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(geolocation_state IS NULL OR geolocation_state = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM geolocation;
-- no missing value

-- 2.3 olist_order_items_dataset
SELECT 'order_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(order_id IS NULL OR order_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(order_id IS NULL OR order_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items
UNION ALL
SELECT 'order_item_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(order_item_id IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(order_item_id IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items
UNION ALL
SELECT 'product_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(product_id IS NULL OR product_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(product_id IS NULL OR product_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items
UNION ALL
SELECT 'seller_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(seller_id IS NULL OR seller_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(seller_id IS NULL OR seller_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items
UNION ALL
SELECT 'shipping_limit_date' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(shipping_limit_date IS NULL OR shipping_limit_date = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(shipping_limit_date IS NULL OR shipping_limit_date = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items
UNION ALL
SELECT 'price' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(price IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(price IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items
UNION ALL
SELECT 'freight_value' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(freight_value IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(freight_value IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_items;
-- no missing value

-- 2.4 olist_order_payments_dataset
SELECT 'order_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(order_id IS NULL OR order_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(order_id IS NULL OR order_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_payments
UNION ALL
SELECT 'payment_sequential' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(payment_sequential IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(payment_sequential IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_payments
UNION ALL
SELECT 'payment_type' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(payment_type IS NULL OR payment_type = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(payment_type IS NULL OR payment_type = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_payments
UNION ALL
SELECT 'payment_installments' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(payment_installments IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(payment_installments IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_payments
UNION ALL
SELECT 'payment_value' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(payment_value IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(payment_value IS NULL, 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM order_payments;
-- no missing value

-- 2.5 olist_order_review_dataset
SELECT 'review_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(review_id IS NULL OR review_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(review_id IS NULL OR review_id = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews
UNION all
SELECT 'order_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(order_id IS NULL OR order_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(order_id IS NULL OR order_id = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews
UNION ALL
SELECT 'review_score' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(review_score IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(review_score IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews
UNION ALL
SELECT 'review_comment_title' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(review_comment_title IS NULL OR review_comment_title = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(review_comment_title IS NULL OR review_comment_title = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews
UNION ALL
SELECT 'review_comment_message' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(review_comment_message IS NULL OR review_comment_message = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(review_comment_message IS NULL OR review_comment_message = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews
UNION ALL 
SELECT 'review_creation_date' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(review_creation_date IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(review_creation_date IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews
UNION ALL
SELECT 'review_answer_timestamp' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(review_answer_timestamp IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(review_answer_timestamp IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM order_reviews;
-- have missing value

-- 2.6 olist_orders_dataset
SELECT 'order_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(order_id IS NULL OR order_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(order_id IS NULL OR order_id = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'customer_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(customer_id IS NULL OR customer_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(customer_id IS NULL OR customer_id = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'order_status' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(order_status IS NULL OR order_status = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(order_status IS NULL OR order_status = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'order_purchase_timestamp' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(order_purchase_timestamp IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(order_purchase_timestamp IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'order_approved_at' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(order_approved_at IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(order_approved_at IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'order_delivered_carrier_date' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(order_delivered_carrier_date IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(order_delivered_carrier_date IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'order_delivered_customer_date' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(order_delivered_customer_date IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(order_delivered_customer_date IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders
UNION ALL
SELECT 'order_estimated_delivery_date' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(order_estimated_delivery_date IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(order_estimated_delivery_date IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM orders;
-- have missing value

-- 2.7 olist_products_dataset
SELECT 'product_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(product_id IS NULL OR product_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(product_id IS NULL OR product_id = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_category_name' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(product_category_name IS NULL OR product_category_name = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(product_category_name IS NULL OR product_category_name = '', 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_name_lenght' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(product_name_lenght IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(product_name_lenght IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_description_lenght' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(product_description_lenght IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(product_description_lenght IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_photos_qty' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(product_photos_qty IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(product_photos_qty IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_weight_g' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(product_weight_g IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(product_weight_g IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_length_cm' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(product_length_cm IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(product_length_cm IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_height_cm' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(product_height_cm IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(product_height_cm IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products
UNION ALL
SELECT 'product_width_cm' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(product_width_cm IS NULL, 1, 0)) AS missing_count,
       ROUND(SUM(IF(product_width_cm IS NULL, 1, 0)) * 100.0 / COUNT(*), 2) AS missing_pct
FROM products;
-- have missing value

-- 2.8 olist_sellers_dataset
SELECT 'seller_id' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(seller_id IS NULL OR seller_id = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(seller_id IS NULL OR seller_id = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM sellers
UNION ALL
SELECT 'seller_zip_code_prefix' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(seller_zip_code_prefix IS NULL OR seller_zip_code_prefix = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(seller_zip_code_prefix IS NULL OR seller_zip_code_prefix = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM sellers
UNION ALL
SELECT 'seller_city' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(seller_city IS NULL OR seller_city = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(seller_city IS NULL OR seller_city = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM sellers
UNION ALL
SELECT 'seller_state' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(seller_state IS NULL OR seller_state = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(seller_state IS NULL OR seller_state = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM sellers;
-- no missing value 

-- 2.9 product_category_name_translation
SELECT 'product_category_name' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(product_category_name IS NULL OR product_category_name = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(product_category_name IS NULL OR product_category_name = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
FROM product_category_name_translation
UNION ALL
SELECT 'product_category_name_english' AS variable,
       COUNT(*) AS total_records,
       SUM(IF(product_category_name_english IS NULL OR product_category_name_english = '', 1, 0)) AS missing_count,
       ROUND(SUM(IF(product_category_name_english IS NULL OR product_category_name_english = '', 1, 0)) / COUNT(*) * 100, 2) AS missing_pct
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
