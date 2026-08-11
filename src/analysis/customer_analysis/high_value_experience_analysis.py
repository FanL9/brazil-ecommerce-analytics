from pathlib import Path

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# High-value user review / delivery experience analysis
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# Review:
# - representative review already selected at order level
# - legal score: 1..5
# - low-rating order: representative_review_score == 1
#
# Delivery:
# - only valid delivery duration enters average delivery time
# - delay rate denominator uses orders eligible for delay metric
#
# Observation cutoff:
# 2018-07-31
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "03_customer_analysis"
)

USER_BASE_PATH = (
    DATA_DIR
    / "member3_user_value_base.csv"
)

EXPERIENCE_BASE_PATH = (
    DATA_DIR
    / "member3_order_experience_base.csv"
)

OUTPUT_PATH = (
    DATA_DIR
    / "high_value_user_experience_profile.csv"
)


def safe_divide(numerator, denominator):
    if denominator == 0:
        return None
    return numerator / denominator


def build_summary(df, group_name):

    # --------------------------------------------------------
    # Review sample
    # --------------------------------------------------------
    reviewed = df[
        df["has_valid_review"] == 1
    ].copy()

    reviewed_orders = reviewed[
        "order_id"
    ].nunique()

    low_score_orders = (
        reviewed[
            "representative_review_score"
        ].eq(1)
        .sum()
    )

    positive_review_orders = (
        reviewed[
            "representative_review_score"
        ].ge(4)
        .sum()
    )

    # --------------------------------------------------------
    # Delivery sample
    # --------------------------------------------------------
    delivery = df[
        df["has_valid_delivery"] == 1
    ].copy()

    delivery_orders = delivery[
        "order_id"
    ].nunique()

    # --------------------------------------------------------
    # Delay sample
    # --------------------------------------------------------
    delay = df[
        df["has_valid_delay_measure"] == 1
    ].copy()

    delay_orders = delay[
        "order_id"
    ].nunique()

    delayed_orders = int(
        delay["is_delayed"].sum()
    )

    return {
        "group": group_name,

        "users":
            df["customer_unique_id"].nunique(),

        "orders":
            df["order_id"].nunique(),

        # Review
        "reviewed_orders":
            reviewed_orders,

        "excluded_review_orders":
            df["order_id"].nunique()
            - reviewed_orders,

        "review_coverage":
            safe_divide(
                reviewed_orders,
                df["order_id"].nunique(),
            ),

        "average_review_score":
            reviewed[
                "representative_review_score"
            ].mean(),

        "low_score_definition":
            "representative_review_score == 1",

        "low_score_orders":
            int(low_score_orders),

        "low_score_order_share":
            safe_divide(
                low_score_orders,
                reviewed_orders,
            ),

        "positive_review_orders":
            int(positive_review_orders),

        "positive_review_rate":
            safe_divide(
                positive_review_orders,
                reviewed_orders,
            ),

        # Delivery
        "delivery_orders":
            delivery_orders,

        "excluded_delivery_orders":
            df["order_id"].nunique()
            - delivery_orders,

        "average_delivery_days":
            delivery["delivery_days"].mean(),

        # Delay
        "delay_eligible_orders":
            delay_orders,

        "delayed_orders":
            delayed_orders,

        "delay_rate":
            safe_divide(
                delayed_orders,
                delay_orders,
            ),
    }


