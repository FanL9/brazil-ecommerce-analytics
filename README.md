| 日期 | 修改人 | 版本号 | 备注 |
|---|---|---|---|
| 2026-08-10 | FL | v1.0 | 同步阶段四可执行范围，并新增品类公共数据层重跑说明 |
| 2026-08-11 | FL | v1.1 | 补充阶段四品类汇总基础表及可重复导出入口 |

# 巴西电商平台数据分析

## 一、项目核心定位

本项目覆盖从数据治理、指标体系搭建到业务洞察、策略输出的全链路分析过程，对标阿里巴巴国际站、亚马逊等跨境电商平台数据分析岗的核心工作要求，重点考核数据处理能力、业务拆解能力和量化决策支撑能力。

## 二、数据基础

使用巴西电商数据集（2016.9-2018.10，10万+订单），覆盖用户、商品、订单、支付、物流、评论六大核心业务模块，共9张关联数据表。

前置工作：梳理完整数据字典、明确表间业务关联关系。

## 三、核心分析任务

### 阶段一：数据治理与基础建设

1. 数据质量校验：使用SQL统计各表缺失值占比、重复记录数，通过箱线图/3σ原则识别金额、时间字段的异常值，输出《数据质量评估报告》，标注不可用数据范围。
2. 核心指标口径统一：制定《平台核心指标定义手册》，明确GMV、有效订单、客单价、复购率、留存率等15+核心指标的计算逻辑，剔除取消订单、未支付订单等无效数据。
3. 数据仓库优化：在SQLite中建立规范化的星型模型，为订单时间、用户ID、商品品类等高频查询字段创建索引，编写通用SQL查询模板提升分析效率。
4. 衍生指标体系构建：计算订单总金额、实际配送时长、用户生命周期价值（LTV）、复购间隔、评论情感倾向等业务分析必需的衍生指标，形成标准化指标表。

### 阶段二：整体业务大盘诊断

1. 核心指标趋势分析：按月度粒度统计GMV、订单量、客单价、新增用户数、活跃用户数的变化趋势，绘制趋势折线图，识别业务增长的关键拐点。
2. 增长质量分析：计算核心指标的同比/环比增长率，拆解增长驱动因素（订单量驱动vs客单价驱动），定位异常波动的时间节点并初步排查原因。
3. 季节性与周期性分析：量化黑五、圣诞节、巴西狂欢节等节假日对销售的影响系数，总结平台业务的季节性规律，为库存和营销规划提供数据支撑。
4. 业务结构拆解：从支付方式、订单金额区间、用户地域等维度拆解GMV构成，分析2017-2018年业务结构的变化趋势，识别结构性风险与机会。

### 阶段三：用户行为与价值分析

1. 用户基础画像构建：分析用户的地域分布、城市等级分布、消费时段分布，量化核心市场（圣保罗、里约热内卢等）的贡献占比，识别高潜力下沉市场。
2. 用户生命周期分析：统计新用户注册到首单的转化时长，计算7日/30日/90日用户留存率、不同生命周期阶段的复购率，绘制用户生命周期漏斗图。
3. RFM用户分层建模：基于最近消费时间（R）、消费频次（F）、消费金额（M）三个维度，采用五分法将用户分为重要价值用户、重要发展用户、重要保持用户、重要挽留用户和一般用户5大层级。
4. 分层用户价值贡献分析：计算各层级用户的数量占比、GMV贡献占比、人均消费额，提炼高价值用户的核心行为特征，输出《高价值用户画像报告》。
5. 流失用户归因分析：定义用户流失标准（如90天未消费），统计流失用户的流失时间分布、最后一次消费特征、历史评论情况，通过对比分析推测核心流失原因。

### 阶段四：商品品类结构分析

1. 品类销售表现分析：统计各品类的商品销售额、订单量、商品件数、平均商品单价和销售额占比，通过帕累托分析识别累计贡献80%销售额所需的实际品类数量和比例。
2. 品类增长趋势分析：计算各品类的月复合增长率（CMGR），对比平台整体增速，识别明星、潜力、稳定、衰退和新兴品类。
3. 品类用户满意度分析：结合评论数据，计算各品类的平均评分、1星差评率、差评关键词词云，定位用户投诉集中的问题品类。
4. 商品关联规则挖掘：使用Apriori算法挖掘频繁购买的商品组合，计算支持度、置信度和提升度；规则不足20条时如实输出实际数量，并以品类级规则补充。

### 阶段五：物流服务与用户体验分析

