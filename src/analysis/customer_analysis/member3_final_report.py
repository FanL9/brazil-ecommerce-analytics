from pathlib import Path
import shutil

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# Final report generator
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "03_customer_analysis"
)

REPORT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "customer"
)

REPORT_PATH = (
    REPORT_DIR
    / "churn_user_analysis_report.md"
)

BACKUP_PATH = (
    REPORT_DIR
    / "churn_user_analysis_report_pre_final.md"
)

FIGURE_DIR = (
    PROJECT_ROOT
    / "visualizations"
    / "customer"
    / "high_value"
)


FILES = {
    "churn_comparison":
        DATA_DIR / "churn_comparison.csv",

    "churn_features":
        DATA_DIR / "churn_related_features.csv",

    "churn_state":
        DATA_DIR / "churn_state_structure.csv",

    "churn_payment":
        DATA_DIR / "churn_payment_structure.csv",

    "churn_first_month":
        DATA_DIR / "churn_first_purchase_month.csv",

    "churn_detail":
        DATA_DIR / "churn_user_detail.csv",

    "rfm":
        DATA_DIR / "rfm_customer_detail.csv",

    "user_base":
        DATA_DIR / "member3_user_value_base.csv",

    "lifecycle":
        DATA_DIR / "member3_lifecycle_bridge.csv",

    "hv_lifecycle":
        DATA_DIR / "high_value_user_lifecycle_summary.csv",

    "hv_consumption":
        DATA_DIR / "high_value_user_consumption_behavior.csv",

    "hv_payment_order":
        DATA_DIR / "high_value_user_payment_method_order_share.csv",

    "hv_payment_gmv":
        DATA_DIR / "high_value_user_payment_method_gmv_share.csv",

    "hv_experience":
        DATA_DIR / "high_value_user_experience_profile.csv",

    "hv_integrated":
        DATA_DIR / "high_value_user_integrated_profile.csv",

    "hv_churn_integrated":
        DATA_DIR / "high_value_churn_user_integrated_profile.csv",
}


FIGURES = {
    "consumption":
        FIGURE_DIR / "high_value_consumption_comparison.png",

    "payment":
        FIGURE_DIR / "high_value_payment_comparison.png",

    "experience":
        FIGURE_DIR / "high_value_experience_comparison.png",
}


def pct_decimal(value):
    if pd.isna(value):
        return "NULL"
    return f"{float(value):.2%}"


def pct_number(value):
    if pd.isna(value):
        return "NULL"
    return f"{float(value):.2f}%"


def num(value, digits=2):
    if pd.isna(value):
        return "NULL"
    return f"{float(value):,.{digits}f}"


def integer(value):
    if pd.isna(value):
        return "NULL"
    return f"{int(round(float(value))):,}"


def markdown_table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]

    for row in rows:
        values = [
            str(value).replace("|", "/")
            for value in row
        ]

        lines.append(
            "| " + " | ".join(values) + " |"
        )

    return "\n".join(lines)


def load_inputs():
    missing = [
        path
        for path in FILES.values()
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing required CSV outputs:\n"
            + "\n".join(str(x) for x in missing)
        )

    return {
        name: pd.read_csv(
            path,
            encoding="utf-8-sig",
        )
        for name, path in FILES.items()
    }


