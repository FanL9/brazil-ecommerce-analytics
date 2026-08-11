from pathlib import Path
import sqlite3

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# Payment installment rule audit
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# Purpose:
# Inspect whether payment_installments is ambiguous when
# multiple payment records exist for the same order.
# No business output is generated in this step.
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

    print("=" * 76)
    print("PAYMENT INSTALLMENT RULE AUDIT")
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

    print("\n[1] FIXED-CUTOFF ORDER BASE")
    print(f"Orders: {len(orders):,}")

    # --------------------------------------------------------
    # 2. Positive payment records only
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

    print("\n[2] POSITIVE PAYMENT DATA")
    print(f"Payment rows: {len(positive):,}")
    print(
        f"Payment orders: "
        f"{positive['order_id'].nunique():,}"
    )

    # --------------------------------------------------------
    # 3. Installment distribution by payment type
    # --------------------------------------------------------
    summary_rows = []

    for payment_type, group in positive.groupby(
        "payment_type",
        dropna=False,
    ):
        summary_rows.append(
            {
                "payment_type": payment_type,
                "payment_rows": len(group),
                "orders": group["order_id"].nunique(),
                "min_installments":
                    group["payment_installments"].min(),
                "median_installments":
                    group["payment_installments"].median(),
                "max_installments":
                    group["payment_installments"].max(),
                "zero_installment_rows":
                    (group["payment_installments"] == 0).sum(),
                "one_installment_rows":
                    (group["payment_installments"] == 1).sum(),
                "multi_installment_rows":
                    (group["payment_installments"] > 1).sum(),
            }
        )

    type_summary = pd.DataFrame(summary_rows)

    print("\n[3] INSTALLMENTS BY PAYMENT TYPE")
    print(
        type_summary
        .sort_values("payment_rows", ascending=False)
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # 4. Aggregate each order + payment_type
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
            payment_rows=(
                "payment_sequential",
                "count",
            ),
            installment_distinct_count=(
                "payment_installments",
                "nunique",
            ),
            installment_min=(
                "payment_installments",
                "min",
            ),
            installment_max=(
                "payment_installments",
                "max",
            ),
        )
    )

    multiple_rows_same_type = (
        type_level["payment_rows"] > 1
    )

    different_installments_same_type = (
        type_level["installment_distinct_count"] > 1
    )

    print("\n[4] SAME ORDER + SAME PAYMENT TYPE")
    print(
        "Groups with multiple payment rows: "
        f"{multiple_rows_same_type.sum():,}"
    )
    print(
        "Groups with >1 installment value: "
        f"{different_installments_same_type.sum():,}"
    )

    # --------------------------------------------------------
    # 5. Determine main payment type using unified rule
    #
    # Largest aggregated payment amount.
    # Tie -> payment_type ASC.
    # --------------------------------------------------------
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
        .reset_index(drop=True)
    )

    print("\n[5] MAIN PAYMENT TYPE")
    print(
        f"Orders assigned a main payment type: "
        f"{len(main_type):,}"
    )

    main_ambiguous = (
        main_type["installment_distinct_count"] > 1
    )

    print(
        "Main-payment groups with "
        ">1 installment value: "
        f"{main_ambiguous.sum():,}"
    )

    print(
        "Main-payment groups with "
        "multiple payment rows: "
        f"{(main_type['payment_rows'] > 1).sum():,}"
    )

    # --------------------------------------------------------
    # 6. Show ambiguous main-payment cases
    # --------------------------------------------------------
    print("\n[6] AMBIGUOUS MAIN-PAYMENT CASES")

    ambiguous_orders = main_type.loc[
        main_ambiguous,
        "order_id",
    ].tolist()

    if len(ambiguous_orders) == 0:
        print(
            "No main-payment order has multiple "
            "installment values."
        )
    else:
        detail = positive[
            positive["order_id"].isin(
                ambiguous_orders
            )
        ].sort_values(
            by=[
                "order_id",
                "payment_type",
                "payment_sequential",
            ]
        )

        print(
            detail[
                [
                    "order_id",
                    "payment_sequential",
                    "payment_type",
                    "payment_installments",
                    "payment_value",
                ]
            ]
            .head(30)
            .to_string(index=False)
        )

    # --------------------------------------------------------
    # 7. Zero-installment records
    # --------------------------------------------------------
    print("\n[7] ZERO-INSTALLMENT RECORDS")

    zero_installments = positive[
        positive["payment_installments"] == 0
    ][
        [
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ]
    ]

    if len(zero_installments) == 0:
        print("None")
    else:
        print(
            zero_installments.to_string(index=False)
        )

    # --------------------------------------------------------
    # 8. Mixed-payment orders
    # --------------------------------------------------------
    payment_type_count = (
        positive.groupby("order_id")["payment_type"]
        .nunique()
    )

    mixed_orders = payment_type_count[
        payment_type_count > 1
    ].index

    print("\n[8] MIXED-PAYMENT ORDERS")
    print(f"Mixed-payment orders: {len(mixed_orders):,}")

    mixed_main = main_type[
        main_type["order_id"].isin(mixed_orders)
    ]

    print("\nMain payment type among mixed-payment orders:")

    print(
        mixed_main["payment_type"]
        .value_counts()
        .rename_axis("payment_type")
        .reset_index(name="orders")
        .to_string(index=False)
    )

    print("\n" + "=" * 76)
    print("AUDIT COMPLETE")
    print(
        "No aggregation rule has been chosen yet."
    )
    print("=" * 76)


if __name__ == "__main__":
    main()
