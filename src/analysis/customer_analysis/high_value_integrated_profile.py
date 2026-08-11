from pathlib import Path

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# Integrated high-value user profile
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# This script consolidates already validated:
# - RFM
# - churn
# - geography
# - lifecycle
# - payment
# - consumption
# - review
# - delivery
#
# Grain:
# one row per high-value customer_unique_id
# ============================================================

CUTOFF = pd.Timestamp("2018-08-01 00:00:00")
HIGH_AMOUNT_THRESHOLD = 500.0

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "03_customer_analysis"
)

USER_PATH = DATA_DIR / "member3_user_value_base.csv"
LIFECYCLE_PATH = DATA_DIR / "member3_lifecycle_bridge.csv"
PAYMENT_PATH = DATA_DIR / "member3_order_payment_base.csv"
EXPERIENCE_PATH = DATA_DIR / "member3_order_experience_base.csv"
ORDER_PATH = DATA_DIR / "customer_order_base.csv"

PROFILE_OUTPUT = (
    DATA_DIR
    / "high_value_user_integrated_profile.csv"
)

CHURN_OUTPUT = (
    DATA_DIR
    / "high_value_churn_user_integrated_profile.csv"
)


def safe_divide(num, den):
    if den == 0:
        return None
    return num / den


def build_payment_profile(payment_orders):

    paid = payment_orders[
        payment_orders["is_paid_order"] == 1
    ].copy()

    rows = []

    for customer_id, group in payment_orders.groupby(
        "customer_unique_id"
    ):

        paid_group = paid[
            paid["customer_unique_id"] == customer_id
        ].copy()

        paid_order_count = paid_group["order_id"].nunique()

        gmv = paid_group["payment_gmv"].fillna(0).sum()

        valid_installment = paid_group[
            paid_group["main_payment_installments"] > 0
        ]

        # Main payment type by order count.
        # Tie -> payment_type ASC.
        payment_type_counts = (
            paid_group.groupby(
                "main_payment_type",
                as_index=False,
            )
            .agg(
                orders=("order_id", "nunique")
            )
            .sort_values(
                by=[
                    "orders",
                    "main_payment_type",
                ],
                ascending=[
                    False,
                    True,
                ],
            )
        )

        if payment_type_counts.empty:
            dominant_type = None
            dominant_type_orders = 0
        else:
            dominant_type = (
                payment_type_counts.iloc[0][
                    "main_payment_type"
                ]
            )
            dominant_type_orders = int(
                payment_type_counts.iloc[0]["orders"]
            )

        rows.append(
            {
                "customer_unique_id": customer_id,

                "paid_orders":
                    paid_order_count,

                "payment_gmv":
                    gmv,

                "average_order_value":
                    safe_divide(
                        gmv,
                        paid_order_count,
                    ),

                "dominant_main_payment_type":
                    dominant_type,

                "dominant_payment_type_order_share":
                    safe_divide(
                        dominant_type_orders,
                        paid_order_count,
                    ),

                "avg_main_payment_installments_valid":
                    valid_installment[
                        "main_payment_installments"
                    ].mean(),

                "one_time_orders":
                    int(
                        paid_group[
                            "installment_status"
                        ].eq("one_time").sum()
                    ),

                "installment_orders":
                    int(
                        paid_group[
                            "installment_status"
                        ].eq("installment").sum()
                    ),

                "zero_installment_orders":
                    int(
                        paid_group[
                            "installment_status"
                        ].eq(
                            "zero_installment_flag"
                        ).sum()
                    ),

                "mixed_payment_orders":
                    int(
                        paid_group[
                            "is_mixed_payment_order"
                        ].sum()
                    ),
            }
        )

    return pd.DataFrame(rows)


def build_experience_profile(experience):

    rows = []

    for customer_id, group in experience.groupby(
        "customer_unique_id"
    ):

        reviewed = group[
            group["has_valid_review"] == 1
        ]

        delivery = group[
            group["has_valid_delivery"] == 1
        ]

        delay = group[
            group["has_valid_delay_measure"] == 1
        ]

        review_count = reviewed["order_id"].nunique()
        delivery_count = delivery["order_id"].nunique()
        delay_count = delay["order_id"].nunique()

        low_score_orders = int(
            reviewed[
                "representative_review_score"
            ].eq(1).sum()
        )

        positive_orders = int(
            reviewed[
                "representative_review_score"
            ].ge(4).sum()
        )

        delayed_orders = int(
            delay["is_delayed"].sum()
        )

        rows.append(
            {
                "customer_unique_id": customer_id,

                "reviewed_orders":
                    review_count,

                "average_review_score":
                    reviewed[
                        "representative_review_score"
                    ].mean(),

                "low_score_orders":
                    low_score_orders,

                "low_score_order_share":
                    safe_divide(
                        low_score_orders,
                        review_count,
                    ),

                "positive_review_rate":
                    safe_divide(
                        positive_orders,
                        review_count,
                    ),

                "delivery_orders":
                    delivery_count,

                "average_delivery_days":
                    delivery[
                        "delivery_days"
                    ].mean(),

                "delay_eligible_orders":
                    delay_count,

                "delayed_orders":
                    delayed_orders,

                "delay_rate":
                    safe_divide(
                        delayed_orders,
                        delay_count,
                    ),
            }
        )

    return pd.DataFrame(rows)


