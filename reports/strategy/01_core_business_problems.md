# 阶段六 Member 1：核心业务问题提炼

| 日期 | 修改人 | 版本号 | 备注 |
|---|---|---|---|
| 2026-08-14 | Codex | v1.0 | 完成阶段一至四证据盘点、候选问题评审、5 个核心业务问题及阶段六交接边界 |
| 2026-08-14 | Codex | v1.1 | 按业务重要性复核，新增区域与支付集中暴露；核心问题扩展至 7 个，并拆分证据强度与业务优先级 |

## 1. 分析目标与交付边界

本报告只完成阶段六 Member 1 的职责：基于仓库内阶段一至四已经产出的报告、SQL/Python、CSV、数据库派生表和图表，提炼可复核的核心业务问题，并为 Member 2 的策略设计和 Member 3 的优先级/效果评估提供统一问题编号、证据基线和分析限制。

本次最终保留 **7 个核心业务问题（CBP-01—CBP-07）**。机器可读摘要见 `outputs/data/strategy/core_problem_summary.csv`，每个问题在 CSV 中只占一行，编号、数值和时间窗与本报告一致。问题选择同时考虑证据可靠性和业务重要性；“证据强度”不再被用作“业务优先级”的替代指标。

### 1.1 阶段六分工确认

- 仓库 `README.md` 的“阶段六：问题总结与策略输出”规定：先提炼 3—5 个有量化证据的核心问题，再进行策略制定、优先级排序和效果评估。
- 当前任务后续指示明确允许在原 5 个问题上再增加 1—2 个，并要求纳入业务层面重要性；因此本版按更具体的新指示扩展为 7 个问题。
- `reports/README.md` 仅把阶段六标记为待交付；仓库中未发现独立的阶段六成员分工文档。
- 因此，本次以当前任务给出的 Member 1 职责为执行边界。既有空占位文件 `reports/strategy/strategy_report.md`、`reports/final/final_report.md` 和其他成员产物均不修改。
- 阶段五物流正式报告仍为空，本任务又明确要求检查阶段一至四，所以本报告不引入阶段五物流结论，也不对物流成本、破损、丢失或物流因果效应作结论。

## 2. 证据使用原则

1. **只用仓库内证据。** 数值必须能回溯到现有 CSV、SQLite 派生表、正式阶段报告、SQL/Python 输出或已生成图表。
2. **先统一口径，再比较。** GMV、支付订单量和 AOV 使用正支付且已交付订单；用户复购/RFM 使用 `customer_unique_id` 和 2018-07-31 正式截点；品类销售额只使用 `order_items.price`，不与支付 GMV 混用。
3. **不把相关写成因果。** 同期变化、分组差异、RFM 分层和关联规则只描述历史数据关系，不证明原因或策略效果。
4. **边界月不进入正式趋势比较。** 2016-09 和 2018-08 为不完整月，只用于覆盖边界说明；2016-11 没有已交付订单，不补零。
5. **证据与业务重要性分开。** “证据强度”评估数值和问题陈述是否可靠；“业务优先级”评估影响规模、收入暴露、经营连续性和可管理性。集中结构可以作为高优先级业务暴露，但必须明确注明尚未验证实际损失。
6. **历史价值不等于未来收益。** RFM Monetary、历史 GMV、关联规则和情景测算均不得直接解释为未来可恢复收入或确定提升。

### 2.1 证据强度定义

| 级别 | 判定标准 | 本报告处理 |
|---|---|---|
| 高 | 正式窗口与定义明确；CSV/数据库可回算；脚本与阶段报告一致；比较基准同口径 | 可进入核心业务问题 |
| 中 | 数值可靠，但缺少外部基准、实际损失或业务负面结果证据 | 仅列观察项 |
| 不足 | 截点、分母、去重或脚本版本未与最终口径统一；结果无法稳定复核 | 列待验证项，不进入核心问题 |

### 2.2 业务优先级定义

| 级别 | 判定标准 | 与证据强度的关系 |
|---|---|---|
| 高 | 覆盖用户/订单/GMV 较大，关系收入质量、客户关系、经营连续性或资源配置，且存在明确管理抓手 | 可以与“负面结果尚未验证”并存，但问题标题必须写成结构暴露而非已发生损失 |
| 中高 | 影响对象明确且可行动，但实际增量、利润或根因仍需实验/拆解 | 适合作为专项改善问题，不等于全平台最高优先级 |
| 中 | 结构事实可靠，但业务后果、规模或可管理性不足以支持优先投入 | 保留监控或补数，不自动升级 |

## 3. 阶段一至四证据盘点

### 3.1 统一窗口与指标口径

| 分析层 | 正式时间范围 | 订单/用户范围 | 本报告使用方式 |
|---|---|---|---|
| 阶段一：数据治理与核心指标 | 原始数据全观察期；已交付订单购买时间覆盖 2016-09-15 12:16:38—2018-08-29 15:00:37 | 订单按 `order_id`；用户按 `customer_unique_id`；支付先聚合到订单 | 用于验证全期 GMV、订单、评价、品类销售额及清洗规则 |
| 阶段二：业务概览 | 月度覆盖 2016-09—2018-08；正式完整月排除 2016-09、2018-08；同比统一用 2017-01—07 与 2018-01—07 | 正支付且 `delivered`；GMV 为订单级正支付额；AOV=GMV/支付订单量 | CBP-02 使用两个完整、等长的 1—7 月窗口 |
| 阶段三：全期用户画像 | 已交付订单全观察期，截至 2018-08-29 | `customer_unique_id` 去重 | 只作总体结构描述，不与正式 RFM 截点直接合并 |
| 阶段三：RFM/流失/高价值正式层 | `order_purchase_timestamp < 2018-08-01`，观察日 2018-07-31 | `delivered`；Monetary 为正支付订单额；复购为窗口内至少 2 单 | CBP-01、CBP-03 的唯一用户价值窗口 |
| 阶段四：品类销售/帕累托/满意度/关联 | 已交付订单全观察期，边界同 2016-09-15—2018-08-29 | 商品销售额=`SUM(order_items.price)`，不含运费；评价每订单一条代表记录 | CBP-04、CBP-05；不与支付 GMV直接相加或替换 |
| 阶段四：品类增长 | 2017-01—2018-07 | 已交付订单、按购买月、商品销售额 | 只用于候选评审，不与全期品类金额混为同一窗口 |

### 3.2 阶段报告

