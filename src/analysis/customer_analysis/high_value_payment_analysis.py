from pathlib import Path
import sqlite3

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# High-value user payment behavior analysis
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# Payment-method order share:
# use one main_payment_type per paid order.
#
# Payment-method GMV share:
# use actual positive payment_value by payment_type.
#
# High-value user:
# R >= 4, F >= 4, M >= 4.
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

DB_PATH = (
    PROJECT_ROOT
    / "database"
    / "brazil_ecommerce.db"
)

USER_BASE_PATH = (
    DATA_DIR
    / "member3_user_value_base.csv"
)

PAYMENT_BASE_PATH = (
    DATA_DIR
    / "member3_order_payment_base.csv"
)

ORDER_SHARE_OUTPUT = (
    DATA_DIR
    / "high_value_user_payment_method_order_share.csv"
)

GMV_SHARE_OUTPUT = (
    DATA_DIR
    / "high_value_user_payment_method_gmv_share.csv"
)

INSTALLMENT_OUTPUT = (
    DATA_DIR
    / "high_value_user_installment_profile.csv"
)

SUMMARY_OUTPUT = (
    DATA_DIR
    / "high_value_user_payment_behavior.csv"
)


def build_group_summary(df, group_name):

    paid = df[
        df["is_paid_order"] == 1
    ].copy()

    valid_installment_status = paid[
        paid["installment_status"].isin(
            ["one_time", "installment"]
        )
    ].copy()

    valid_status_count = len(
        valid_installment_status
    )

    one_time_orders = (
        valid_installment_status[
            "installment_status"
        ].eq("one_time").sum()
    )

    installment_orders = (
        valid_installment_status[
            "installment_status"
        ].eq("installment").sum()
    )

    if valid_status_count == 0:
        one_time_share = None
        installment_share = None
    else:
        one_time_share = (
            one_time_orders
            / valid_status_count
        )

        installment_share = (
            installment_orders
            / valid_status_count
        )

    return {
        "group": group_name,
        "users":
            df["customer_unique_id"].nunique(),
        "orders":
            df["order_id"].nunique(),
        "paid_orders":
            paid["order_id"].nunique(),
        "gmv":
            paid["payment_gmv"].fillna(0).sum(),
        "average_main_payment_installments":
            paid["main_payment_installments"].mean(),
        "median_main_payment_installments":
            paid["main_payment_installments"].median(),
        "one_time_orders":
            int(one_time_orders),
        "installment_orders":
            int(installment_orders),
        "one_time_share_valid":
            one_time_share,
        "installment_share_valid":
            installment_share,
        "zero_installment_orders":
            int(
                paid["installment_status"]
                .eq("zero_installment_flag")
                .sum()
            ),
        "mixed_payment_orders":
            int(
                paid["is_mixed_payment_order"]
                .sum()
            ),
        "mixed_payment_share":
            paid["is_mixed_payment_order"].mean(),
    }


def build_order_share(df, group_name):

    paid = df[
        df["is_paid_order"] == 1
    ].copy()

    denominator = paid[
        "order_id"
    ].nunique()

    result = (
        paid.groupby(
            "main_payment_type",
            as_index=False,
            dropna=False,
        )
        .agg(
            orders=(
                "order_id",
                "nunique",
            )
        )
    )

    result["order_share"] = (
        result["orders"]
        / denominator
    )

    result.insert(
        0,
        "group",
        group_name,
    )

    return result


