--- Growth Quality Analysis ---

-- 1. overall table
WITH RECURSIVE all_months AS (
SELECT DATE(MIN(month)||'-01') AS month
FROM monthly_kpi
UNION ALL
SELECT DATE(month,'+1 month')
FROM all_months
WHERE month<(SELECT DATE(MAX(month)||'-01') FROM monthly_kpi)
),
kpi AS (
SELECT
strftime('%Y-%m',a.month) AS month,
k.gmv,
k.order_count,
k.average_order_value,
k.new_users,
k.active_users
FROM all_months a
LEFT JOIN monthly_kpi k
ON strftime('%Y-%m',a.month)=k.month
)
SELECT
month,
CASE WHEN gmv IS NULL OR LAG(gmv) OVER(ORDER BY month) IS NULL THEN NULL
ELSE ROUND((gmv-LAG(gmv) OVER(ORDER BY month))*1.0/LAG(gmv) OVER(ORDER BY month),4)
END AS gmv_mom,
CASE WHEN gmv IS NULL OR LAG(gmv,12) OVER(ORDER BY month) IS NULL THEN NULL
ELSE ROUND((gmv-LAG(gmv,12) OVER(ORDER BY month))*1.0/LAG(gmv,12) OVER(ORDER BY month),4)
END AS gmv_yoy,
CASE WHEN order_count IS NULL OR LAG(order_count) OVER(ORDER BY month) IS NULL THEN NULL
ELSE ROUND((order_count-LAG(order_count) OVER(ORDER BY month))*1.0/LAG(order_count) OVER(ORDER BY month),4)
END AS order_count_mom,
CASE WHEN order_count IS NULL OR LAG(order_count,12) OVER(ORDER BY month) IS NULL THEN NULL
ELSE ROUND((order_count-LAG(order_count,12) OVER(ORDER BY month))*1.0/LAG(order_count,12) OVER(ORDER BY month),4)
END AS order_count_yoy,
CASE WHEN average_order_value IS NULL OR LAG(average_order_value) OVER(ORDER BY month) IS NULL THEN NULL
ELSE ROUND((average_order_value-LAG(average_order_value) OVER(ORDER BY month))*1.0/LAG(average_order_value) OVER(ORDER BY month),4)
END AS aov_mom,
CASE WHEN average_order_value IS NULL OR LAG(average_order_value,12) OVER(ORDER BY month) IS NULL THEN NULL
ELSE ROUND((average_order_value-LAG(average_order_value,12) OVER(ORDER BY month))*1.0/LAG(average_order_value,12) OVER(ORDER BY month),4)
END AS aov_yoy,
CASE WHEN new_users IS NULL OR LAG(new_users) OVER(ORDER BY month) IS NULL THEN NULL
ELSE ROUND((new_users-LAG(new_users) OVER(ORDER BY month))*1.0/LAG(new_users) OVER(ORDER BY month),4)
END AS new_users_mom,
CASE WHEN new_users IS NULL OR LAG(new_users,12) OVER(ORDER BY month) IS NULL THEN NULL
ELSE ROUND((new_users-LAG(new_users,12) OVER(ORDER BY month))*1.0/LAG(new_users,12) OVER(ORDER BY month),4)
END AS new_users_yoy,
CASE WHEN active_users IS NULL OR LAG(active_users) OVER(ORDER BY month) IS NULL THEN NULL
ELSE ROUND((active_users-LAG(active_users) OVER(ORDER BY month))*1.0/LAG(active_users) OVER(ORDER BY month),4)
END AS active_users_mom,
CASE WHEN active_users IS NULL OR LAG(active_users,12) OVER(ORDER BY month) IS NULL THEN NULL
ELSE ROUND((active_users-LAG(active_users,12) OVER(ORDER BY month))*1.0/LAG(active_users,12) OVER(ORDER BY month),4)
END AS active_users_yoy
FROM kpi
ORDER BY month;