| 阶段 | 文件 | 指标口径 | 时间范围与采用状态 |
|---|---|---|---|
| 一 | `reports/data_quality/data_quality_report.md` | 9 张原始表、主外键/缺失/重复/时间逻辑、清洗视图、核心指标验证 | 全观察期；作为数据可用性与异常边界依据 |
| 二 | `reports/business_analysis/02_business_overview_report.md` | 支付型月度 KPI、增长质量、支付/订单金额/州结构 | 正式整合报告；完整月与全期结构分开使用 |
| 二 | `reports/business_analysis/business_trend_analysis.md` | 月度 GMV、支付订单量、AOV、新增/活跃用户、IQR 环比诊断 | 2016-09—2018-08；边界月只标记、不作正式比较 |
| 二 | `reports/business_analysis/growth_quality_holiday_seasonality_analysis.md` | 环比、节假日日均 GMV/订单/AOV | 历史支撑报告；最终口径以整合报告为准 |
| 二 | `reports/business_analysis/business_diagnosis_report.md` | 支付、订单金额、州结构和诊断 | 部分比较曾包含不完整 2018-08；本报告不采用其跨年 1—8 月比较 |
| 二 | `reports/business_analysis/core_business_issues.md` | 阶段二候选问题 | 历史候选清单；区域旧值和风险表述不作为本次最终证据 |
| 二 | `reports/business_analysis/strategy_scenario_analysis.md` | AOV、支付、区域情景测算 | 所有提升率为条件假设，不作为已发生事实或预测证据 |
| 三 | `reports/customer/03_customer_analysis_final_report.md` | 全期画像、截止日 RFM/流失/高价值交叉及口径对账 | 阶段三正式整合报告；明确排除未统一重跑的短期留存/生命周期数值 |
| 三 | `reports/customer/customer_analysis_report.md` | 全期地域、城市、时段和区域增长画像 | 截至 2018-08-29；只作全期描述 |
| 三 | `reports/customer/rfm_customer_value_report.md` | Recency/Frequency/Monetary、五类分群、复购和历史 GMV | 截止 2018-07-31；CBP-01、CBP-03 主要报告来源 |
| 三 | `reports/customer/customer_lifecycle_cohort_analysis.md` | Cohort、短期复购、生命周期分层 | 旧产物未完全与最终截止日/分母统一；只列待验证 |
| 三 | `reports/customer/churn_user_analysis_report.md` | Recency>90 天的行为型流失、体验/支付/地域对比 | 截止 2018-07-31；只支持观察项，不能解释永久流失或原因 |
| 四 | `reports/product/product_analysis_report.md` | 72 品类销售、增长、满意度、关联规则的正式整合 | 销售/满意度/关联为全期；增长为 2017-01—2018-07 |
| 四 | `reports/product/01_category_pareto.md` | 商品销售额及 80% 帕累托头部规则 | 全观察期 delivered；商品 `price`，不含运费 |
| 四 | `reports/product/02_category_growth.md` | 品类月销售和 CMGR 分类 | 2017-01—2018-07；分类数量以最终 CSV/整合报告为准 |
| 四 | `reports/product/03_category_satisfaction.md` | 每订单代表评价、均分、1 星率、有效评价门槛 | 全观察期；正式比较要求 `valid_review_orders>=30` |
| 四 | `reports/product/04_product_association.md` | 商品/品类购物篮、支持度、置信度、Lift | 全观察期 96,478 个 delivered 订单 |

### 3.3 关键 CSV

