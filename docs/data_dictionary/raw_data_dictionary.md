````markdown
# Olist Brazilian E-commerce Dataset 数据表说明

本项目基于 Olist Brazilian E-commerce 数据集进行分析，共包含 9 张核心数据表。各表按照业务关系可分为：

- **客户维度表**：customers
- **订单事实表**：orders、order_items、order_payments、order_reviews
- **商品维度表**：products、product_category_name_translation
- **卖家维度表**：sellers
- **地理维度表**：geolocation

数据库通过主键与外键关系连接各业务实体，实现订单、用户、商品、支付、评价和物流等多维度分析。

---

# 1. olist_customers_dataset —— 客户表（customers）

## 表作用

客户表记录订单对应的客户身份信息。

需要注意的是，该表中的一行并不完全代表一个真实用户，而是代表一个订单关联的客户记录。

同一个真实客户可能因为多次购买产生多个 `customer_id`，但其 `customer_unique_id` 保持一致。

---

## 字段说明

| 字段 | 含义 |
|---|---|
| customer_id | 客户记录ID，与订单表连接 |
| customer_unique_id | 真实客户唯一ID，用于识别同一用户的重复购买行为 |
| customer_zip_code_prefix | 客户邮编前缀 |
| customer_city | 客户所在城市 |
| customer_state | 客户所在州 |

---

## 关键字段说明

### customer_id

作用：

- 用于连接订单表；
- 建立订单与客户记录之间的关系。

连接方式：

```text
orders.customer_id
        ↓
customers.customer_id
````

---

### customer_unique_id

作用：

* 统计真实客户数量；
* 计算复购率；
* 用户生命周期分析。

原因：

一个真实客户可能存在多个 `customer_id`：

```text
customer_unique_id = A

        |
        |---- customer_id 001
        |
        |---- customer_id 002
```

因此：

* 用户数量统计应使用 `customer_unique_id`；
* 订单关联使用 `customer_id`。

---

# 2. olist_geolocation_dataset —— 地理位置表（geolocation）

## 表作用

用于根据邮编前缀获取客户或卖家的地理信息，包括：

* 经纬度；
* 城市；
* 州。

---

## 字段说明

| 字段                          | 含义   |
| --------------------------- | ---- |
| geolocation_zip_code_prefix | 邮编前缀 |
| geolocation_lat             | 纬度   |
| geolocation_lng             | 经度   |
| geolocation_city            | 城市   |
| geolocation_state           | 州    |

---

## 连接关系

客户位置：

```text
customers.customer_zip_code_prefix
            ↓
geolocation.geolocation_zip_code_prefix
```

卖家位置：

```text
sellers.seller_zip_code_prefix
            ↓
geolocation.geolocation_zip_code_prefix
```

---

## 注意事项

一个邮编前缀可能对应多条地理记录。

因此：

不能直接将：

```text
geolocation_zip_code_prefix
```

作为唯一主键进行连接。

否则可能导致：

* 一条客户记录匹配多条地理记录；
* JOIN 后数据量异常增长；
* 指标统计错误。

通常处理方式：

先根据邮编计算平均经纬度：

```text
zip_code_prefix
        ↓
AVG(latitude)
AVG(longitude)
```

再与客户或卖家表连接。

---

# 3. olist_order_items_dataset —— 订单商品明细表（order_items）

## 表作用

记录订单中的商品明细。

每一行代表：

> 一个订单中的一件商品。

---

## 字段说明

| 字段                  | 含义        |
| ------------------- | --------- |
| order_id            | 订单ID      |
| order_item_id       | 商品在订单中的序号 |
| product_id          | 商品ID      |
| seller_id           | 卖家ID      |
| shipping_limit_date | 卖家最迟发货时间  |
| price               | 商品价格      |
| freight_value       | 运费        |

---

## 主键设计

建议使用联合主键：

```text
(order_id, order_item_id)
```

原因：

一个订单可能包含多个商品：

例如：

```text
order_id = A001

order_item_id = 1
product_id = P001

order_item_id = 2
product_id = P002
```

---

## 金额计算

商品销售额：

```sql
SUM(price)
```

订单运费：

```sql
SUM(freight_value)
```

订单商品及运费总额：

```sql
SUM(price + freight_value)
```

---

# 4. olist_order_payments_dataset —— 订单支付表（order_payments）

## 表作用

记录订单支付信息。

每一行代表一次付款记录。

---

## 字段说明

| 字段                   | 含义   |
| -------------------- | ---- |
| order_id             | 订单ID |
| payment_sequential   | 支付顺序 |
| payment_type         | 支付方式 |
| payment_installments | 分期数量 |
| payment_value        | 支付金额 |

---

## 主键设计

建议使用联合主键：

```text
(order_id, payment_sequential)
```

---

## 注意事项

一个订单可能：

* 多次支付；
* 使用多个支付方式。

例如：

```text
order_id = A001

payment 1:
credit_card