def validate_inputs(data):
    print("\n[1] FINAL INPUT VALIDATION")

    churn = data["churn_comparison"]

    # --------------------------------------------------------
    # Official population
    # --------------------------------------------------------
    total_users = int(
        churn["user_count"].sum()
    )

    print(
        f"Churn comparison users: "
        f"{total_users:,}"
    )

    if total_users != 87214:
        raise ValueError(
            "Expected 87,214 users in churn comparison."
        )

    if len(data["churn_detail"]) != 87214:
        raise ValueError(
            "churn_user_detail must contain 87,214 rows."
        )

    if len(data["rfm"]) != 87214:
        raise ValueError(
            "rfm_customer_detail must contain 87,214 rows."
        )

    if len(data["user_base"]) != 87214:
        raise ValueError(
            "member3_user_value_base must contain 87,214 rows."
        )

    if len(data["lifecycle"]) != 87214:
        raise ValueError(
            "member3_lifecycle_bridge must contain 87,214 rows."
        )

    print("Official user population: PASS")

    # --------------------------------------------------------
    # High-value population
    # --------------------------------------------------------
    hv = data["hv_integrated"]
    hv_churn = data["hv_churn_integrated"]

    print(
        f"High-value users: "
        f"{len(hv):,}"
    )

    print(
        f"High-value churn users: "
        f"{len(hv_churn):,}"
    )

    if len(hv) != 4:
        raise ValueError(
            "Expected exactly 4 high-value users."
        )

    if len(hv_churn) != 1:
        raise ValueError(
            "Expected exactly 1 high-value churn user."
        )

    lifecycle_hv = int(
        data["hv_lifecycle"][
            "high_value_users"
        ].sum()
    )

    if lifecycle_hv != 4:
        raise ValueError(
            "Lifecycle summary must recover 4 high-value users."
        )

    print("High-value population: PASS")

    # --------------------------------------------------------
    # Cross-module user key
    # --------------------------------------------------------
    for name in [
        "churn_detail",
        "rfm",
        "user_base",
        "lifecycle",
    ]:
        frame = data[name]

        if (
            "customer_unique_id"
            not in frame.columns
        ):
            raise ValueError(
                f"{name} missing customer_unique_id."
            )

        if frame[
            "customer_unique_id"
        ].duplicated().any():
            raise ValueError(
                f"{name} contains duplicate users."
            )

    print("Customer grain validation: PASS")

    # --------------------------------------------------------
    # Final figures
    # --------------------------------------------------------
    for name, path in FIGURES.items():

        if not path.exists():
            raise FileNotFoundError(
                f"Missing final figure: {path}"
            )

        if path.stat().st_size == 0:
            raise RuntimeError(
                f"Empty final figure: {path}"
            )

        print(
            f"Figure {name}: PASS "
            f"({path.stat().st_size:,} bytes)"
        )

    print("Final figure validation: PASS")
    print("Final input validation: PASS")


def build_churn_summary(data):
    frame = data["churn_comparison"].copy()

    churned = frame.loc[
        frame["churn_status"] == "Churned"
    ].iloc[0]

    non_churned = frame.loc[
        frame["churn_status"] == "Non-churned"
    ].iloc[0]

    metric_specs = [
        (
            "Users",
            "user_count",
            integer,
        ),
        (
            "User Share",
            "user_share_pct",
            pct_number,
        ),
        (
            "Spend per User (BRL)",
            "spend_per_user",
            lambda x: num(x, 2),
        ),
        (
            "Average Purchase Frequency",
            "avg_purchase_frequency",
            lambda x: num(x, 4),
        ),
        (
            "Repeat Rate",
            "repeat_rate_pct",
            pct_number,
        ),
        (
            "Average Lifecycle Days",
            "avg_lifecycle_days",
            lambda x: num(x, 2),
        ),
        (
            "Average Order Value (BRL)",
            "average_order_value",
            lambda x: num(x, 2),
        ),
        (
            "Average Review Score",
            "avg_review_score",
            lambda x: num(x, 3),
        ),
        (
            "Average Delivery Days",
            "avg_delivery_days",
            lambda x: num(x, 2),
        ),
        (
            "Late Delivery Rate",
            "delay_rate_pct",
            pct_number,
        ),
    ]

    rows = []

    for label, column, formatter in metric_specs:

        if column not in frame.columns:
            continue

        rows.append(
            [
                label,
                formatter(churned[column]),
                formatter(non_churned[column]),
            ]
        )

    table = markdown_table(
        [
            "Metric",
            "Churned",
            "Non-churned",
        ],
        rows,
    )

    return churned, non_churned, table


def build_churn_feature_table(data):
    frame = data["churn_features"].copy()

    rows = []

    for _, row in frame.iterrows():

        rows.append(
            [
                row.get("feature", ""),
                row.get("feature_type", ""),
                num(
                    row.get(
                        "churned_value",
                        float("nan"),
                    ),
                    4,
                ),
                num(
                    row.get(
                        "non_churned_value",
                        float("nan"),
                    ),
                    4,
                ),
                num(
                    row.get(
                        "difference",
                        float("nan"),
                    ),
                    4,
                ),
                row.get(
                    "interpretation",
                    "",
                ),
                row.get(
                    "limitation",
                    "",
                ),
            ]
        )

    return markdown_table(
        [
            "Feature",
            "Type",
            "Churned",
            "Non-churned",
            "Difference",
            "Interpretation",
            "Limitation",
        ],
        rows,
    )


