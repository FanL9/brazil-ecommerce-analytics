PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT NOT NULL PRIMARY KEY,
    customer_unique_id TEXT NOT NULL,
    customer_zip_code_prefix TEXT NOT NULL,
    customer_city TEXT NOT NULL,
    customer_state TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS geolocation (
    geolocation_id INTEGER PRIMARY KEY,
    geolocation_zip_code_prefix TEXT NOT NULL,
    geolocation_lat REAL NOT NULL,
    geolocation_lng REAL NOT NULL,
    geolocation_city TEXT NOT NULL,
    geolocation_state TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id TEXT NOT NULL PRIMARY KEY,
    product_category_name TEXT,
    product_name_lenght INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g INTEGER,
    product_length_cm INTEGER,
    product_height_cm INTEGER,
    product_width_cm INTEGER
);

CREATE TABLE IF NOT EXISTS sellers (
    seller_id TEXT NOT NULL PRIMARY KEY,
    seller_zip_code_prefix TEXT NOT NULL,
    seller_city TEXT NOT NULL,
    seller_state TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS product_category_name_translation (
    product_category_name TEXT NOT NULL PRIMARY KEY,
    product_category_name_english TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT NOT NULL PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_status TEXT NOT NULL,
    order_purchase_timestamp TEXT NOT NULL,
    order_approved_at TEXT,
    order_delivered_carrier_date TEXT,
    order_delivered_customer_date TEXT,
    order_estimated_delivery_date TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id TEXT NOT NULL,
    order_item_id INTEGER NOT NULL,
    product_id TEXT NOT NULL,
    seller_id TEXT NOT NULL,
    shipping_limit_date TEXT NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    freight_value REAL NOT NULL CHECK (freight_value >= 0),
    PRIMARY KEY (order_id, order_item_id),
    FOREIGN KEY (order_id) REFERENCES orders (order_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id),
    FOREIGN KEY (seller_id) REFERENCES sellers (seller_id)
);

CREATE TABLE IF NOT EXISTS order_payments (
    order_id TEXT NOT NULL,
    payment_sequential INTEGER NOT NULL,
    payment_type TEXT NOT NULL,
    payment_installments INTEGER NOT NULL CHECK (payment_installments >= 0),
    payment_value REAL NOT NULL CHECK (payment_value >= 0),
    PRIMARY KEY (order_id, payment_sequential),
    FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

CREATE TABLE IF NOT EXISTS order_reviews (
    review_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    review_score INTEGER NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TEXT NOT NULL,
    review_answer_timestamp TEXT NOT NULL,
    PRIMARY KEY (review_id, order_id),
    FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

CREATE INDEX IF NOT EXISTS idx_customers_customer_unique_id
    ON customers (customer_unique_id);
CREATE INDEX IF NOT EXISTS idx_customers_zip_code_prefix
    ON customers (customer_zip_code_prefix);
CREATE INDEX IF NOT EXISTS idx_geolocation_zip_code_prefix
    ON geolocation (geolocation_zip_code_prefix);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id
    ON orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_purchase_timestamp
    ON orders (order_purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_orders_status
    ON orders (order_status);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id
    ON order_items (product_id);
CREATE INDEX IF NOT EXISTS idx_order_items_seller_id
    ON order_items (seller_id);
CREATE INDEX IF NOT EXISTS idx_order_reviews_order_id
    ON order_reviews (order_id);
CREATE INDEX IF NOT EXISTS idx_products_category_name
    ON products (product_category_name);
CREATE INDEX IF NOT EXISTS idx_sellers_zip_code_prefix
    ON sellers (seller_zip_code_prefix);