| 阶段 | 文件 | 关键指标与粒度 | 时间范围/限制 |
|---|---|---|---|
| 一 | `outputs/data_quality_issues.csv` | 一行一个数据质量问题及严重度/处理规则 | 原始全期；不把数据异常当作业务原因 |
| 一 | `outputs/metric_validation.csv` | 56 条指标验证；含全期 GMV 15,422,461.77、有效订单 96,478、平台均分 4.155908 | 全观察期；M18 的旧 74 品类行数不用于阶段四，阶段四以 72 品类正式层为准 |
| 二 | `outputs/data/02_business_overview/monthly_kpi.csv` | 月粒度 GMV、支付订单、AOV、新增/活跃用户 | 2016-09—2018-08；CBP-02 主表 |
| 二 | `outputs/data/02_business_overview/monthly_growth_rates.csv` | 连续观测月环比 | 边界月及极低基数需单独解释 |
| 二 | `outputs/data/02_business_overview/monthly_trend_diagnostics.csv` | IQR 异常月和连续性诊断 | 同月度 KPI 窗口 |
| 二 | `outputs/data/02_business_overview/daily_kpi.csv` | 日 GMV/订单/AOV | 全观察期，用于节日窗口，不直接外推季节规律 |
| 二 | `outputs/data/02_business_overview/holiday_comparison.csv` | 节前/节中/节后日均 KPI | 仅覆盖有完整观测的节日样本 |
| 二 | `outputs/data/02_business_overview/payment_structure.csv` | 支付方式 GMV/订单结构；带 ALL_DATA 和两个 1—7 月总计 | 全期及 2017/2018 年 1—7 月；CBP-02 交叉核验、CBP-07 主表 |
| 二 | `outputs/data/02_business_overview/order_value_structure.csv` | 订单金额带的订单/GMV份额 | 全期正支付 delivered；金额不代表利润 |
| 二 | `outputs/data/02_business_overview/state_structure.csv` | 州级 GMV、订单、份额、HHI 和可比期增长 | 全期及 2017/2018 年 1—7 月；CBP-06 主表；未按人口或市场容量标准化 |
| 二 | `outputs/data/02_business_overview/strategy_scenarios.csv` | 假设提升率与情景结果 | 以 2018-07 为基线；只是假设，不作为核心问题事实 |
| 三 | `outputs/data/03_customer_analysis/customer_order_base.csv` | 一行一笔 delivered 订单，支付已聚合到订单 | 全观察期；阶段三公共底层 |
| 三 | `outputs/data/03_customer_analysis/customer_profile.csv` | 全期用户/订单/GMV总览 | 截至 2018-08-29；不与截止日层直接合并 |
| 三 | `outputs/data/03_customer_analysis/state_customer_profile.csv` | 州级用户与 GMV | 全观察期 |
| 三 | `outputs/data/03_customer_analysis/city_customer_profile.csv` | 城市级用户与 GMV | 全观察期 |
| 三 | `outputs/data/03_customer_analysis/hourly_customer_behavior.csv` | 下单小时分布 | 全观察期；描述性 |
| 三 | `outputs/data/03_customer_analysis/weekday_customer_behavior.csv` | 星期分布 | 全观察期；描述性 |
| 三 | `outputs/data/03_customer_analysis/potential_regional_markets.csv` | 两个等长阶段的州级增长候选 | 2017-08—2018-01 对比 2018-02—2018-07；只作市场候选，不证明潜力实现 |
| 三 | `outputs/data/03_customer_analysis/rfm_customer_detail.csv` | 87,214 行用户级 RFM、复购、历史 GMV和分群 | 截止 2018-07-31 |
| 三 | `outputs/data/03_customer_analysis/rfm_segment_summary.csv` | 五类用户数、订单、GMV、复购、Recency | 截止 2018-07-31；CBP-01、CBP-03 主表 |
| 三 | `outputs/data/03_customer_analysis/rfm_validation.csv` | RFM 总量、唯一性、分群和边界校验 | 截止 2018-07-31 |
| 三 | `outputs/data/03_customer_analysis/churn_user_detail.csv` | 87,214 行行为型流失标记 | 截止 2018-07-31；阈值 Recency>90 天 |
| 三 | `outputs/data/03_customer_analysis/churn_comparison.csv` | 流失/未流失的用户、GMV、复购、评价、配送对比 | 同截止日；相关差异不构成因果 |
| 三 | `outputs/data/03_customer_analysis/churn_related_features.csv` | 流失与行为/体验特征的关联摘要 | 同截止日；不作原因解释 |
| 三 | `outputs/data/03_customer_analysis/cohort_monthly_retention.csv` | 自然月 Cohort 留存 | 含较新 cohort 右截尾；只作待验证/观察 |
| 三 | `outputs/data/03_customer_analysis/short_term_repeat_retention.csv` | 旧版 7/30/90 天口径 | 最终阶段报告已标记未统一重跑；不采用 |
| 三 | `outputs/data/03_customer_analysis/customer_lifecycle_segment.csv` | 旧版生命周期分层 | 截点/分母与正式层未统一；不采用 |
| 四 | `outputs/data/06_product_analysis/category_sales_base.csv` | 72 品类销售额、份额、订单、商品数和排名 | 全期 delivered；`price` 不含运费 |
| 四 | `outputs/data/06_product_analysis/category_pareto.csv` | 72 品类累计销售份额和 head/long_tail | 全期；第 18 个品类跨过 80%阈值 |
| 四 | `outputs/data/06_product_analysis/category_monthly_sales_base.csv` | 月×品类销售、订单、商品数 | 全观察期；增长正式窗口另限 2017-01—2018-07 |
| 四 | `outputs/data/06_product_analysis/category_and_platform_cmgr.csv` | 品类和平台 CMGR | 2017-01—2018-07；缺起止月者不计算有效 CMGR |
| 四 | `outputs/data/06_product_analysis/category_classification.csv` | 72 品类增长分类 | 2017-01—2018-07；以该 CSV 和整合报告为最终版本 |
| 四 | `outputs/data/06_product_analysis/category_satisfaction.csv` | 72 品类评价订单、均分、1 星率、好评率、负向文本数 | 全期；63 个品类满足不少于 30 单，CBP-05 主表 |
| 四 | `outputs/data/06_product_analysis/category_negative_keywords.csv` | 1 星文本关键词明细/统计 | 全期；仅作问题定位线索，不证明根因 |
| 四 | `outputs/data/06_product_analysis/product_association_top20.csv` | 通过阈值的商品规则 Top20 | 全期 96,478 单；共现样本很小 |
| 四 | `outputs/data/06_product_analysis/category_association_top20.csv` | 通过阈值的跨品类规则 | 全期；只有 1 条，CBP-04 主表之一 |

### 3.4 关键 SQL/Python 脚本

| 阶段 | 文件 | 计算口径 | 时间范围 |
|---|---|---|---|
| 一 | `sql/01_data_quality/data_quality_check.sql` | 9 表质量检查、主外键、时间/金额/重复异常 | 原始全期 |
| 一 | `sql/02_data_cleaning/data_cleaning_rules.sql` | 订单、支付、评价、配送等清洗视图 | 原始全期；IQR 长尾保留并标记 |
| 一 | `sql/03_metrics/core_metrics.sql` | GMV、订单、用户、配送、平均评价等核心指标 | 全观察期或调用时指定窗口 |
| 一 | `sql/03_metrics/derived_metrics.sql` | AOV、复购率、留存、LTV、延迟率、好评率等派生指标 | 依指标窗口；支付先到订单级 |
| 一 | `src/data_processing/build_sqlite_database.py` | 原始 CSV 入库及公共数据库构建 | 原始全期 |
| 二 | `sql/02_business_overview/00_monthly_kpi_view.sql` | 正支付 delivered 月度 GMV/订单/AOV/新增/活跃 | 观测自然月；CBP-02 口径源 |
| 二 | `sql/02_business_overview/02_growth_quality.sql` | 月度增长质量和诊断 | 完整月规则由阶段二标准约束 |
| 二 | `sql/02_business_overview/03_seasonality_analysis.sql` | 日/节日窗口聚合 | 有覆盖的节日窗口 |
| 二 | `sql/02_business_overview/04_business_structure.sql` | 支付、订单金额、州结构 | 全期及两个 1—7 月可比窗；CBP-06/07 口径源 |
| 二 | `src/analysis/business_overview/business_overview_trends.py` | 月度结果导出和趋势图 | 2016-09—2018-08，边界标记 |
| 二 | `src/analysis/business_overview/business_structure.py` | 支付/金额/州结构导出与图表 | 全期及可比窗 |
| 二 | `src/analysis/business_overview/seasonality_analysis.py` | 节日比较 | 完整节日窗口 |
| 二 | `src/analysis/business_overview/strategy_scenario_analysis.py` | 条件情景测算 | 2018-07 基线；不作预测证据 |
| 三 | `sql/05_customer_analysis/00_customer_common_views.sql` | 订单级客户公共层、支付订单级聚合 | 全观察期 |
| 三 | `sql/05_customer_analysis/01_customer_profile_analysis.sql` | 地域、城市、时段和阶段画像 | 全观察期及报告规定的等长区域窗 |
| 三 | `sql/05_customer_analysis/02_rfm_analysis.sql` | 截止日 RFM、五类分群、复购和汇总 | 观察日 2018-07-31；CBP-01/03 口径源 |
| 三 | `sql/05_customer_analysis/03_churn_analysis.sql` | Recency>90 天行为型流失与对比 | 订单时间早于 2018-08-01 |
| 三 | `sql/05_customer_analysis/03_customer_lifecycle_cohort_analysis.sql` | Cohort/生命周期旧产物 | 未全部与最终正式层统一，不用于核心结论 |
| 三 | `src/analysis/customer_analysis/customer_profile_analysis.py` | 用户画像 CSV/图表 | 全观察期 |
| 三 | `src/analysis/customer_analysis/rfm_analysis.py` | RFM 导出、验证和图表 | 截止 2018-07-31 |
| 三 | `src/analysis/customer_analysis/churn_analysis.py` | 流失输出和比较 | 截止 2018-07-31 |
| 四 | `sql/06_product_analysis/category_order_base.sql` | delivered 商品明细、订单×品类和月×品类公共层 | 全观察期；商品销售额不含运费 |
| 四 | `sql/06_product_analysis/01_category_sales_pareto.sql` | 80% 累计销售额头部长尾规则 | 全观察期 |
| 四 | `sql/06_product_analysis/02_category_growth.sql` | 月增长、CMGR 和分类 | 2017-01—2018-07 |
| 四 | `sql/06_product_analysis/04_category_satisfaction.sql` | 每订单代表评价、品类均分和样本门槛 | 全观察期 |
| 四 | `src/analysis/product_analysis/category_common_layer.py` | 品类公共层构建/导出 | 全观察期 |
| 四 | `src/analysis/product_analysis/category_pareto_analysis.py` | 帕累托导出与图表 | 全观察期 |
| 四 | `src/analysis/product_analysis/category_review_keywords.py` | 1 星文本关键词 | 全观察期 |
| 四 | `src/analysis/product_analysis/product_association_rules.py` | 去重商品/品类篮子；共现≥5、置信度≥10%、Lift>1 | 全期 96,478 个 delivered 订单；CBP-04 口径源 |