def build_churn_state_table(data):
    frame = data["churn_state"].copy()

    # Use the churned rows for state-level churn profile.
    if "churn_status" in frame.columns:
        frame = frame.loc[
            frame["churn_status"] == "Churned"
        ].copy()

    frame = (
        frame.sort_values(
            [
                "user_count",
                "customer_state",
            ],
            ascending=[
                False,
                True,
            ],
        )
        .head(10)
    )

    rows = []

    for _, row in frame.iterrows():

        rows.append(
            [
                row["customer_state"],
                integer(row["user_count"]),
                integer(row["churned_users"]),
                integer(row["non_churned_users"]),
                pct_number(
                    row["churn_rate_pct"]
                ),
                pct_number(
                    row["user_share_pct"]
                ),
            ]
        )

    return markdown_table(
        [
            "State",
            "Users",
            "Churned Users",
            "Non-churned Users",
            "Churn Rate",
            "User Share",
        ],
        rows,
    )


def build_churn_payment_table(data):
    frame = data["churn_payment"].copy()

    rows = []

    for _, row in frame.iterrows():

        rows.append(
            [
                row["churn_status"],
                row["primary_payment_type"],
                integer(row["order_count"]),
                pct_number(
                    row["order_share_pct"]
                ),
                integer(
                    row[
                        "users_using_payment_type"
                    ]
                ),
            ]
        )

    return markdown_table(
        [
            "Group",
            "Primary Payment Type",
            "Orders",
            "Order Share",
            "Users",
        ],
        rows,
    )


def build_high_value_geography_tables(data):
    frame = data["hv_integrated"].copy()

    # --------------------------------------------------------
    # State-level summary
    # --------------------------------------------------------
    state = (
        frame.groupby(
            "profile_state",
            as_index=False,
        )
        .agg(
            high_value_users=(
                "customer_unique_id",
                "nunique",
            ),
            high_value_churn_users=(
                "is_high_value_churn_user",
                "sum",
            ),
            total_gmv=(
                "monetary",
                "sum",
            ),
        )
        .sort_values(
            [
                "high_value_users",
                "profile_state",
            ],
            ascending=[
                False,
                True,
            ],
        )
    )

    state_rows = []

    for _, row in state.iterrows():

        state_rows.append(
            [
                row["profile_state"],
                integer(
                    row["high_value_users"]
                ),
                integer(
                    row[
                        "high_value_churn_users"
                    ]
                ),
                num(
                    row["total_gmv"],
                    2,
                ),
            ]
        )

    state_table = markdown_table(
        [
            "State",
            "High-Value Users",
            "High-Value Churn Users",
            "GMV (BRL)",
        ],
        state_rows,
    )

    # --------------------------------------------------------
    # User-level city detail
    # --------------------------------------------------------
    detail = frame.sort_values(
        [
            "profile_state",
            "profile_city",
            "customer_unique_id",
        ]
    )

    city_rows = []

    for _, row in detail.iterrows():

        city_rows.append(
            [
                row["profile_state"],
                row["profile_city"],
                integer(row["frequency"]),
                num(row["monetary"], 2),
                row["lifecycle_stage"],
                integer(
                    row[
                        "is_high_value_churn_user"
                    ]
                ),
            ]
        )

    city_table = markdown_table(
        [
            "State",
            "City",
            "Orders",
            "GMV (BRL)",
            "Lifecycle Stage",
            "Churn",
        ],
        city_rows,
    )

    return state_table, city_table


def build_high_value_lifecycle_table(data):
    frame = data["hv_lifecycle"].copy()

    rows = []

    for _, row in frame.iterrows():

        rows.append(
            [
                row["lifecycle_stage"],
                integer(
                    row["high_value_users"]
                ),
                integer(
                    row[
                        "high_value_churn_users"
                    ]
                ),
                integer(
                    row["total_orders"]
                ),
                num(
                    row["total_gmv"],
                    2,
                ),
                num(
                    row["avg_recency_days"],
                    2,
                ),
                num(
                    row["avg_lifecycle_days"],
                    2,
                ),
                pct_decimal(
                    row[
                        "high_value_user_share"
                    ]
                ),
            ]
        )

    return markdown_table(
        [
            "Lifecycle Stage",
            "High-Value Users",
            "High-Value Churn Users",
            "Orders",
            "GMV (BRL)",
            "Average Recency Days",
            "Average Lifecycle Days",
            "High-Value User Share",
        ],
        rows,
    )


