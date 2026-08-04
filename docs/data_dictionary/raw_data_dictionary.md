1. olist_customers_dataset——客户表

每行代表一个订单对应的客户身份。

字段	含义
customer_id	客户记录ID，与订单表连接
customer_unique_id	真实客户的唯一ID，用于识别重复购买客户
customer_zip_code_prefix	客户邮编前缀
customer_city	客户城市
customer_state	客户所在州

关键点：

customer_id：用于连接订单。
customer_unique_id：用于统计真实客户数、复购率。
同一个真实客户可能有多个 customer_id，但拥有相同的 customer_unique_id。
2. olist_geolocation_dataset——地理位置表

用于根据邮编前缀获取经纬度、城市和州。

字段	含义
geolocation_zip_code_prefix	邮编前缀
geolocation_lat	纬度
geolocation_lng	经度
geolocation_city	城市
geolocation_state	州

连接方式：

customers.customer_zip_code_prefix
→ geolocation.geolocation_zip_code_prefix

sellers.seller_zip_code_prefix
→ geolocation.geolocation_zip_code_prefix

注意：一个邮编前缀可能对应多条经纬度记录。不能直接把它当作主键连接，否则可能造成数据行数膨胀。通常先按邮编计算平均经纬度，再进行连接。

3. olist_order_items_dataset——订单商品明细表

每行代表订单中的一件商品明细。

字段	含义
order_id	订单ID
order_item_id	商品在订单中的序号
product_id	商品ID
seller_id	卖家ID
shipping_limit_date	卖家最迟发货时间
price	商品价格
freight_value	运费

建议联合主键：

(order_id, order_item_id)

一张订单可能包含多个商品，因此同一个 order_id 会出现多次。

订单商品总额：

商品销售额 = SUM(price)
订单运费 = SUM(freight_value)
订单商品及运费总额 = SUM(price + freight_value)
4. olist_order_payments_dataset——订单付款表

每行代表一次付款记录。

字段	含义
order_id	订单ID
payment_sequential	付款顺序
payment_type	付款方式
payment_installments	分期数量
payment_value	付款金额

建议联合主键：

(order_id, payment_sequential)

同一订单可能使用多次付款或多种付款方式，因此一个订单可以有多条记录。

订单实付金额：

SUM(payment_value)
5. olist_order_reviews_dataset——订单评价表

记录客户对订单的评分和评论。

字段	含义
review_id	评价ID
order_id	订单ID
review_score	评分，通常为1～5分
review_comment_title	评论标题
review_comment_message	评论内容
review_creation_date	评价创建时间
review_answer_timestamp	评价回答或提交时间

可以分析：

平均评分；
差评率；
评论文本；
物流延迟是否影响评分；
商品类别或卖家评分差异。

不要未经检查就假定每个订单只有一条评价，应先检查 order_id 是否重复。

6. olist_orders_dataset——订单主表

这是整个项目最核心的表，每行代表一个订单。

字段	含义
order_id	订单唯一ID
customer_id	客户记录ID
order_status	订单状态
order_purchase_timestamp	下单时间
order_approved_at	付款批准时间
order_delivered_carrier_date	交给物流承运商时间
order_delivered_customer_date	实际送达客户时间
order_estimated_delivery_date	预计送达时间

主键：

order_id

可以计算：

审批时长 = order_approved_at - order_purchase_timestamp

备货时长 = order_delivered_carrier_date - order_approved_at

运输时长 = order_delivered_customer_date - order_delivered_carrier_date

总配送时长 = order_delivered_customer_date - order_purchase_timestamp

延迟天数 = order_delivered_customer_date - order_estimated_delivery_date
7. olist_products_dataset——商品表

每行代表一种商品。

字段	含义
product_id	商品ID
product_category_name	葡萄牙语商品类别
product_name_lenght	商品名称长度
product_description_lenght	商品描述长度
product_photos_qty	商品图片数量
product_weight_g	商品重量，克
product_length_cm	长度，厘米
product_height_cm	高度，厘米
product_width_cm	宽度，厘米

主键：

product_id

注意：原始数据中的 lenght 是拼写错误，但读取原始 CSV 时必须使用原字段名。后续可以重命名为：

product_name_length
product_description_length

还可以计算商品体积：

product_volume_cm3 =
product_length_cm × product_height_cm × product_width_cm
8. olist_sellers_dataset——卖家表

每行代表一个卖家。

字段	含义
seller_id	卖家ID
seller_zip_code_prefix	卖家邮编前缀
seller_city	卖家城市
seller_state	卖家所在州

主键：

seller_id

可以分析：

卖家销售额；
卖家订单量；
卖家平均评分；
卖家发货速度；
卖家所在地区分布。
9. product_category_name_translation——商品类别翻译表

将葡萄牙语商品类别转换成英文。

字段	含义
product_category_name	葡萄牙语类别名称
product_category_name_english	英文类别名称

连接方式：

products.product_category_name
→ translation.product_category_name

它属于辅助维度表，不直接记录订单或销售数据。