payment 2:
voucher
```

因此不能假设：

```text
一个订单 = 一条支付记录
```

---

## 订单实付金额

计算：

```sql
SUM(payment_value)
```

---

# 5. olist_order_reviews_dataset —— 订单评价表（order_reviews）

## 表作用

记录客户对订单的评价信息。

包括：

* 评分；
* 评论文本；
* 评论时间。

---

## 字段说明

| 字段                      | 含义       |
| ----------------------- | -------- |
| review_id               | 评价ID     |
| order_id                | 订单ID     |
| review_score            | 评分（1-5分） |
| review_comment_title    | 评论标题     |
| review_comment_message  | 评论内容     |
| review_creation_date    | 评论创建时间   |
| review_answer_timestamp | 评论回答时间   |

---

## 可分析内容

该表可以用于：

* 平均评分分析；
* 差评率分析；
* 评论文本分析；
* 物流延迟与满意度关系分析；
* 商品类别评分比较；
* 卖家服务质量分析。

---

## 注意事项

不要默认：

```text
一个订单 = 一个评价
```

应先检查：

```sql
COUNT(order_id)
```

确认订单评价关系。

---

# 6. olist_orders_dataset —— 订单主表（orders）

## 表作用

订单主表是整个项目最核心的数据表。

每一行代表：

> 一个订单。

---

## 字段说明

| 字段                            | 含义     |
| ----------------------------- | ------ |
| order_id                      | 订单唯一ID |
| customer_id                   | 客户记录ID |
| order_status                  | 订单状态   |
| order_purchase_timestamp      | 下单时间   |
| order_approved_at             | 支付批准时间 |
| order_delivered_carrier_date  | 交给物流时间 |
| order_delivered_customer_date | 实际送达时间 |
| order_estimated_delivery_date | 预计送达时间 |

---

## 主键

```text
order_id
```

---

## 可计算指标

### 审批时长

```text
order_approved_at
-
order_purchase_timestamp
```

---

### 备货时长

```text
order_delivered_carrier_date
-
order_approved_at
```

---

### 运输时长

```text
order_delivered_customer_date
-
order_delivered_carrier_date
```

---

### 总配送时长

```text
order_delivered_customer_date
-
order_purchase_timestamp
```

---

### 配送延迟天数

```text
order_delivered_customer_date
-
order_estimated_delivery_date
```

---

# 7. olist_products_dataset —— 商品表（products）

## 表作用

记录商品基础信息。

每一行代表一种商品。

---

## 字段说明

| 字段                         | 含义       |
| -------------------------- | -------- |
| product_id                 | 商品ID     |
| product_category_name      | 葡萄牙语商品类别 |
| product_name_lenght        | 商品名称长度   |
| product_description_lenght | 商品描述长度   |
| product_photos_qty         | 商品图片数量   |
| product_weight_g           | 商品重量（克）  |
| product_length_cm          | 商品长度（厘米） |
| product_height_cm          | 商品高度（厘米） |
| product_width_cm           | 商品宽度（厘米） |

---

## 主键

```text
product_id
```

---

## 字段注意

原始数据中：

```text
lenght
```

为拼写错误。

读取 CSV 时必须保持原字段名。

后续分析时可以重命名：

```text
product_name_length

product_description_length
```

---

## 商品体积计算

可以计算：

```text
product_volume_cm3 =
product_length_cm
×
product_height_cm
×
product_width_cm
```

---

# 8. olist_sellers_dataset —— 卖家表（sellers）

## 表作用

记录卖家基础信息。

每一行代表一个卖家。

---

## 字段说明

| 字段                     | 含义     |
| ---------------------- | ------ |
| seller_id              | 卖家ID   |
| seller_zip_code_prefix | 卖家邮编前缀 |
| seller_city            | 卖家城市   |
| seller_state           | 卖家所在州  |

---

## 主键

```text
seller_id
```

---

## 可分析内容

结合订单数据，可以分析：

* 卖家销售额；
* 卖家订单量；
* 卖家平均评分；
* 卖家发货速度；
* 卖家地区分布。

---

# 9. product_category_name_translation —— 商品类别翻译表

## 表作用

用于将葡萄牙语商品类别转换为英文类别。

属于辅助维度表。

---

## 字段说明

| 字段                            | 含义       |
| ----------------------------- | -------- |
| product_category_name         | 葡萄牙语类别名称 |
| product_category_name_english | 英文类别名称   |

---

## 连接关系

```text
products.product_category_name

            ↓

product_category_name_translation.product_category_name
```

---

## 注意事项

该表：

* 不包含订单信息；
* 不包含销售数据；
* 不直接参与交易分析。

主要用于：

* 商品类别可视化；
* 英文展示；
* 分类分析。

---

# 数据表整体关系总结

```text
customers
     |
     |
orders
     |
     |
 ┌───────────────┬───────────────┬───────────────┐
 |               |               |
order_items   payments       reviews
 |
 |
products
 |
 |
category_translation


order_items
 |
 |
sellers


customers
 |
 |
geolocation

sellers
 |
 |
geolocation
```

通过以上关系，可以完成：

* 用户分析；
* 订单分析；
* GMV分析；
* 商品分析；
* 卖家分析；
* 地域分析；
* 用户生命周期分析；
* 复购分析；
* RFM 分层分析。

```
```
