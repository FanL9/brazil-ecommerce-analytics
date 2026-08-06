# 数据质量评估报告
>数据集：Olist 巴西电商数据集，共9张数据表

## 目录
1. 基础统计：各表总行数
2. 缺失值检查
3. 重复记录检查
4. 检查关键重复
5. 表间关联完整性检查
6. 数值异常检查（金额类）
7. 时间字段异常检查
8. 业务标识键空值检测
9. IQR四分位法数值异常值检测
10. 异常处理规则汇总

---

## 1. 基础统计：各表总行数

| 表名                            | 总行数  |
|---------------------------------|---------||
| customers                       | 99441   |
| geolocation                     | 1000163 |
| order_items                     | 112650  |
| order_payments                  | 103886  |
| order_reviews                   | 99224   |
| orders                          | 99441   |
| product_category_name_translation | 71    |
| products                        | 32951   |
| sellers                         | 3095    |

---

## 2. 缺失值检查
>说明：9张数据表中，仅 `olist_order_reviews_dataset`、`olist_orders_dataset`、`olist_products_dataset` 存在缺失值；
>其余6张表（customers、geolocation、order_items、order_payments、sellers、category翻译表）所有字段无缺失值。

### 2.1 关键标识字段空值检查
>关键字段：`order_id`、`customer_id`、`customer_unique_id`、`product_id`
>检测结果：全部关键字段缺失数量 = 0，业务主键无空值。

### 2.2 存在缺失值的三张明细表

#### olist_order_reviews_dataset（总记录：99224）
| 字段                     | 缺失数量 | 总记录 | 缺失率(%) |
|--------------------------|---------:|-------:|----------:|
| review_id                | 0       | 99224  | 0.00      |
| order_id                 | 0       | 99224  | 0.00      |
| review_score             | 0       | 99224  | 0.00      |
| review_comment_title     | 87656   | 99224  | 88.34     |
| review_comment_message   | 58247   | 99224  | 58.70     |
| review_creation_date     | 0       | 99224  | 0.00      |
| review_answer_timestamp  | 0       | 99224  | 0.00      |

#### olist_orders_dataset（总记录：99441）
| 字段                           | 缺失数量 | 总记录 | 缺失率(%) |
|--------------------------------|---------:|-------:|----------:|
| order_id                       | 0       | 99441  | 0.00      |
| customer_id                    | 0       | 99441  | 0.00      |
| order_status                   | 0       | 99441  | 0.00      |
| order_purchase_timestamp       | 0       | 99441  | 0.00      |
| order_approved_at              | 160     | 99441  | 0.16      |
| order_delivered_carrier_date   | 1783    | 99441  | 1.79      |
| order_delivered_customer_date  | 2965    | 99441  | 2.98      |
| order_estimated_delivery_date  | 0       | 99441  | 0.00      |

#### olist_products_dataset（总记录：32951）
| 字段                      | 缺失数量 | 总记录 | 缺失率(%) |
|---------------------------|---------:|-------:|----------:|
| product_id                | 0       | 32951  | 0.00      |
| product_category_name     | 610     | 32951  | 1.85      |
| product_name_lenght       | 610     | 32951  | 1.85      |
| product_description_lenght| 610     | 32951  | 1.85      |
| product_photos_qty        | 610     | 32951  | 1.85      |
| product_weight_g          | 2       | 32951  | 0.01      |
| product_length_cm         | 2       | 32951  | 0.01      |
| product_height_cm         | 2       | 32951  | 0.01      |
| product_width_cm          | 2       | 32951  | 0.01      |


### 2.3 其余数据表缺失情况
>olist_customers_dataset、olist_geolocation_dataset、olist_order_items_dataset、olist_order_payments_dataset、olist_sellers_dataset、product_category_name_translation：**全部字段无缺失值**。

---


