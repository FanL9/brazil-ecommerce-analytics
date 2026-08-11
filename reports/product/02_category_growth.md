| 时间 | 修改人 | 版本号 | 备注 |
|---|---|---|---|
| 2026-08-11 | hongshucham | V1.0 | 完成品类增长趋势分析，包括月度增长指标计算、CMGR 计算及品类增长表现分类 |

# 品类增长趋势分析（阶段四 Member 2）

## 1. 复用范围
- ['outputs/data/06_product_analysis/category_monthly_sales_base.csv'](outputs/data/06_product_analysis/category_monthly_sales_base.csv)
- ['outputs/data/06_product_analysis/category_sales_base.csv'](outputs/data/06_product_analysis/category_sales_base.csv)

---
以下表格制作皆根据['sql/06_product_analysis/02_category_growth.sql'](sql/06_product_analysis/02_category_growth.sql )
---

## 2. 增长分析
- 品类月度商品销售额环比；
- 品类月度订单量环比；
- 品类月度商品件数环比；

产出：
- ['outputs/data/06_product_analysis/category_monthly_growth.csv'](outputs/data/06_product_analysis/category_monthly_growth.csv)
- ['src/analysis/product_analysis/category_sales_heatmap.py'](src/analysis/product_analysis/category_sales_heatmap.py)
- ['visualizations/productcategory_sales_heatmap.png'](visualizations/productcategory_sales_heatmap.png)

描述：
- `sales_mom_growth`, `order_mom_growth`, `item_mom_growth`分别代表品类月度商品销售额环比，品类月度订单量环比，品类月度商品件数环比
- `sales_mom_growth`, `order_mom_growth`, `item_mom_growth`早期数据缺失由于无上月完整数据分析
- ['visualizations/productcategory_sales_heatmap.png'](visualizations/productcategory_sales_heatmap.png)只分析了 Top 15 品类
- Top 15 是根据整个观察期内累计销售额最高的15个品类来选取：health_beauty，watches_gifts，bed_bath_table，sports_leisure，computers_accessories，furniture_decor，housewares，cool_stuff，auto，toys，garden_tools，baby，perfumery，telephony，office_furniture

根据图片大致推断：
- Top 15 品类早期（2016‑09 至 2017 年上半年）颜色偏深紫、深蓝，销售额普遍偏低；从2017 年下半年开始，大量品类颜色逐步变亮，整体销售额持续抬升，平台整体规模随时间扩张
- 在Top 15 中，品类表现分化依旧明显，部分品类始终维持较低销售基数
- 未观察到品类统一的月度季节性

## 3.品类 CMGR 与平台整体 CMGR 

产出：
- ['outputs/data/06_product_analysis/category_and_platform_cmgr.csv'](outputs/data/06_product_analysis/category_and_platform_cmgr.csv)

描述：
- CMGR = (期末商品销售额 / 期初商品销售额)^(1 / 间隔月数) - 1
- 期初商品销售额：该品类第一个有销售记录月份的 `monthly_sales_amount`
- 期末商品销售额：该品类最后一个有销售记录月份的 `monthly_sales_amount`

大致推断：
- 得到所有品类的平均CMGR = 0.1204853049448846 > 0,对后续分析有帮助：1.05 * 平均CMGR > 0; 0.95 * 平均CMGR > 0
- 平台的CMGR = 0.461929152899462

## 4. 品类定义
- 明星品类：销售额 > 品类销售额中位数，且品类CMGR高于所有品类平均CMGR超过 5 percentage points；
- 潜力品类：销售额 ≤ 品类销售额中位数，但品类CMGR高于所有品类平均CMGR超过 5 percentage points；
- 稳定品类：CMGR ≥ 0，且未达到明星或潜力品类增长标准；
- 衰退品类：CMGR < 0；
- 新兴品类：观察期内首次出现销售，且无法计算有效 CMGR 的品类。

产出：['outputs/data/06_product_analysis/category_classification.csv'](outputs/data/06_product_analysis/category_classification.csv)

描述：

| Category Type | Number of Categories | Proportion | Core Characteristics |
|---|---:|---:|---|
| Stable Category（稳定品类） | 43 | 59.72% | 平台品类主体，CMGR 接近整体品类平均水平，增长表现平稳，构成业绩基本盘 |
| Star Category（明星品类） | 13 | 18.06% | 高销售额、高 CMGR，是平台核心增长驱动力 |
| Potential Category（潜力品类） | 9 | 12.50% | 当前销售规模较小，但 CMGR 显著高于平均品类 CMGR，具备未来增长潜力 |
| Declining Category（衰退品类） | 7 | 9.72% | CMGR < 0，长期复合增长为负，销售趋势持续下滑，需要进一步评估运营策略 |
| Emerging Category（新兴品类） | 0 | 0% | 观察期内缺少足够销售记录，无法计算有效 CMGR |

大致推断：
- 平台的增长动力不仅来自销售额最大的品类，也来自一些中小规模但增长速度很快的品类
- 部分潜力品类可能处于成长早期阶段，未来可能成为新的增长来源
- 平台没有明显的大规模品类衰退问题，主要挑战是如何扩大潜力品类规模，而不是处理大量衰退业务




