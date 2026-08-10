from pathlib import Path
import math
import sqlite3

import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# Configuration
# ============================================================

DB_PATH = Path("database/brazil_ecommerce.db")

DATA_DIR = Path("outputs/data/03_customer_analysis")
FIGURE_DIR = Path("visualizations/customer")

DATA_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Helper
# ============================================================

def cramers_v(table: pd.DataFrame) -> float:
    """Calculate Cramer's V from a contingency table."""

    values = table.to_numpy(dtype=float)

    n = values.sum()

    if n == 0:
        return float("nan")

    row_totals = values.sum(axis=1)
    col_totals = values.sum(axis=0)

    expected = (
        row_totals[:, None]
        * col_totals[None, :]
        / n
    )

    mask = expected > 0

    chi2 = (
        ((values - expected) ** 2 / expected)[mask]
    ).sum()

    k = min(
        values.shape[0] - 1,
        values.shape[1] - 1
    )

    if k <= 0:
        return float("nan")

    return math.sqrt(
        chi2 / (n * k)
    )


# ============================================================
# 1. Build official Member 3 churn user detail
# ============================================================

USER_DETAIL_SQL = """
WITH observation_orders AS (
    SELECT
        customer_unique_id,
        customer_id,
        order_id,
        order_purchase_timestamp,
        customer_state,
        customer_city,
        order_gmv,
        is_paid_order

    FROM customer_order_base

    WHERE DATETIME(order_purchase_timestamp) IS NOT NULL
      AND DATETIME(order_purchase_timestamp)
          < DATETIME('2018-08-01 00:00:00')
),

user_summary AS (
    SELECT
        customer_unique_id,

        MIN(order_purchase_timestamp)
            AS first_purchase_timestamp,

        MAX(order_purchase_timestamp)
            AS last_purchase_timestamp,

        COUNT(DISTINCT order_id)
            AS valid_order_count,

        SUM(is_paid_order)
            AS paid_order_count,

        SUM(order_gmv)
            AS lifetime_gmv

    FROM observation_orders

    GROUP BY customer_unique_id
),

user_metrics AS (
    SELECT
        *,

        CASE
            WHEN paid_order_count > 0
            THEN lifetime_gmv * 1.0
                 / NULLIF(paid_order_count, 0)
            ELSE NULL
        END AS average_order_value,

        CAST(
            JULIANDAY(DATE('2018-07-31'))
            - JULIANDAY(DATE(last_purchase_timestamp))
            AS INTEGER
        ) AS recency_days,

        CAST(
            JULIANDAY(DATE(last_purchase_timestamp))
            - JULIANDAY(DATE(first_purchase_timestamp))
            AS INTEGER
        ) AS customer_lifecycle_days

    FROM user_summary
),

user_churn AS (
    SELECT
        *,

        CASE
            WHEN valid_order_count >= 2
            THEN 1
            ELSE 0
        END AS is_repeat_customer,

        CASE
            WHEN recency_days > 90
            THEN 1
            ELSE 0
        END AS churn_flag,

        DATE('2018-07-31')
            AS observation_date

    FROM user_metrics
),

order_experience AS (
    SELECT
        o.*,

        CASE
            WHEN r.review_score BETWEEN 1 AND 5
            THEN r.review_score
            ELSE NULL
        END AS valid_review_score,

        CASE
            WHEN oc.order_delivered_customer_date IS NULL
              OR DATETIME(
                    oc.order_delivered_customer_date
                 ) IS NULL
              OR DATETIME(
                    o.order_purchase_timestamp
                 ) IS NULL
              OR DATETIME(
                    oc.order_delivered_customer_date
                 ) < DATETIME(
                    o.order_purchase_timestamp
                 )
            THEN NULL

            ELSE
                JULIANDAY(
                    oc.order_delivered_customer_date
                )
                - JULIANDAY(
                    o.order_purchase_timestamp
                )
        END AS delivery_days,

        CASE
            WHEN oc.order_delivered_customer_date IS NULL
              OR oc.order_estimated_delivery_date IS NULL
              OR DATETIME(
                    oc.order_delivered_customer_date
                 ) IS NULL
              OR DATETIME(
                    oc.order_estimated_delivery_date
                 ) IS NULL
              OR DATETIME(
                    o.order_purchase_timestamp
                 ) IS NULL
              OR DATETIME(
                    oc.order_delivered_customer_date
                 ) < DATETIME(
                    o.order_purchase_timestamp
                 )
            THEN NULL

            WHEN DATETIME(
                    oc.order_delivered_customer_date
                 )
                 >
                 DATETIME(
                    oc.order_estimated_delivery_date
                 )
            THEN 1

            ELSE 0
        END AS is_delayed

    FROM observation_orders AS o

    LEFT JOIN vw_orders_clean AS oc
        ON o.order_id = oc.order_id

    LEFT JOIN vw_order_reviews_order_level AS r
        ON o.order_id = r.order_id
),

order_ranked AS (
    SELECT
        *,

        ROW_NUMBER() OVER (
            PARTITION BY customer_unique_id
            ORDER BY
                DATETIME(
                    order_purchase_timestamp
                ) DESC,
                order_id DESC,
                customer_id DESC
        ) AS latest_order_rank

    FROM order_experience
),

user_experience AS (
    SELECT
        customer_unique_id,

        MAX(
            CASE
                WHEN latest_order_rank = 1
                THEN order_gmv
            END
        ) AS latest_order_amount,

        MAX(
            CASE
                WHEN latest_order_rank = 1
                THEN customer_state
            END
        ) AS customer_state,

        MAX(
            CASE
                WHEN latest_order_rank = 1
                THEN customer_city
            END
        ) AS customer_city,

        AVG(valid_review_score)
            AS avg_review_score,

        AVG(delivery_days)
            AS avg_delivery_days,

        COUNT(is_delayed)
            AS delay_eligible_orders,

        SUM(
            CASE
                WHEN is_delayed = 1
                THEN 1
                ELSE 0
            END
        ) AS delayed_orders,

        CASE
            WHEN COUNT(is_delayed) > 0
            THEN
                100.0
                * SUM(
                    CASE
                        WHEN is_delayed = 1
                        THEN 1
                        ELSE 0
                    END
                )
                / NULLIF(
                    COUNT(is_delayed),
                    0
                )
            ELSE NULL
        END AS delay_rate_pct

    FROM order_ranked

    GROUP BY customer_unique_id
)

SELECT
    uc.customer_unique_id,
    uc.first_purchase_timestamp,
    uc.last_purchase_timestamp,
    uc.valid_order_count,
    uc.paid_order_count,

    ROUND(
        uc.lifetime_gmv,
        2
    ) AS lifetime_gmv,

    ROUND(
        uc.average_order_value,
        2
    ) AS average_order_value,

    uc.recency_days,
    uc.customer_lifecycle_days,
    uc.is_repeat_customer,
    uc.churn_flag,
    uc.observation_date,

    ROUND(
        ue.latest_order_amount,
        2
    ) AS latest_order_amount,

    ue.customer_state,
    ue.customer_city,

    ROUND(
        ue.avg_review_score,
        3
    ) AS avg_review_score,

    ROUND(
        ue.avg_delivery_days,
        2
    ) AS avg_delivery_days,

    ue.delay_eligible_orders,
    ue.delayed_orders,

    ROUND(
        ue.delay_rate_pct,
        2
    ) AS delay_rate_pct

FROM user_churn AS uc

LEFT JOIN user_experience AS ue
    ON uc.customer_unique_id
     = ue.customer_unique_id

ORDER BY uc.customer_unique_id;
"""