def build_consumption_profile(orders):

    rows = []

    for customer_id, group in orders.groupby(
        "customer_unique_id"
    ):

        paid = group[
            group["is_paid_order"] == 1
        ]

        total_orders = group["order_id"].nunique()
        paid_orders = paid["order_id"].nunique()

        high_amount_orders = int(
            (
                paid["order_gmv"]
                >= HIGH_AMOUNT_THRESHOLD
            ).sum()
        )

        weekday_orders = int(
            group["weekday_number"]
            .between(1, 5)
            .sum()
        )

        weekend_orders = (
            total_orders
            - weekday_orders
        )

        hour_counts = (
            group.groupby(
                "purchase_hour",
                as_index=False,
            )
            .agg(
                orders=("order_id", "nunique")
            )
            .sort_values(
                by=[
                    "orders",
                    "purchase_hour",
                ],
                ascending=[
                    False,
                    True,
                ],
            )
        )

        peak_hour = (
            None
            if hour_counts.empty
            else int(
                hour_counts.iloc[0][
                    "purchase_hour"
                ]
            )
        )

        peak_hour_orders = (
            0
            if hour_counts.empty
            else int(
                hour_counts.iloc[0]["orders"]
            )
        )

        rows.append(
            {
                "customer_unique_id":
                    customer_id,

                "valid_orders":
                    total_orders,

                "high_amount_threshold_brl":
                    HIGH_AMOUNT_THRESHOLD,

                "high_amount_orders":
                    high_amount_orders,

                "high_amount_order_share":
                    safe_divide(
                        high_amount_orders,
                        paid_orders,
                    ),

                "weekday_orders":
                    weekday_orders,

                "weekend_orders":
                    weekend_orders,

                "weekday_order_share":
                    safe_divide(
                        weekday_orders,
                        total_orders,
                    ),

                "peak_purchase_hour":
                    peak_hour,

                "peak_hour_orders":
                    peak_hour_orders,
            }
        )

    return pd.DataFrame(rows)