1. 整体物流时效分析：计算平台平均发货时长、平均配送时长、准时送达率，分析2016-2018年物流时效的变化趋势。
2. 区域物流差异分析：对比巴西26个州和1个联邦区的配送时效、运费标准，绘制物流时效热力图，识别物流服务薄弱地区。
3. 物流与满意度相关性分析：通过皮尔逊相关系数量化配送时长、发货时长与用户评论评分的相关程度，建立物流时效对满意度的影响模型。
4. 异常物流订单分析：统计配送超时订单、丢失订单、破损订单的占比和分布，拆解超时原因（发货延迟vs运输延迟），量化异常订单对GMV和用户流失的影响。
5. 物流成本分析：分析不同重量、不同体积、不同地区的运费差异，计算物流成本占GMV的比例，识别物流成本优化的核心方向。

### 阶段六：问题总结与策略输出

1. 核心业务问题提炼：基于上述五大模块的分析结论，总结平台当前面临的3-5个最核心数据驱动的业务问题，每个问题必须有量化数据支撑。
2. 量化增长策略制定：针对每个核心问题，提出具体、可量化、可落地的数据建议，明确策略的执行主体、执行步骤和关键成功因素。
3. 策略优先级排序：构建“实施难度-预期效果-投入成本”三维评估矩阵，对所有策略进行优先级排序，输出高优先级快速落地策略清单。
4. 策略效果量化预估：基于历史数据建立预测模型，对每条策略的预期GMV增长、用户留存提升、成本降低等效果进行量化预估，计算投资回报率（ROI）。

## 四、选做内容

1. 营销活动效果预测与归因：基于历史黑五促销数据，使用时间序列模型预测本次黑五的GMV增长，构建多维度营销归因模型，制定分品类、分用户层级的精准促销策略。
2. 用户流失预警模型构建：使用逻辑回归算法构建用户流失风险评分体系，筛选出Top10%高风险流失用户，输出针对性的挽回策略建议。
3. 卖家绩效评估体系搭建：设计包含销售能力、物流时效、服务质量三个维度的卖家绩效指标体系，计算卖家综合得分，提出卖家分层管理和激励机制建议。
4. 区域市场进入策略分析：基于各州的市场规模、增长率、竞争程度、物流成本等指标，使用K-means聚类算法将巴西市场分为4个等级，输出新市场拓展优先级和资源分配建议。
5. 自动化报表开发：使用Tableau/Power BI开发自动化业务监控报表，实现核心指标的实时更新和多维度下钻分析。

## 五、岗位交付物要求

### 1. 业务诊断分析报告（核心交付物）

- 项目背景与分析目标
- 数据说明与处理逻辑（含数据质量评估、指标定义手册）
- 五大模块核心分析发现（配关键数据图表，所有结论必须有数据支撑）
- 平台核心业务问题总结（量化呈现）
- 分优先级的业务增长策略及量化效果预估
- 分析局限性与后续分析建议

### 2. 数据处理成果包

- 清洗后的SQLite数据库文件（含所有业务数据表、衍生指标表、优化后的索引）
- 完整的数据清洗SQL脚本、指标计算SQL脚本
- 表结构说明文档

### 3. 数据可视化图表集

- 包含所有核心分析结论的可视化图表（趋势图、柱状图、饼图、热力图、漏斗图等）
- 每个图表需标注标题、坐标轴、数据来源和核心结论

### 4. 交互式核心指标看板

- 汇总平台日常运营所需的15+关键指标
- 支持按时间、区域、品类、用户层级多维度下钻
- 设置指标异常预警阈值
- 形成可复用的运营监控模板

## 六、本地数据库构建

