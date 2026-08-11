| 日期 | 修改人 | 版本号 | 备注 |
|---|---|---|---|
| 2026-08-11 | FSH | v1.1 | 修复报告编码，并同步 src 与 visualizations 新目录结构 |

# 品类用户满意度与差评关键词分析

## 1. 分析目的与数据范围

本分析用于比较不同商品品类的用户评分表现，并结合 1 星文字评论识别值得进一步关注的投诉主题。

统一分析口径以 `docs/unified_analysis_standards.md` 为最高优先级，阶段四公共层及字段规则参考 `docs/category_analysis_dictionary.md`。

正式分析仅使用 `order_status = 'delivered'` 的订单，购买时间使用 `orders.order_purchase_timestamp`。满意度分析建立在 `category_order_base` 的“订单—品类”粒度上，并通过 `order_id` 连接已经收敛为一单一条代表评论的 `vw_order_reviews_order_level`。

代表评论按照以下顺序稳定选择：

1. `review_answer_timestamp DESC`
2. `review_creation_date DESC`
3. `review_id DESC`

只有评分为 1—5 分的有效代表评论进入评分指标。

## 2. 满意度指标与样本规则

每个品类计算：

- 有效评分订单数；
- 平均评分；
- 1 星评论订单数；
- 1 星差评率；
- 4—5 星好评率；
- 1 星且正文非空的文字差评订单数。

其中：

`1 星差评率 = 1 星代表评论订单数 / 有有效代表评分的订单数`

正式满意度排名仅纳入有效评分订单数不少于 30 的品类。当前 72 个品类中，63 个达到正式比较要求，另外 9 个保留并标记为 `small_sample`，不参与正式排名。

同一订单如果包含多个品类，其代表评论会进入该订单包含的每个品类。因此，各品类评论订单数之间允许重叠，不能直接加总后与平台去重评论订单数进行对账。

完整结果：

- `outputs/data/06_product_analysis/category_satisfaction.csv`
- `visualizations/product/category_satisfaction_matrix.png`

## 3. 核心满意度发现

正式可比较品类中，部分品类表现出相对较低的平均评分或较高的 1 星差评率。

### office_furniture

- 平均评分约为 3.64；
- 1 星差评率约为 17.20%；
- 1 星文字差评订单约 170 条。

该品类同时表现出相对偏低的平均评分和较高的 1 星差评率，是当前较值得优先复核的品类之一。

### audio

- 平均评分约为 3.84；
- 1 星差评率约为 16.23%；
- 1 星文字差评订单约 39 条。

该品类的 1 星差评率同样处于较高水平，但文字评论样本量明显低于部分大规模品类，因此解释时需要同时考虑样本规模。

### bed_bath_table

- 平均评分约为 4.00；
- 1 星差评率约为 12.02%；
- 1 星文字差评订单约 860 条。

虽然其平均评分并非最低，但文字差评样本规模较大，因此非常适合作为投诉文本主题分析对象。

上述结果反映的是历史评论数据中的评分结构差异，不能据此认定某一业务因素直接导致差评。

## 4. 差评关键词分析

关键词分析仅使用：

- 代表评论；
- `review_score = 1`；
- `review_comment_message` 非空。

评论文本统一进行：

- 小写转换；
- 标点、数字及无意义字符清理；
- 葡萄牙语停用词过滤；
- unigram 统计；
- bigram 统计。

本次关键词分析处理约 7,461 条符合条件的“订单—品类”文字差评记录，并覆盖 63 个正式可比较品类。

完整关键词频次：

`outputs/data/06_product_analysis/category_negative_keywords.csv`

结合差评率和文字样本量，本次选择以下三个品类生成正式辅助词云：

- `office_furniture`
- `audio`
- `bed_bath_table`

对应图表：

- `visualizations/product/negative_keywords_office_furniture.png`
- `visualizations/product/negative_keywords_audio.png`
- `visualizations/product/negative_keywords_bed_bath_table.png`

评论中频繁出现与商品、收货、交付等待等相关的葡萄牙语词汇和词组，提示这些内容是差评文本中较常出现的讨论主题。

需要强调：关键词频率只能用于归纳评论主题，不能直接认定这些主题是造成差评的原因。

## 5. 业务关注方向

1. 优先复核平均评分偏低且 1 星差评率较高的品类，例如 `office_furniture` 和 `audio`。
2. 对 `bed_bath_table` 等拥有大量文字差评样本的品类，可进一步开展订单、配送、商品或卖家层面的主题分类。
3. 小样本品类继续积累评价数据，不依据当前少量样本进行正式满意度排名。
4. 后续业务动作应结合订单、配送和商品明细进一步验证，不能仅依赖关键词频次判断原因。

## 6. 分析局限性

- 多品类订单的一条代表评论可以同时进入多个品类，因此品类评论订单数不能跨品类简单加总。
- 评论文本属于非结构化葡萄牙语数据，本次仅进行基础词频和双词组合分析。
- 当前分析属于描述性和关联性分析，不包含因果识别。
- Olist 数据未提供完整商品成本、利润和售后处理字段，因此不涉及利润、毛利或售后成本判断。

## 7. 可复现文件

- `sql/06_product_analysis/04_category_satisfaction.sql`
- `src/analysis/product_analysis/category_review_keywords.py`
- `src/analysis/product_analysis/category_member3_figures.py`
- `outputs/data/06_product_analysis/category_satisfaction.csv`
- `outputs/data/06_product_analysis/category_negative_keywords.csv`
- `visualizations/product/category_satisfaction_matrix.png`
- `visualizations/product/negative_keywords_office_furniture.png`
- `visualizations/product/negative_keywords_audio.png`
- `visualizations/product/negative_keywords_bed_bath_table.png`