def main():

    print("=" * 76)
    print("HIGH-VALUE USER PAYMENT BEHAVIOR ANALYSIS")
    print("=" * 76)

    # --------------------------------------------------------
    # 1. Load standardized inputs
    # --------------------------------------------------------
    users = pd.read_csv(
        USER_BASE_PATH
    )

    payments = pd.read_csv(
        PAYMENT_BASE_PATH,
        parse_dates=["order_purchase_timestamp"],
    )

    print("\n[1] INPUT")
    print(
        f"User-base rows: "
        f"{len(users):,}"
    )
    print(
        f"Payment-base rows: "
        f"{len(payments):,}"
    )

    if len(users) != 87214:
        raise ValueError(
            "User base must contain 87,214 users."
        )

    if len(payments) != 90127:
        raise ValueError(
            "Payment base must contain 90,127 orders."
        )

    if users[
        "customer_unique_id"
    ].duplicated().any():
        raise ValueError(
            "User base contains duplicate users."
        )

    if payments[
        "order_id"
    ].duplicated().any():
        raise ValueError(
            "Payment base contains duplicate orders."
        )

    print("Input validation: PASS")

    # --------------------------------------------------------
    # 2. Attach high-value flag
    # --------------------------------------------------------
    user_flags = users[
        [
            "customer_unique_id",
            "is_high_value_user",
            "is_high_value_churn_user",
            "frequency",
            "monetary",
        ]
    ].copy()

    orders = payments.merge(
        user_flags,
        on="customer_unique_id",
        how="left",
        validate="many_to_one",
    )

    missing_user_flag = (
        orders["is_high_value_user"]
        .isna()
        .sum()
    )

    print("\n[2] USER MATCHING")
    print(
        f"Orders missing user flag: "
        f"{missing_user_flag:,}"
    )

    if missing_user_flag != 0:
        raise ValueError(
            "Some orders failed to match user base."
        )

    print("User matching: PASS")

    # --------------------------------------------------------
    # 3. High-value population reconciliation
    # --------------------------------------------------------
    high_value_orders = orders[
        orders["is_high_value_user"] == 1
    ].copy()

    high_value_users = users[
        users["is_high_value_user"] == 1
    ].copy()

    expected_hv_orders = int(
        high_value_users["frequency"].sum()
    )

    actual_hv_orders = (
        high_value_orders[
            "order_id"
        ].nunique()
    )

    expected_hv_gmv = (
        high_value_users["monetary"].sum()
    )

    actual_hv_gmv = (
        high_value_orders[
            "payment_gmv"
        ].fillna(0).sum()
    )

    print("\n[3] HIGH-VALUE RECONCILIATION")
    print(
        f"High-value users: "
        f"{len(high_value_users):,}"
    )
    print(
        f"Expected orders from RFM Frequency: "
        f"{expected_hv_orders:,}"
    )
    print(
        f"Actual orders in payment base: "
        f"{actual_hv_orders:,}"
    )
    print(
        f"Expected GMV from RFM Monetary: "
        f"{expected_hv_gmv:,.2f}"
    )
    print(
        f"Actual GMV in payment base: "
        f"{actual_hv_gmv:,.2f}"
    )

    if expected_hv_orders != actual_hv_orders:
        raise ValueError(
            "High-value order count does not reconcile."
        )

    if abs(
        expected_hv_gmv
        - actual_hv_gmv
    ) > 0.01:
        raise ValueError(
            "High-value GMV does not reconcile."
        )

    print("High-value reconciliation: PASS")

    # --------------------------------------------------------
    # 4. Payment-method order share
    # --------------------------------------------------------
    overall_order_share = (
        build_order_share(
            orders,
            "all_users",
        )
    )

    hv_order_share = (
        build_order_share(
            high_value_orders,
            "high_value_users",
        )
    )

    order_share = pd.concat(
        [
            overall_order_share,
            hv_order_share,
        ],
        ignore_index=True,
    )

    print("\n[4] MAIN PAYMENT TYPE ORDER SHARE")

    display_order_share = (
        order_share.copy()
    )

    display_order_share[
        "order_share"
    ] = display_order_share[
        "order_share"
    ].map(
        lambda x: f"{x:.2%}"
    )

    print(
        display_order_share
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # 5. Actual payment-type GMV
    # --------------------------------------------------------
    con = sqlite3.connect(
        DB_PATH
    )

    raw_payments = pd.read_sql_query(
        """
        SELECT
            order_id,
            payment_sequential,
            payment_type,
            payment_value
        FROM order_payments
        WHERE payment_value IS NOT NULL
          AND payment_value > 0
        """,
        con,
    )

    con.close()

    order_flags = orders[
        [
            "order_id",
            "customer_unique_id",
            "is_high_value_user",
        ]
    ].copy()

    payment_detail = (
        raw_payments.merge(
            order_flags,
            on="order_id",
            how="inner",
            validate="many_to_one",
        )
    )

    def build_gmv_share(
        df,
        group_name,
    ):

        total_gmv = (
            df["payment_value"]
            .sum()
        )

        result = (
            df.groupby(
                "payment_type",
                as_index=False,
                dropna=False,
            )
            .agg(
                payment_gmv=(
                    "payment_value",
                    "sum",
                )
            )
        )

        result["gmv_share"] = (
            result["payment_gmv"]
            / total_gmv
        )

        result.insert(
            0,
            "group",
            group_name,
        )

        return result

    overall_gmv_share = (
        build_gmv_share(
            payment_detail,
            "all_users",
        )
    )

    hv_payment_detail = (
        payment_detail[
            payment_detail[
                "is_high_value_user"
            ] == 1
        ].copy()
    )

    hv_gmv_share = (
        build_gmv_share(
            hv_payment_detail,
            "high_value_users",
        )
    )

    gmv_share = pd.concat(
        [
            overall_gmv_share,
            hv_gmv_share,
        ],
        ignore_index=True,
    )

    print("\n[5] ACTUAL PAYMENT-TYPE GMV SHARE")

    display_gmv_share = (
        gmv_share.copy()
    )

    display_gmv_share[
        "gmv_share"
    ] = display_gmv_share[
        "gmv_share"
    ].map(
        lambda x: f"{x:.2%}"
    )

    print(
        display_gmv_share
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # 6. Installment comparison
    # --------------------------------------------------------
    overall_summary = (
        build_group_summary(
            orders,
            "all_users",
        )
    )

    hv_summary = (
        build_group_summary(
            high_value_orders,
            "high_value_users",
        )
    )

    installment_profile = (
        pd.DataFrame(
            [
                overall_summary,
                hv_summary,
            ]
        )
    )

    print("\n[6] INSTALLMENT / PAYMENT SUMMARY")

    display_summary = (
        installment_profile.copy()
    )

    for col in [
        "one_time_share_valid",
        "installment_share_valid",
        "mixed_payment_share",
    ]:
        display_summary[col] = (
            display_summary[col]
            .map(
                lambda x:
                    "NULL"
                    if pd.isna(x)
                    else f"{x:.2%}"
            )
        )

    print(
        display_summary
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # 7. Save outputs
    # --------------------------------------------------------
    order_share.to_csv(
        ORDER_SHARE_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    gmv_share.to_csv(
        GMV_SHARE_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    installment_profile.to_csv(
        INSTALLMENT_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    installment_profile.to_csv(
        SUMMARY_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n[7] OUTPUTS")
    print(
        f"Saved: "
        f"{ORDER_SHARE_OUTPUT}"
    )
    print(
        f"Saved: "
        f"{GMV_SHARE_OUTPUT}"
    )
    print(
        f"Saved: "
        f"{INSTALLMENT_OUTPUT}"
    )
    print(
        f"Saved: "
        f"{SUMMARY_OUTPUT}"
    )

    print("\n" + "=" * 76)
    print("FINAL RESULT: PASS")
    print(
        "High-value payment behavior outputs "
        "successfully created."
    )
    print(
        "IMPORTANT: high-value population = 4 users; "
        "results are descriptive only."
    )
    print("=" * 76)


if __name__ == "__main__":
    main()