### 3.5 已检查的关键图表

| 阶段 | 图表文件 | 指标与时间范围 | 使用状态 |
|---|---|---|---|
| 二 | `visualizations/business_overview/01_gmv_trend.png`；`02_order_count_trend.png`；`03_average_order_value_trend.png`；`04_new_users_trend.png`；`05_active_users_trend.png`；`06_core_metrics_overview.png` | 支付型月度 KPI，2016-09—2018-08，边界月有标记 | 与月度 CSV/正式报告一致；CBP-02 使用总览图作视觉出处 |
| 二 | `visualizations/business_overview/monthly_growth_rate.png`；`seasonal_pattern.png` | 环比与节日模式 | 只作诊断；不把单一节日写成稳定规律 |
| 二 | `visualizations/business_overview/payment_structure.png`；`order_value_structure.png`；`regional_structure_change.png`；`state_gmv_ranking.png` | 全期及 2017/2018 年 1—7 月结构 | 支付/区域/金额集中只列观察项 |
| 三 | `visualizations/customer/state_users_gmv_contribution.png`；`top10_city_users.png`；`hourly_consumption_distribution.png`；`weekday_consumption_distribution.png`；`regional_market_potential.png` | 全期画像及两个等长区域窗口 | 描述性，不与截止日 RFM 合并 |
| 三 | `visualizations/customer/rfm/rfm_segment_user_distribution.png`；`rfm_segment_gmv_contribution.png`；`rfm_user_vs_gmv_share.png`；`rfm_spend_per_user.png`；`rfm_repeat_purchase_rate.png` | 截止 2018-07-31 的 RFM | 与 RFM CSV 一致；CBP-01/03 图表出处 |
| 三 | `visualizations/customer/churn_core_metrics_comparison.png`；`churn_experience_comparison.png`；`churn_feature_association_strength.png`；`churn_payment_structure.png`；`churn_state_comparison.png`；`churn_weekday_weekend_comparison.png` | 截止 2018-07-31 的行为型流失对比 | 只支持关联观察，不支持原因结论 |
| 三 | `visualizations/customer/cohort_retention_heatmap_log.png` | 自然月 Cohort 留存，含右截尾 | 观察项；不进入核心问题 |
| 三 | `visualizations/customer/high_value/high_value_consumption_comparison.png`；`high_value_experience_comparison.png`；`high_value_payment_comparison.png` | 正式截止日的高价值样本对比 | 高价值/保持样本极小，只作个案警示 |
| 四 | `visualizations/product/category_sales_pareto.png`；`category_head_long_tail_structure.png`；`category_sales_heatmap.png` | 全期销售及 2017-01—2018-07 月度热力图 | 品类集中只列观察项 |
| 四 | `visualizations/product/category_satisfaction_matrix.png`；`negative_keywords_office_furniture.png`；`negative_keywords_audio.png`；`negative_keywords_bed_bath_table.png` | 全期满意度及 1 星文本 | CBP-05 使用满意度矩阵；关键词只作后续定位线索 |

## 4. 候选问题证据评审

| 候选编号 | 候选问题/观察 | 核心数值与比较 | 事实证据 | 业务优先级 | 是否形成结论 |
|---|---|---|---|---|---|
| C01 | 正式窗口复购基础薄弱 | 2,621/87,214 复购，3.0053%；84,593 人、96.9947% 仅一单 | 高 | 高 | 是，CBP-01 |
| C02 | 可比期 AOV 未随规模同幅提升 | 2018 年 1—7 月相对上年同期：GMV +164.0709%、支付订单 +160.7807%、AOV +1.2617% | 高 | 高 | 是，CBP-02 |
| C03 | 历史价值集中在重要挽留用户 | 23.3804% 用户贡献 42.7799% GMV；平均 Recency 316.31558 天 | 高 | 高 | 是，CBP-03 |
| C04 | 购物篮单商品化、共购证据稀疏 | 单商品订单 96.686291%；多商品仅 3.313709%；跨品类有效规则 1 条且支持度 0.0445697% | 高 | 中高 | 是，CBP-04 |
| C05 | office_furniture 满意度落后 | 1,244 个有效评价均分 3.644695；平台 4.155908；差 -0.511214；正式可比品类最低 | 高 | 中高 | 是，CBP-05 |
| C06 | 区域 GMV 集中暴露 | SP/RJ/MG 合计 62.5402%，其余 24 州合计 37.4598%；Top10 占 87.3633% | 高（结构事实） | 高 | 是，CBP-06；不声称已发生损失 |
| C07 | 支付方式集中暴露 | 信用卡贡献 78.4641% GMV、覆盖 75.4429% 主支付订单；其他方式分别为 21.5359%/24.5571% | 高（结构事实） | 高 | 是，CBP-07；不声称渠道已经失效 |
| O01 | 行为型流失占比较高 | Recency>90 天用户 68,686/87,214，占 78.76%；未流失 21.24% | 高（阈值事实） | 高 | 观察项；右截尾且与 C01/C03 重叠，不独立升级 |
| O02 | 品类销售集中 | 18/72 个品类贡献 81.2887%，其余 54 个贡献 18.7113% | 高（结构事实） | 中 | 观察项；集中结构本身不是经营损失或品类缺陷 |
| O03 | Black Friday 单次窗口放量 | 2017 Black Friday 日均 GMV +381.67%、订单 +469.29%、AOV -15.39% | 高（单次事件） | 中 | 观察项；单一完整事件样本不能证明稳定季节规律 |
| V01 | 7/30/90 天短期留存 | 旧输出存在，但最终阶段三报告明确未按统一截止日和分母完整重跑 | 不足 | 待定 | 待验证；不引用为事实基线 |
| V02 | 生命周期分层占比 | 旧生命周期输出与正式 2018-07-31 截止层未完成一致性对账 | 不足 | 待定 | 待验证；不进入核心问题 |