-- 1.1 GMV month-on-month growth rate and year-on-year growth rate
WITH RECURSIVE all_months AS (
    SELECT DATE(MIN(month)||'-01') AS month FROM monthly_kpi
    UNION ALL
    SELECT DATE(month,'+1 month')
    FROM all_months
    WHERE month < (SELECT DATE(MAX(month)||'-01') FROM monthly_kpi)
),
full_gmv AS (
    SELECT strftime('%Y-%m',a.month) AS month,m.gmv
    FROM all_months a
    LEFT JOIN monthly_kpi m
    ON strftime('%Y-%m',a.month)=m.month
),
growth AS (
    SELECT month,gmv,
    LAG(gmv,1) OVER(ORDER BY month) AS prev_m,
    LAG(gmv,12) OVER(ORDER BY month) AS prev_y
    FROM full_gmv
)
SELECT
    month,
    CASE WHEN gmv IS NULL OR prev_m IS NULL THEN NULL
    ELSE ROUND((gmv-prev_m)*1.0/prev_m,4) END AS gmv_mom_rate,
    CASE WHEN gmv IS NULL OR prev_y IS NULL THEN NULL
    ELSE ROUND((gmv-prev_y)*1.0/prev_y,4) END AS gmv_yoy_rate
FROM growth
ORDER BY month;

-- 1.2 order_count month-on-month growth rate and year-on-year growth rate
WITH RECURSIVE all_months AS (
    SELECT DATE(MIN(month)||'-01') AS month FROM monthly_kpi
    UNION ALL
    SELECT DATE(month,'+1 month')
    FROM all_months
    WHERE month < (SELECT DATE(MAX(month)||'-01') FROM monthly_kpi)
),
data AS (
    SELECT 
        strftime('%Y-%m',a.month) AS month,
        k.order_count
    FROM all_months a
    LEFT JOIN monthly_kpi k
    ON strftime('%Y-%m',a.month)=k.month
)
SELECT
    month,
    CASE 
        WHEN order_count IS NULL 
          OR LAG(order_count,1) OVER(ORDER BY month) IS NULL
        THEN NULL
        ELSE ROUND(
            (order_count-LAG(order_count,1) OVER(ORDER BY month))*1.0
            /LAG(order_count,1) OVER(ORDER BY month),4)
    END AS order_count_mom,
    CASE 
        WHEN order_count IS NULL 
          OR LAG(order_count,12) OVER(ORDER BY month) IS NULL
        THEN NULL
        ELSE ROUND(
            (order_count-LAG(order_count,12) OVER(ORDER BY month))*1.0
            /LAG(order_count,12) OVER(ORDER BY month),4)
    END AS order_count_yoy
FROM data
ORDER BY month;

-- 1.3 average_order_value month-on-month growth rate and year-on-year growth rate
WITH RECURSIVE all_months AS (
    SELECT DATE(MIN(month)||'-01') AS month FROM monthly_kpi
    UNION ALL
    SELECT DATE(month,'+1 month')
    FROM all_months
    WHERE month < (SELECT DATE(MAX(month)||'-01') FROM monthly_kpi)
),
data AS (
    SELECT 
        strftime('%Y-%m',a.month) AS month,
        k.average_order_value
    FROM all_months a
    LEFT JOIN monthly_kpi k
    ON strftime('%Y-%m',a.month)=k.month
)
SELECT
    month,
    CASE 
        WHEN average_order_value IS NULL 
          OR LAG(average_order_value,1) OVER(ORDER BY month) IS NULL
        THEN NULL
        ELSE ROUND(
            (average_order_value-LAG(average_order_value,1) OVER(ORDER BY month))*1.0
            /LAG(average_order_value,1) OVER(ORDER BY month),4)
    END AS aov_mom,
    CASE 
        WHEN average_order_value IS NULL 
          OR LAG(average_order_value,12) OVER(ORDER BY month) IS NULL
        THEN NULL
        ELSE ROUND(
            (average_order_value-LAG(average_order_value,12) OVER(ORDER BY month))*1.0
            /LAG(average_order_value,12) OVER(ORDER BY month),4)
    END AS aov_yoy
