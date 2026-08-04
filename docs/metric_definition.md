# 指标定义文档

本文档用于定义项目中可直接用于分析和汇报的核心指标，字段和表结构基于当前 SQLite 数据库及 schema.sql 的实际定义。实际分析前，应确保本地数据库已通过仓库构建脚本完成导入。数据库文件本身被 .gitignore 忽略，应使用构建脚本复现。

## 统一口径

- 有效订单统一定义为：orders.order_status = 'delivered'
- 订单唯一标识统一使用：orders.order_id
- 用户唯一标识统一使用：customers.customer_unique_id
  - 不得使用 customer_id 作为用户去重字段
  - customer_id 在 customers 表中唯一，主要用于 orders 与 customers 的关联
  - 当前数据中有 2,997 个 customer_unique_id 对应多个 customer_id，因此连接后必须再按 customer_unique_id 进行用户级去重
- 默认时间归属字段为：orders.order_purchase_timestamp
- 所有一对多关系必须先聚合到目标统计粒度，再计算指标，避免重复或放大

## 一对多关系处理原则

项目中存在多对一、一对多关系时，避免重复计算的原则如下：

- 订单明细表（order_items）与订单表是一对多关系：同一订单可能有多条商品明细，计算订单级指标时应先聚合到订单级，再进行后续统计。
- 支付表（order_payments）与订单表是一对多关系：同一订单可能存在多条支付记录，计算订单金额类指标时必须先按 order_id 汇总支付金额，再计算。
- 评论表（order_reviews）与订单表是一对多关系：同一订单可能有多条评论记录，计算好评率等评论类指标时应先按 order_id 选择唯一代表评论，再统计。
- 用户表（customers）与订单表是多对一关系：一个用户可对应多笔订单，用户级指标应先通过 customer_id 建立连接，再按 customer_unique_id 去重。
- 禁止将多个一对多明细表直接同时连接后计算指标，否则会产生笛卡尔式放大。

---

## 1. GMV

### 1.1 指标名称
GMV

### 1.2 指标定义
在指定时间窗口内，有效订单的订单级支付金额之和，用于衡量平台成交金额规模。

### 1.3 计算公式
GMV = SUM(order_payment_amount)

其中：
- order_payment_amount = SUM(payment_value) GROUP BY order_id
- 仅保留 delivered 订单
- 最终汇总所有订单级支付金额

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
- 先按 order_id 聚合 payment_value，得到每个订单的支付金额；禁止在未按 order_id 聚合时直接与其他明细表连接后求和。
- 当前数据中 order_payments 共 103,886 条记录，2,961 个订单存在多条支付记录，单个订单最多有 29 条支付记录。
- payment_value 无空值和负值；0 金额支付记录可以保留，但应在数据质量检查中单独识别。
- delivered 订单中有 1 笔没有支付记录，该订单不产生 GMV。
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
- order_id 为空的不计入；当前数据中 order_id 无空值且无重复。
- 订单量以订单表为准，不受是否存在支付或评论记录影响。
- 时间口径默认使用 orders.order_purchase_timestamp。

---

## 3. 客单价

### 3.1 指标名称
客单价

### 3.2 指标定义
在指定时间窗口内，有效订单支付金额总和除以有至少一条有效支付记录的有效订单数。

### 3.3 计算公式
客单价 =
有效订单支付金额总和
/
有至少一条有效支付记录的有效订单数

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
- 先按 order_id 汇总 payment_value，得到每个订单的支付金额。
- 仅保留 delivered 且存在支付汇总记录的订单。
- 分子为这些订单的支付金额总和；分母为这些订单的去重 order_id 数。
- 没有支付记录的 delivered 订单不进入客单价分子和分母。
- 订单支付金额为 0 的订单仍属于有支付记录的订单，保留在分母中。
- 当分母为 0 时返回 NULL，不进行除零计算。
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
- 仅统计产生 delivered 订单的用户。
- 先通过 orders.customer_id = customers.customer_id 建立关联。
- 再按 customer_unique_id 去重。
- customer_unique_id 为空的记录不计入。
- 当前数据中订单与 customers 均能完整关联。
- 时间口径默认使用 orders.order_purchase_timestamp。

---

## 5. 复购率

### 5.1 指标名称
复购率

### 5.2 指标定义
统计时间窗口内，拥有至少 2 笔 delivered 订单的用户数 / 统计时间窗口内，拥有至少 1 笔 delivered 订单的用户数。

### 5.3 计算公式
复购率 = 复购用户数 / 至少下过一次有效订单的用户数