## 5. 核心问题总览

| 问题编号 | 核心问题 | 最小充分证据 | 优先影响对象 | 证据强度 | 业务优先级 |
|---|---|---|---|---|---|
| CBP-01 | 正式分析窗内复购基础薄弱 | 复购率 3.0053%；96.9947% 用户仅一单 | 84,593 名单次购买用户 | 高 | 高 |
| CBP-02 | 可比期规模扩张未伴随 AOV 同幅提升 | 同比 GMV +164.0709%、支付订单 +160.7807%、AOV +1.2617% | 2018 年 1—7 月 46,432 个支付订单 | 高 | 高 |
| CBP-03 | 高历史价值集中在重要挽留用户 | 23.3804% 用户贡献 42.7799% 历史 GMV；平均 Recency 316.31558 天 | 20,391 名重要挽留用户 | 高 | 高 |
| CBP-04 | 历史购物篮高度单商品化且共购证据稀疏 | 96.686291% 单商品订单；仅 1 条跨品类有效规则 | 全期 96,478 个 delivered 订单 | 高 | 中高 |
| CBP-05 | office_furniture 满意度明显低于平台均值 | 3.644695 vs 4.155908，低 0.511214 分；正式品类最低 | 1,244 个有效评价订单及品类销售额 268,154.31 BRL | 高 | 中高 |
| CBP-06 | 区域 GMV 高度集中于少数核心州 | SP/RJ/MG 占 62.5402%；Top10 占 87.3633% | 全期 96,477 个支付订单及 15,422,461.77 BRL GMV | 高（结构事实） | 高 |
| CBP-07 | 支付方式高度集中且渠道韧性数据不足 | 信用卡占 78.4641% GMV、75.4429% 主支付订单 | 72,785 个信用卡主支付订单 | 高（结构事实） | 高 |

## 6. 核心问题完整证据链

### CBP-01：正式分析窗内复购基础薄弱

**问题定义。** 在统一截止窗口内，绝大多数活跃用户只产生一笔已交付订单，窗口内重复购买覆盖面很小。

**可复核量化证据。** `rfm_segment_summary.csv` 五个层级合计 87,214 名用户、90,127 个已交付订单和 2,621 名复购用户：

- 复购率 = 2,621 / 87,214 = **3.0053%**；
- 单次购买用户 = 87,214 - 2,621 = **84,593 人**，占 **96.9947%**；
- 平均购买频次 = 90,127 / 87,214 = **1.033401 单/用户**。

**比较基准。** 本问题采用同一窗口内“复购用户 vs 单次购买用户”的内部结构比较，不引用行业目标。单次购买用户比复购用户多 81,972 人。

**证据来源。** `outputs/data/03_customer_analysis/rfm_segment_summary.csv`；`reports/customer/rfm_customer_value_report.md`；`reports/customer/03_customer_analysis_final_report.md`；`sql/05_customer_analysis/02_rfm_analysis.sql`。

**影响范围/优先对象。** 正式窗口内 87,214 名活跃用户，优先分析 84,593 名单次购买用户；后续应先按首购品类、金额、购买时间和可用体验字段分层，不能视为同质人群。

**分析限制与禁止解释。** 这是 2018-07-31 截点下的窗口内复购率，不是完整历史累计复购率；数据开始前的购买不可见。现有证据不能说明低复购由商品、营销、物流、价格或支付造成，也不能与旧版 7/30/90 天留存率混用。

**后续策略方向。** 对可触达的单次购买用户分层设计二购实验，保留随机或准实验对照组；主指标用增量复购率和净 GMV，并以毛利、退货/取消和触达成本作护栏。方向只定义验证方式，不预设提升成立。

### CBP-02：可比期规模扩张未伴随 AOV 同幅提升

**问题定义。** 在两个完整、等长的 1—7 月窗口中，GMV与支付订单量均大幅增加，但 AOV 只小幅变化，订单价值没有随规模同幅提升。

**可复核量化证据。** 对 `monthly_kpi.csv` 的两个七个月窗口求和，并用同口径 GMV/支付订单量计算 AOV：

| 指标 | 2017-01—2017-07 | 2018-01—2018-07 | 同比变化 |
|---|---:|---:|---:|
| GMV（BRL） | 2,827,862.15 | 7,467,560.92 | +164.0709% |
| 支付订单量 | 17,805 | 46,432 | +160.7807% |
| AOV（BRL/单） | 158.824047 | 160.827897 | +1.2617% |

`payment_structure.csv` 在两个可比期间给出的 `total_gmv` 和 `total_paid_orders` 与上述汇总一致。阶段二正式报告还显示，2017-02—2018-07 的月 AOV 主要位于 146.282007—169.757785 BRL/单，明显比规模指标稳定。

**比较基准。** 相同月份的同比比较，排除了不完整的 2018-08，也避免把 2016-09 边界月作为基准。

**证据来源。** `outputs/data/02_business_overview/monthly_kpi.csv`；`outputs/data/02_business_overview/payment_structure.csv`；`reports/business_analysis/02_business_overview_report.md`；`sql/02_business_overview/00_monthly_kpi_view.sql`；`visualizations/business_overview/06_core_metrics_overview.png`。

**影响范围/优先对象。** 2018 年 1—7 月 46,432 个正支付且已交付订单；后续可以订单金额带、品类、用户层级进一步拆分，但每次拆分必须保持支付订单分母一致。

**分析限制与禁止解释。** 该分解是会计恒等式和同比描述，不证明获客、促销、品类或外部市场导致增长；GMV 未扣除成本、退款、获客费用和补贴。不能将 +164.0709% 外推为未来增速，也不能把 AOV 提升情景写成已实现收益。

**后续策略方向。** 在保持订单转化、净收益和服务质量护栏的条件下，小流量测试加购、组合和价格带呈现；联合监控订单量、AOV、净 GMV、毛利和取消/评价，防止只优化单一 AOV。

