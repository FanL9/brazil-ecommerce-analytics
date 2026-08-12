| 时间 | 修改人 | 版本号 | 备注 |
|---|---|---|---|
| 2026-08-11 | hongshucham | V1.0 | 完成品类增长趋势分析，包括月度增长指标计算、CMGR 计算及品类增长表现分类 |
| 2026-08-12 | hongshucham | V1.1 | 数据集范围更改及分类定义修改 |

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
- 由于部分数据缺失，我们只保留2017-01到2018-07的数据进行分析
- `sales_mom_growth`, `order_mom_growth`, `item_mom_growth`分别代表品类月度商品销售额环比，品类月度订单量环比，品类月度商品件数环比
- `sales_mom_growth`, `order_mom_growth`, `item_mom_growth`早期数据缺失由于无上月完整数据分析
- ['visualizations/productcategory_sales_heatmap.png'](visualizations/productcategory_sales_heatmap.png)只分析了 Top 15 品类
- Top 15 是根据整个观察期内累计销售额最高的15个品类来选取：health_beauty，watches_gifts，bed_bath_table，sports_leisure，computers_accessories，furniture_decor，housewares，cool_stuff，auto，toys，garden_tools，baby，perfumery，telephony，office_furniture

根据图片大致推断：
- Top 15 品类早期（2016‑01 至 2017 年上半年）颜色偏深紫、深蓝，销售额普遍偏低；从2017 年下半年开始，大量品类颜色逐步变亮，整体销售额持续抬升，平台整体规模随时间扩张
- 在Top 15 中，品类表现分化依旧明显，部分品类始终维持较低销售基数
- 未观察到品类统一的月度季节性

## 3.品类 CMGR 与平台整体 CMGR 

产出：
- ['outputs/data/06_product_analysis/category_and_platform_cmgr.csv'](outputs/data/06_product_analysis/category_and_platform_cmgr.csv)

描述：
- CMGR = (期末商品销售额 / 期初商品销售额)^(1 / 间隔月数) - 1
- 期初商品销售额：该品类第一个有销售记录月份的 `monthly_sales_amount`
- 期末商品销售额：该品类最后一个有销售记录月份的 `monthly_sales_amount`
- 平台CMGR = （平台期末总额 / 平台期初总额）^(1 / 间隔月数) - 1
- 由于部分数据缺失，我们只保留2017-01到2018-07的数据进行分析
- 只有在2017-01与2018-07有数据的才会参与品类 CMGR 的计算，其他一律显示null

大致推断：
- 得到平台CMGR = 0.1205928153252045 > 0,对后续分析有帮助：1.05 * 平均CMGR > 0; 0.95 * 平均CMGR > 0

## 4. 品类定义
- 明星品类（Star Category）：有有效 CMGR，且销售额高于品类销售额中位数，同时品类 CMGR 高于平台 CMGR 超过 5 个 percentage points。
- 潜力品类（Potential Category）：有有效 CMGR，且销售额低于或等于品类销售额中位数，同时品类 CMGR 高于平台 CMGR 超过 5 个 percentage points。
- 稳定品类（Stable Category）：有有效 CMGR，且 CMGR ≥ 0，但未达到明星品类或潜力品类的增长标准。
- 衰退品类（Declining Category）：
   1. 对于有有效 CMGR 的品类：CMGR < 0；
   2. 对于无法计算 CMGR 的品类：2018-07 无销售记录。
- 新兴品类（Emerging Category）：无法计算有效 CMGR，且 2017-01 无销售记录、2018-07 有销售记录。

产出：['outputs/data/06_product_analysis/category_classification.csv'](outputs/data/06_product_analysis/category_classification.csv)

描述：

| Category Type | Number of Categories | Proportion | 
| ------------------------ | -------------------: | ---------- | 
| Stable Category（稳定品类） | 36 | 50.00% | 
| Star Category（明星品类） | 5 | 6.94% | 
| Potential Category（潜力品类） | 5 | 6.94% | 
| Declining Category（衰退品类） | 14 | 19.44% | 
| Emerging Category（新兴品类） | 12 | 16.67% | 

大致推断：
- 平台整体增长较为稳定：平台 CMGR 为 12.06%，说明 2017-01 至 2018-07 期间平台销售额保持较明显的复合增长。所有有效 CMGR 品类的平均值为 12.18%，与平台 CMGR 非常接近，说明整体品类增长水平与平台基本一致。
-  高销售额品类不一定都是高增长品类：health_beauty、watches_gifts、bed_bath_table 等销售额较高的核心品类，CMGR 虽然为正，但没有达到'平台 CMGR + 5 percentage points'的标准，因此属于 Stable Category。相比之下，housewares、telephony 等虽然销售规模不同，但 CMGR 明显高于平台，因此被划为 Star Category。说明销售规模和增长速度是两个不同维度，不能单纯根据销售额判断品类发展潜力。
- 星品类是平台的重要增长来源：典型明星品类包括 housewares、telephony、pet_shop、musical_instruments、agro_industry_and_commerce。这些品类的 CMGR 都明显高于平台 12.06% + 5pp = 17.06%，说明它们具备相对更强的增长动能。
- 潜力品类规模较小，但增长速度较快: 例如 food、music、furniture_bedroom、fashion_shoes、books_general_interest。它们销售额低于品类销售额中位数，但增长明显高于平台，因此可以视为未来值得关注的增长储备。
- 大量品类属于 Stable Category: 这是目前最明显的特征：很多品类 CMGR 为正，但没有达到平台 CMGR + 5pp 的高增长门槛。例如 health_beauty、watches_gifts、sports_leisure、computers_accessories。这说明平台的品类结构中，大部分品类并不是高速扩张，而是在较稳定地增长，构成平台的基本盘。
- 还存在明显的衰退品类: 例如 market_place、fashion_underwear_beach、home_confort_2。这些品类的 CMGR < 0，说明期初到期末销售额出现长期复合下降，需要进一步观察是否属于需求下降、季节性变化或品类规模较小导致的波动。

