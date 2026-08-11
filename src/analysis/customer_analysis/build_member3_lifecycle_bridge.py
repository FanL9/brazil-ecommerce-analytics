from pathlib import Path

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# Build official-cutoff lifecycle bridge
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# IMPORTANT:
# This does NOT overwrite Member 2's original output.
#
# Observation date:
# 2018-07-31
#
# Order window:
# order_purchase_timestamp < 2018-08-01 00:00:00
# ============================================================

OBSERVATION_DATE = pd.Timestamp("2018-07-31")
CUTOFF = pd.Timestamp("2018-08-01 00:00:00")

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "03_customer_analysis"
)

ORDER_BASE_PATH = (
    DATA_DIR
    / "customer_order_base.csv"
)

CHURN_PATH = (
    DATA_DIR
    / "churn_user_detail.csv"
)

OUTPUT_PATH = (
    DATA_DIR
    / "member3_lifecycle_bridge.csv"
)


def assign_stage(row):

    recency = row["recency_days"]
    orders = row["valid_order_count"]
    lifetime = row["customer_lifecycle_days"]

    # Unified exclusive order:
    # 1. Dormant
    if recency > 90:
        return "Dormant Customer"

    # 2. New
    if orders == 1 and recency <= 30:
        return "New Customer"

    # 3. Early
    if orders == 1 and 30 < recency <= 90:
        return "Early Customer"

    # 4. Growing
    if orders >= 2 and lifetime <= 180:
        return "Growing Customer"

    # 5. Mature
    if orders >= 2 and lifetime > 180:
        return "Mature Customer"

    return "UNCLASSIFIED"