def main():

    print("=" * 76)
    print("HIGH-VALUE USER REVIEW / DELIVERY EXPERIENCE ANALYSIS")
    print("=" * 76)

    # --------------------------------------------------------
    # 1. Load inputs
    # --------------------------------------------------------
    users = pd.read_csv(
        USER_BASE_PATH
    )

    experience = pd.read_csv(
        EXPERIENCE_BASE_PATH
    )

    print("\n[1] INPUT")
    print(f"User-base rows: {len(users):,}")
    print(
        f"Experience-base rows: "
        f"{len(experience):,}"
    )

    if len(users) != 87214:
        raise ValueError(
            "User base must contain 87,214 users."
        )

    if len(experience) != 90127:
        raise ValueError(
            "Experience base must contain 90,127 orders."
        )

    if users["customer_unique_id"].duplicated().any():
        raise ValueError(
            "User base contains duplicate users."
        )

    if experience["order_id"].duplicated().any():
        raise ValueError(
            "Experience base contains duplicate orders."
        )

    print("Input validation: PASS")

    # --------------------------------------------------------
    # 2. Attach high-value flags
    # --------------------------------------------------------
    user_flags = users[
        [
            "customer_unique_id",
            "frequency",
            "monetary",
            "is_high_value_user",
            "is_high_value_churn_user",
        ]
    ].copy()

    orders = experience.merge(
        user_flags,
        on="customer_unique_id",
        how="left",
        validate="many_to_one",
    )

    missing_flags = (
        orders["is_high_value_user"]
        .isna()
        .sum()
    )

    print("\n[2] USER MATCHING")
    print(
        f"Orders missing user flags: "
        f"{missing_flags:,}"
    )

    if missing_flags != 0:
        raise ValueError(
            "Some orders failed to match user base."
        )

    print("User matching: PASS")

    # --------------------------------------------------------
    # 3. High-value population reconciliation
    # --------------------------------------------------------
    high_value_users = users[
        users["is_high_value_user"] == 1
    ].copy()

    high_value_orders = orders[
        orders["is_high_value_user"] == 1
    ].copy()

    expected_orders = int(
        high_value_users["frequency"].sum()
    )

    actual_orders = high_value_orders[
        "order_id"
    ].nunique()

    print("\n[3] HIGH-VALUE RECONCILIATION")
    print(
        f"High-value users: "
        f"{len(high_value_users):,}"
    )
    print(
        f"Expected orders from RFM Frequency: "
        f"{expected_orders:,}"
    )
    print(
        f"Actual experience orders: "
        f"{actual_orders:,}"
    )

    if expected_orders != actual_orders:
        raise ValueError(
            "High-value order count does not reconcile."
        )

    print("High-value reconciliation: PASS")

    # --------------------------------------------------------
    # 4. Build comparison
    # --------------------------------------------------------
    overall = build_summary(
        orders,
        "all_users",
    )

    high_value = build_summary(
        high_value_orders,
        "high_value_users",
    )

    result = pd.DataFrame(
        [
            overall,
            high_value,
        ]
    )

    print("\n[4] REVIEW / DELIVERY EXPERIENCE")

    display = result.copy()

    for col in [
        "review_coverage",
        "low_score_order_share",
        "positive_review_rate",
        "delay_rate",
    ]:
        display[col] = (
            display[col]
            .map(
                lambda x:
                "NULL"
                if pd.isna(x)
                else f"{x:.2%}"
            )
        )

    print(
        display.to_string(index=False)
    )

    # --------------------------------------------------------
    # 5. High-value review score distribution
    # --------------------------------------------------------
    print("\n[5] HIGH-VALUE REVIEW SCORE DISTRIBUTION")

    hv_reviewed = high_value_orders[
        high_value_orders[
            "has_valid_review"
        ] == 1
    ]

    print(
        hv_reviewed[
            "representative_review_score"
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # --------------------------------------------------------
    # 6. High-value churn user detail
    # --------------------------------------------------------
    print("\n[6] HIGH-VALUE CHURN USER EXPERIENCE")

    hv_churn = high_value_orders[
        high_value_orders[
            "is_high_value_churn_user"
        ] == 1
    ].copy()

    print(
        f"High-value churn users: "
        f"{hv_churn['customer_unique_id'].nunique():,}"
    )

    print(
        f"High-value churn orders: "
        f"{hv_churn['order_id'].nunique():,}"
    )

    hv_churn_reviewed = hv_churn[
        hv_churn["has_valid_review"] == 1
    ]

    hv_churn_delivery = hv_churn[
        hv_churn["has_valid_delivery"] == 1
    ]

    hv_churn_delay = hv_churn[
        hv_churn["has_valid_delay_measure"] == 1
    ]

    print(
        "Average review score: ",
        "NULL"
        if hv_churn_reviewed.empty
        else f"{hv_churn_reviewed['representative_review_score'].mean():.4f}",
    )

    print(
        "Average delivery days: ",
        "NULL"
        if hv_churn_delivery.empty
        else f"{hv_churn_delivery['delivery_days'].mean():.4f}",
    )

    print(
        "Delay rate: ",
        "NULL"
        if hv_churn_delay.empty
        else f"{hv_churn_delay['is_delayed'].mean():.2%}",
    )

    # --------------------------------------------------------
    # 7. Validation
    # --------------------------------------------------------
    print("\n[7] VALIDATION")

    overall_review_count = int(
        orders["has_valid_review"].sum()
    )

    overall_delivery_count = int(
        orders["has_valid_delivery"].sum()
    )

    overall_delay_count = int(
        orders["has_valid_delay_measure"].sum()
    )

    print(
        f"Valid review orders recovered: "
        f"{overall_review_count:,}"
    )

    print(
        f"Valid delivery orders recovered: "
        f"{overall_delivery_count:,}"
    )

    print(
        f"Delay-eligible orders recovered: "
        f"{overall_delay_count:,}"
    )

    if overall_review_count != 89502:
        raise ValueError(
            "Expected 89,502 valid review orders."
        )

    if overall_delivery_count != 90119:
        raise ValueError(
            "Expected 90,119 valid delivery orders."
        )

    if overall_delay_count != 90119:
        raise ValueError(
            "Expected 90,119 delay-eligible orders."
        )

    print("Experience denominator reconciliation: PASS")

    # --------------------------------------------------------
    # 8. Save
    # --------------------------------------------------------
    result.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n[8] OUTPUT")
    print(f"Saved: {OUTPUT_PATH}")
    print(f"Rows written: {len(result):,}")

    print("\n" + "=" * 76)
    print("FINAL RESULT: PASS")
    print(
        "High-value review / delivery experience "
        "profile successfully created."
    )
    print(
        "IMPORTANT: high-value population = 4 users; "
        "results are descriptive only."
    )
    print("=" * 76)


if __name__ == "__main__":
    main()
