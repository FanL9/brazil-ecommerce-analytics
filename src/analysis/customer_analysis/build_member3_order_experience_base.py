from pathlib import Path
import sqlite3

import pandas as pd


# ============================================================
# Stage 3 - Member 3
# Build standardized order-level review / delivery base
#
# Highest-priority standard:
# docs/unified_analysis_standards.md
#
# Grain:
# one row per order_id
#
# Review rule:
# legal score = 1..5
# representative review:
# review_answer_timestamp DESC
# review_creation_date DESC
# review_id DESC
#
# Delivery rule:
# delivery_days =
# delivered_customer_date - purchase_timestamp
#
# Delay:
# delivered_customer_date > estimated_delivery_date
# ============================================================

CUTOFF = pd.Timestamp("2018-08-01 00:00:00")

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DB_PATH = (
    PROJECT_ROOT
    / "database"
    / "brazil_ecommerce.db"
)

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

OUTPUT_PATH = (
    DATA_DIR
    / "member3_order_experience_base.csv"
)


def main():

    print("=" * 76)
    print("BUILD STANDARDIZED ORDER EXPERIENCE BASE")
    print("=" * 76)

    # --------------------------------------------------------
    # 1. Fixed-cutoff delivered order population
    # --------------------------------------------------------
    order_base = pd.read_csv(
        ORDER_BASE_PATH,
        parse_dates=["order_purchase_timestamp"],
    )

    order_base = order_base[
        order_base["order_purchase_timestamp"] < CUTOFF
    ].copy()

    if len(order_base) != 90127:
        raise ValueError(
            f"Expected 90,127 orders, got {len(order_base):,}."
        )

    if order_base["order_id"].duplicated().any():
        raise ValueError(
            "customer_order_base is not one row per order."
        )

    print("\n[1] FIXED-CUTOFF ORDER BASE")
    print(f"Orders: {len(order_base):,}")
    print(
        f"Customers: "
        f"{order_base['customer_unique_id'].nunique():,}"
    )

    # --------------------------------------------------------
    # 2. Load raw orders + reviews
    # --------------------------------------------------------
    con = sqlite3.connect(DB_PATH)

    raw_orders = pd.read_sql_query(
        """
        SELECT
            order_id,
            order_status,
            order_purchase_timestamp,
            order_delivered_customer_date,
            order_estimated_delivery_date
        FROM orders
        """,
        con,
    )

    reviews = pd.read_sql_query(
        """
        SELECT
            review_id,
            order_id,
            review_score,
            review_creation_date,
            review_answer_timestamp
        FROM order_reviews
        """,
        con,
    )

    con.close()

    for col in [
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]:
        raw_orders[col] = pd.to_datetime(
            raw_orders[col],
            errors="coerce",
        )

    for col in [
        "review_creation_date",
        "review_answer_timestamp",
    ]:
        reviews[col] = pd.to_datetime(
            reviews[col],
            errors="coerce",
        )

    # --------------------------------------------------------
    # 3. Restrict raw orders to official fixed-cutoff orders
    # --------------------------------------------------------
    order_detail = order_base[
        [
            "customer_unique_id",
            "customer_id",
            "order_id",
            "order_purchase_timestamp",
            "order_gmv",
            "is_paid_order",
        ]
    ].merge(
        raw_orders[
            [
                "order_id",
                "order_status",
                "order_delivered_customer_date",
                "order_estimated_delivery_date",
            ]
        ],
        on="order_id",
        how="left",
        validate="one_to_one",
    )

    print("\n[2] RAW ORDER MATCHING")
    print(
        f"Missing raw order matches: "
        f"{order_detail['order_status'].isna().sum():,}"
    )

    if order_detail["order_status"].isna().any():
        raise ValueError(
            "Some official orders are missing from raw orders."
        )

    non_delivered = (
        order_detail["order_status"] != "delivered"
    ).sum()

    print(
        f"Non-delivered rows: "
        f"{non_delivered:,}"
    )

    if non_delivered != 0:
        raise ValueError(
            "Fixed-cutoff customer_order_base contains "
            "non-delivered orders."
        )

    print("Order matching/status validation: PASS")

    # --------------------------------------------------------
    # 4. Select one representative legal review per order
    # --------------------------------------------------------
    legal_reviews = reviews[
        reviews["review_score"].between(1, 5)
    ].copy()

    legal_reviews = (
        legal_reviews
        .sort_values(
            by=[
                "order_id",
                "review_answer_timestamp",
                "review_creation_date",
                "review_id",
            ],
            ascending=[
                True,
                False,
                False,
                False,
            ],
            na_position="last",
        )
        .drop_duplicates(
            subset=["order_id"],
            keep="first",
        )
    )

    representative_review = legal_reviews[
        [
            "order_id",
            "review_id",
            "review_score",
            "review_creation_date",
            "review_answer_timestamp",
        ]
    ].rename(
        columns={
            "review_id": "representative_review_id",
            "review_score": "representative_review_score",
            "review_creation_date":
                "representative_review_creation_date",
            "review_answer_timestamp":
                "representative_review_answer_timestamp",
        }
    )

    print("\n[3] REPRESENTATIVE REVIEW")
    print(
        f"Orders with representative review: "
        f"{len(representative_review):,}"
    )

    if representative_review["order_id"].duplicated().any():
        raise ValueError(
            "Representative review is not one row per order."
        )

    print("Representative review grain: PASS")

    # --------------------------------------------------------
    # 5. Merge representative review
    # --------------------------------------------------------
    base = order_detail.merge(
        representative_review,
        on="order_id",
        how="left",
        validate="one_to_one",
    )

    base["has_valid_review"] = (
        base["representative_review_score"]
        .notna()
    ).astype(int)

    # --------------------------------------------------------
    # 6. Delivery validity
    # --------------------------------------------------------
    valid_delivery = (
        base["order_purchase_timestamp"].notna()
        & base["order_delivered_customer_date"].notna()
        & (
            base["order_delivered_customer_date"]
            >= base["order_purchase_timestamp"]
        )
    )

    base["has_valid_delivery"] = (
        valid_delivery.astype(int)
    )

    base["delivery_days"] = pd.NA

    base.loc[
        valid_delivery,
        "delivery_days",
    ] = (
        (
            base.loc[
                valid_delivery,
                "order_delivered_customer_date",
            ]
            - base.loc[
                valid_delivery,
                "order_purchase_timestamp",
            ]
        )
        .dt.total_seconds()
        / 86400
    )

    base["delivery_days"] = pd.to_numeric(
        base["delivery_days"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # 7. Delay validity / flag
    # --------------------------------------------------------
    valid_delay = (
        valid_delivery
        & base["order_estimated_delivery_date"].notna()
    )

    base["has_valid_delay_measure"] = (
        valid_delay.astype(int)
    )

    base["is_delayed"] = pd.NA

    base.loc[
        valid_delay,
        "is_delayed",
    ] = (
        base.loc[
            valid_delay,
            "order_delivered_customer_date",
        ]
        > base.loc[
            valid_delay,
            "order_estimated_delivery_date",
        ]
    ).astype(int)

    base["is_delayed"] = pd.to_numeric(
        base["is_delayed"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # 8. Validation
    # --------------------------------------------------------
    print("\n[4] FINAL ORDER GRAIN")
    print(f"Rows: {len(base):,}")
    print(
        f"Unique order_id: "
        f"{base['order_id'].nunique():,}"
    )

    if len(base) != 90127:
        raise ValueError(
            "Final experience base must contain 90,127 rows."
        )

    if base["order_id"].duplicated().any():
        raise ValueError(
            "Final experience base contains duplicate orders."
        )

    print("One row per order: PASS")

    print("\n[5] REVIEW COVERAGE")

    review_count = (
        base["has_valid_review"].sum()
    )

    print(
        f"Orders with valid representative review: "
        f"{review_count:,}"
    )

    print(
        f"Orders without valid representative review: "
        f"{len(base) - review_count:,}"
    )

    print(
        f"Review coverage: "
        f"{review_count / len(base):.2%}"
    )

    print("\n[6] DELIVERY COVERAGE")

    delivery_count = (
        base["has_valid_delivery"].sum()
    )

    print(
        f"Orders with valid delivery duration: "
        f"{delivery_count:,}"
    )

    print(
        f"Orders excluded from delivery duration: "
        f"{len(base) - delivery_count:,}"
    )

    if delivery_count > 0:
        print(
            f"Average valid delivery days: "
            f"{base.loc[valid_delivery, 'delivery_days'].mean():.4f}"
        )

    print("\n[7] DELAY COVERAGE")

    delay_count = (
        base["has_valid_delay_measure"].sum()
    )

    delayed_count = (
        base.loc[
            base["has_valid_delay_measure"] == 1,
            "is_delayed",
        ]
        .sum()
    )

    print(
        f"Orders eligible for delay metric: "
        f"{delay_count:,}"
    )

    print(
        f"Delayed orders: "
        f"{int(delayed_count):,}"
    )

    if delay_count > 0:
        print(
            f"Delay rate: "
            f"{delayed_count / delay_count:.2%}"
        )

    # --------------------------------------------------------
    # 9. Score distribution
    # --------------------------------------------------------
    print("\n[8] REPRESENTATIVE REVIEW SCORE DISTRIBUTION")

    print(
        base.loc[
            base["has_valid_review"] == 1,
            "representative_review_score",
        ]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # --------------------------------------------------------
    # 10. Save
    # --------------------------------------------------------
    base.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print("\n[9] OUTPUT")
    print(f"Saved: {OUTPUT_PATH}")
    print(f"Rows written: {len(base):,}")

    print("\n" + "=" * 76)
    print("FINAL RESULT: PASS")
    print(
        "Standardized order-level experience base "
        "successfully created."
    )
    print("=" * 76)


if __name__ == "__main__":
    main()