conn = sqlite3.connect(DB_PATH)

try:
    user_detail = pd.read_sql_query(
        USER_DETAIL_SQL,
        conn
    )

finally:
    conn.close()


# ============================================================
# Validation
# ============================================================

print("=== User Detail Validation ===")

print(
    "Rows:",
    len(user_detail)
)

print(
    "Unique users:",
    user_detail[
        "customer_unique_id"
    ].nunique()
)

print(
    "Churned users:",
    int(user_detail["churn_flag"].sum())
)

print(
    "Non-churned users:",
    int(
        (user_detail["churn_flag"] == 0).sum()
    )
)

assert len(user_detail) == 87214

assert (
    user_detail["customer_unique_id"].nunique()
    == 87214
)

assert (
    int(user_detail["churn_flag"].sum())
    == 68686
)

assert (
    int(
        (user_detail["churn_flag"] == 0).sum()
    )
    == 18528
)

assert (
    user_detail["recency_days"].min()
    >= 0
)

assert (
    user_detail[
        "customer_lifecycle_days"
    ].min()
    >= 0
)

assert (
    user_detail["observation_date"]
    .nunique()
    == 1
)

assert (
    user_detail["observation_date"]
    .iloc[0]
    == "2018-07-31"
)

print("User detail checks: PASS")


# ============================================================
# Export user detail
# ============================================================

USER_DETAIL_PATH = (
    DATA_DIR / "churn_user_detail.csv"
)

user_detail.to_csv(
    USER_DETAIL_PATH,
    index=False,
    encoding="utf-8-sig"
)

print(
    f"[CSV] {USER_DETAIL_PATH} "
    f"| rows={len(user_detail)}"
)


# ============================================================
# 2. Read formal results generated by churn_analysis.py
# ============================================================

comparison = pd.read_csv(
    DATA_DIR / "churn_comparison.csv"
)

payment = pd.read_csv(
    DATA_DIR / "churn_payment_structure.csv"
)

