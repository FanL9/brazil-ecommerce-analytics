--- 1. Growth Quality Analysis ---

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