FROM data
ORDER BY month;

-- 1.4 new_users month-on-month growth rate and year-on-year growth rate
WITH RECURSIVE all_months AS (
    SELECT DATE(MIN(month)||'-01') AS month FROM monthly_kpi
    UNION ALL
    SELECT DATE(month,'+1 month')
    FROM all_months
    WHERE month < (SELECT DATE(MAX(month)||'-01') FROM monthly_kpi)
),
data AS (
    SELECT 
        strftime('%Y-%m',a.month) AS month,
        k.new_users
    FROM all_months a
    LEFT JOIN monthly_kpi k
    ON strftime('%Y-%m',a.month)=k.month
)
SELECT
    month,
    CASE 
        WHEN new_users IS NULL 
          OR LAG(new_users,1) OVER(ORDER BY month) IS NULL
        THEN NULL
        ELSE ROUND(
            (new_users-LAG(new_users,1) OVER(ORDER BY month))*1.0
            /LAG(new_users,1) OVER(ORDER BY month),4)
    END AS new_users_mom,
    CASE 
        WHEN new_users IS NULL 
          OR LAG(new_users,12) OVER(ORDER BY month) IS NULL
        THEN NULL
        ELSE ROUND(
            (new_users-LAG(new_users,12) OVER(ORDER BY month))*1.0
            /LAG(new_users,12) OVER(ORDER BY month),4)
    END AS new_users_yoy
FROM data
ORDER BY month;

-- 1.5 active_users month-on-month growth rate and year-on-year growth rate
WITH RECURSIVE all_months AS (
    SELECT DATE(MIN(month)||'-01') AS month FROM monthly_kpi
    UNION ALL
    SELECT DATE(month,'+1 month')
    FROM all_months
    WHERE month < (SELECT DATE(MAX(month)||'-01') FROM monthly_kpi)
),
data AS (
    SELECT 
        strftime('%Y-%m',a.month) AS month,
        k.active_users
    FROM all_months a
    LEFT JOIN monthly_kpi k
    ON strftime('%Y-%m',a.month)=k.month
)
SELECT
    month,
    CASE 
        WHEN active_users IS NULL 
          OR LAG(active_users,1) OVER(ORDER BY month) IS NULL
        THEN NULL
        ELSE ROUND(
            (active_users-LAG(active_users,1) OVER(ORDER BY month))*1.0
            /LAG(active_users,1) OVER(ORDER BY month),4)
    END AS active_users_mom,
    CASE 
        WHEN active_users IS NULL 
          OR LAG(active_users,12) OVER(ORDER BY month) IS NULL
        THEN NULL
        ELSE ROUND(
            (active_users-LAG(active_users,12) OVER(ORDER BY month))*1.0
            /LAG(active_users,12) OVER(ORDER BY month),4)
    END AS active_users_yoy
FROM data
ORDER BY month;

-- 2. Identification of Key Growth Drivers of GMV
WITH g AS (
SELECT *,
LAG(gmv) OVER(ORDER BY month) pg,
LAG(order_count) OVER(ORDER BY month) po,
LAG(average_order_value) OVER(ORDER BY month) pa
FROM monthly_kpi
)
SELECT
month,
CASE WHEN gmv>pg THEN 'growth' END AS gmv_growth_flag,
CASE 
WHEN gmv<=pg OR pg IS NULL THEN NULL
WHEN order_count>po AND average_order_value>pa THEN 'Both'
WHEN order_count>po THEN 'Order volume driven'
WHEN average_order_value>pa THEN 'AOV driven'
ELSE 'Mixed'
END AS growth_driver
FROM g
ORDER BY month;