def build_high_value_payment_tables(data):
    order_frame = data["hv_payment_order"].copy()
    gmv_frame = data["hv_payment_gmv"].copy()

    # --------------------------------------------------------
    # Main payment type order share
    # --------------------------------------------------------
    order_rows = []

    for _, row in order_frame.iterrows():

        order_rows.append(
            [
                row["group"],
                row["main_payment_type"],
                integer(row["orders"]),
                pct_decimal(
                    row["order_share"]
                ),
            ]
        )

    order_table = markdown_table(
        [
            "Group",
            "Main Payment Type",
            "Orders",
            "Order Share",
        ],
        order_rows,
    )

    # --------------------------------------------------------
    # Actual payment-type GMV share
    # --------------------------------------------------------
    gmv_rows = []

    for _, row in gmv_frame.iterrows():

        gmv_rows.append(
            [
                row["group"],
                row["payment_type"],
                num(
                    row["payment_gmv"],
                    2,
                ),
                pct_decimal(
                    row["gmv_share"]
                ),
            ]
        )

    gmv_table = markdown_table(
        [
            "Group",
            "Payment Type",
            "Payment GMV (BRL)",
            "GMV Share",
        ],
        gmv_rows,
    )

    return order_table, gmv_table


def build_high_value_consumption_table(data):
    frame = data["hv_consumption"].copy()

    rows = []

    for _, row in frame.iterrows():

        rows.append(
            [
                row["group"],
                integer(row["users"]),
                integer(row["valid_orders"]),
                integer(row["paid_orders"]),
                num(row["gmv"], 2),
                num(
                    row["spend_per_user"],
                    2,
                ),
                num(
                    row["average_order_value"],
                    2,
                ),
                num(
                    row[
                        "average_purchase_frequency"
                    ],
                    4,
                ),
                pct_decimal(
                    row["repeat_rate"]
                ),
                pct_decimal(
                    row[
                        "high_amount_order_share"
                    ]
                ),
            ]
        )

    return markdown_table(
        [
            "Group",
            "Users",
            "Valid Orders",
            "Paid Orders",
            "GMV (BRL)",
            "Spend per User (BRL)",
            "Average Order Value (BRL)",
            "Purchase Frequency",
            "Repeat Rate",
            "High-Amount Order Share",
        ],
        rows,
    )


def build_high_value_experience_table(data):
    frame = data["hv_experience"].copy()

    rows = []

    for _, row in frame.iterrows():

        rows.append(
            [
                row["group"],
                integer(
                    row["reviewed_orders"]
                ),
                num(
                    row["average_review_score"],
                    3,
                ),
                pct_decimal(
                    row["low_score_order_share"]
                ),
                pct_decimal(
                    row["positive_review_rate"]
                ),
                integer(
                    row["delivery_orders"]
                ),
                num(
                    row["average_delivery_days"],
                    2,
                ),
                pct_decimal(
                    row["delay_rate"]
                ),
            ]
        )

    return markdown_table(
        [
            "Group",
            "Reviewed Orders",
            "Average Review Score",
            "1-Star Order Share",
            "Positive Review Rate",
            "Delivery Orders",
            "Average Delivery Days",
            "Late Delivery Rate",
        ],
        rows,
    )


def build_high_value_churn_case_table(data):
    frame = data[
        "hv_churn_integrated"
    ].copy()

    if len(frame) != 1:
        raise ValueError(
            "Expected exactly one high-value churn user."
        )

    row = frame.iloc[0]

    rows = [
        [
            "Customer",
            row["customer_unique_id"],
        ],
        [
            "State / City",
            (
                f"{row['profile_state']} / "
                f"{row['profile_city']}"
            ),
        ],
        [
            "Lifecycle Stage",
            row["lifecycle_stage"],
        ],
        [
            "Recency Days",
            integer(row["recency_days"]),
        ],
        [
            "Frequency",
            integer(row["frequency"]),
        ],
        [
            "Monetary (BRL)",
            num(row["monetary"], 2),
        ],
        [
            "R Score",
            integer(row["r_score"]),
        ],
        [
            "F Score",
            integer(row["f_score"]),
        ],
        [
            "M Score",
            integer(row["m_score"]),
        ],
        [
            "Dominant Payment Type",
            row["dominant_main_payment_type"],
        ],
        [
            "Average Order Value (BRL)",
            num(
                row["average_order_value"],
                2,
            ),
        ],
        [
            "Average Review Score",
            num(
                row["average_review_score"],
                3,
            ),
        ],
        [
            "Average Delivery Days",
            num(
                row["average_delivery_days"],
                2,
            ),
        ],
        [
            "Late Delivery Rate",
            pct_decimal(
                row["delay_rate"]
            ),
        ],
        [
            "Weekday Order Share",
            pct_decimal(
                row["weekday_order_share"]
            ),
        ],
        [
            "Peak Purchase Hour",
            (
                f"{integer(row['peak_purchase_hour'])}:00"
            ),
        ],
    ]

    return markdown_table(
        [
            "Metric",
            "Value",
        ],
        rows,
    )