GitHub 不保存生成后的 SQLite 数据库。进入项目根目录后，可以使用原始 CSV 在本地完整重建：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src\data_processing\build_sqlite_database.py
```

成功后会生成 `database/brazil_ecommerce.db`。详细说明参见 [`database/README.md`](database/README.md)。

## 七、创建清洗视图

数据库构建完成后，需执行一次清洗 SQL，才能在 DBeaver 或其他 SQLite 工具中使用 `vw_*` 清洗视图：

```powershell
python -c "from pathlib import Path; import sqlite3; c=sqlite3.connect(r'database/brazil_ecommerce.db'); c.executescript(Path(r'sql/02_data_cleaning/data_cleaning_rules.sql').read_text(encoding='utf-8-sig')); c.close()"
```

该脚本可重复执行，不会修改或删除原始表数据。

## 八、创建月度 KPI 公共数据层

完成数据库构建和清洗 View 创建后，执行月度公共数据层 SQL：

```powershell
python -c "from pathlib import Path; import sqlite3; c=sqlite3.connect(r'database/brazil_ecommerce.db'); c.executescript(Path(r'sql/02_business_overview/00_monthly_kpi_view.sql').read_text(encoding='utf-8-sig')); c.close()"
```

该 SQL 可重复执行，会创建或重建支付型 `monthly_kpi` View。View 仅纳入订单级正支付金额大于 0 的 delivered 订单，并按自然月输出以下字段：

```text
month,gmv,order_count,average_order_value,new_users,active_users
```

指标口径以 [`docs/metric_definition.md`](docs/metric_definition.md) 和 [`docs/metric_dictionary.csv`](docs/metric_dictionary.csv) 为准。详细字段说明参见 [`docs/monthly_kpi_dictionary.md`](docs/monthly_kpi_dictionary.md)，已导出的实际月度结果位于 [`outputs/data/02_business_overview/monthly_kpi.csv`](outputs/data/02_business_overview/monthly_kpi.csv)。

可以执行以下命令检查 View 是否可正常查询：

```powershell
python -c "import sqlite3; c=sqlite3.connect(r'database/brazil_ecommerce.db'); print(c.execute('SELECT * FROM monthly_kpi ORDER BY month LIMIT 5').fetchall()); c.close()"
```

## 九、运行阶段三 Member 1 用户画像分析

阶段三用户画像复用阶段一清洗 View，并建立订单级 `customer_order_base` 与用户级 `customer_profile` 两个公共表。数据库与清洗 View 准备完成后，从项目根目录执行：

```powershell
.venv\Scripts\python.exe src\analysis\customer_analysis\customer_profile_analysis.py
```

脚本会自动执行 `sql/05_customer_analysis` 下的两个 SQL 文件，随后导出：

- 用户与订单公共层：`outputs/data/03_customer_analysis/`
- 州、城市、时段和潜力区域市场统计：`outputs/data/03_customer_analysis/`
- 300 DPI 图表：`visualizations/customer/`
- 分析报告：`reports/customer/customer_analysis_report.md`
- 验证明细：`outputs/data/03_customer_analysis/customer_analysis_validation.csv`

公共层字段、代表地域规则和下游使用说明参见 [`docs/customer_common_layer_dictionary.md`](docs/customer_common_layer_dictionary.md)。该阶段不依赖 `monthly_kpi`，但依赖 `vw_orders_clean` 与 `vw_order_payments_clean`；如缺少清洗 View，请先执行本 README 第七节命令。


## 十、运行阶段三 Member 1 RFM 用户价值分析

RFM 分析依赖阶段三用户画像脚本创建的订单级 `customer_order_base` 和用户级 `customer_profile`。首次运行或公共表需要更新时，先执行：

```powershell
.venv\Scripts\python.exe src\analysis\customer_analysis\customer_profile_analysis.py
```

随后从项目根目录执行 RFM 全流程：

```powershell
.venv\Scripts\python.exe src\analysis\customer_analysis\rfm_analysis.py
```

脚本固定使用 `2018-07-31` 作为观察截止日，会自动执行 RFM SQL、导出用户明细和层级汇总、运行严格验证、生成 300 DPI 图表，并更新规则说明与分析报告。主要交付物包括：

- Member 3 用户明细：`outputs/data/03_customer_analysis/rfm_customer_detail.csv`
- 层级汇总：`outputs/data/03_customer_analysis/rfm_segment_summary.csv`
- 评分边界和 Frequency 映射：`outputs/data/03_customer_analysis/rfm_scoring_boundaries.csv`、`rfm_frequency_score_mapping.csv`
- 验证明细：`outputs/data/03_customer_analysis/rfm_validation.csv`
- 评分规则：[`docs/rfm_scoring_rules.md`](docs/rfm_scoring_rules.md)
- 分析报告：[`reports/customer/rfm_customer_value_report.md`](reports/customer/rfm_customer_value_report.md)
- 核心图表：`visualizations/customer/rfm/`

该脚本可重复执行，所有路径均基于项目根目录解析。默认使用 `database/brazil_ecommerce.db`；如需指定其他数据库，可增加 `--database <项目相对路径>`。

## 十一、创建阶段四品类公共数据层

阶段四公共层包括商品级 `category_item_base`、订单—品类级 `category_order_base`、品类级 `category_sales_base` 和月份—品类级 `category_monthly_sales_base`。数据库构建完成后，从项目根目录执行：

```powershell
python src\analysis\product_analysis\category_common_layer.py
```

该脚本可重复执行，会创建清洗 View、重建四张阶段四公共表、运行口径回算并导出以下 UTF-8 BOM CSV，不修改原始表：

- `outputs/data/06_product_analysis/category_sales_base.csv`
- `outputs/data/06_product_analysis/category_monthly_sales_base.csv`

字段、品类映射规则和质量校验请参见 [`docs/category_analysis_dictionary.md`](docs/category_analysis_dictionary.md)；阶段四完整口径以 [`docs/unified_analysis_standards.md`](docs/unified_analysis_standards.md) 为准。

## 十二、打开交互式可视化面板

在项目根目录打开 PowerShell，激活虚拟环境并安装依赖：

```powershell
.venv\Scripts\activate
pip install -r requirements.txt

运行python -m streamlit run src\analysis\business_overview\dashboard.py

或手动访问 http://localhost:8501

停止运行时，在终端输入Ctrl + C
