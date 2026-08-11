from pathlib import Path
import sqlite3

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# Build standardized order-level payment base
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# Unified rules:
# 1. Positive payment_value only for GMV/payment analysis.
# 2. Main payment type:
#    highest aggregated payment amount within order;
#    tie -> payment_type ASC.
#
# Supplemental installment rule:
# Within the main payment type, select the payment record with
# the largest payment_value;
# tie -> payment_sequential ASC.
# Its payment_installments becomes main_payment_installments.
# ============================================================

CUTOFF = pd.Timestamp("2018-08-01 00:00:00")

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DB_PATH = PROJECT_ROOT / "database" / "brazil_ecommerce.db"

DATA_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "03_customer_analysis"
)

ORDER_BASE_PATH = DATA_DIR / "customer_order_base.csv"

OUTPUT_PATH = DATA_DIR / "member3_order_payment_base.csv"


def main():

    print("=" * 76)
    print("BUILD STANDARDIZED ORDER PAYMENT BASE")
    print("=" * 76)

    # --------------------------------------------------------
    # 1. Fixed-cutoff delivered orders
    # --------------------------------------------------------
    orders = pd.read_csv(
        ORDER_BASE_PATH,
        parse_dates=["order_purchase_timestamp"],
    )

    orders = orders[
        orders["order_purchase_timestamp"] < CUTOFF
    ].copy()

    if orders["order_id"].duplicated().any():
        raise ValueError(
            "customer_order_base is not one row per order."
        )

    print("\n[1] FIXED-CUTOFF ORDER BASE")
    print(f"Orders: {len(orders):,}")
    print(
        f"Paid orders: "
        f"{(orders['is_paid_order'] == 1).sum():,}"
    )

    # --------------------------------------------------------
    # 2. Load raw payment details
    # --------------------------------------------------------
    con = sqlite3.connect(DB_PATH)

    payments = pd.read_sql_query(
        """
        SELECT
            order_id,
            payment_sequential,
            payment_type,
            payment_installments,
            payment_value
        FROM order_payments
        """,
        con,
    )

    con.close()

    payments = payments.merge(
        orders[["order_id"]],
        on="order_id",
        how="inner",
        validate="many_to_one",
    )

    positive = payments[
        payments["payment_value"].notna()
        & (payments["payment_value"] > 0)
    ].copy()

    print("\n[2] POSITIVE PAYMENTS")
    print(f"Payment rows: {len(positive):,}")
    print(
        f"Payment orders: "
        f"{positive['order_id'].nunique():,}"
    )

    # --------------------------------------------------------
    # 3. Payment-type-level aggregation
    # --------------------------------------------------------
    type_level = (
        positive.groupby(
            ["order_id", "payment_type"],
            as_index=False,
        )
        .agg(
            payment_type_value=(
                "payment_value",
                "sum",
            ),
            payment_type_record_count=(
                "payment_sequential",
                "count",
            ),
        )
    )

    # Unified rule:
    # highest aggregated amount;
    # tie -> payment_type ASC
    main_type = (
        type_level
        .sort_values(
            by=[
                "order_id",
                "payment_type_value",
                "payment_type",
            ],
            ascending=[
                True,
                False,
                True,
            ],
        )
        .drop_duplicates(
            subset=["order_id"],
            keep="first",
        )
        .rename(
            columns={
                "payment_type":
                    "main_payment_type",
                "payment_type_value":
                    "main_payment_type_value",
                "payment_type_record_count":
                    "main_payment_type_record_count",
            }
        )
    )

    # --------------------------------------------------------
    # 4. Representative payment record inside main type
    # --------------------------------------------------------
    representative = positive.merge(
        main_type[
            [
                "order_id",
                "main_payment_type",
            ]
        ],
        on="order_id",
        how="inner",
        validate="many_to_one",
    )

    representative = representative[
        representative["payment_type"]
        == representative["main_payment_type"]
    ].copy()

    representative = (
        representative
        .sort_values(
            by=[
                "order_id",
                "payment_value",
                "payment_sequential",
            ],
            ascending=[
                True,
                False,
                True,
            ],
        )
        .drop_duplicates(
            subset=["order_id"],
            keep="first",
        )
    )

    representative = representative[
        [
            "order_id",
            "payment_sequential",
            "payment_installments",
            "payment_value",
        ]
    ].rename(
        columns={
            "payment_sequential":
                "representative_payment_sequential",
            "payment_installments":
                "main_payment_installments",
            "payment_value":
                "representative_payment_value",
        }
    )

    # --------------------------------------------------------
    # 5. Total payment-level order information
    # --------------------------------------------------------
    order_payment_summary = (
        positive.groupby(
            "order_id",
            as_index=False,
        )
        .agg(
            payment_gmv=(
                "payment_value",
                "sum",
            ),
            payment_record_count=(
                "payment_sequential",
                "count",
            ),
            payment_type_count=(
                "payment_type",
                "nunique",
            ),
        )
    )

    # --------------------------------------------------------
    # 6. Build one-row-per-order payment base
    # --------------------------------------------------------
    base = orders[
        [
            "customer_unique_id",
            "customer_id",
            "order_id",
            "order_purchase_timestamp",
            "customer_state",
            "customer_city",
            "order_gmv",
            "is_paid_order",
        ]
    ].copy()

    base = base.merge(
        order_payment_summary,
        on="order_id",
        how="left",
        validate="one_to_one",
    )

    base = base.merge(
        main_type[
            [
                "order_id",
                "main_payment_type",
                "main_payment_type_value",
                "main_payment_type_record_count",
            ]
        ],
        on="order_id",
        how="left",
        validate="one_to_one",
    )

    base = base.merge(
        representative,
        on="order_id",
        how="left",
        validate="one_to_one",
    )

    # --------------------------------------------------------
    # 7. Installment status
    # --------------------------------------------------------
    def classify_installment(value):

        if pd.isna(value):
            return "no_positive_payment"

        if value == 0:
            return "zero_installment_flag"

        if value == 1:
            return "one_time"

        if value > 1:
            return "installment"

        return "unknown"

    base["installment_status"] = (
        base["main_payment_installments"]
        .apply(classify_installment)
    )

    base["is_mixed_payment_order"] = (
        base["payment_type_count"].fillna(0) > 1
    ).astype(int)

    # --------------------------------------------------------
    # 8. Validation
    # --------------------------------------------------------
    print("\n[3] FINAL ORDER GRAIN")
    print(f"Rows: {len(base):,}")
    print(
        f"Unique order_id: "
        f"{base['order_id'].nunique():,}"
    )

    if len(base) != 90127:
        raise ValueError(
            f"Expected 90,127 rows, got {len(base):,}."
        )

    if base["order_id"].duplicated().any():
        raise ValueError(
            "Final payment base contains duplicate orders."
        )

    print("One row per order: PASS")

    # --------------------------------------------------------
    # 9. GMV reconciliation
    # --------------------------------------------------------
    base["payment_gmv_check"] = (
        base["payment_gmv"].fillna(0)
    )

    base["order_gmv_check"] = (
        base["order_gmv"].fillna(0)
    )

    diff = (
        base["payment_gmv_check"]
        - base["order_gmv_check"]
    ).abs()

    print("\n[4] GMV RECONCILIATION")
    print(
        f"Order-base GMV: "
        f"{base['order_gmv_check'].sum():,.2f}"
    )
    print(
        f"Payment GMV: "
        f"{base['payment_gmv_check'].sum():,.2f}"
    )
    print(
        f"Orders with difference > 0.01: "
        f"{(diff > 0.01).sum():,}"
    )

    if (diff > 0.01).any():
        raise ValueError(
            "Payment GMV does not reconcile."
        )

    print("GMV reconciliation: PASS")

    # --------------------------------------------------------
    # 10. Main-payment validation
    # --------------------------------------------------------
    paid = base[
        base["is_paid_order"] == 1
    ].copy()

    print("\n[5] MAIN PAYMENT ASSIGNMENT")
    print(
        f"Paid orders: "
        f"{len(paid):,}"
    )
    print(
        f"Missing main_payment_type: "
        f"{paid['main_payment_type'].isna().sum():,}"
    )
    print(
        f"Missing main_payment_installments: "
        f"{paid['main_payment_installments'].isna().sum():,}"
    )

    if paid["main_payment_type"].isna().any():
        raise ValueError(
            "Paid order missing main payment type."
        )

    if paid["main_payment_installments"].isna().any():
        raise ValueError(
            "Paid order missing representative installments."
        )

    print("Main-payment assignment: PASS")

    # --------------------------------------------------------
    # 11. Installment status
    # --------------------------------------------------------
    print("\n[6] INSTALLMENT STATUS")
    print(
        base["installment_status"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\n[7] MIXED PAYMENT")
    print(
        f"Mixed-payment orders: "
        f"{base['is_mixed_payment_order'].sum():,}"
    )

    # --------------------------------------------------------
    # 12. Save
    # --------------------------------------------------------
    base = base.drop(
        columns=[
            "payment_gmv_check",
            "order_gmv_check",
        ]
    )

    base.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n[8] OUTPUT")
    print(f"Saved: {OUTPUT_PATH}")
    print(f"Rows written: {len(base):,}")

    print("\n" + "=" * 76)
    print("FINAL RESULT: PASS")
    print(
        "Standardized order-level payment base successfully created."
    )
    print("=" * 76)


if __name__ == "__main__":
    main()
