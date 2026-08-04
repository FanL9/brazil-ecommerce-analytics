# 指标定义文档

本文档用于定义项目中可直接用于分析和汇报的核心指标，基于当前项目中实际存在的字段进行说明。

## 统一口径

- 有效订单：orders.order_status = 'delivered'
- 用户唯一标识：customers.customer_unique_id，不使用 customer_id 作为去重口径
- GMV：SUM(order_payments.payment_value)，即支付金额口径
- 指标时间窗口：默认使用 orders.order_purchase_timestamp

## 一对多关系处理原则

项目中存在多对一、一对多关系时，避免重复计算的原则如下：

- 订单明细表（order_items）与订单表是一对多关系：同一订单可能有多条商品明细，计算订单级指标时应先聚合到订单级，再进行后续统计。
- 支付表（order_payments）与订单表是一对多关系：同一订单可能存在多条支付记录，计算订单金额类指标时应先按订单去重汇总，再计算。
- 评论表（order_reviews）与订单表是一对多关系：同一订单可能有多条评论记录，计算好评率等评论类指标时应先按订单去重，再统计。
- 用户表（customers）与订单表是多对一关系：一个用户可对应多笔订单，用户级指标应以 customer_unique_id 为粒度聚合。

---

## 1. GMV

### 1.1 指标名称
GMV

### 1.2 指标定义
在指定时间窗口内，所有有效订单的支付金额总和，用于衡量平台成交金额规模。

### 1.3 计算公式
GMV = SUM(order_payments.payment_value)

### 1.4 使用的数据表和字段
- orders
  - order_id
  - order_status
  - order_purchase_timestamp
- order_payments
  - order_id
  - payment_value

### 1.5 筛选、去重和空值处理规则
- 仅统计 orders.order_status = 'delivered' 的有效订单。
- 由于 order_payments 与 orders 是一对多关系，同一订单可能有多条支付记录，需先按 order_id 聚合支付金额，再求和，避免重复计算。
- 对 payment_value 为空或为 null 的记录，按“无有效金额”处理，不计入 GMV。
- 时间口径默认使用 orders.order_purchase_timestamp。

---

## 2. 订单量

### 2.1 指标名称
订单量

### 2.2 指标定义
在指定时间窗口内，成交的有效订单数量。

### 2.3 计算公式
订单量 = COUNT(DISTINCT orders.order_id)

### 2.4 使用的数据表和字段
- orders
  - order_id
  - order_status
  - order_purchase_timestamp

### 2.5 筛选、去重和空值处理规则
- 仅统计 orders.order_status = 'delivered' 的订单。
- 以 order_id 为去重粒度，避免同一订单被重复计数。
- order_id 为空的记录不应计入。
- 时间口径默认使用 orders.order_purchase_timestamp。

---

## 3. 客单价

### 3.1 指标名称
客单价

### 3.2 指标定义
在指定时间窗口内，所有具有有效支付记录的有效订单的支付金额总和，除以有有效支付记录的有效订单数。

### 3.3 计算公式
客单价 =
有效订单支付金额总和
/
有有效支付记录的有效订单数

### 3.4 使用的数据表和字段
- orders
  - order_id
  - order_status
  - order_purchase_timestamp
- order_payments
  - order_id
  - payment_value

### 3.5 筛选、去重和空值处理规则
- 有效订单仍为 orders.order_status = 'delivered'。
- 先按 order_id 汇总 payment_value，得到每笔订单的支付金额。
- 没有支付记录或订单支付金额为空的订单，不进入客单价的分子和分母。
- 单独的“订单量”指标仍统计所有 delivered 订单，不受该口径影响。
- 时间口径默认使用 orders.order_purchase_timestamp。

---

## 4. 用户数

### 4.1 指标名称
用户数

### 4.2 指标定义
在指定时间窗口内，产生有效订单的去重用户数量。

### 4.3 计算公式
用户数 = COUNT(DISTINCT customers.customer_unique_id)

### 4.4 使用的数据表和字段
- orders
  - customer_id
  - order_status
  - order_purchase_timestamp
- customers
  - customer_id
  - customer_unique_id

### 4.5 筛选、去重和空值处理规则
- 仅统计有效订单。
- 用户去重口径统一使用 customers.customer_unique_id，不使用 customer_id。
- 若 customer_unique_id 为空，则该记录不计入指标。
- 需先通过 orders.customer_id 与 customers.customer_id 建立关联，再按 customer_unique_id 去重。
- 时间口径默认使用 orders.order_purchase_timestamp。

---