def generate_report(data):
    """Generate the final Member 3 Markdown report from validated official outputs."""

    churn_summary = build_churn_summary(data)
    churn_features = build_churn_feature_table(data)
    churn_state = build_churn_state_table(data)
    churn_payment = build_churn_payment_table(data)

    hv_geography = build_high_value_geography_tables(data)
    hv_lifecycle = build_high_value_lifecycle_table(data)
    hv_payment = build_high_value_payment_tables(data)
    hv_consumption = build_high_value_consumption_table(data)
    hv_experience = build_high_value_experience_table(data)
    hv_churn_case = build_high_value_churn_case_table(data)

    context = {
        "data": data,
        "churn_summary": churn_summary[2],
        "churn_features": churn_features,
        "churn_state": churn_state,
        "churn_payment": churn_payment,
        "hv_geography": hv_geography,
        "hv_lifecycle": hv_lifecycle,
        "hv_payment": hv_payment,
        "hv_consumption": hv_consumption,
        "hv_experience": hv_experience,
        "hv_churn_case": hv_churn_case,
        "official_user_n": len(data["user_base"]),
        "high_value_n": len(data["hv_integrated"]),
        "high_value_churn_n": len(data["hv_churn_integrated"]),
    }

    sections = []
    sections.extend(_build_report_sections_1_4(context))
    sections.extend(_build_report_sections_5_8(context))
    sections.extend(_build_report_sections_9_14(context))

    return "`n".join(sections).rstrip() + "`n"

def _build_report_sections_1_4(context):
    """Build version record and Sections 1-4 of the final report."""

    sections = [
        """<!--
Version Record
- Stage: Phase 3 / Member 3
- Report: Churn User Analysis and High-Value User Profile
- Observation cutoff: 2018-07-31
- Official customer key: customer_unique_id
- Valid orders: delivered orders purchased before 2018-08-01 00:00:00
-->""",

        """# 阶段三 Member 3：流失用户分析与高价值用户画像报告

本报告基于阶段三统一分析口径，对流失用户特征、重要价值用户画像以及
RFM × Churn × Lifecycle 交叉结果进行汇总。

报告中的流失为固定观察窗口下的**行为型流失**，不代表用户永久离开。
所有画像及组间差异均属于描述性分析，不作直接因果推断。
""",

        """## 1. 分析目标

本报告主要完成以下分析目标：

- 汇总正式观察窗口下的流失用户规模与结构；
- 对比流失与未流失用户的核心行为特征；
- 描述重要价值用户的地域、支付、消费及评论配送体验；
- 联合 RFM、Churn 与 Lifecycle 进行交叉分析；
- 对高价值流失用户进行个案级综合描述；
- 明确小样本、观察窗口和非因果解释边界。
""",

        """## 2. 数据范围与统一口径

### 2.1 数据范围

本报告严格遵循 `docs/unified_analysis_standards.md`。

正式用户唯一标识为 `customer_unique_id`；仅纳入
`order_status = delivered` 且
`order_purchase_timestamp < 2018-08-01 00:00:00`
的有效订单。

固定观察截止日为 **2018-07-31**。

GMV 仅统计正 `payment_value`；AOV 使用
**GMV / 正支付订单量**，而不是除以全部 delivered 订单量。
存在支付信息异常但符合 delivered 有效订单口径的订单时，不因此删除有效订单。

### 2.2 流失规则

用户最近一次有效购买距离观察截止日：

- `recency_days > 90`：流失用户；
- `recency_days <= 90`：未流失用户。

该定义表示固定窗口下的行为型流失状态，不等价于永久客户流失。

### 2.3 重要价值用户规则

重要价值用户严格定义为：

`R >= 4 AND F >= 4 AND M >= 4`

分析过程中不因样本量较小而调整 RFM 或 churn 阈值。

### 2.4 生命周期交叉口径

Member 3 正式生命周期交叉使用
`member3_lifecycle_bridge.csv`，不直接使用观察窗口不同的原 Member 2
`customer_lifecycle_segment.csv`。

正式生命周期规则首先判断 `recency > 90` 为 Dormant Customer，
再对未流失用户依据订单数、recency 与 lifecycle_days
划分 New、Early、Growing 和 Mature Customer。
""",

        """## 3. 流失用户分析

### 3.1 总体流失规模

""" + context["churn_summary"] + """

### 3.2 流失与未流失用户核心指标

""" + context["churn_features"] + """

以上结果用于描述正式观察窗口内两类用户的行为差异。
这些差异可能与客户活跃程度和历史购买行为相关，但不能据此推断因果关系。

### 3.3 流失相关特征

流失相关特征分析基于统一用户粒度和固定观察截止日完成。
对于不同特征组之间观察到的差异，本报告仅进行描述性解释。

### 3.4 地域结构

""" + context["churn_state"] + """

地域分布用于展示当前样本结构，不意味着特定州本身造成更高或更低的流失风险。

### 3.5 支付方式结构

""" + context["churn_payment"] + """

支付方式结构同样属于观察性结果。混合支付及订单级主支付方式均按照
Member 3 已锁定的支付口径处理，避免一张订单被重复计入多个主支付方式。

### 3.6 首购时间解释

首购月份结构用于辅助理解用户进入平台的时间差异。
由于较早进入平台的用户拥有更长的可观察历史，因此首购时间与当前流失状态之间
可能同时受到观察窗口长度影响，不能将首购月份直接解释为流失原因。
""",

        """## 4. 重要价值用户总体情况

正式 RFM 结果中，重要价值用户共 **{high_value_n} 人**，
其中高价值流失用户 **{high_value_churn_n} 人**。

由于重要价值用户总体样本仅为 **{high_value_n} 人**，
后续地域、支付、消费、体验及生命周期画像均只代表该小样本中的观察结果，
不能推广为全部高价值客户群体的稳定规律。
""".format(
            high_value_n=context["high_value_n"],
            high_value_churn_n=context["high_value_churn_n"],
        ),
    ]

    return sections

