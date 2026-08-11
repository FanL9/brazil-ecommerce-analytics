from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# Stage 3 - Member 3
# High-value user consumption behavior analysis
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# Supplemental rule:
# High-amount order = paid order with order_gmv >= 500 BRL,
# corresponding exactly to the standardized [500, +inf) bin.
#
# High amount is NOT an anomaly definition.
# ============================================================

OBSERVATION_DATE = pd.Timestamp("2018-07-31")
CUTOFF = pd.Timestamp("2018-08-01 00:00:00")
HIGH_AMOUNT_THRESHOLD = 500.0

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

ORDER_BASE_PATH = (
    DATA_DIR
    / "customer_order_base.csv"
)

SUMMARY_OUTPUT = (
    DATA_DIR
    / "high_value_user_consumption_behavior.csv"
)

ORDER_VALUE_OUTPUT = (
    DATA_DIR
    / "high_value_user_order_value_structure.csv"
)

HOURLY_OUTPUT = (
    DATA_DIR
    / "high_value_user_hourly_behavior.csv"
)

DAY_TYPE_OUTPUT = (
    DATA_DIR
    / "high_value_user_weekday_weekend.csv"
)


def safe_divide(numerator, denominator):
    if denominator == 0:
        return None
    return numerator / denominator


def build_summary(users, orders, group_name):

    user_count = users["customer_unique_id"].nunique()

    valid_order_count = orders["order_id"].nunique()

    paid_orders = orders[
        orders["is_paid_order"] == 1
    ].copy()

    paid_order_count = paid_orders["order_id"].nunique()

    gmv = paid_orders["order_gmv"].fillna(0).sum()

    repeat_users = (
        users["frequency"] >= 2
    ).sum()

    high_amount_orders = (
        paid_orders["order_gmv"]
        >= HIGH_AMOUNT_THRESHOLD
    ).sum()

    high_amount_gmv = (
        paid_orders.loc[
            paid_orders["order_gmv"]
            >= HIGH_AMOUNT_THRESHOLD,
            "order_gmv",
        ]
        .sum()
    )

    return {
        "group": group_name,
        "users": user_count,
        "valid_orders": valid_order_count,
        "paid_orders": paid_order_count,
        "gmv": gmv,
        "spend_per_user":
            safe_divide(gmv, user_count),
        "average_order_value":
            safe_divide(gmv, paid_order_count),
        "average_purchase_frequency":
            safe_divide(valid_order_count, user_count),
        "repeat_users": int(repeat_users),
        "repeat_rate":
            safe_divide(repeat_users, user_count),
        "high_amount_threshold_brl":
            HIGH_AMOUNT_THRESHOLD,
        "high_amount_orders":
            int(high_amount_orders),
        "high_amount_order_share":
            safe_divide(
                high_amount_orders,
                paid_order_count,
            ),
        "high_amount_gmv":
            high_amount_gmv,
        "high_amount_gmv_share":
            safe_divide(
                high_amount_gmv,
                gmv,
            ),
    }


def build_order_value_structure(
    orders,
    group_name,
):

    paid = orders[
        orders["is_paid_order"] == 1
    ].copy()

    bins = [
        0,
        50,
        100,
        200,
        500,
        np.inf,
    ]

    labels = [
        "[0,50)",
        "[50,100)",
        "[100,200)",
        "[200,500)",
        "[500,+inf)",
    ]

    paid["order_value_band"] = pd.cut(
        paid["order_gmv"],
        bins=bins,
        labels=labels,
        right=False,
        include_lowest=True,
    )

    if paid["order_value_band"].isna().any():
        raise ValueError(
            f"{group_name}: some paid orders were not "
            "assigned to an order-value band."
        )

    total_orders = paid["order_id"].nunique()
    total_gmv = paid["order_gmv"].sum()

    result = (
        paid.groupby(
            "order_value_band",
            observed=False,
            as_index=False,
        )
        .agg(
            orders=(
                "order_id",
                "nunique",
            ),
            gmv=(
                "order_gmv",
                "sum",
            ),
        )
    )

    result["order_share"] = (
        result["orders"]
        / total_orders
    )

    result["gmv_share"] = (
        result["gmv"]
        / total_gmv
    )

    result.insert(
        0,
        "group",
        group_name,
    )

    return result


def build_hourly_profile(
    orders,
    group_name,
):

    total_orders = orders[
        "order_id"
    ].nunique()

    result = (
        orders.groupby(
            "purchase_hour",
            as_index=False,
        )
        .agg(
            orders=(
                "order_id",
                "nunique",
            ),
            gmv=(
                "order_gmv",
                "sum",
            ),
        )
    )

    result["order_share"] = (
        result["orders"]
        / total_orders
    )

    result.insert(
        0,
        "group",
        group_name,
    )

    return result