-- 3. Identification of months with fastest growth, largest decline and abnormal volatility of GMV (out of mean±2σ)
WITH g AS (
    SELECT
        month,
        (gmv-LAG(gmv) OVER(ORDER BY month))*1.0/
        LAG(gmv) OVER(ORDER BY month) AS mom
    FROM monthly_kpi
),
s AS (
    SELECT
        MAX(mom) max_mom,
        MIN(mom) min_mom,
        AVG(mom) avg_mom
    FROM g
    WHERE mom IS NOT NULL
),
v AS (
    SELECT
        g.*,
        s.*,
        sqrt(
            (SELECT AVG((mom-s.avg_mom)*(mom-s.avg_mom))
             FROM g
             WHERE mom IS NOT NULL)
        ) AS sd
    FROM g,s
)
SELECT
    month,
    ROUND(mom,4) AS gmv_mom_rate,
    CASE
        WHEN mom=max_mom THEN 'Fastest growth; '
        ELSE ''
    END ||
    CASE
        WHEN mom=min_mom THEN 'Largest decline; '
        ELSE ''
    END ||
    CASE
        WHEN mom>avg_mom+2*sd
          OR mom<avg_mom-2*sd
        THEN 'Abnormal volatility; '
        ELSE ''
    END ||
    CASE
        WHEN mom<>max_mom
         AND mom<>min_mom
         AND mom<=avg_mom+2*sd
         AND mom>=avg_mom-2*sd
        THEN 'Normal'
        ELSE ''
    END AS label
FROM v
WHERE mom IS NOT NULL
ORDER BY month;

-- 4. Detecting anomalies of GMV growth rate 
-- order_count_too_low: Months with order_count < 1,000 
-- growth_rate_too_high / growth_rate_too_low: Months with GMV MoM growth rate > 5 or < -5 
SELECT
    month,
    gmv,
    order_count,
    ROUND(
        (gmv-LAG(gmv) OVER(ORDER BY month))*1.0
        /LAG(gmv) OVER(ORDER BY month),
        4
    ) AS gmv_mom_growth_rate
FROM monthly_kpi
)
SELECT
    month,
    gmv_mom_growth_rate,
    order_count,
    CASE
        WHEN order_count<1000 
         AND gmv_mom_growth_rate>5
        THEN 'order_count_too_low, growth_rate_too_high'
        WHEN order_count<1000
         AND gmv_mom_growth_rate<-5
        THEN 'order_count_too_low, growth_rate_too_low'
        WHEN order_count<1000
        THEN 'order_count_too_low'
        WHEN gmv_mom_growth_rate>5
        THEN 'growth_rate_too_high'
        WHEN gmv_mom_growth_rate<-5
        THEN 'growth_rate_too_low'
        ELSE 'none'
    END AS label,
    CASE
        WHEN order_count<1000
          OR gmv_mom_growth_rate>5
          OR gmv_mom_growth_rate<-5
        THEN 'abnormal'
        ELSE 'normal'
    END AS status
FROM g
ORDER BY month;

-- 5. Assessment of Growth Stability and Sustainability of GMV
-- after deleting anomalies
-- calculate growth rate std
WITH g AS (
SELECT
    month,
    gmv,
    order_count,
    (gmv-LAG(gmv) OVER(ORDER BY month))*1.0
    /LAG(gmv) OVER(ORDER BY month) AS growth_rate
FROM monthly_kpi
),
clean AS (
SELECT growth_rate
FROM g
WHERE growth_rate IS NOT NULL
AND order_count >= 1000
AND growth_rate <= 5
AND growth_rate >= -5
),
avg_g AS (
SELECT AVG(growth_rate) avg_growth
FROM clean
)
SELECT
ROUND(
SQRT(AVG((growth_rate-avg_growth)*(growth_rate-avg_growth))),
4
) AS growth_rate_std
FROM clean,avg_g;
-- std=0.3153