def _build_report_sections_5_8(context):
    """Build Sections 5-8 of the final report."""

    state_table, city_table = context["hv_geography"]
    payment_order_table, payment_gmv_table = context["hv_payment"]

    sections = [
        f"""## 5. 重要价值用户地域画像

重要价值用户仅 **{context['high_value_n']} 人**，因此本节地域结果仅用于描述
当前正式高价值样本的实际分布，不将样本分布推广为整体市场结构。

### 5.1 州级分布

{state_table}

州级结果反映当前样本中重要价值用户及其累计消费的分布情况。
由于样本量很小，不据此判断某一州是高价值用户的稳定“核心市场”。

### 5.2 用户所在城市

{city_table}

城市级结果用于展示这组重要价值用户的实际所在地，
不进行城市间高价值用户总体占比或流失风险的统计推广。
""",

        f"""## 6. 重要价值用户支付画像

重要价值用户支付结构继续采用阶段三锁定口径。
订单支付方式占比使用 `main_payment_type`，保证一张订单只归属一个主支付方式；
支付方式 GMV 占比则使用原始正 `payment_value` 按实际 `payment_type` 拆分，
避免将混合支付订单的全部 GMV 错误归入单一支付方式。

### 6.1 主支付方式订单占比

{payment_order_table}

### 6.2 实际支付方式 GMV 占比

{payment_gmv_table}

![High-value payment comparison](../../visualizations/customer/high_value/high_value_payment_comparison.png)

以上支付特征仅描述当前 **{context['high_value_n']} 位**重要价值用户样本，
不能据此推断某种支付方式会导致更高客户价值或更低流失风险。
""",

        f"""## 7. 重要价值用户消费画像

{context["hv_consumption"]}

![High-value consumption comparison](../../visualizations/customer/high_value/high_value_consumption_comparison.png)

高金额订单继续严格定义为 `order_gmv >= 500 BRL`，
即统一金额档 `[500,+inf)`，不使用此前讨论过的 200 BRL 阈值。

消费画像用于区分购买频次、累计消费、订单金额结构和购买时间特征。
当前重要价值样本仅 **{context['high_value_n']} 人**，
因此相关差异只作描述性解释，不作为总体高价值客户行为规律。
""",

        f"""## 8. 评论与配送体验画像

{context["hv_experience"]}

![High-value experience comparison](../../visualizations/customer/high_value/high_value_experience_comparison.png)

评论指标仅使用 1～5 分的合法代表评分；一订单多评论时按照已锁定规则选择唯一代表评论。
低评分订单统一定义为代表评分等于 1 的订单，不能用 `1 - 好评率` 替代。

配送时长仅纳入购买时间与实际送达时间合法且配送时长非负的订单；
延迟订单定义为实际送达时间晚于预计送达时间。

体验差异同样属于观察性描述。即使高价值用户或高价值流失个案表现出
评分、配送时长或延迟率差异，也不能直接解释为导致流失的因果因素。
""",
    ]

    return sections

