------ 阶段四 Member 2：品类增长趋势分析 ------

--- 1. 复用范围
--复用：
-- `outputs/data/06_product_analysis/category_sales_base`
-- `outputs/data/06_product_analysis/category_monthly_sales_base`

--- 2. 增长分析 
-- 品类月度商品销售额环比；
-- 品类月度订单量环比；
-- 品类月度商品件数环比；
-- 由于部分数据缺失，我们只保留2017-01到2018-07的数据进行分析
-- 产出：outputs/data/06_product_analysis/category_monthly_growth.csv

SELECT
a.purchase_month,
a.category_name,
a.monthly_sales_amount,
CASE WHEN b.monthly_sales_amount IS NULL OR b.monthly_sales_amount=0 THEN NULL
ELSE (a.monthly_sales_amount-b.monthly_sales_amount)*1.0/b.monthly_sales_amount END AS sales_mom_growth,
a.monthly_order_count,
CASE WHEN b.monthly_order_count IS NULL OR b.monthly_order_count=0 THEN NULL
ELSE (a.monthly_order_count-b.monthly_order_count)*1.0/b.monthly_order_count END AS order_mom_growth,
a.monthly_item_count,
CASE WHEN b.monthly_item_count IS NULL OR b.monthly_item_count=0 THEN NULL
ELSE (a.monthly_item_count-b.monthly_item_count)*1.0/b.monthly_item_count END AS item_mom_growth
FROM category_monthly_sales_base a
LEFT JOIN category_monthly_sales_base b
ON a.category_name=b.category_name
AND b.purchase_month=strftime('%Y-%m',date(a.purchase_month||'-01','-1 month'))
WHERE a.purchase_month BETWEEN '2017-01' AND '2018-07'
ORDER BY a.purchase_month,a.category_name;

--- 3. 品类 CMGR 与平台整体 CMGR category_and_platform_cmgr.csv
-- CMGR = (期末商品销售额 / 期初商品销售额)^(1 / 间隔月数) - 1
-- 期初商品销售额：该品类第一个有销售记录月份的 monthly_sales_amount
-- 期末商品销售额：该品类最后一个有销售记录月份的 monthly_sales_amount
-- 平台CMGR = （平台期末总额 / 平台期初总额）^(1 / 间隔月数) - 1
-- 只有在2017-01与2018-07有数据的才会参与品类和平台 CMGR 的计算，其他一律显示null
-- 产出：outputs/data/06_product_analysis/category_and_platform_cmgr.csv

WITH base AS (
SELECT *
FROM category_monthly_sales_base
WHERE purchase_month BETWEEN '2017-01' AND '2018-07'
),
category_cmgr AS (
SELECT
category_name,
MIN(purchase_month) AS start_month,
MAX(purchase_month) AS end_month,
SUM(CASE WHEN purchase_month=(SELECT MIN(purchase_month) FROM base x WHERE x.category_name=a.category_name) THEN monthly_sales_amount ELSE 0 END) AS start_sales,
SUM(CASE WHEN purchase_month=(SELECT MAX(purchase_month) FROM base x WHERE x.category_name=a.category_name) THEN monthly_sales_amount ELSE 0 END) AS end_sales
FROM base a
GROUP BY category_name
),
category_result AS (
SELECT
category_name,
start_month,
end_month,
start_sales,
end_sales,
((CAST(substr(end_month,1,4) AS INTEGER)-CAST(substr(start_month,1,4) AS INTEGER))*12+
(CAST(substr(end_month,6,2) AS INTEGER)-CAST(substr(start_month,6,2) AS INTEGER))) AS month_diff,
CASE
WHEN start_month='2017-01'
AND end_month='2018-07'
AND start_sales>0
THEN POWER(end_sales*1.0/start_sales,1.0/18)-1
ELSE NULL
END AS category_cmgr
FROM category_cmgr
),
platform AS (
SELECT
MIN(purchase_month) AS start_month,
MAX(purchase_month) AS end_month,
SUM(CASE WHEN purchase_month=(SELECT MIN(purchase_month) FROM base) THEN monthly_sales_amount ELSE 0 END) AS start_sales,
SUM(CASE WHEN purchase_month=(SELECT MAX(purchase_month) FROM base) THEN monthly_sales_amount ELSE 0 END) AS end_sales
FROM base
)
SELECT
'category' AS level,
category_name,
start_month,
end_month,
start_sales,
end_sales,
month_diff,
category_cmgr
FROM category_result
UNION ALL
SELECT
'platform' AS level,
'ALL' AS category_name,
start_month,
end_month,
start_sales,
end_sales,
((CAST(substr(end_month,1,4) AS INTEGER)-CAST(substr(start_month,1,4) AS INTEGER))*12+
(CAST(substr(end_month,6,2) AS INTEGER)-CAST(substr(start_month,6,2) AS INTEGER))) AS month_diff,
CASE
WHEN start_sales=0 THEN NULL
ELSE POWER(end_sales*1.0/start_sales,1.0/(
((CAST(substr(end_month,1,4) AS INTEGER)-CAST(substr(start_month,1,4) AS INTEGER))*12+
(CAST(substr(end_month,6,2) AS INTEGER)-CAST(substr(start_month,6,2) AS INTEGER)))
))-1
END AS platform_cmgr
FROM platform;