### 5.4 使用的数据表和字段
- orders
  - order_id
  - customer_id
  - order_status
  - order_purchase_timestamp
- customers
  - customer_id
  - customer_unique_id

### 5.5 筛选、去重和空值处理规则
- 用户粒度使用 customers.customer_unique_id。
- 用户订单数使用 COUNT(DISTINCT orders.order_id)。
- 同一用户同一天或同一个月的多笔不同订单，应分别计为多笔订单。
- 同一订单不得重复计算。
- customer_unique_id 为空的用户不计入。
- 本文档中该指标仅指“统计窗口内复购率”，与“历史累计复购率”不可混用。
- 时间口径默认使用 orders.order_purchase_timestamp。

---

## 6. 留存率

### 6.1 指标名称
留存率

### 6.2 指标定义
本项目统一使用“自然月 cohort 留存率”。

用户首购时间为该用户全部历史 delivered 订单中最早的 order_purchase_timestamp；首购月份为该时间所在自然月。

第 N 月留存率 =
首购月份为 M，且在 M+N 自然月再次产生 delivered 订单的用户数
/
首购月份为 M 的用户总数

### 6.3 计算公式
自然月 cohort 留存率 =
在首购月份 M 的用户中，至 M+N 自然月仍再次产生 delivered 订单的用户数
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
- 用户使用 customers.customer_unique_id。
- 首购时间需基于用户全部历史 delivered 订单计算，不能先限制分析时间窗口再计算首购。
- 首购月份必须基于完整历史计算，不能仅看当前分析窗口。
- 同一用户在同一自然月内无论产生多少笔订单，只计为 1 名留存用户。
- 当前数据覆盖约 2016-09 至 2018-08，可用于自然月 cohort 分析。
- 处理右截尾问题时，仅纳入数据观察期内已经完整经历 N 个月的 cohort；尚未拥有完整观察窗口的较新 cohort 不进入该期留存率汇总。
- 不再保留 7 日、30 日、90 日留存的模糊描述。
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
- 两个时间字段均非空。
- order_delivered_customer_date 必须大于或等于 order_purchase_timestamp。
- 单位统一为天。
- 时间字段缺失或出现负值的订单不计入。
- 当前数据中没有负配送时长；有 8 笔 delivered 订单缺少实际签收时间。
- 配送时长存在明显长尾，最大约 209.63 天；正数长尾不得在没有业务依据的情况下自动删除。
- 核心平均配送时长默认保留所有合法非负记录；分析和汇报时建议同时提供中位数，并单独标记超过 60、90 或 180 天的异常长订单。
- 如某次分析采用截尾、缩尾或异常值排除，必须单独披露规则，不能改变基础指标定义。
- 不再使用 order_delivered_carrier_date 计算本指标；若未来分析承运商运输效率，可另行定义运输时长 = order_delivered_customer_date - order_delivered_carrier_date。

---

## 8. 好评率

### 8.1 指标名称
好评率

### 8.2 指标定义
在指定时间窗口内，去重后好评订单数占去重后有有效评分的订单数的比例。

### 8.3 计算公式
好评率 = 去重后好评订单数 / 去重后有有效评分的订单数

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
  - review_id

### 8.5 筛选、去重和空值处理规则
- 仅统计 delivered 订单。
- 无评论订单不进入分母。
- review_score 为空的评论不进入分母。
- 不要直接把评论行数当作订单数。
- 同一订单有多条评论时，只保留一条代表评论。
- 评论去重顺序为：
  1. 优先选择 review_answer_timestamp 最新的记录
  2. 如果 review_answer_timestamp 为空，则使用 review_creation_date
  3. 如果时间仍完全相同，使用 review_id 作为稳定的最终排序字段
  4. 每个 order_id 最终只能保留一条评论
- 当前数据中有 547 个订单存在多条评论，单个订单最多有 3 条评论；delivered 订单中有 6,646 笔没有评论。
- review_score 当前均在 1 至 5 范围内。
- 好评定义固定为 review_score >= 4。
- 好评率时间归属统一使用 orders.order_purchase_timestamp；不使用评论创建时间作为默认统计周期。

---

## 说明

- 指标字段和表结构基于当前 SQLite 数据库及 schema.sql。
- 实际分析前应确保本地数据库已经通过仓库构建脚本完成导入。
- 数据库文件本身被 .gitignore 忽略，应使用构建脚本复现。
- 若后续接入数据库表名与当前命名存在差异，应以实际数据库中的表名和字段为准。