def main():

    print("=" * 78)
    print("BUILD INTEGRATED HIGH-VALUE USER PROFILE")
    print("=" * 78)

    # --------------------------------------------------------
    # 1. Load validated inputs
    # --------------------------------------------------------
    users = pd.read_csv(USER_PATH)

    lifecycle = pd.read_csv(
        LIFECYCLE_PATH
    )

    payment = pd.read_csv(
        PAYMENT_PATH
    )

    experience = pd.read_csv(
        EXPERIENCE_PATH
    )

    orders = pd.read_csv(
        ORDER_PATH,
        parse_dates=["order_purchase_timestamp"],
    )

    orders = orders[
        orders["order_purchase_timestamp"] < CUTOFF
    ].copy()

    high_value = users[
        users["is_high_value_user"] == 1
    ].copy()

    high_value_ids = set(
        high_value["customer_unique_id"]
    )

    print("\n[1] HIGH-VALUE POPULATION")
    print(
        f"High-value users: "
        f"{len(high_value):,}"
    )
    print(
        f"High-value churn users: "
        f"{high_value['is_high_value_churn_user'].sum():,}"
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
    # 2. Restrict order-level bases
    # --------------------------------------------------------
    hv_payment = payment[
        payment[
            "customer_unique_id"
        ].isin(high_value_ids)
    ].copy()

    hv_experience = experience[
        experience[
            "customer_unique_id"
        ].isin(high_value_ids)
    ].copy()

    hv_orders = orders[
        orders[
            "customer_unique_id"
        ].isin(high_value_ids)
    ].copy()

    print("\n[2] ORDER COVERAGE")
    print(
        f"Payment orders: "
        f"{hv_payment['order_id'].nunique():,}"
    )
    print(
        f"Experience orders: "
        f"{hv_experience['order_id'].nunique():,}"
    )
    print(
        f"Consumption orders: "
        f"{hv_orders['order_id'].nunique():,}"
    )

    if (
        hv_payment["order_id"].nunique() != 35
        or hv_experience["order_id"].nunique() != 35
        or hv_orders["order_id"].nunique() != 35
    ):
        raise ValueError(
            "High-value order coverage must be 35 "
            "across all order-level modules."
        )

    print("Order coverage: PASS")

    # --------------------------------------------------------
    # 3. Lifecycle fields
    # --------------------------------------------------------
    hv_lifecycle = lifecycle[
        lifecycle[
            "customer_unique_id"
        ].isin(high_value_ids)
    ][
        [
            "customer_unique_id",
            "first_purchase_date",
            "last_purchase_date",
            "customer_lifecycle_days",
            "lifecycle_stage",
        ]
    ].copy()

    # --------------------------------------------------------
    # 4. Build module profiles
    # --------------------------------------------------------
    payment_profile = (
        build_payment_profile(
            hv_payment
        )
    )

    experience_profile = (
        build_experience_profile(
            hv_experience
        )
    )

    consumption_profile = (
        build_consumption_profile(
            hv_orders
        )
    )

    # --------------------------------------------------------
    # 5. Merge
    # --------------------------------------------------------
    base_columns = [
        "customer_unique_id",
        "profile_state",
        "profile_city",
        "recency_days",
        "frequency",
        "monetary",
        "r_score",
        "f_score",
        "m_score",
        "rfm_segment",
        "churn_flag",
        "is_high_value_user",
        "is_high_value_churn_user",
    ]

    profile = high_value[
        base_columns
    ].merge(
        hv_lifecycle,
        on="customer_unique_id",
        how="left",
        validate="one_to_one",
    )

    profile = profile.merge(
        payment_profile,
        on="customer_unique_id",
        how="left",
        validate="one_to_one",
    )

    profile = profile.merge(
        consumption_profile,
        on="customer_unique_id",
        how="left",
        validate="one_to_one",
    )

    profile = profile.merge(
        experience_profile,
        on="customer_unique_id",
        how="left",
        validate="one_to_one",
    )

    print("\n[3] FINAL USER GRAIN")
    print(f"Rows: {len(profile):,}")
    print(
        f"Unique customers: "
        f"{profile['customer_unique_id'].nunique():,}"
    )

    if len(profile) != 4:
        raise ValueError(
            "Integrated profile must contain 4 users."
        )

    if profile[
        "customer_unique_id"
    ].duplicated().any():
        raise ValueError(
            "Integrated profile contains duplicate users."
        )

    print("One row per high-value user: PASS")

    # --------------------------------------------------------
    # 6. Reconciliation
    # --------------------------------------------------------
    frequency_ok = (
        profile["frequency"]
        == profile["valid_orders"]
    ).all()

    monetary_ok = (
        (
            profile["monetary"]
            - profile["payment_gmv"]
        ).abs() <= 0.01
    ).all()

    print("\n[4] RECONCILIATION")
    print(
        "Frequency vs valid orders:",
        "PASS" if frequency_ok else "FAIL",
    )
    print(
        "Monetary vs payment GMV:",
        "PASS" if monetary_ok else "FAIL",
    )

    if not frequency_ok or not monetary_ok:
        raise ValueError(
            "Integrated profile failed reconciliation."
        )

    # --------------------------------------------------------
    # 7. Display
    # --------------------------------------------------------
    profile = profile.sort_values(
        by=[
            "is_high_value_churn_user",
            "monetary",
        ],
        ascending=[
            False,
            False,
        ],
    ).reset_index(drop=True)

    print("\n[5] INTEGRATED HIGH-VALUE PROFILE")

    display_cols = [
        "customer_unique_id",
        "profile_state",
        "profile_city",
        "lifecycle_stage",
        "recency_days",
        "frequency",
        "monetary",
        "dominant_main_payment_type",
        "average_order_value",
        "average_review_score",
        "average_delivery_days",
        "delay_rate",
        "weekday_order_share",
        "peak_purchase_hour",
        "is_high_value_churn_user",
    ]

    print(
        profile[
            display_cols
        ].to_string(index=False)
    )

    # --------------------------------------------------------
    # 8. High-value churn user
    # --------------------------------------------------------
    churn_profile = profile[
        profile[
            "is_high_value_churn_user"
        ] == 1
    ].copy()

    print("\n[6] HIGH-VALUE CHURN INTEGRATED PROFILE")

    print(
        churn_profile[
            display_cols
        ].to_string(index=False)
    )

    # --------------------------------------------------------
    # 9. Save
    # --------------------------------------------------------
    profile.to_csv(
        PROFILE_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    churn_profile.to_csv(
        CHURN_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n[7] OUTPUTS")
    print(f"Saved: {PROFILE_OUTPUT}")
    print(f"Saved: {CHURN_OUTPUT}")

    print("\n" + "=" * 78)
    print("FINAL RESULT: PASS")
    print(
        "Integrated high-value user profile "
        "successfully created."
    )
    print(
        "IMPORTANT: high-value users = 4; "
        "high-value churn users = 1; "
        "all interpretation must remain descriptive."
    )
    print("=" * 78)


if __name__ == "__main__":
    main()
