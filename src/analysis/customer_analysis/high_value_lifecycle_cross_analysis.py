from pathlib import Path

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# RFM x Churn x Lifecycle cross analysis
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# High-value user:
# R >= 4, F >= 4, M >= 4
#
# Churn:
# recency_days > 90
#
# Lifecycle:
# use member3_lifecycle_bridge.csv,
# rebuilt under official 2018-07-31 cutoff.
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

LIFECYCLE_PATH = (
    DATA_DIR
    / "member3_lifecycle_bridge.csv"
)

DETAIL_OUTPUT = (
    DATA_DIR
    / "high_value_user_lifecycle_cross.csv"
)

SUMMARY_OUTPUT = (
    DATA_DIR
    / "high_value_user_lifecycle_summary.csv"
)


def main():

    print("=" * 76)
    print("RFM x CHURN x LIFECYCLE CROSS ANALYSIS")
    print("=" * 76)

    # --------------------------------------------------------
    # 1. Load official inputs
    # --------------------------------------------------------
    users = pd.read_csv(
        USER_BASE_PATH
    )

    lifecycle = pd.read_csv(
        LIFECYCLE_PATH
    )

    print("\n[1] INPUT")
    print(f"User base: {len(users):,}")
    print(f"Lifecycle bridge: {len(lifecycle):,}")

    if len(users) != 87214:
        raise ValueError(
            "User base must contain 87,214 users."
        )

    if len(lifecycle) != 87214:
        raise ValueError(
            "Lifecycle bridge must contain 87,214 users."
        )

    if users["customer_unique_id"].duplicated().any():
        raise ValueError(
            "User base contains duplicate users."
        )

    if lifecycle["customer_unique_id"].duplicated().any():
        raise ValueError(
            "Lifecycle bridge contains duplicate users."
        )

    print("Input validation: PASS")

    # --------------------------------------------------------
    # 2. Merge
    # --------------------------------------------------------
    lifecycle_fields = lifecycle[
        [
            "customer_unique_id",
            "first_purchase_date",
            "last_purchase_date",
            "valid_order_count",
            "lifetime_gmv",
            "customer_lifecycle_days",
            "recency_days",
            "lifecycle_stage",
            "observation_date",
        ]
    ].rename(
        columns={
            "valid_order_count":
                "lifecycle_valid_order_count",
            "lifetime_gmv":
                "lifecycle_gmv",
            "customer_lifecycle_days":
                "lifecycle_days",
            "recency_days":
                "lifecycle_recency_days",
            "observation_date":
                "lifecycle_observation_date",
        }
    )

    merged = users.merge(
        lifecycle_fields,
        on="customer_unique_id",
        how="left",
        validate="one_to_one",
    )

    missing = merged[
        "lifecycle_stage"
    ].isna().sum()

    print("\n[2] MERGE")
    print(f"Rows: {len(merged):,}")
    print(f"Missing lifecycle matches: {missing:,}")

    if missing != 0:
        raise ValueError(
            "Some users failed to match lifecycle bridge."
        )

    print("Lifecycle matching: PASS")

    # --------------------------------------------------------
    # 3. Cross-module consistency
    # --------------------------------------------------------
    frequency_match = (
        merged["frequency"]
        == merged["lifecycle_valid_order_count"]
    ).all()

    monetary_match = (
        (
            merged["monetary"]
            - merged["lifecycle_gmv"]
        ).abs() <= 0.01
    ).all()

    recency_match = (
        merged["recency_days"]
        == merged["lifecycle_recency_days"]
    ).all()

    churn_dormant_match = (
        (merged["churn_flag"].astype(int) == 1)
        == (
            merged["lifecycle_stage"]
            == "Dormant Customer"
        )
    ).all()

    print("\n[3] CROSS-MODULE CONSISTENCY")
    print(
        "Frequency vs lifecycle order count:",
        "PASS" if frequency_match else "FAIL",
    )
    print(
        "Monetary vs lifecycle GMV:",
        "PASS" if monetary_match else "FAIL",
    )
    print(
        "Recency:",
        "PASS" if recency_match else "FAIL",
    )
    print(
        "Churn == Dormant Customer:",
        "PASS" if churn_dormant_match else "FAIL",
    )

    if not all(
        [
            frequency_match,
            monetary_match,
            recency_match,
            churn_dormant_match,
        ]
    ):
        raise ValueError(
            "Cross-module metrics do not reconcile."
        )

    # --------------------------------------------------------
    # 4. High-value users
    # --------------------------------------------------------
    high_value = merged[
        merged["is_high_value_user"] == 1
    ].copy()

    print("\n[4] HIGH-VALUE POPULATION")
    print(f"High-value users: {len(high_value):,}")
    print(
        "High-value churn users:",
        int(
            high_value[
                "is_high_value_churn_user"
            ].sum()
        ),
    )

    if len(high_value) != 4:
        raise ValueError(
            "Expected 4 high-value users."
        )

    if (
        high_value[
            "is_high_value_churn_user"
        ].sum()
        != 1
    ):
        raise ValueError(
            "Expected 1 high-value churn user."
        )

    # --------------------------------------------------------
    # 5. Lifecycle distribution
    # --------------------------------------------------------
    summary = (
        high_value.groupby(
            "lifecycle_stage",
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
            total_orders=(
                "frequency",
                "sum",
            ),
            total_gmv=(
                "monetary",
                "sum",
            ),
            avg_recency_days=(
                "recency_days",
                "mean",
            ),
            avg_lifecycle_days=(
                "lifecycle_days",
                "mean",
            ),
        )
    )

    summary["high_value_user_share"] = (
        summary["high_value_users"]
        / len(high_value)
    )

    print("\n[5] HIGH-VALUE LIFECYCLE DISTRIBUTION")

    display_summary = summary.copy()

    display_summary[
        "high_value_user_share"
    ] = display_summary[
        "high_value_user_share"
    ].map(
        lambda x: f"{x:.2%}"
    )

    print(
        display_summary.to_string(index=False)
    )

    # --------------------------------------------------------
    # 6. High-value detail
    # --------------------------------------------------------
    detail_columns = [
        "customer_unique_id",
        "profile_state",
        "profile_city",
        "first_purchase_date",
        "last_purchase_date",
        "recency_days",
        "frequency",
        "monetary",
        "r_score",
        "f_score",
        "m_score",
        "rfm_segment",
        "churn_flag",
        "lifecycle_days",
        "lifecycle_stage",
        "is_high_value_churn_user",
    ]

    detail = (
        high_value[
            detail_columns
        ]
        .sort_values(
            by=[
                "is_high_value_churn_user",
                "monetary",
            ],
            ascending=[
                False,
                False,
            ],
        )
        .reset_index(drop=True)
    )

    print("\n[6] HIGH-VALUE USER DETAIL")
    print(
        detail.to_string(index=False)
    )

    # --------------------------------------------------------
    # 7. High-value churn user
    # --------------------------------------------------------
    hv_churn = detail[
        detail[
            "is_high_value_churn_user"
        ] == 1
    ]

    print("\n[7] HIGH-VALUE CHURN USER")

    print(
        hv_churn.to_string(index=False)
    )

    # --------------------------------------------------------
    # 8. Save
    # --------------------------------------------------------
    detail.to_csv(
        DETAIL_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    summary.to_csv(
        SUMMARY_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n[8] OUTPUTS")
    print(f"Saved: {DETAIL_OUTPUT}")
    print(f"Saved: {SUMMARY_OUTPUT}")

    print("\n" + "=" * 76)
    print("FINAL RESULT: PASS")
    print(
        "RFM x churn x lifecycle cross analysis "
        "successfully created."
    )
    print(
        "IMPORTANT: high-value population = 4; "
        "high-value churn population = 1; "
        "interpret descriptively only."
    )
    print("=" * 76)


if __name__ == "__main__":
    main()