## 5. 复购率

### 5.1 指标名称
复购率

### 5.2 指标定义
在指定观察窗口内，至少下过两次有效订单的用户占所有至少下过一次有效订单用户的比例。

### 5.3 计算公式
复购率 = 复购用户数 / 至少下过一次有效订单的用户数

### 5.4 使用的数据表和字段
- orders
  - customer_id
  - order_status
  - order_purchase_timestamp
- customers
  - customer_id
  - customer_unique_id

### 5.5 筛选、去重和空值处理规则
- 仅统计有效订单。
- 先将订单按 customer_unique_id 聚合，统计每个用户的订单次数。
- 复购用户定义为订单次数 >= 2 的用户。
- 分母为至少下过一次有效订单的用户。
- 若 customer_unique_id 为空，则不计入指标。
- 时间口径默认使用 orders.order_purchase_timestamp；可进一步定义观察窗口（如月度、季度、年度）。

---

## 6. 留存率

### 6.1 指标名称
留存率

### 6.2 指标定义
本项目统一使用“月度 cohort 留存率”。

用户首购月份为该用户历史上第一笔有效订单的下单月份；首购时间必须基于全部历史有效订单计算，不能只在当前分析时间窗口内计算。

第 N 月留存率 =
首购月份为 M 且在 M+N 自然月再次产生有效订单的用户数
/
首购月份为 M 的用户数

### 6.3 计算公式
月度 cohort 留存率 =
在首购月份 M 的用户中，至 M+N 自然月仍再次产生有效订单的用户数
/
首购月份为 M 的用户数

### 6.4 使用的数据表和字段
- orders
  - customer_id
  - order_status
  - order_purchase_timestamp
- customers
  - customer_id
  - customer_unique_id

### 6.5 筛选、去重和空值处理规则
- 仅统计有效订单，即 orders.order_status = 'delivered'。
- 使用 customers.customer_unique_id 识别用户。
- 用户首购月份需根据该用户历史上第一笔有效订单的下单月份确定，先计算完整历史首购时间，再进行留存判断。
- 第 N 月留存率中，同一用户在同一留存月份只计算一次。
- 若 customer_unique_id 为空，则不计入指标。
- 本项目统一使用自然月留存，不使用 7 日、30 日、90 日等模糊描述。
- 时间口径默认使用 orders.order_purchase_timestamp。

---

## 7. 配送时长

### 7.1 指标名称
配送时长

### 7.2 指标定义
本项目中配送时长统一定义为：从用户下单到实际签收的总时长，单位为天。

### 7.3 计算公式
配送时长 =
orders.order_delivered_customer_date
-
orders.order_purchase_timestamp

### 7.4 使用的数据表和字段
- orders
  - order_id
  - order_status
  - order_purchase_timestamp
  - order_delivered_customer_date

### 7.5 筛选、去重和空值处理规则
- 仅统计 orders.order_status = 'delivered' 的订单。
- 两个时间字段必须同时非空。
- orders.order_delivered_customer_date 必须大于或等于 orders.order_purchase_timestamp。
- 异常负值记录不计入指标。
- 以 order_id 为粒度，避免同一订单重复计算。
- 不再使用 order_delivered_carrier_date 计算本指标。
- 若未来需要分析承运商运输效率，可另外定义“运输时长 = order_delivered_customer_date - order_delivered_carrier_date”。

---

## 8. 好评率

### 8.1 指标名称
好评率

### 8.2 指标定义
在指定时间窗口内，评分达到好评标准的订单占所有有评论订单的比例。

### 8.3 计算公式
好评率 = 好评订单数 / 有评论订单数

### 8.4 使用的数据表和字段
- orders
  - order_id
  - order_status
  - order_purchase_timestamp
- order_reviews
  - order_id
  - review_score
  - review_creation_date
  - review_answer_timestamp

### 8.5 筛选、去重和空值处理规则
- 以订单为统计单位，先按 order_id 关联订单与评论。
- 同一订单存在多条评论记录时，优先保留 review_answer_timestamp 最新的一条；若 review_answer_timestamp 为空，则使用 review_creation_date 判断最新记录。
- 无评论或 review_score 为空的订单不计入指标。
- 本文档默认将 review_score >= 4 视为好评。
- 时间口径统一使用 orders.order_purchase_timestamp，不再使用评论时间口径。

---

## 说明

- 本文档中的字段均来自当前项目中已存在的数据文件与字段名称，未引入额外虚构字段。
- 若后续接入数据库表名与当前命名存在差异，应以实际数据库中的表名和字段为准。