### CBP-03：高历史价值集中在重要挽留用户

**问题定义。** 以正式 RFM 规则划分后，历史 GMV 最大的一组不是近期活跃层，而是 Recency 较低、Frequency 较低、Monetary 较高的“重要挽留用户”。

**可复核量化证据。** `rfm_segment_summary.csv` 显示：

- 重要挽留用户 **20,391 人**，占 **23.3804%**；
- 观察期历史 GMV **6,176,160.10 BRL**，占 **42.7799%**，比其用户占比高 **19.3995 个百分点**；
- 平均 Recency **316.31558 天**，人均历史消费 **302.89 BRL**；
- 作为比较，重要发展用户平均 Recency **84.067946 天**、GMV 占比 **30.7030%**；重要挽留用户是五类中历史 GMV 占比最高的一类。

**比较基准。** 同一 RFM 窗口、同一 Monetary 定义下的用户占比与 GMV占比，以及与重要发展用户的层级对比。

**证据来源。** `outputs/data/03_customer_analysis/rfm_segment_summary.csv`；`outputs/data/03_customer_analysis/rfm_customer_detail.csv`；`reports/customer/rfm_customer_value_report.md`；`sql/05_customer_analysis/02_rfm_analysis.sql`；`visualizations/customer/rfm/rfm_user_vs_gmv_share.png`。

**影响范围/优先对象。** 20,391 名重要挽留用户；该层历史 GMV 规模为 6,176,160.10 BRL，但这只是历史观察值，不是可恢复收入承诺。

**分析限制与禁止解释。** RFM 分层本身使用 Recency/Frequency/Monetary，因此不能把层级差异解释为营销或体验造成。历史 GMV 不代表未来购买，Recency>90 的行为型流失标记也不等同于永久流失。由于 F 高分对应的极高频样本很小，不能用“重要价值用户 4 人、重要保持用户 1 人”做规模策略外推。

**后续策略方向。** 先按最近品类、历史金额、最近购买时间和可触达性再次分层，再以对照实验验证召回；评估增量复购、净 GMV、毛利和触达成本，禁止把 42.7799% 历史 GMV直接列为目标回收额。

### CBP-04：历史购物篮高度单商品化且共购证据稀疏

**问题定义。** 已交付订单的去重商品篮子几乎都是单商品订单，历史数据中满足正式阈值的跨品类关联证据也极少。

**可复核量化证据。** 对数据库 `category_item_base` 按订单统计去重商品：

- 总 delivered 订单 **96,478**；
- 单商品订单 **93,281**，占 **96.686291%**；
- 多商品订单 **3,197**，占 **3.313709%**。

关联脚本使用“共现订单≥5、置信度≥10%、Lift>1”的固定门槛。`category_association_top20.csv` 只输出 1 条规则：`home_confort → bed_bath_table`，共现 **43 单**，支持度 **0.0445697%**，置信度 10.9694%，Lift 1.1414。

**比较基准。** 同一 96,478 单分母下单商品与多商品订单的内部比较；关联规则与固定正式阈值比较。

**证据来源。** `database/brazil_ecommerce.db` 的 `category_item_base`；`src/analysis/product_analysis/product_association_rules.py`；`outputs/data/06_product_analysis/category_association_top20.csv`；`reports/product/04_product_association.md`；`reports/product/product_analysis_report.md`。

**影响范围/优先对象。** 全期 96,478 个 delivered 订单；策略探索应先聚焦已经出现多商品购买的 3,197 单、相关入口和高流量品类，而不是把唯一规则直接全站推广。

**分析限制与禁止解释。** 购物篮数据没有曝光、搜索意图、推荐位、库存、利润、退款和价格实验字段；单商品订单不证明平台缺少推荐能力；关联不代表因果。唯一跨品类规则的支持度很低，不能据此承诺加购或 GMV 提升。

**后续策略方向。** 把历史规则只作为候选组合生成器，在高流量品类页或购物车做小流量随机实验；以多商品订单占比、转化率、净收益、取消/退货和评分为联合指标。

### CBP-05：office_furniture 满意度明显低于平台均值

**问题定义。** `office_furniture` 在达到正式样本门槛的品类中平均评分最低，同时具有可观销售规模，形成可定位、可复核的体验改进对象。

**可复核量化证据。** `category_satisfaction.csv` 与 `category_sales_base.csv` 显示：

- 有效评价订单 **1,244 单**，高于 30 单正式比较门槛；
- 平均评分 **3.644695**；平台全期平均评分为 **4.155908**，低 **0.511214 分**；
- 1 星评价 **214 单**，1 星率 **17.2026%**；有文本的 1 星评价 **170 单**；
- 在 63 个达到门槛的品类中平均评分最低；
- 全期商品销售额 **268,154.31 BRL**，在 72 品类中排名 **15**，份额 **2.0282%**。

**比较基准。** 品类平均分与同样采用订单级代表评价规则的全平台 4.155908 分比较；同时在 `valid_review_orders>=30` 的 63 个正式可比品类内排序。

**证据来源。** `outputs/data/06_product_analysis/category_satisfaction.csv`；`outputs/data/06_product_analysis/category_sales_base.csv`；`outputs/metric_validation.csv`；`reports/product/03_category_satisfaction.md`；`reports/product/product_analysis_report.md`；`sql/06_product_analysis/04_category_satisfaction.sql`；`visualizations/product/category_satisfaction_matrix.png`。

**影响范围/优先对象。** `office_furniture` 的 1,244 个有效评价订单、214 个 1 星评价订单，以及该品类 268,154.31 BRL 的全期商品销售额。优先排查对象应由后续卖家/SKU/线路/评价文本拆分确定。

**分析限制与禁止解释。** 本版没有单独进行统计显著性检验，因此“明显低于”只表示数值差异和正式品类排序，不表示统计学显著。评分差异不能定位到商品质量、卖家、配送、安装、价格或预期管理。一个多品类订单可进入多个品类评价统计，但同一品类内部按订单去重。商品销售额只含 `price`、不含运费且不是支付 GMV；未控制订单结构差异，不能把 0.511214 分差写成任何单一环节的因果效果。

**后续策略方向。** 结合 170 个负向文本订单，按卖家、SKU、线路、配送时长和评论主题继续拆解；只有在定位问题环节后再做定向整改实验，以评分、1 星率、履约、取消和净销售作联合评估。

### CBP-06：区域 GMV 高度集中于少数核心州

**问题定义。** 全观察期支付型 GMV 在少数核心州集中。该结论用于描述现有收入组合暴露和资源配置边界，不表示集中已经造成经营损失，也不等同于非头部州表现差。