def build_day_type_profile(
    orders,
    group_name,
    weekday_days,
    weekend_days,
):

    tmp = orders.copy()

    tmp["day_type"] = np.where(
        tmp["weekday_number"].between(1, 5),
        "weekday",
        "weekend",
    )

    result = (
        tmp.groupby(
            "day_type",
            as_index=False,
        )
        .agg(
            orders=(
                "order_id",
                "nunique",
            ),
            gmv=(
                "order_gmv",
                "sum",
            ),
        )
    )

    day_count_map = {
        "weekday": weekday_days,
        "weekend": weekend_days,
    }

    result["natural_days"] = (
        result["day_type"]
        .map(day_count_map)
    )

    result["avg_daily_orders"] = (
        result["orders"]
        / result["natural_days"]
    )

    total_orders = result["orders"].sum()

    result["order_share"] = (
        result["orders"]
        / total_orders
    )

    result.insert(
        0,
        "group",
        group_name,
    )

    return result


def main():

    print("=" * 76)
    print("HIGH-VALUE USER CONSUMPTION BEHAVIOR ANALYSIS")
    print("=" * 76)

    # --------------------------------------------------------
    # 1. Load standardized inputs
    # --------------------------------------------------------
    users = pd.read_csv(
        USER_BASE_PATH
    )

    orders = pd.read_csv(
        ORDER_BASE_PATH,
        parse_dates=[
            "order_purchase_timestamp",
            "purchase_date",
        ],
    )

    orders = orders[
        orders["order_purchase_timestamp"] < CUTOFF
    ].copy()

    print("\n[1] INPUT")
    print(f"Users: {len(users):,}")
    print(f"Orders: {len(orders):,}")

    if len(users) != 87214:
        raise ValueError(
            "Expected 87,214 user rows."
        )

    if len(orders) != 90127:
        raise ValueError(
            "Expected 90,127 fixed-cutoff orders."
        )

    if users["customer_unique_id"].duplicated().any():
        raise ValueError(
            "User base contains duplicate users."
        )

    if orders["order_id"].duplicated().any():
        raise ValueError(
            "Order base contains duplicate orders."
        )

    print("Input validation: PASS")

    # --------------------------------------------------------
    # 2. Attach high-value flag
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

    orders = orders.merge(
        user_flags[
            [
                "customer_unique_id",
                "is_high_value_user",
                "is_high_value_churn_user",
            ]
        ],
        on="customer_unique_id",
        how="left",
        validate="many_to_one",
    )

    if orders["is_high_value_user"].isna().any():
        raise ValueError(
            "Some orders failed to match user base."
        )

    high_value_users = users[
        users["is_high_value_user"] == 1
    ].copy()

    high_value_orders = orders[
        orders["is_high_value_user"] == 1
    ].copy()

    print("\n[2] HIGH-VALUE RECONCILIATION")
    print(
        f"High-value users: "
        f"{len(high_value_users):,}"
    )

    print(
        f"Expected orders from RFM Frequency: "
        f"{int(high_value_users['frequency'].sum()):,}"
    )

    print(
        f"Actual orders: "
        f"{high_value_orders['order_id'].nunique():,}"
    )

    print(
        f"Expected GMV from RFM Monetary: "
        f"{high_value_users['monetary'].sum():,.2f}"
    )

    print(
        f"Actual GMV: "
        f"{high_value_orders['order_gmv'].sum():,.2f}"
    )

    if (
        int(high_value_users["frequency"].sum())
        != high_value_orders["order_id"].nunique()
    ):
        raise ValueError(
            "High-value order count does not reconcile."
        )

    if abs(
        high_value_users["monetary"].sum()
        - high_value_orders["order_gmv"].sum()
    ) > 0.01:
        raise ValueError(
            "High-value GMV does not reconcile."
        )

    print("High-value reconciliation: PASS")

    # --------------------------------------------------------
    # 3. Core consumption indicators
    # --------------------------------------------------------
    overall_summary = build_summary(
        users,
        orders,
        "all_users",
    )

    hv_summary = build_summary(
        high_value_users,
        high_value_orders,
        "high_value_users",
    )

    summary = pd.DataFrame(
        [
            overall_summary,
            hv_summary,
        ]
    )

    print("\n[3] CORE CONSUMPTION INDICATORS")

    display_summary = summary.copy()

    for col in [
        "repeat_rate",
        "high_amount_order_share",
        "high_amount_gmv_share",
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
        display_summary.to_string(index=False)
    )

    # --------------------------------------------------------
    # 4. Standardized order-value bands
    # --------------------------------------------------------
    overall_value = (
        build_order_value_structure(
            orders,
            "all_users",
        )
    )

    hv_value = (
        build_order_value_structure(
            high_value_orders,
            "high_value_users",
        )
    )

    order_value = pd.concat(
        [
            overall_value,
            hv_value,
        ],
        ignore_index=True,
    )

    print("\n[4] ORDER VALUE STRUCTURE")

    display_value = order_value.copy()

    display_value["order_share"] = (
        display_value["order_share"]
        .map(lambda x: f"{x:.2%}")
    )

    display_value["gmv_share"] = (
        display_value["gmv_share"]
        .map(lambda x: f"{x:.2%}")
    )

    print(
        display_value.to_string(index=False)
    )

    # --------------------------------------------------------
    # 5. Hourly behavior
    # --------------------------------------------------------
    overall_hourly = (
        build_hourly_profile(
            orders,
            "all_users",
        )
    )

    hv_hourly = (
        build_hourly_profile(
            high_value_orders,
            "high_value_users",
        )
    )

    hourly = pd.concat(
        [
            overall_hourly,
            hv_hourly,
        ],
        ignore_index=True,
    )

    print("\n[5] PEAK PURCHASE HOURS")

    for group_name in [
        "all_users",
        "high_value_users",
    ]:
        top_hours = (
            hourly[
                hourly["group"] == group_name
            ]
            .sort_values(
                ["orders", "purchase_hour"],
                ascending=[False, True],
            )
            .head(5)
        )

        print(f"\n{group_name}:")
        print(
            top_hours[
                [
                    "purchase_hour",
                    "orders",
                    "order_share",
                ]
            ].to_string(
                index=False,
                formatters={
                    "order_share":
                        lambda x: f"{x:.2%}"
                },
            )
        )

    # --------------------------------------------------------
    # 6. Weekday / weekend
    # --------------------------------------------------------
    if not orders[
        "weekday_number"
    ].between(1, 7).all():
        raise ValueError(
            "weekday_number contains invalid values."
        )

    calendar = pd.date_range(
        start=orders["purchase_date"].min(),
        end=OBSERVATION_DATE,
        freq="D",
    )

    weekday_days = int(
        (calendar.weekday < 5).sum()
    )

    weekend_days = int(
        (calendar.weekday >= 5).sum()
    )

    overall_day_type = (
        build_day_type_profile(
            orders,
            "all_users",
            weekday_days,
            weekend_days,
        )
    )

    hv_day_type = (
        build_day_type_profile(
            high_value_orders,
            "high_value_users",
            weekday_days,
            weekend_days,
        )
    )

    day_type = pd.concat(
        [
            overall_day_type,
            hv_day_type,
        ],
        ignore_index=True,
    )

    print("\n[6] WEEKDAY / WEEKEND")

    display_day_type = day_type.copy()

    display_day_type["order_share"] = (
        display_day_type["order_share"]
        .map(lambda x: f"{x:.2%}")
    )

    print(
        display_day_type.to_string(index=False)
    )

    # --------------------------------------------------------
    # 7. Validation
    # --------------------------------------------------------
    print("\n[7] VALIDATION")

    paid_orders = orders[
        orders["is_paid_order"] == 1
    ]["order_id"].nunique()

    recovered_paid_orders = (
        overall_value["orders"].sum()
    )

    print(
        f"Paid orders: "
        f"{paid_orders:,}"
    )

    print(
        f"Orders recovered from value bands: "
        f"{recovered_paid_orders:,}"
    )

    if paid_orders != recovered_paid_orders:
        raise ValueError(
            "Order-value bands do not reconcile."
        )

    print("Order-value structure reconciliation: PASS")

    # --------------------------------------------------------
    # 8. Save outputs
    # --------------------------------------------------------
    summary.to_csv(
        SUMMARY_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    order_value.to_csv(
        ORDER_VALUE_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    hourly.to_csv(
        HOURLY_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    day_type.to_csv(
        DAY_TYPE_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n[8] OUTPUTS")
    print(f"Saved: {SUMMARY_OUTPUT}")
    print(f"Saved: {ORDER_VALUE_OUTPUT}")
    print(f"Saved: {HOURLY_OUTPUT}")
    print(f"Saved: {DAY_TYPE_OUTPUT}")

    print("\n" + "=" * 76)
    print("FINAL RESULT: PASS")
    print(
        "High-value consumption behavior outputs "
        "successfully created."
    )
    print(
        "IMPORTANT: high-value population = 4 users; "
        "results are descriptive only."
    )
    print("=" * 76)


if __name__ == "__main__":
    main()