state = pd.read_csv(
    DATA_DIR / "churn_state_structure.csv"
)

weekday = pd.read_csv(
    DATA_DIR / "churn_weekday_weekend.csv"
)

first_purchase = pd.read_csv(
    DATA_DIR / "churn_first_purchase_month.csv"
)


# ============================================================
# Core metric helper
# ============================================================

comparison_indexed = (
    comparison
    .set_index("churn_status")
)

churned = comparison_indexed.loc["Churned"]
non_churned = comparison_indexed.loc["Non-churned"]


# ============================================================
# 3. Association strength
# ============================================================

payment_table = (
    payment
    .pivot(
        index="churn_status",
        columns="primary_payment_type",
        values="order_count"
    )
    .fillna(0)
)

payment_v = cramers_v(
    payment_table
)


state_table = pd.DataFrame(
    [
        state["churned_users"].values,
        state["non_churned_users"].values
    ],
    index=[
        "Churned",
        "Non-churned"
    ],
    columns=state["customer_state"]
)

state_v = cramers_v(
    state_table
)


weekday_table = (
    weekday
    .pivot(
        index="churn_status",
        columns="day_type",
        values="order_count"
    )
    .fillna(0)
)

weekday_v = cramers_v(
    weekday_table
)


# ============================================================
# 4. First-purchase right-censoring evidence
# ============================================================

may_2018 = first_purchase[
    first_purchase["first_purchase_month"]
    == "2018-05"
]

june_2018 = first_purchase[
    first_purchase["first_purchase_month"]
    == "2018-06"
]

july_2018 = first_purchase[
    first_purchase["first_purchase_month"]
    == "2018-07"
]


# ============================================================
# 5. Final related-feature summary
# ============================================================

