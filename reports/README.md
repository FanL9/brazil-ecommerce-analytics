| 日期 | 修改人 | 版本号 | 备注 |
|---|---|---|---|
| 2026-08-10 | FL | v1.0 | 新增报告目录索引，并标注阶段二最终报告优先级 |
| 2026-08-11 | hong shucham | v1.1 | 新增阶段三member2报告目录索引 |
| 2026-08-11 | FL | v1.2 | 区分阶段四公共汇总层与分析报告交付状态 |

# 报告目录索引

本目录汇总各阶段的分析报告。阅读报告前，建议先查看 [`docs/unified_analysis_standards.md`](../docs/unified_analysis_standards.md)，确认有效订单、GMV、用户、时间窗口等统一口径。

## 阅读优先级

1. **阶段二结论以 [`阶段二整体业务大盘诊断最终报告`](business_analysis/02_business_overview_report.md) 为准。**该报告已经完成模块整合和最终质量控制；若 `business_analysis/` 下的其他成员专题报告与其存在数字、时间范围、异常规则或表述不一致，应采用最终报告中的结果。
2. 阶段一至阶段四的指标定义和分析口径，以 [`全团队统一分析口径`](../docs/unified_analysis_standards.md) 及其引用的专项字典为准。
3. 各专题报告用于查看分析过程、拆分结果和补充细节，不应覆盖最终报告或统一口径中的正式结论。

## 分阶段交付物

| 阶段 | 状态 | 主要报告 | 内容说明 |
|---|---|---|---|
| 阶段一：数据治理与基础建设 | 已交付 | [`data_quality/data_quality_report.md`](data_quality/data_quality_report.md) | 数据质量检查、异常分类及可用范围；指标定义详见 [`docs/metric_definition.md`](../docs/metric_definition.md) |
| 阶段二：整体业务大盘诊断 | **最终版已交付** | **[`阶段二最终报告`](business_analysis/02_business_overview_report.md)** | 趋势、增长质量、节假日与季节性、业务结构、核心问题及策略测算的最终整合版本 |
| 阶段三：用户行为与价值分析 | 部分交付 | [`customer/customer_analysis_report.md`](customer/customer_analysis_report.md)、[`customer/rfm_customer_value_report.md`](customer/rfm_customer_value_report.md) [`customer/customer_lifecycle_cohort_analysis.md`](customer/customer_lifecycle_cohort_analysis.md)| 当前覆盖 Member 1 的用户画像、公共数据层和 RFM 用户价值分析；Member 2 部分已完成，完成用户生命周期与 Cohort 留存分析，包括留存指标计算、短期复购分析、生命周期分层及用户价值对比。|
| 阶段四：商品品类结构分析 | 公共汇总层已交付，报告待交付 | [`product/product_analysis_report.md`](product/product_analysis_report.md) | 品类总体与月份—品类汇总基础表已交付，详见 [`docs/category_analysis_dictionary.md`](../docs/category_analysis_dictionary.md)；当前报告文件仍为空，仅作目录占位 |
| 阶段五：物流服务与用户体验分析 | 待交付 | [`logistics/logistics_analysis_report.md`](logistics/logistics_analysis_report.md) | 当前文件为空，仅作目录占位 |
| 阶段六：问题总结与策略输出 | 待交付 | [`strategy/strategy_report.md`](strategy/strategy_report.md)、[`final/final_report.md`](final/final_report.md) | 当前文件为空，分别预留策略报告和全项目最终报告位置 |

> [`metrics/core_metrics_definition.md`](metrics/core_metrics_definition.md) 当前也是空占位文件。正式指标定义请查看 [`docs/metric_definition.md`](../docs/metric_definition.md) 和 [`docs/metric_dictionary.csv`](../docs/metric_dictionary.csv)。

## 阶段二专题材料

以下文件保留成员分析过程和专项细节，但不是阶段二最终结论入口：

| 文件 | 主要内容 |
|---|---|
| [`business_analysis/business_trend_analysis.md`](business_analysis/business_trend_analysis.md) | 月度核心指标趋势、异常月份和业务阶段划分 |
| [`business_analysis/growth_quality_holiday_seasonality_analysis.md`](business_analysis/growth_quality_holiday_seasonality_analysis.md) | 增长质量、同比/环比、节假日与季节性分析 |
| [`business_analysis/business_diagnosis_report.md`](business_analysis/business_diagnosis_report.md) | 支付方式、订单金额区间和州级业务结构分析 |
| [`business_analysis/core_business_issues.md`](business_analysis/core_business_issues.md) | 核心业务问题及证据汇总 |
| [`business_analysis/strategy_scenario_analysis.md`](business_analysis/strategy_scenario_analysis.md) | 增长策略与保守、基准、乐观情景测算 |

如需引用阶段二数字、结论或图表，请先从阶段二最终报告取值；只有在最终报告未覆盖某项分析细节时，再回查上述专题材料，并核对其口径是否已被最终质量控制修正。
