| 日期 | 修改人 | 版本号 | 备注 |
|---|---|---|---|
| 2026-08-11 | FSH | v1.1 | 修复报告编码，并同步 src 新目录结构 |

# 商品与品类关联规则分析

## 1. 分析目的

本分析用于识别 delivered 订单中商品和品类之间的历史共购关系，为组合推荐、交叉销售线索及后续业务验证提供参考。

统一分析口径以 `docs/unified_analysis_standards.md` 为最高优先级。

## 2. 购物篮定义

购物篮定义：

- `basket_id = order_id`
- 商品级 `item_id = product_id`
- 仅使用 `order_status = 'delivered'` 的订单
- 同一订单内相同 `product_id` 去重
- 单商品订单保留在 Support 分母中
- Support 分母固定为全部 delivered 订单

本次分析共有 96,478 个 delivered 订单：

- 单商品订单：93,281 个；
- 多商品订单：3,197 个；
- 两者合计：96,478 个。

因此购物篮数量与正式 Support 分母完全一致。

## 3. 正式规则筛选标准

商品级和品类级规则统一使用以下正式阈值：

- 共现订单数不少于 5；
- `confidence >= 0.10`；
- `lift > 1`。

规则数量不足 20 条时如实披露实际数量，不降低阈值凑数。

核心指标：

`Support(A,B) = 同时购买 A 和 B 的订单数 / 全部 delivered 订单数`

`Confidence(A→B) = 同时购买 A 和 B 的订单数 / 购买 A 的订单数`

`Lift(A→B) = Confidence(A→B) / Support(B)`

完整正式结果：

- `outputs/data/06_product_analysis/product_association_top20.csv`
- `outputs/data/06_product_analysis/category_association_top20.csv`

## 4. 商品级关联规则

按照正式阈值，共有 23 条商品级方向性关联规则达到要求，正式结果文件保留排序后的 Top 20。

商品级排名靠前的规则通常具有以下特点：

- 共现订单数多数只有 5—6 单；
- Support 大约在 0.00005—0.00006；
- 部分 Lift 非常高。

例如部分商品组合 Lift 达到数千，但其共现订单仅为 5—6 个。

这并不是公式异常。对于销售规模非常小的商品，只要其有限订单经常共同出现，就可能产生极高 Lift。

因此这些规则更适合解释为：

**低覆盖率但相对较强的局部共现关系。**

不能仅依据高 Lift 将其解释为大规模、稳定的交叉销售机会。正式业务判断必须同时考虑：

- 共现订单数；
- Support；
- Confidence；
- 商品销售规模；
- 业务可解释性。

## 5. 品类级关联规则

按照相同正式阈值，当前仅有 1 条品类级方向性规则达到要求：

`home_confort → bed_bath_table`

其指标约为：

- 共现订单数：43；
- Support：0.000446；
- Confidence：0.1097；
- Lift：1.1414。

该规则表示购买 `home_confort` 品类的订单中，约 10.97% 同时包含 `bed_bath_table`，且这种共同购买概率略高于独立购买情况下的预期水平。

但由于：

- Support 很低；
- Lift 仅略高于 1；

因此只能说明历史订单中存在轻度正向共现迹象，不能直接认定存在稳定或高价值的组合销售关系。

品类级只有 1 条规则达到正式标准，也说明当前数据并不支持构建大量稳定的跨品类关联结论。

## 6. 数据质量验证

正式分析已完成以下验证：

- delivered 订单数 = 96,478；
- 商品购物篮数 = 96,478；
- 品类购物篮数 = 96,478；
- 单商品订单完整保留在 Support 分母；
- 同一订单相同商品已经去重；
- 商品级正式输出全部满足共现、Confidence 和 Lift 阈值；
- 品类级正式输出全部满足相同阈值；
- Support、Confidence 和 Lift 均可由订单计数重新计算；
- 公式回算仅存在机器浮点精度级误差。

因此当前结果在统一分析口径下通过正式质量检查。

## 7. 业务解释与局限性

1. 高 Lift 不等于高业务价值，特别是稀有商品容易产生很高的 Lift。
2. Support 和共现订单量必须与 Lift 同时解读。
3. 关联规则反映历史共购关系，不代表商品 A 导致商品 B 被购买。
4. 当前分析没有利润、营销成本、推荐曝光和用户购买意图字段，因此无法直接估计组合推荐收益。
5. 如果未来用于推荐系统，需要进行时间外验证、用户分层验证或在线实验。

## 8. 可复现文件

- `src/analysis/product_analysis/product_association_rules.py`
- `outputs/data/06_product_analysis/product_association_top20.csv`
- `outputs/data/06_product_analysis/category_association_top20.csv`
