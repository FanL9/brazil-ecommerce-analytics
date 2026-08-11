from pathlib import Path
import sqlite3

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# Payment source validation
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
# ============================================================

CUTOFF = pd.Timestamp("2018-08-01 00:00:00")

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DB_PATH = (
    PROJECT_ROOT
    / "database"
    / "brazil_ecommerce.db"
)

ORDER_BASE_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "03_customer_analysis"
    / "customer_order_base.csv"
)


def main():

    print("=" * 72)
    print("PAYMENT SOURCE VALIDATION")
    print("=" * 72)

    # --------------------------------------------------------
    # 1. Fixed-cutoff delivered order population
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
        f"Unique customers: "
        f"{orders['customer_unique_id'].nunique():,}"
    )
    print(
        f"Paid-order flag = 1: "
        f"{(orders['is_paid_order'] == 1).sum():,}"
    )

    # --------------------------------------------------------
    # 2. Read raw payment table
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

    print("\n[2] RAW PAYMENT TABLE")
    print(f"Rows: {len(payments):,}")
    print(
        f"Unique orders: "
        f"{payments['order_id'].nunique():,}"
    )

    duplicate_payment_keys = payments.duplicated(
        subset=[
            "order_id",
            "payment_sequential",
        ]
    ).sum()

    print(
        "Duplicated "
        "(order_id, payment_sequential): "
        f"{duplicate_payment_keys:,}"
    )

    if duplicate_payment_keys != 0:
        raise ValueError(
            "Payment detail key is not unique."
        )

    print("Payment detail grain: PASS")

    # --------------------------------------------------------
    # 3. Restrict to fixed-cutoff delivered orders
    # --------------------------------------------------------
    cutoff_payments = payments.merge(
        orders[["order_id"]],
        on="order_id",
        how="inner",
        validate="many_to_one",
    )

    print("\n[3] PAYMENTS WITHIN FIXED-CUTOFF ORDERS")
    print(f"Payment rows: {len(cutoff_payments):,}")
    print(
        f"Orders with any payment row: "
        f"{cutoff_payments['order_id'].nunique():,}"
    )

    # --------------------------------------------------------
    # 4. Positive-payment rule
    # --------------------------------------------------------
    positive_payments = cutoff_payments[
        cutoff_payments["payment_value"].notna()
        & (cutoff_payments["payment_value"] > 0)
    ].copy()

    positive_order_count = (
        positive_payments["order_id"].nunique()
    )

    print("\n[4] POSITIVE PAYMENT RULE")
    print(
        f"Positive payment rows: "
        f"{len(positive_payments):,}"
    )
    print(
        f"Positive-payment orders: "
        f"{positive_order_count:,}"
    )

    non_positive_rows = (
        cutoff_payments["payment_value"].isna()
        | (cutoff_payments["payment_value"] <= 0)
    ).sum()

    print(
        f"NULL/non-positive payment rows: "
        f"{non_positive_rows:,}"
    )

    expected_paid_orders = int(
        (orders["is_paid_order"] == 1).sum()
    )

    if positive_order_count != expected_paid_orders:
        raise ValueError(
            "Positive-payment order count does not match "
            "customer_order_base is_paid_order."
        )

    print("Paid-order count reconciliation: PASS")

    # --------------------------------------------------------
    # 5. Aggregate positive payments to order level
    # --------------------------------------------------------
    payment_order = (
        positive_payments
        .groupby(
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

    reconciliation = orders[
        [
            "order_id",
            "order_gmv",
            "is_paid_order",
        ]
    ].merge(
        payment_order,
        on="order_id",
        how="left",
        validate="one_to_one",
    )

    reconciliation["payment_gmv"] = (
        reconciliation["payment_gmv"]
        .fillna(0)
    )

    reconciliation["order_gmv_compare"] = (
        reconciliation["order_gmv"]
        .fillna(0)
    )

    reconciliation["gmv_diff"] = (
        reconciliation["payment_gmv"]
        - reconciliation["order_gmv_compare"]
    )

    # floating-point tolerance
    mismatch = (
        reconciliation["gmv_diff"].abs() > 0.01
    )

    print("\n[5] ORDER-LEVEL GMV RECONCILIATION")
    print(
        f"customer_order_base GMV: "
        f"{reconciliation['order_gmv_compare'].sum():,.2f}"
    )
    print(
        f"Positive payment GMV: "
        f"{reconciliation['payment_gmv'].sum():,.2f}"
    )
    print(
        f"Orders with GMV difference > 0.01: "
        f"{mismatch.sum():,}"
    )
    print(
        f"Maximum absolute difference: "
        f"{reconciliation['gmv_diff'].abs().max():.6f}"
    )

    if mismatch.any():
        raise ValueError(
            "Order-level payment GMV does not reconcile "
            "with customer_order_base."
        )

    print("Order-level GMV reconciliation: PASS")

    # --------------------------------------------------------
    # 6. Mixed-payment structure
    # --------------------------------------------------------
    payment_type_counts = (
        positive_payments.groupby(
            "order_id"
        )["payment_type"]
        .nunique()
    )

    mixed_payment_orders = (
        payment_type_counts > 1
    ).sum()

    print("\n[6] MIXED PAYMENT ORDERS")
    print(
        f"Orders using >1 payment type: "
        f"{mixed_payment_orders:,}"
    )

    if positive_order_count == 0:
        mixed_share = None
    else:
        mixed_share = (
            mixed_payment_orders
            / positive_order_count
        )

    if mixed_share is None:
        print("Mixed-payment order share: NULL")
    else:
        print(
            f"Mixed-payment order share: "
            f"{mixed_share:.4%}"
        )

    # --------------------------------------------------------
    # 7. Payment-type structure
    # --------------------------------------------------------
    type_summary = (
        positive_payments.groupby(
            "payment_type",
            dropna=False,
            as_index=False,
        )
        .agg(
            payment_rows=(
                "payment_sequential",
                "count",
            ),
            orders=(
                "order_id",
                "nunique",
            ),
            payment_value=(
                "payment_value",
                "sum",
            ),
        )
        .sort_values(
            "payment_value",
            ascending=False,
        )
    )

    print("\n[7] POSITIVE PAYMENT TYPES")
    print(type_summary.to_string(index=False))

    # --------------------------------------------------------
    # 8. Installment source check
    # --------------------------------------------------------
    print("\n[8] INSTALLMENT SOURCE CHECK")
    print(
        f"Missing payment_installments: "
        f"{positive_payments['payment_installments'].isna().sum():,}"
    )
    print(
        f"Zero payment_installments: "
        f"{(positive_payments['payment_installments'] == 0).sum():,}"
    )
    print(
        f"Minimum installments: "
        f"{positive_payments['payment_installments'].min()}"
    )
    print(
        f"Maximum installments: "
        f"{positive_payments['payment_installments'].max()}"
    )

    print("\n" + "=" * 72)
    print("FINAL RESULT: PASS")
    print(
        "Payment source is ready for construction "
        "of the standardized order-level payment layer."
    )
    print("=" * 72)


if __name__ == "__main__":
    main()