def _build_report_sections_9_14(context):
    """Build Sections 9-14 of the final report."""

    sections = [
        f"""## 9. RFM × Churn × Lifecycle 交叉

{context["hv_lifecycle"]}

生命周期交叉统一使用 `member3_lifecycle_bridge.csv`，
其观察截止日、有效订单范围、用户粒度与 Member 3 正式分析保持一致。

正式对账已经验证：

- RFM Frequency 与生命周期有效订单数一致；
- RFM Monetary 与生命周期累计 GMV 一致；
- Recency 与固定观察截止日口径一致；
- Churn 用户与 Dormant Customer 完全一致。

重要价值用户仅 **{context['high_value_n']} 人**，
因此生命周期分布只能描述该正式样本，不应据此估计稳定的高价值客户生命周期结构。
""",

        f"""## 10. 高价值流失用户综合个案

正式高价值流失用户共 **{context['high_value_churn_n']} 人**。

{context["hv_churn_case"]}

该个案综合了地域、RFM、生命周期、支付、消费以及评论配送体验信息。

对于该高价值流失个体，可以描述其在评分、配送时长等维度表现出的特征，
并将其作为后续客户运营或进一步研究的关注对象。

但由于高价值流失样本仅 **{context['high_value_churn_n']} 人**，
不能将个体体验特征推广为高价值客户流失的一般规律，
更不能将配送、评分、支付方式等观察性差异解释为直接流失原因。
""",

        f"""## 11. 核心结论

1. 正式分析严格基于固定观察窗口、`customer_unique_id` 用户粒度以及 delivered 有效订单口径，
   流失状态表示行为型流失，不代表用户永久离开。

2. 流失与未流失用户在消费、购买频次、生命周期及体验等维度存在可观察差异，
   这些结果用于用户结构描述和运营线索识别，不作因果解释。

3. 正式重要价值用户仅 **{context['high_value_n']} 人**，
   其中高价值流失用户 **{context['high_value_churn_n']} 人**。
   因此高价值画像首先是小样本事实描述，而不是总体参数估计。

4. 当前高价值样本的价值特征更明显来自较高购买频次与累计消费，
   而不是依靠 `order_gmv >= 500 BRL` 的单笔高金额订单。

5. 当前高价值样本在地域、支付方式、评论和配送体验上均呈现一定集中或差异，
   但受样本量限制，只能表述为“本样本中”的观察结果。

6. RFM、Churn 与 Lifecycle 已通过统一口径桥接和跨模块对账，
   正式生命周期分析使用 `member3_lifecycle_bridge.csv`，
   不直接使用观察窗口不同的原 Member 2 生命周期文件。
""",

        f"""## 12. 数据限制与解释边界

本报告正式用户总体为 **{context['official_user_n']:,} 人**，
但重要价值用户只有 **{context['high_value_n']} 人**，
高价值流失用户只有 **{context['high_value_churn_n']} 人**。

因此需要遵守以下解释边界：

- churn 是固定观察窗口下的行为型流失，不等于永久离开；
- 所有组间差异均来自观察性数据，只能描述相关、差异或可能的解释线索；
- 不根据观察性结果直接推断因果关系；
- 不为了增加高价值样本而修改 RFM 或 churn 阈值；
- 地域、支付、消费和体验画像均需明确小样本限制；
- 高价值流失分析属于个案级描述，不能推广为群体稳定规律；
- 合法高金额订单应保留，高金额本身不等于异常；
- delivered 有效订单不能因为缺少正支付 GMV 而被删除；
- 跨模块一对多数据必须先处理到订单级再进行 JOIN，避免订单数和 GMV 重复放大。
""",

        """## 13. 正式产物与复现

### 13.1 核心数据产物

Member 3 正式数据产物位于：

`outputs/data/03_customer_analysis/`

核心文件包括：

- `churn_user_detail.csv`
- `churn_comparison.csv`
- `churn_related_features.csv`
- `churn_state_structure.csv`
- `churn_payment_structure.csv`
- `churn_first_purchase_month.csv`
- `member3_user_value_base.csv`
- `member3_order_payment_base.csv`
- `member3_order_experience_base.csv`
- `member3_lifecycle_bridge.csv`
- `high_value_user_integrated_profile.csv`
- `high_value_churn_user_integrated_profile.csv`

### 13.2 正式图表

正式高价值图表位于：

`visualizations/customer/high_value/`

包括：

- `high_value_consumption_comparison.png`
- `high_value_payment_comparison.png`
- `high_value_experience_comparison.png`

### 13.3 关键脚本

核心分析与复现脚本位于：

`src/analysis/customer_analysis/`

包括流失分析、正式用户基础表、支付基础表、体验基础表、
生命周期 bridge、高价值综合画像、正式可视化以及本报告生成脚本。

本报告由：

`member3_final_report.py`

根据正式 CSV 动态生成。

### 13.4 跨成员输入

RFM 正式输入继续使用统一口径下的 `rfm_customer_detail.csv`。

生命周期交叉不直接采用观察窗口不同的原 Member 2
`customer_lifecycle_segment.csv`，而使用重新按 Member 3 正式截止日构建的
`member3_lifecycle_bridge.csv`。

原 Member 1 和 Member 2 报告保持不修改。
""",

        """## 14. 结语

Member 3 已完成流失用户分析、重要价值用户四类画像、
RFM × Churn × Lifecycle 交叉以及高价值流失用户综合个案分析。

最终结果应被理解为统一观察窗口下的正式描述性分析。
其中高价值用户和高价值流失用户样本尤其有限，
因此报告坚持以数据事实、口径一致性和解释边界为优先，
不通过调整阈值扩大样本，也不将观察性差异包装为因果结论。
""",
    ]

    return sections