**可复核量化证据。** `state_structure.csv` 的 `ALL_DATA` 层显示：

- SP、RJ、MG 三州 GMV 合计 **9,645,234.25 BRL**，占全期 GMV **62.5402%**；
- 其余 **24 州** GMV 合计 **5,777,227.52 BRL**，占 **37.4598%**；
- Top5 州 GMV 占 **73.1982%**，Top10 州占 **87.3633%**；
- 州级 GMV HHI 为 **1,831.76**。

**比较基准。** 同一全期支付订单层下，Top3 与其余 24 州比较，并同时展示 Top5、Top10 累计份额。没有引入外部地区份额目标。

**证据来源。** `outputs/data/02_business_overview/state_structure.csv`；`reports/business_analysis/02_business_overview_report.md`；`sql/02_business_overview/04_business_structure.sql`；`visualizations/business_overview/state_gmv_ranking.png`；`visualizations/business_overview/regional_structure_change.png`。

**影响范围/优先对象。** 全期 **96,477 个支付订单**和 **15,422,461.77 BRL GMV**；管理对象同时包括贡献 62.5402% GMV 的 SP/RJ/MG 核心市场，以及需要按单位经济性继续评估的其余 24 州。

**业务重要性。** 该结构关系核心市场需求变化、履约连续性和非头部州资源配置，影响范围覆盖全部支付型 GMV，因此业务优先级评为“高”。该优先级不代表已经观察到损失。

**分析限制与禁止解释。** 州份额没有按人口、可服务市场、营销投入、竞争强度或物流成本标准化；仓库也没有州级利润和实际冲击数据。不能据此认定非头部州经营失败、核心州风险已发生，或直接主张从核心州转移资源。

**后续策略方向。** 一端建立核心州需求、履约和支付连续性监控；另一端在补齐人口、获客成本、物流和利润数据后，对非头部州开展分层小规模试点，以增量净 GMV 和单位经济性验证扩张价值。

### CBP-07：支付方式高度集中且渠道韧性数据不足

**问题定义。** 全观察期支付 GMV 与主支付订单均集中于信用卡；与此同时，仓库缺少支付失败、费率、拒付、重试和降级数据，无法进一步量化渠道集中带来的实际成本或连续性影响。

**可复核量化证据。** `payment_structure.csv` 显示：

- 信用卡支付 GMV **12,101,094.88 BRL**，占全期支付 GMV **78.4641%**；
- 信用卡作为主支付方式的订单 **72,785 单**，占支付订单 **75.4429%**；
- 其他支付方式合计 GMV **3,321,366.89 BRL**，占 **21.5359%**；其他主支付订单 **23,692 单**，占 **24.5571%**；
- 信用卡 GMV 占比由 2017 年 1—7 月的 **76.7894%** 升至 2018 年 1—7 月的 **78.9402%**，增加 **2.1508 个百分点**。

**比较基准。** 全期信用卡与其他支付方式比较；两个完整、等长的 1—7 月窗口用于观察份额变化。GMV 按支付明细归属，订单份额按主支付方式归属，两个指标不互相替代。

**证据来源。** `outputs/data/02_business_overview/payment_structure.csv`；`reports/business_analysis/02_business_overview_report.md`；`sql/02_business_overview/04_business_structure.sql`；`visualizations/business_overview/payment_structure.png`。

**影响范围/优先对象。** 全期 **96,477 个支付订单**及 **15,422,461.77 BRL GMV**，重点为 72,785 个信用卡主支付订单和占 78.4641% 的信用卡支付 GMV。

**业务重要性。** 支付是订单转化和收入确认的关键链路，集中结构覆盖大部分历史支付 GMV；渠道成功率、故障恢复和费用管理均具有经营连续性意义，因此业务优先级评为“高”。这不表示信用卡渠道当前存在故障。

**分析限制与禁止解释。** 集中度不证明渠道已造成损失。现有数据缺少支付尝试、失败率、手续费、拒付、退款、重试、备用路由和故障时段；不能据此要求把交易强制迁移到其他支付方式，也不能预测分流收益。

**后续策略方向。** 先建立各支付方式成功率、费率、拒付、重试和降级监控，再通过受控实验验证备用支付提示或路由；联合评估支付成功率、净收入、成本和用户转化。

## 7. 观察项与待验证项

### 7.1 观察项：数值可靠，但不足以单独定义核心问题

1. **行为型流失占比 78.76%。** 68,686/87,214 名用户在 2018-07-31 的 Recency>90 天；这是运营阈值下的状态，不代表永久离开。它与低复购高度重叠，且受到用户首购时间和右截尾影响，因此保留监控，不另立核心问题。
2. **品类集中。** 18/72 个品类贡献商品销售额 81.2887%。这是结构事实，未提供库存、毛利、退货和战略品类目标，不能把长尾份额低直接认定为缺陷。
3. **节日样本差异。** 2017 Black Friday 日均 GMV +381.67%、订单 +469.29%、AOV -15.39%，但只有一个完整 Black Friday 样本，其他节日方向不一致，不能升级为稳定季节规律。

### 7.2 待验证项：本版禁止使用为策略基线

- `short_term_repeat_retention.csv` 的 7/30/90 天结果尚未按正式截止日、订单范围和分母完整重跑；后续必须从 `customer_order_base` 或正式截止订单层重建并对账。
- `customer_lifecycle_segment.csv` 的旧生命周期分层与 2018-07-31 正式 RFM/流失层未完成一致性复核；原占比不得与本报告 87,214 用户直接拼接。
- Cohort 热力图包含较新 cohort 的右截尾；任何留存月比较必须只纳入已经完整经历相应月份的 cohort。
- 流失组配送、评分和复购差异是分组相关，未控制购买时间、地区、品类、订单金额和样本结构，不能写成物流或满意度导致流失。
- 关联规则不含曝光与利润数据；阶段二 AOV 情景、支付结构转移和区域转移均为假设，不得作为 Member 3 的“已验证效果”。

## 8. 对 Member 2 和 Member 3 的交接建议

### 8.1 Member 2：策略设计