-- 得到平台CMGR =0.1205928153252045 > 0,对后续分析有帮助：1.05 * 平均CMGR > 0; 0.95 * 平均CMGR > 0

--- 4. 品类定义
-- 明星品类（Star Category）：有有效 CMGR，且销售额高于品类销售额中位数，同时品类 CMGR 高于平台 CMGR 超过 5 个 percentage points。
-- 潜力品类（Potential Category）：有有效 CMGR，且销售额低于或等于品类销售额中位数，同时品类 CMGR 高于平台 CMGR 超过 5 个 percentage points。
-- 稳定品类（Stable Category）：有有效 CMGR，且 CMGR ≥ 0，但未达到明星品类或潜力品类的增长标准。
-- 衰退品类（Declining Category）：
   -- 对于有有效 CMGR 的品类：CMGR < 0；
   -- 对于无法计算 CMGR 的品类：2018-07 无销售记录。
-- 新兴品类（Emerging Category）：无法计算有效 CMGR，且 2017-01 无销售记录、2018-07 有销售记录。
-- 产出：outputs/data/06_product_analysis/category_classification.csv

WITH avg_cmgr AS (
SELECT
AVG(category_cmgr) AS avg_category_cmgr
FROM category_and_platform_cmgr
WHERE level='category'
AND category_cmgr IS NOT NULL
),
platform_cmgr AS (
SELECT
MAX(category_cmgr) AS platform_cmgr
FROM category_and_platform_cmgr
WHERE level='platform'
),
median_sales AS (
SELECT AVG(sales_amount) AS median_sales
FROM (
SELECT
sales_amount,
ROW_NUMBER() OVER (ORDER BY sales_amount) AS rn,
COUNT(*) OVER () AS total_count
FROM category_sales_base
)
WHERE rn IN (
(total_count+1)/2,
(total_count+2)/2
)
)
SELECT
c.category_name,
s.sales_amount,
c.category_cmgr,
a.avg_category_cmgr,
p.platform_cmgr,
CASE
WHEN c.category_cmgr IS NOT NULL
AND s.sales_amount>m.median_sales
AND c.category_cmgr>p.platform_cmgr+0.05
THEN 'Star Category'
WHEN c.category_cmgr IS NOT NULL
AND s.sales_amount<=m.median_sales
AND c.category_cmgr>p.platform_cmgr+0.05
THEN 'Potential Category'
WHEN c.category_cmgr IS NOT NULL
AND c.category_cmgr>=0
THEN 'Stable Category'
WHEN c.category_cmgr IS NOT NULL
AND c.category_cmgr<0
THEN 'Declining Category'
WHEN c.category_cmgr IS NULL
AND c.start_month>'2017-01'
AND c.end_month='2018-07'
THEN 'Emerging Category'
WHEN c.category_cmgr IS NULL
AND c.end_month<'2018-07'
THEN 'Declining Category'
END AS category_type
FROM category_and_platform_cmgr c
LEFT JOIN category_sales_base s
ON c.category_name=s.category_name
CROSS JOIN avg_cmgr a
CROSS JOIN platform_cmgr p
CROSS JOIN median_sales m
WHERE c.level='category'
ORDER BY s.sales_amount DESC;