def main():
    """Build, write, and validate the final Member 3 report."""

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Preserve the pre-final report only once.
    if REPORT_PATH.exists() and not BACKUP_PATH.exists():
        BACKUP_PATH.write_bytes(REPORT_PATH.read_bytes())
        print(f"Backup created: {BACKUP_PATH}")
    elif BACKUP_PATH.exists():
        print(f"Backup already exists: {BACKUP_PATH}")
    else:
        print("No pre-final report found; backup skipped.")

    data = load_inputs()
    validate_inputs(data)

    report = generate_report(data)
    REPORT_PATH.write_text(report, encoding="utf-8")

    if not REPORT_PATH.exists():
        raise AssertionError("Final report was not created.")

    report_text = REPORT_PATH.read_text(encoding="utf-8")
    report_lines = report_text.splitlines()

    required_sections = [
        "# 阶段三 Member 3：流失用户分析与高价值用户画像报告",
        "## 1. 分析目标",
        "## 2. 数据范围与统一口径",
        "### 2.1 数据范围",
        "### 2.2 流失规则",
        "### 2.3 重要价值用户规则",
        "### 2.4 生命周期交叉口径",
        "## 3. 流失用户分析",
        "### 3.1 总体流失规模",
        "### 3.2 流失与未流失用户核心指标",
        "### 3.3 流失相关特征",
        "### 3.4 地域结构",
        "### 3.5 支付方式结构",
        "### 3.6 首购时间解释",
        "## 4. 重要价值用户总体情况",
        "## 5. 重要价值用户地域画像",
        "### 5.1 州级分布",
        "### 5.2 用户所在城市",
        "## 6. 重要价值用户支付画像",
        "### 6.1 主支付方式订单占比",
        "### 6.2 实际支付方式 GMV 占比",
        "## 7. 重要价值用户消费画像",
        "## 8. 评论与配送体验画像",
        "## 9. RFM × Churn × Lifecycle 交叉",
        "## 10. 高价值流失用户综合个案",
        "## 11. 核心结论",
        "## 12. 数据限制与解释边界",
        "## 13. 正式产物与复现",
        "### 13.1 核心数据产物",
        "### 13.2 正式图表",
        "### 13.3 关键脚本",
        "### 13.4 跨成员输入",
        "## 14. 结语",
    ]

    missing_sections = [
        section for section in required_sections
        if section not in report_text
    ]
    if missing_sections:
        raise AssertionError(
            "Missing required sections: " + ", ".join(missing_sections)
        )

    if len(report_lines) <= 37:
        raise AssertionError(
            f"Final report is unexpectedly short: {len(report_lines)} lines."
        )

    if report_text.count("```") % 2 != 0:
        raise AssertionError("Unbalanced Markdown code fences.")

    required_figure_refs = [
        "![High-value payment comparison](../../visualizations/customer/high_value/high_value_payment_comparison.png)",
        "![High-value consumption comparison](../../visualizations/customer/high_value/high_value_consumption_comparison.png)",
        "![High-value experience comparison](../../visualizations/customer/high_value/high_value_experience_comparison.png)",
    ]

    missing_figures = [
        ref for ref in required_figure_refs
        if ref not in report_text
    ]
    if missing_figures:
        raise AssertionError(
            "Missing Markdown figure references: " + ", ".join(missing_figures)
        )

    print(f"Final report: {REPORT_PATH}")
    print(f"Report lines: {len(report_lines)}")
    print(f"Report chars: {len(report_text)}")
    print("Required sections: PASS")
    print("Markdown fence balance: PASS")
    print("Three formal figure references: PASS")
    print("Final report validation: PASS")
    print("FINAL RESULT: PASS")


if __name__ == "__main__":
    main()
