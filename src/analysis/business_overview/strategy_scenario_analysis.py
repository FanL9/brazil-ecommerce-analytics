#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
仅基于 core_business_issues.md 的 3.1—3.3 生成增长策略与情景测算。

问题范围：
3.1 GMV增长主要依赖订单规模，客单价提升不足
3.2 GMV高度集中于信用卡支付，支付渠道结构较为单一
3.3 GMV集中于少数头部州，区域增长表现存在分化

所有提升率与转移比例均为情景假设，不是因果预测。
"""

import argparse
import csv
from pathlib import Path

BASE_MONTH = "2018-07"
BASE_GMV = 1_027_903.86
BASE_ORDERS = 6_159
BASE_AOV = 166.89
CREDIT_CARD_SHARE = 0.7846
TOP3_SHARE = 0.6212
NON_TOP3_SHARE = 1 - TOP3_SHARE

SCENARIOS = [("保守", 0), ("基准", 1), ("乐观", 2)]


def project_root():
    p = Path(__file__).resolve()
    for parent in p.parents:
        if parent.name == "src":
            return parent.parent
    return Path.cwd()


def common():
    return {
        "基准月份": BASE_MONTH,
        "基准月GMV_BRL": BASE_GMV,
        "基准月订单量": BASE_ORDERS,
        "基准客单价_BRL": BASE_AOV,
        "情景性质": "假设测算，非因果预测",
        "数据限制": "缺少营销费用、毛利、退款、支付失败率、手续费、物流成本及完整州级月度明细。",
    }


def strategy_aov():
    rates = {"保守": 0.02, "基准": 0.05, "乐观": 0.08}
    rows = []
    for label, _ in SCENARIOS:
        r = rates[label]
        new_aov = BASE_AOV * (1 + r)
        inc_gmv = BASE_ORDERS * (new_aov - BASE_AOV)
        rows.append({
            **common(),
            "策略ID": "S1",
            "优先级": 1,
            "策略名称": "提升客单价的加购与组合销售策略",
            "对应业务问题": "3.1 GMV增长主要依赖订单规模，客单价提升不足",
            "目标用户": "已有购买意愿、进入商品页或购物车的活跃用户",
            "目标地区": "全平台",
            "目标订单金额区间": "全部有效订单；优先覆盖接近当前客单价的订单",
            "执行时间窗口": "8—12周试点",
            "执行动作": "增加关联商品、组合包、多件购和适度满额优惠；通过A/B测试控制优惠强度。",
            "监测指标": "客单价、每单商品数、加购率、结算转化率、GMV、优惠成本率、退款率",
            "情景": label,
            "基准口径": "2018-07完整月订单量 × 2018-07客单价",
            "目标基准值": BASE_AOV,
            "目标基准单位": "BRL/单",
            "假设提升率": r,
            "假设转移占比百分点": 0,
            "预计增量GMV_BRL": round(inc_gmv, 2),
            "预计增量订单数": 0,
            "预计转移GMV_BRL": 0,
            "预计转移订单数": 0,
            "预计总GMV_BRL": round(BASE_GMV + inc_gmv, 2),
            "预计整体GMV提升率": inc_gmv / BASE_GMV,
            "预计目标指标": f"客单价由166.89提升至约{new_aov:.2f} BRL",
            "计算公式": "预计增量GMV = 基准月订单量 × (新客单价 - 基准客单价)",
            "关键假设": "订单量保持不变；客单价提升来自真实加购或组合销售，不显著压低转化率。",
            "成本等级": "中",
            "潜在风险": "优惠成本上升、转化率下降、商品推荐相关性不足、毛利被侵蚀",
            "证据说明": "2016-10至2018-07 GMV和订单量大幅增长，但客单价由175.72降至166.89 BRL。",
        })
    return rows


def strategy_payment():
    shifts = {"保守": 0.01, "基准": 0.025, "乐观": 0.04}
    rows = []
    for label, _ in SCENARIOS:
        s = shifts[label]
        shifted_gmv = BASE_GMV * s
        rows.append({
            **common(),
            "策略ID": "S2",
            "优先级": 2,
            "策略名称": "非信用卡支付引导与支付韧性建设",
            "对应业务问题": "3.2 GMV高度集中于信用卡支付，支付渠道结构较为单一",
            "目标用户": "结算环节可使用非信用卡支付方式的用户",
            "目标地区": "全平台",
            "目标订单金额区间": "全部有效订单",
            "执行时间窗口": "6—10周试点",
            "执行动作": "优化boleto、voucher、debit card入口；测试备用支付路径和轻量引导。",
            "监测指标": "信用卡GMV占比、非信用卡渗透率、支付成功率、失败恢复率、手续费率、取消率",
            "情景": label,
            "基准口径": "2018-07月GMV；按总GMV百分点进行渠道转移",
            "目标基准值": BASE_GMV,
            "目标基准单位": "BRL/月",
            "假设提升率": 0,
            "假设转移占比百分点": s,
            "预计增量GMV_BRL": 0,
            "预计增量订单数": 0,
            "预计转移GMV_BRL": round(shifted_gmv, 2),
            "预计转移订单数": round(shifted_gmv / BASE_AOV),
            "预计总GMV_BRL": BASE_GMV,
            "预计整体GMV提升率": 0,
            "预计目标指标": f"信用卡GMV占比由78.46%降至约{(CREDIT_CARD_SHARE-s)*100:.2f}%",
            "计算公式": "预计转移GMV = 基准月GMV × 假设转移百分点；不计新增GMV",
            "关键假设": "渠道转移不改变总体支付成功率和总GMV，转移来自支付方式替代而非新增需求。",
            "成本等级": "低—中",
            "潜在风险": "非信用卡体验较差、到账慢、取消率上升、激励成本高于手续费节省",
            "证据说明": "信用卡贡献78.46%的GMV；当前数据缺少失败率、手续费和拒付率，因此不推断利润改善。",
        })
    return rows


def strategy_region():
    rates = {"保守": 0.015, "基准": 0.03, "乐观": 0.05}
    pool = BASE_GMV * NON_TOP3_SHARE
    rows = []
    for label, _ in SCENARIOS:
        r = rates[label]
        inc_gmv = pool * r
        total = BASE_GMV + inc_gmv
        new_share = (pool + inc_gmv) / total
        rows.append({
            **common(),
            "策略ID": "S3",
            "优先级": 3,
            "策略名称": "非头部州分层增长试点",
            "对应业务问题": "3.3 GMV集中于少数头部州，区域增长表现存在分化",
            "目标用户": "RJ、RS、PR、BA等大规模低增速州用户；DF、ES等小规模高增速州用户",
            "目标地区": "非SP、RJ、MG州为测算目标池；实际执行按州分层",
            "目标订单金额区间": "全部有效订单",
            "执行时间窗口": "3—6个月",
            "执行动作": "大规模低增速州做召回、品类补齐和本地化促销；小规模高增速州增加高转化品类曝光并验证物流承载。",
            "监测指标": "州级GMV、订单量、活跃用户、转化率、客单价、配送时效、取消率、营销成本/增量GMV",
            "情景": label,
            "基准口径": "2018-07月GMV × 非前三州GMV占比37.88%",
            "目标基准值": round(pool, 2),
            "目标基准单位": "BRL/月",
            "假设提升率": r,
            "假设转移占比百分点": 0,
            "预计增量GMV_BRL": round(inc_gmv, 2),
            "预计增量订单数": round(inc_gmv / BASE_AOV),
            "预计转移GMV_BRL": 0,
            "预计转移订单数": 0,
            "预计总GMV_BRL": round(total, 2),
            "预计整体GMV提升率": inc_gmv / BASE_GMV,
            "预计目标指标": f"非前三州GMV占比由37.88%提升至约{new_share*100:.2f}%",
            "计算公式": "预计增量GMV = 基准月GMV × 37.88% × 假设区域提升率；预计增量订单 = 增量GMV ÷ 166.89",
            "关键假设": "全样本州级结构近似代表2018-07结构；新增订单客单价接近平台基准；物流与供给可承接增长。",
            "成本等级": "中—高",
            "潜在风险": "区域营销效率偏低、物流时效恶化、小州低基数放大增长率、州级结构近似产生误差",
            "证据说明": "SP、RJ、MG合计贡献62.12%的GMV；部分大州增速偏慢，而DF、ES规模较小但增速较高。",
        })
    return rows


COLUMNS = [
    "策略ID","优先级","策略名称","对应业务问题","目标用户","目标地区","目标订单金额区间",
    "执行时间窗口","执行动作","监测指标","情景","情景性质","基准月份","基准口径",
    "目标基准值","目标基准单位","基准月GMV_BRL","基准月订单量","基准客单价_BRL",
    "假设提升率","假设转移占比百分点","预计增量GMV_BRL","预计增量订单数",
    "预计转移GMV_BRL","预计转移订单数","预计总GMV_BRL","预计整体GMV提升率",
    "预计目标指标","计算公式","关键假设","成本等级","潜在风险","证据说明","数据限制"
]


def build_rows():
    rows = strategy_aov() + strategy_payment() + strategy_region()
    assert len(rows) == 9
    assert {r["策略ID"] for r in rows} == {"S1", "S2", "S3"}
    assert all(r["对应业务问题"].startswith(("3.1", "3.2", "3.3")) for r in rows)
    return rows


def main():
    default_output = project_root() / "outputs" / "data" / "02_business_overview" / "strategy_scenarios.csv"
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=default_output)
    args = parser.parse_args()

    rows = build_rows()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"已生成: {args.output}")
    print("问题范围: 3.1—3.3")
    print("策略数: 3")
    print("情景行数: 9")


if __name__ == "__main__":
    main()