## 3. 重复记录检查
>完全重复行：整行所有字段全部相同
>重复记录检测用于识别数据表中完全或业务意义上等价的冗余行。
>针对 `olist_geolocation_dataset`，**重复判定不纳入 `geolocation_city` 字段**：巴西同一城市存在多种缩写、大小写、拼写变体，若将城市字段参与分组，会造成大量误判。
>实际判定依据：`geolocation_zip_code_prefix + geolocation_lat + geolocation_lng + geolocation_state`，组合一致即视为业务重复记录。

| Table name                      | Total rows | Redundant duplicate rows | Note |
|---------------------------------|------------|--------------------------|------|
| olist_orders_dataset            | 99441      | 0                        | No duplication |
| olist_customers_dataset         | 99441      | 0                        | No duplication |
| olist_order_items_dataset       | 115981     | 0                        | No duplication |
| olist_order_payments_dataset    | 103886     | 0                        | No duplication |
| olist_order_reviews_dataset     | 99224      | 0                        | No duplication |
| olist_products_dataset          | 32951      | 0                        | No duplication |
| olist_sellers_dataset           | 3095       | 0                        | No duplication |
| olist_geolocation_dataset       | 400004     | 280007                   | Massive redundancy; city excluded from duplicate check |
| olist_category_name_translation | 71         | 0                        | No duplication |

---

## 4. 检查关键重复
### 4.1 Detect duplicate orders**
检测`orders`表主键`order_id`，未发现重复。

### 4.2 Detect duplicate customers**
在`orders`表中检测`customer_id`，未发现重复。

### 4.3 Detect duplicate order‑item records**
检测`order_items`业务组合键 `(order_id, order_item_id)`，未发现重复。

### 4.4 Detect duplicate payment sequential entries**
检测`order_payments`业务组合键 `(order_id, payment_sequential)`，未发现重复。

### 4.5 Detect duplicate review records**
- 第一步CTE：筛选出全部出现多次的`review_id`（主键重复的id）
- 第二步明细查询：取出这些重复`review_id`的原始数据，同时按`review_id, review_comment_title, review_comment_message`分组。
> 作用：不仅识别`review_id`主键重复，进一步查看**同一个重复id下，评论标题、评论内容是否一致**，区分是整行拷贝的脏重复，还是ID冲突但评价内容不同
- 第三步统计查询：计算得到主键重复带来的**总冗余行数为841**

| 检测对象                | 检测键                          | 是否检出重复 | 冗余重复行数 |
|-------------------------|---------------------------------|--------------|--------------|
| orders                  | order_id                        | 否           | 0            |
| customers（orders表）   | customer_id                     | 否           | 0            |
| order_items             | order_id, order_item_id         | 否           | 0            |
| order_payments          | order_id, payment_sequential    | 否           | 0            |
| order_reviews           | review_id, review_comment_title, review_comment_message | 是           | 841          |

---

## 5. 表间关联完整性检查
>外键断裂：子表ID在主表找不到对应记录，无法join关联
>参照完整性用于校验外键关联：检查子表中的关联字段，是否能够在父表中找到对应的匹配记录，识别**子表存在、父表不存在**的孤立脏数据。

| 检测内容 | 校验逻辑 | 是否存在孤立记录 |
|----------|----------|------------------|
| Orders cannot be linked to customers | 校验`orders`表的`customer_id`，是否可以在`customers`表找到对应客户 | 否（normal） |
| Order‑items cannot be linked to orders | 校验`order_items`表的`order_id`，是否可以在`orders`表找到对应订单 | 否（normal） |
| Products cannot be linked to product information | 校验订单项内产品ID，是否可以在产品基础信息表找到匹配记录 | 否（normal） |
| Payments cannot be linked to orders | 校验`order_payments`表的`order_id`，是否可以在`orders`表找到对应订单 | 否（normal） |
| Reviews cannot be linked to orders | 校验`order_reviews`表的`order_id`，是否可以在`orders`表找到对应订单 | 否（normal） |

---

## 6. 数值异常检查（金额类）
>针对货币、金额类数值字段做业务合法性校验，识别空值、零值、负数等不符合业务逻辑的异常金额。