| 问题编号 | 可进入策略设计的方向 | 必须保留的边界/护栏 |
|---|---|---|
| CBP-01 | 单次购买用户分层、二购触达对照实验 | 不混用旧 7/30/90 天留存；主看增量复购、净 GMV、毛利和触达成本 |
| CBP-02 | 加购、组合、价格带呈现和订单价值测试 | 不以牺牲转化率换 AOV；同时看订单量、净收益、取消和评分 |
| CBP-03 | 重要挽留用户再分层召回 | 42.7799% 是历史 GMV，不是可恢复收入；必须设对照组和频控 |
| CBP-04 | 高流量入口的小流量组合/推荐实验 | 规则只作候选；支持度 0.0445697%，禁止全站直接复制或承诺效果 |
| CBP-05 | office_furniture 卖家/SKU/线路/文本问题定位后定向整改 | 先定位环节；评分差异不得直接归因商品或物流 |
| CBP-06 | 核心州韧性监控与非头部州分层试点 | 不把集中度写成损失；补齐人口、获客成本、物流和利润后再决定资源配置 |
| CBP-07 | 支付观测体系、备用方式提示或路由实验 | 先补成功率、费率、拒付和重试数据；不得仅因集中就强制迁移支付方式 |

Member 2 输出策略时建议保留 `CBP-xx` 编号，并为每条策略明确执行主体、数据前置条件、实验单元、主指标、护栏指标、停止条件和不适用范围。

### 8.2 Member 3：优先级与效果评估

1. 以本报告数值作为**历史基线**，不要把阶段二 `strategy_scenarios.csv` 的假设提升率当作模型真值。
2. 优先级矩阵应把“受影响对象规模、证据强度、业务优先级、可实验性、数据缺口、实施成本”分开评分；没有成本数据的项目不得计算确定 ROI。
3. CBP-01/03 的实验分母统一使用用户；CBP-02/04 使用订单；CBP-05 使用订单级代表评价；CBP-06 使用州×时间；CBP-07 的 GMV 份额按支付明细、订单份额按主支付方式。不同统计单元不能直接拼接效果率。
4. 效果估计优先采用随机对照、分层随机或明确的准实验；历史前后对比只能写成同期变化，不能写成策略因果效果。
5. 对 CBP-05 先补齐卖家/SKU/履约拆分，对 CBP-04 先补曝光与利润数据，对 CBP-06 补人口/营销/物流/利润，对 CBP-07 补支付失败/费率/重试；数据未补齐时只给测量方案，不给确定收益承诺。

## 9. 数据口径、时间范围与不确定性说明

- **当前性限制：** 数据结束于 2018-08-29，本报告描述该历史观察期，不代表 2026 年平台现状。
- **订单口径：** 有效订单为去重 `delivered`；支付型指标进一步要求订单级正支付金额。全期有效订单 96,478、支付订单 96,477，二者不能随意替换。
- **GMV 与品类销售额：** GMV 为正支付金额，阶段四品类销售额为商品 `price`，全期分别为 15,422,461.77 BRL 和 13,221,498.11 BRL；二者不应混算。
- **用户口径：** 用户以 `customer_unique_id` 去重。阶段三全期画像 93,358 人；正式截止日 RFM 87,214 人；两个窗口不能直接横向解释为流失或增长。
- **时间边界：** 2016-09 和 2018-08 不完整；2016-11 没有 delivered 订单，不填零。正式月度同比只用完整且等长的月份。
- **评价口径：** 每订单按确定规则选一条代表评价。多品类订单会进入多个品类，但同一品类内按订单去重，因此品类评价订单数不可跨品类求和对账平台总数。
- **RFM 限制：** Recency/Frequency/Monetary 是观察期历史行为；数据开始前历史不可见，数据结束后行为右截尾；分层标签不是未来结果标签。
- **关联限制：** 支持度分母是全部 96,478 个 delivered 订单；置信度和 Lift 不表示策略增量或因果效果。
- **区域限制：** 州级 GMV 份额是现有支付收入结构，未按人口、可服务市场、营销投入、竞争和物流成本标准化；集中度不等于损失。
- **支付限制：** 支付 GMV 份额按支付明细汇总，订单份额按主支付方式分类；缺少支付尝试、失败、费率、拒付和重试数据，不能量化渠道韧性效果。
- **成本/利润缺口：** 现有核心证据没有完整获客成本、毛利、退款、库存、推荐曝光和支付费率，所以本报告只给策略方向，不给确定 ROI 或预测。

## 10. 交付前自核查

### 10.1 数值回溯

| 问题 | CSV 数值 | 真实输入字段/回算 |
|---|---|---|
| CBP-01 | 87,214；2,621；3.0053%；84,593；96.9947%；1.033401 | `rfm_segment_summary.csv` 各层 `user_count`、`repeat_customer_count`、`valid_order_count` 求和；按定义相除 |
| CBP-02 | 2,827,862.15/17,805/158.824047；7,467,560.92/46,432/160.827897；三项同比 | `monthly_kpi.csv` 分别汇总两个 1—7 月；AOV=GMV/订单；`payment_structure.csv` 总量交叉核验 |
| CBP-03 | 20,391；23.3804%；6,176,160.10；42.7799%；316.31558；84.067946 | `rfm_segment_summary.csv` 的“重要挽留用户”和“重要发展用户”行 |
| CBP-04 | 96,478；93,281；96.686291%；3,197；3.313709%；43；0.0445697% | SQLite `category_item_base` 按订单计去重商品；`category_association_top20.csv` 的唯一规则 |
| CBP-05 | 1,244；3.644695；214；17.2026%；170；268,154.31；15/72；平台 4.155908；差 -0.511214 | `category_satisfaction.csv`、`category_sales_base.csv`、`outputs/metric_validation.csv` |
| CBP-06 | 9,645,234.25；62.5402%；5,777,227.52；37.4598%；Top5 73.1982%；Top10 87.3633%；HHI 1,831.76 | `state_structure.csv` 的 `ALL_DATA` 27 州按 `gmv_rank` 汇总；文件内 Top5/Top10/HHI 字段交叉核验 |
| CBP-07 | 12,101,094.88；78.4641%；72,785；75.4429%；其他方式 3,321,366.89/21.5359% 与 23,692/24.5571%；可比期 76.7894%/78.9402% | `payment_structure.csv` 的 `ALL_DATA` 及两个 1—7 月信用卡行；总量减信用卡得到其他方式 |

### 10.2 一致性与改动范围

- Markdown 与 CSV 均为 7 个问题，编号均为 CBP-01—CBP-07。
- CSV 每条数值均在本报告完整证据链和数值回溯表中出现；展示精度一致。
- 所有策略措辞均为“测试、验证、拆解、监控”，没有把因果、预测或假设效果写成事实。
- 支付与区域集中按业务重要性升级为“结构暴露”，但未写成已发生损失；品类集中、行为型流失和节日变化仍与核心问题分开；未统一口径的短期留存和生命周期结果只列待验证。
- 本次只新增 `reports/strategy/01_core_business_problems.md` 和 `outputs/data/strategy/core_problem_summary.csv`；未覆盖其他成员报告、公共历史报告或既有产物。
