from pathlib import Path

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# Customer order base validation
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
# ============================================================

CUTOFF = pd.Timestamp("2018-08-01 00:00:00")

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "03_customer_analysis"
    / "customer_order_base.csv"
)


def main():
    print("=" * 70)
    print("CUSTOMER ORDER BASE VALIDATION")
    print("=" * 70)

    df = pd.read_csv(
        DATA_PATH,
        parse_dates=["order_purchase_timestamp"],
    )

    print("\n[1] SOURCE DATA")
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------
    required = [
        "customer_unique_id",
        "customer_id",
        "order_id",
        "order_purchase_timestamp",
        "customer_state",
        "customer_city",
        "order_gmv",
        "is_paid_order",
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    print("\n[2] REQUIRED COLUMNS")
    print("Required columns: PASS")

    # --------------------------------------------------------
    # Order grain
    # --------------------------------------------------------
    duplicate_orders = df["order_id"].duplicated().sum()

    print("\n[3] ORDER GRAIN")
    print(f"Unique order_id: {df['order_id'].nunique():,}")
    print(f"Duplicated order_id: {duplicate_orders:,}")

    if duplicate_orders != 0:
        raise ValueError(
            "customer_order_base is not one row per order."
        )

    print("One row per order_id: PASS")

    # --------------------------------------------------------
    # User key
    # --------------------------------------------------------
    missing_users = df["customer_unique_id"].isna().sum()

    print("\n[4] CUSTOMER KEY")
    print(
        f"Missing customer_unique_id: "
        f"{missing_users:,}"
    )

    if missing_users != 0:
        raise ValueError(
            "customer_unique_id contains missing values."
        )

    print("customer_unique_id: PASS")

    # --------------------------------------------------------
    # Time coverage
    # --------------------------------------------------------
    print("\n[5] TIME COVERAGE")
    print(
        "Minimum purchase timestamp:",
        df["order_purchase_timestamp"].min(),
    )
    print(
        "Maximum purchase timestamp:",
        df["order_purchase_timestamp"].max(),
    )

    before_cutoff = df[
        df["order_purchase_timestamp"] < CUTOFF
    ].copy()

    after_cutoff = df[
        df["order_purchase_timestamp"] >= CUTOFF
    ].copy()

    print(
        f"Rows before 2018-08-01: "
        f"{len(before_cutoff):,}"
    )
    print(
        f"Rows on/after 2018-08-01: "
        f"{len(after_cutoff):,}"
    )

    # --------------------------------------------------------
    # Fixed-cutoff population
    # --------------------------------------------------------
    print("\n[6] FIXED-CUTOFF POPULATION")
    print(
        f"Unique customers before cutoff: "
        f"{before_cutoff['customer_unique_id'].nunique():,}"
    )
    print(
        f"Unique orders before cutoff: "
        f"{before_cutoff['order_id'].nunique():,}"
    )

    # --------------------------------------------------------
    # Geography check
    # --------------------------------------------------------
    print("\n[7] GEOGRAPHY")
    print(
        f"Missing customer_state: "
        f"{before_cutoff['customer_state'].isna().sum():,}"
    )
    print(
        f"Missing customer_city: "
        f"{before_cutoff['customer_city'].isna().sum():,}"
    )

    # --------------------------------------------------------
    # GMV / paid-order check
    # --------------------------------------------------------
    print("\n[8] GMV / PAID ORDER")
    print(
        "is_paid_order values:",
        sorted(before_cutoff["is_paid_order"].dropna().unique().tolist()),
    )

    print(
        f"Paid orders: "
        f"{(before_cutoff['is_paid_order'] == 1).sum():,}"
    )

    print(
        f"Zero/NULL GMV rows: "
        f"{((before_cutoff['order_gmv'].fillna(0)) <= 0).sum():,}"
    )

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