| 序号 | 检测内容 | 校验逻辑 | 检测结果 |
|------|----------|----------|----------|
| 6.1  | Check NULL monetary values | 检查金额字段是否存在NULL空值 | normal（无异常） |
| 6.2  | Check zero monetary values | 检查金额字段是否存在等于0的记录 | normal（无异常） |
| 6.3  | Check negative monetary values | 检查金额字段是否存在小于0的负数记录 | normal（无异常） |

---

## 7. 时间字段异常检查
>检查点：空值、无法转换、时间顺序错误、超出业务时间范围
>针对订单时间字段开展校验，检测时间空值、非法时间格式、业务时序颠倒三类时间相关异常。
>业务正常时序：`order_purchase_timestamp`（下单） → `order_approved_at`（审核） → `order_delivered_carrier_date`（交物流） → `order_delivered_customer_date`（用户签收）

| 序号 | 检测内容 | 校验逻辑 | 检测结果 |
|------|----------|----------|----------|
| 7.1  | Check time NULL values | 检查订单各时间字段是否存在NULL空值 | have missing values（存在时间缺失） |
| 7.2  | Check untranslatable / invalid timestamps | 检查是否存在无法解析、格式非法的时间戳 | normal（无异常） |
| 7.3  | Check wrong chronological order | 校验业务时间先后顺序，识别时序颠倒记录 | have chronological error（存在时序错误） |

>**注释**
>扫描订单全部关键时间戳，任意一个时间字段为NULL即标记为缺失；数据集存在部分订单时间信息空缺。
>校验时间字符串是否可以正常转换为时间类型，未发现格式损坏的时间。
>业务上后续节点时间不能早于前置节点；识别审核早于下单、签收早于发货等时间倒流的业务逻辑错误。

---

## 8. 业务标识键空值检测
>检测各表核心业务ID字段是否存在NULL。主键/业务标识键一旦为空，该行记录将无法唯一识别、无法参与表关联。

| 序号 | 检测内容 | 校验逻辑 | 检测结果 |
|------|----------|----------|----------|
| 8.1  | order_id | 检查`orders`表`order_id`、`customer_id`是否为空 | no missing value（无缺失） |
| 8.2  | customer_id and customer_unique_id | 检查`customers`表`customer_id`、`customer_unique_id`是否为空 | no missing value（无缺失） |
| 8.3  | product_id | 检查`order_items`表`order_id`、`product_id`是否为空 | no missing value（无缺失） |

---

## 9. IQR四分位法数值异常值检测
>使用箱线图IQR（四分位距）规则识别数值字段的上下极端异常。
- 下边界：Q1 - 1.5*IQR
- 上边界：Q3 + 1.5*IQR
>小于下边界为**下极端异常**；大于上边界为**上极端异常**

| 序号 | source_table | field_name | valid_count | min_value | q1 | median | q3 | max_value | lower_bound | upper_bound | lower_extreme_count | upper_extreme_count |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9.1 | order_items | freight_value | 112650 | 0 |13.08 |16.26 |21.15 |409.68 |0.975 |33.255 |0 |11613 |
| 9.2 | order_items | price | 112650 |0.85 |39.9 |74.99 |134.9 |6735 |‑102.6 |277.4 |0 |8427 |
| 9.3 | order_payments | payment_installments |103886 |0 |1 |1 |4 |24 |‑3.5 |8.5 |0 |6313 |
| 9.4 | order_payments | payment_value |103886 |0 |56.79 |100 |171.84 |13664.08 |‑115.785 |344.415 |0 |7981 |
| 9.5 | orders | actual_delivery_days |96476 |0.53 |6.77 |10.22 |15.72 |209.63 |‑6.66 |29.15 |0 |4899 |

> **注释**
> 1. 所有字段均**无下侧异常值（lower_extreme_count = 0）**；全部异常集中在上边界以外，即数值偏大的极端样本。
> 2. `freight_value`运费字段上侧异常最多，共11613条；其次是`payment_value`支付金额7981条。
> 3. IQR仅做异常标记，不直接删除；部分大值属于业务真实场景（高价商品、超长配送、多期分期），需要结合业务再评估，不能直接判定为脏数据。

---

## 10. 异常处理规则汇总