def main():

    print("=" * 76)
    print("BUILD MEMBER 3 OFFICIAL LIFECYCLE BRIDGE")
    print("=" * 76)

    # --------------------------------------------------------
    # 1. Load official order base
    # --------------------------------------------------------
    orders = pd.read_csv(
        ORDER_BASE_PATH,
        parse_dates=["order_purchase_timestamp"],
    )

    orders = orders[
        orders["order_purchase_timestamp"] < CUTOFF
    ].copy()

    print("\n[1] FIXED-CUTOFF ORDER BASE")
    print(f"Orders: {len(orders):,}")
    print(
        f"Customers: "
        f"{orders['customer_unique_id'].nunique():,}"
    )

    if len(orders) != 90127:
        raise ValueError(
            f"Expected 90,127 orders, got {len(orders):,}."
        )

    if orders["customer_unique_id"].nunique() != 87214:
        raise ValueError(
            "Expected 87,214 customers."
        )

    # --------------------------------------------------------
    # 2. User-level lifecycle metrics
    # --------------------------------------------------------
    user = (
        orders.groupby(
            "customer_unique_id",
            as_index=False,
        )
        .agg(
            first_purchase_timestamp=(
                "order_purchase_timestamp",
                "min",
            ),
            last_purchase_timestamp=(
                "order_purchase_timestamp",
                "max",
            ),
            valid_order_count=(
                "order_id",
                "nunique",
            ),
            lifetime_gmv=(
                "order_gmv",
                "sum",
            ),
        )
    )

    user["first_purchase_date"] = (
        user["first_purchase_timestamp"]
        .dt.normalize()
    )

    user["last_purchase_date"] = (
        user["last_purchase_timestamp"]
        .dt.normalize()
    )

    # Unified lifecycle length:
    # last valid purchase date - first valid purchase date
    user["customer_lifecycle_days"] = (
        user["last_purchase_date"]
        - user["first_purchase_date"]
    ).dt.days

    # Unified recency:
    # observation date - last valid purchase date
    user["recency_days"] = (
        OBSERVATION_DATE
        - user["last_purchase_date"]
    ).dt.days

    user["lifecycle_stage"] = user.apply(
        assign_stage,
        axis=1,
    )

    user["observation_date"] = (
        OBSERVATION_DATE.strftime("%Y-%m-%d")
    )

    print("\n[2] USER-LEVEL LIFECYCLE")
    print(f"Rows: {len(user):,}")
    print(
        f"Unique customers: "
        f"{user['customer_unique_id'].nunique():,}"
    )

    if len(user) != 87214:
        raise ValueError(
            "Lifecycle bridge must contain 87,214 users."
        )

    if user["customer_unique_id"].duplicated().any():
        raise ValueError(
            "Lifecycle bridge contains duplicate users."
        )

    # --------------------------------------------------------
    # 3. Stage integrity
    # --------------------------------------------------------
    print("\n[3] LIFECYCLE STAGE DISTRIBUTION")

    print(
        user["lifecycle_stage"]
        .value_counts()
        .to_string()
    )

    unclassified = (
        user["lifecycle_stage"] == "UNCLASSIFIED"
    ).sum()

    print(
        f"\nUnclassified users: "
        f"{unclassified:,}"
    )

    if unclassified != 0:
        raise ValueError(
            "Lifecycle classification is not complete."
        )

    # --------------------------------------------------------
    # 4. Reconcile against official churn output
    # --------------------------------------------------------
    churn = pd.read_csv(
        CHURN_PATH
    )

    check = churn[
        [
            "customer_unique_id",
            "valid_order_count",
            "customer_lifecycle_days",
            "recency_days",
            "churn_flag",
        ]
    ].merge(
        user[
            [
                "customer_unique_id",
                "valid_order_count",
                "customer_lifecycle_days",
                "recency_days",
                "lifecycle_stage",
            ]
        ],
        on="customer_unique_id",
        how="inner",
        suffixes=("_churn", "_lifecycle"),
        validate="one_to_one",
    )

    order_match = (
        check["valid_order_count_churn"]
        == check["valid_order_count_lifecycle"]
    ).all()

    lifetime_match = (
        check["customer_lifecycle_days_churn"]
        == check["customer_lifecycle_days_lifecycle"]
    ).all()

    recency_match = (
        check["recency_days_churn"]
        == check["recency_days_lifecycle"]
    ).all()

    churn_stage_match = (
        (check["churn_flag"] == 1)
        == (
            check["lifecycle_stage"]
            == "Dormant Customer"
        )
    ).all()

    print("\n[4] CROSS-MODULE RECONCILIATION")
    print(
        "valid_order_count: "
        f"{'PASS' if order_match else 'FAIL'}"
    )
    print(
        "customer_lifecycle_days: "
        f"{'PASS' if lifetime_match else 'FAIL'}"
    )
    print(
        "recency_days: "
        f"{'PASS' if recency_match else 'FAIL'}"
    )
    print(
        "churn_flag == Dormant Customer: "
        f"{'PASS' if churn_stage_match else 'FAIL'}"
    )

    if not all(
        [
            order_match,
            lifetime_match,
            recency_match,
            churn_stage_match,
        ]
    ):
        raise ValueError(
            "Lifecycle bridge does not reconcile "
            "with official churn metrics."
        )

    # --------------------------------------------------------
    # 5. Save
    # --------------------------------------------------------
    output_columns = [
        "customer_unique_id",
        "first_purchase_timestamp",
        "last_purchase_timestamp",
        "first_purchase_date",
        "last_purchase_date",
        "valid_order_count",
        "lifetime_gmv",
        "customer_lifecycle_days",
        "recency_days",
        "lifecycle_stage",
        "observation_date",
    ]

    user[
        output_columns
    ].to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n[5] OUTPUT")
    print(f"Saved: {OUTPUT_PATH}")
    print(f"Rows written: {len(user):,}")

    print("\n" + "=" * 76)
    print("FINAL RESULT: PASS")
    print(
        "Official-cutoff lifecycle bridge "
        "successfully created."
    )
    print("=" * 76)


if __name__ == "__main__":
    main()