summary_rows = [
    {
        "feature": "Spend per User",
        "feature_type": "Continuous",
        "churned_value": churned["spend_per_user"],
        "non_churned_value": non_churned["spend_per_user"],
        "difference": (
            churned["spend_per_user"]
            - non_churned["spend_per_user"]
        ),
        "association_metric": "",
        "association_value": "",
        "interpretation":
            "Churned users show lower spend per user.",
        "limitation":
            "Descriptive difference only; no causal claim."
    },
    {
        "feature": "Average Purchase Frequency",
        "feature_type": "Continuous",
        "churned_value":
            churned["avg_purchase_frequency"],
        "non_churned_value":
            non_churned["avg_purchase_frequency"],
        "difference":
            churned["avg_purchase_frequency"]
            - non_churned["avg_purchase_frequency"],
        "association_metric": "",
        "association_value": "",
        "interpretation":
            "Purchase frequency is slightly lower among churned users.",
        "limitation":
            "Observed difference is small."
    },
    {
        "feature": "Repeat Rate",
        "feature_type": "Percentage",
        "churned_value":
            churned["repeat_rate_pct"],
        "non_churned_value":
            non_churned["repeat_rate_pct"],
        "difference":
            churned["repeat_rate_pct"]
            - non_churned["repeat_rate_pct"],
        "association_metric": "",
        "association_value": "",
        "interpretation":
            "Churned users have a lower repeat-purchase rate.",
        "limitation":
            "Descriptive association only."
    },
    {
        "feature": "Average Lifecycle Days",
        "feature_type": "Continuous",
        "churned_value":
            churned["avg_lifecycle_days"],
        "non_churned_value":
            non_churned["avg_lifecycle_days"],
        "difference":
            churned["avg_lifecycle_days"]
            - non_churned["avg_lifecycle_days"],
        "association_metric": "",
        "association_value": "",
        "interpretation":
            "Churned users show shorter observed purchase lifecycles.",
        "limitation":
            "Lifecycle is strongly related to sparse repeat purchasing."
    },
    {
        "feature": "Average Order Value",
        "feature_type": "BRL",
        "churned_value":
            churned["average_order_value"],
        "non_churned_value":
            non_churned["average_order_value"],
        "difference":
            churned["average_order_value"]
            - non_churned["average_order_value"],
        "association_metric": "",
        "association_value": "",
        "interpretation":
            "Churned users have lower AOV.",
        "limitation":
            "Descriptive difference only."
    },
    {
        "feature": "Latest Order Amount",
        "feature_type": "BRL",
        "churned_value":
            churned["avg_latest_order_amount"],
        "non_churned_value":
            non_churned["avg_latest_order_amount"],
        "difference":
            churned["avg_latest_order_amount"]
            - non_churned["avg_latest_order_amount"],
        "association_metric": "",
        "association_value": "",
        "interpretation":
            "The latest order amount is lower among churned users.",
        "limitation":
            "Descriptive difference only."
    },
    {
        "feature": "Average Review Score",
        "feature_type": "Score 1-5",
        "churned_value":
            churned["avg_review_score"],
        "non_churned_value":
            non_churned["avg_review_score"],
        "difference":
            churned["avg_review_score"]
            - non_churned["avg_review_score"],
        "association_metric": "",
        "association_value": "",
        "interpretation":
            "Churned users have lower average review scores.",
        "limitation":
            "Only orders with valid representative review scores are included."
    },
    {
        "feature": "Average Delivery Days",
        "feature_type": "Days",
        "churned_value":
            churned["avg_delivery_days"],
        "non_churned_value":
            non_churned["avg_delivery_days"],
        "difference":
            churned["avg_delivery_days"]
            - non_churned["avg_delivery_days"],
        "association_metric": "",
        "association_value": "",
        "interpretation":
            "Churned users experienced longer average delivery times.",
        "limitation":
            "Only orders with valid delivery timestamps are included."
    },
    {
        "feature": "Delay Rate",
        "feature_type": "Percentage",
        "churned_value":
            churned["delay_rate_pct"],
        "non_churned_value":
            non_churned["delay_rate_pct"],
        "difference":
            churned["delay_rate_pct"]
            - non_churned["delay_rate_pct"],
        "association_metric": "",
        "association_value": "",
        "interpretation":
            "Churned users show a higher delayed-delivery rate.",
        "limitation":
            "Association does not establish that delay causes churn."
    },
    {
        "feature": "Primary Payment Type",
        "feature_type": "Categorical",
        "churned_value": "",
        "non_churned_value": "",
        "difference": "",
        "association_metric": "Cramer's V",
        "association_value":
            round(payment_v, 4),
        "interpretation":
            "Payment structure differs slightly, but overall association is weak.",
        "limitation":
            "Mixed-payment orders use the unified primary-payment rule."
    },
    {
        "feature": "Customer State",
        "feature_type": "Categorical",
        "churned_value": "",
        "non_churned_value": "",
        "difference": "",
        "association_metric": "Cramer's V",
        "association_value":
            round(state_v, 4),
        "interpretation":
            "Some states differ in churn rate, but overall state association is weak.",
        "limitation":
            "Large absolute churn counts may simply reflect market size."
    },
    {
        "feature": "Weekday / Weekend",
        "feature_type": "Categorical",
        "churned_value": "",
        "non_churned_value": "",
        "difference": "",
        "association_metric": "Cramer's V",
        "association_value":
            round(weekday_v, 4),
        "interpretation":
            "Weekday/weekend purchase structure has almost no association with churn.",
        "limitation":
            "Calendar-day counts include zero-order dates."
    },
    {
        "feature": "First Purchase Month",
        "feature_type": "Time Structure",
        "churned_value": "",
        "non_churned_value": "",
        "difference": "",
        "association_metric":
            "Observation-window check",
        "association_value": "",
        "interpretation":
            "Recent cohorts cannot be directly compared with older cohorts on churn rate.",
        "limitation":
            (
                "2018-05 has only "
                f"{int(may_2018['users_with_full_90d_opportunity'].iloc[0])}"
                "/"
                f"{int(may_2018['cohort_users'].iloc[0])}"
                " users with full 90-day opportunity; "
                "2018-06 and 2018-07 have none."
            )
    }
]


feature_summary = pd.DataFrame(
    summary_rows
)

FEATURE_PATH = (
    DATA_DIR / "churn_related_features.csv"
)

feature_summary.to_csv(
    FEATURE_PATH,
    index=False,
    encoding="utf-8-sig"
)

print(
    f"[CSV] {FEATURE_PATH} "
    f"| rows={len(feature_summary)}"
)


# ============================================================
# 6. Association-strength visualization
# ============================================================

association = pd.Series(
    {
        "Primary Payment Type": payment_v,
        "Customer State": state_v,
        "Weekday / Weekend": weekday_v
    }
)

fig, ax = plt.subplots()

association.plot(
    kind="bar",
    ax=ax
)

ax.set_title(
    "Association Strength with Churn Status"
)

ax.set_xlabel("")
ax.set_ylabel("Cramer's V")

ax.tick_params(
    axis="x",
    rotation=0
)

fig.tight_layout()

FIGURE_PATH = (
    FIGURE_DIR
    / "churn_feature_association_strength.png"
)

fig.savefig(
    FIGURE_PATH,
    dpi=180,
    bbox_inches="tight"
)

plt.close(fig)

print(
    f"[FIG] {FIGURE_PATH}"
)


# ============================================================
# Final output
# ============================================================

print("\n=== Association Strength ===")

print(
    "Payment Cramer's V:",
    round(payment_v, 4)
)

print(
    "State Cramer's V:",
    round(state_v, 4)
)

print(
    "Weekday/Weekend Cramer's V:",
    round(weekday_v, 4)
)

print(
    "\nMember 3 churn finalization: PASS"
)
