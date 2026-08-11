------ 阶段四 Member 2：品类增长趋势分析 ------

--- 1. 复用范围
--复用：
-- `outputs/data/06_product_analysis/category_sales_base`
-- `outputs/data/06_product_analysis/category_monthly_sales_base`

--- 2. 增长分析 
-- 品类月度商品销售额环比；
-- 品类月度订单量环比；
-- 品类月度商品件数环比；
-- 产出：outputs/data/06_product_analysis/category_monthly_growth.csv
   
SELECT 
a.purchase_month,
a.category_name,
a.monthly_sales_amount,
CASE WHEN b.monthly_sales_amount IS NULL OR b.monthly_sales_amount=0 THEN NULL ELSE (a.monthly_sales_amount-b.monthly_sales_amount)*1.0/b.monthly_sales_amount END AS sales_mom_growth,
a.monthly_order_count,
CASE WHEN b.monthly_order_count IS NULL OR b.monthly_order_count=0 THEN NULL ELSE (a.monthly_order_count-b.monthly_order_count)*1.0/b.monthly_order_count END AS order_mom_growth,
a.monthly_item_count,
CASE WHEN b.monthly_item_count IS NULL OR b.monthly_item_count=0 THEN NULL ELSE (a.monthly_item_count-b.monthly_item_count)*1.0/b.monthly_item_count END AS item_mom_growth
FROM category_monthly_sales_base a
LEFT JOIN category_monthly_sales_base b
ON a.category_name=b.category_name
AND b.purchase_month=strftime('%Y-%m',date(a.purchase_month||'-01','-1 month'))
ORDER BY a.purchase_month,a.category_name;

--- 3. 品类 CMGR 与平台整体 CMGR category_and_platform_cmgr.csv
-- CMGR = (期末商品销售额 / 期初商品销售额)^(1 / 间隔月数) - 1
-- 期初商品销售额：该品类第一个有销售记录月份的 monthly_sales_amount
-- 期末商品销售额：该品类最后一个有销售记录月份的 monthly_sales_amount
-- 产出：outputs/data/06_product_analysis/category_and_platform_cmgr.csv

WITH category_cmgr AS (
SELECT
category_name,
MIN(purchase_month) AS start_month,
MAX(purchase_month) AS end_month,
SUM(CASE WHEN purchase_month=(SELECT MIN(purchase_month) FROM category_monthly_sales_base x WHERE x.category_name=a.category_name) THEN monthly_sales_amount END) AS start_sales,
SUM(CASE WHEN purchase_month=(SELECT MAX(purchase_month) FROM category_monthly_sales_base x WHERE x.category_name=a.category_name) THEN monthly_sales_amount END) AS end_sales
FROM category_monthly_sales_base a
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
CASE WHEN start_sales=0 OR start_sales IS NULL THEN NULL
ELSE POWER(end_sales*1.0/start_sales,1.0/(
((CAST(substr(end_month,1,4) AS INTEGER)-CAST(substr(start_month,1,4) AS INTEGER))*12+
(CAST(substr(end_month,6,2) AS INTEGER)-CAST(substr(start_month,6,2) AS INTEGER)))
))-1 END AS category_cmgr
FROM category_cmgr
),
platform AS (
SELECT
MIN(purchase_month) AS start_month,
MAX(purchase_month) AS end_month,
SUM(CASE WHEN purchase_month=(SELECT MIN(purchase_month) FROM category_monthly_sales_base) THEN monthly_sales_amount END) AS start_sales,
SUM(CASE WHEN purchase_month=(SELECT MAX(purchase_month) FROM category_monthly_sales_base) THEN monthly_sales_amount END) AS end_sales
FROM category_monthly_sales_base
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
CASE WHEN start_sales=0 THEN NULL
ELSE POWER(end_sales*1.0/start_sales,1.0/(
((CAST(substr(end_month,1,4) AS INTEGER)-CAST(substr(start_month,1,4) AS INTEGER))*12+
(CAST(substr(end_month,6,2) AS INTEGER)-CAST(substr(start_month,6,2) AS INTEGER)))
))-1 END AS platform_cmgr
FROM platform;

--所有品类平均CMGR
SELECT 
    AVG(category_cmgr) AS avg_category_cmgr
FROM category_and_platform_cmgr
WHERE level = 'category'
AND category_cmgr IS NOT NULL;
-- 得到所有品类的平均CMGR =0.1204853049448846 > 0,对后续分析有帮助：1.05 * 平均CMGR > 0; 0.95 * 平均CMGR > 0

--- 4. 品类定义
-- 明星品类：销售额 > 品类销售额中位数，且品类CMGR高于所有品类平均CMGR超过 5 percentage points；
-- 潜力品类：销售额 ≤ 品类销售额中位数，但品类CMGR高于所有品类平均CMGR超过 5 percentage points；
-- 稳定品类：CMGR ≥ 0，且未达到明星或潜力品类增长标准；
-- 衰退品类：CMGR < 0；
-- 新兴品类：观察期内首次出现销售，且无法计算有效 CMGR 的品类。
-- 产出：outputs/data/06_product_analysis/category_classification.csv
WITH avg_cmgr AS (
    SELECT 
        AVG(category_cmgr) AS avg_category_cmgr
    FROM category_and_platform_cmgr
    WHERE level = 'category'
      AND category_cmgr IS NOT NULL
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
        (total_count + 1) / 2,
        (total_count + 2) / 2
    )
)
SELECT
    c.category_name,
    s.sales_amount,
    c.category_cmgr,
    a.avg_category_cmgr,
    CASE
        WHEN c.category_cmgr IS NULL
            THEN 'Emerging Category'
        WHEN c.category_cmgr < 0
            THEN 'Declining Category'
        WHEN s.sales_amount > m.median_sales
             AND c.category_cmgr > a.avg_category_cmgr + 0.05
            THEN 'Star Category'
        WHEN s.sales_amount <= m.median_sales
             AND c.category_cmgr > a.avg_category_cmgr + 0.05
            THEN 'Potential Category'
        WHEN c.category_cmgr >= 0
            THEN 'Stable Category'
    END AS category_type
FROM category_and_platform_cmgr c
LEFT JOIN category_sales_base s
ON c.category_name = s.category_name
CROSS JOIN avg_cmgr a
CROSS JOIN median_sales m
WHERE c.level = 'category'
ORDER BY s.sales_amount DESC;