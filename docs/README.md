| 日期 | 修改人 | 版本号 | 备注 |
|---|---|---|---|
| 2026-08-10 | FL | v1.0 | docs/README.md |
| 2026-08-10 | FL | v1.1 | 新增阶段四品类公共层入口 |

# 文档目录索引

本目录存放数据结构、指标口径、公共数据层和分析方法说明。报告结论请前往 [`reports/README.md`](../reports/README.md)；本文档目录主要回答“数据是什么、指标怎么算、不同阶段应遵循什么规则”。

## 建议阅读顺序

1. [`unified_analysis_standards.md`](unified_analysis_standards.md)：阶段一至阶段四的统一口径入口。若其他说明、代码或旧报告与其冲突，以该文件为准。
2. 根据所处阶段查看对应的指标定义或公共数据层字典。
3. 需要核对原始字段和表连接关系时，再查看数据字典、表关系和 ER 图。

## 通用数据基础

| 文档 | 用途 |
|---|---|
| [`data_dictionary/raw_data_dictionary.md`](data_dictionary/raw_data_dictionary.md) | 9 张 Olist 原始表的字段、含义和数据说明 |
| [`table_relationship.md`](table_relationship.md) | 数据表之间的业务关系、连接键及连接注意事项 |
| [`erd/ER_diagram.png`](erd/ER_diagram.png) | 数据库实体关系图 |
| [`unified_analysis_standards.md`](unified_analysis_standards.md) | 跨阶段、跨成员统一的订单、GMV、用户、时间窗口及分析规则 |

## 分阶段文档

| 阶段 | 状态 | 文档 | 主要用途 |
|---|---|---|---|
| 阶段一：数据治理与基础建设 | 已交付 | [`metric_definition.md`](metric_definition.md) | 18 项正式核心指标的业务定义、公式和计算口径 |
| 阶段一：数据治理与基础建设 | 已交付 | [`metric_dictionary.csv`](metric_dictionary.csv) | 核心指标的机器可读字典，便于程序校验和复用 |
| 阶段二：整体业务大盘诊断 | 已交付 | [`monthly_kpi_dictionary.md`](monthly_kpi_dictionary.md) | 月度 KPI 公共层的字段、粒度、计算逻辑和质量校验规则 |
| 阶段三：用户行为与价值分析 | 已交付（公共层与 RFM） | [`customer_common_layer_dictionary.md`](customer_common_layer_dictionary.md) | 订单级 `customer_order_base` 和用户级 `customer_profile` 公共层说明 |
| 阶段三：用户行为与价值分析 | 已交付（RFM） | [`rfm_scoring_rules.md`](rfm_scoring_rules.md) | RFM 评分、同值同分及五类互斥分层规则 |
| 阶段四：商品品类结构分析 | 已交付（公共层） | [`category_analysis_dictionary.md`](category_analysis_dictionary.md) | 商品级 `category_item_base` 和订单—品类级 `category_order_base` 公共层说明 |
| 跨阶段分析方法 | 待补充 | [`methodology/analysis_methodology.md`](methodology/analysis_methodology.md) | 当前为空文件，仅作方法论文档占位 |

## 阶段二特别说明

阶段二的正式分析结论、最终数字和质量控制修正，请以 [`阶段二整体业务大盘诊断最终报告`](../reports/business_analysis/02_business_overview_report.md) 为主。`reports/business_analysis/` 中除该最终报告外的其他文件属于成员专题材料，可能保留早期口径或探索性规则；发生不一致时，按以下优先级处理：

1. 指标和分析口径：[`unified_analysis_standards.md`](unified_analysis_standards.md)；
2. 阶段二最终数字与结论：[`阶段二最终报告`](../reports/business_analysis/02_business_overview_report.md)；
3. 字段实现细节：[`monthly_kpi_dictionary.md`](monthly_kpi_dictionary.md)；
4. 专项过程和补充分析：[`reports/business_analysis/`](../reports/business_analysis/)。
