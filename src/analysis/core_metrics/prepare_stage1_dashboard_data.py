"""
Prepare the Stage 1 order-level dataset used by the core-metrics dashboard.

Output
------
outputs/data/01_core_metrics/stage1_order_metric_base.csv

Data grain
----------
One row per order_id.

Purpose
-------
This dataset is the safe order-level base for Stage 1 metrics M01-M17.
It preserves all cleaned order statuses so cancellation rate can use all
orders, while metric-specific flags distinguish delivered and paid-delivered
cohorts. Payment, delivery, and review data are joined only after they have
been reduced to order level.

Prerequisites
-------------
1. database/brazil_ecommerce.db exists.
2. sql/02_data_cleaning/data_cleaning_rules.sql has been executed.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATABASE_PATH = (
    PROJECT_ROOT
    / "database"
    / "brazil_ecommerce.db"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "01_core_metrics"
    / "stage1_order_metric_base.csv"
)

REQUIRED_OBJECTS = {
    "customers",
    "vw_orders_clean",
    "vw_order_payments_clean",
    "vw_delivery_analysis_clean",
    "vw_order_reviews_order_level",
}


ORDER_BASE_QUERY = """
WITH payment_by_order AS (
    SELECT
        order_id,
        SUM(payment_value) AS order_payment_amount
    FROM vw_order_payments_clean
    GROUP BY order_id
),
first_delivered_purchase AS (
    SELECT
        c.customer_unique_id,
        MIN(o.order_purchase_timestamp)
            AS first_delivered_purchase_timestamp
    FROM vw_orders_clean AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp IS NOT NULL
      AND c.customer_unique_id IS NOT NULL
    GROUP BY c.customer_unique_id
)
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.customer_state,

    o.order_status,
    o.order_purchase_timestamp,
    DATE(o.order_purchase_timestamp) AS purchase_date,
    STRFTIME('%Y-%m', o.order_purchase_timestamp) AS purchase_month,

    CASE
        WHEN o.order_status = 'delivered'
        THEN 1 ELSE 0
    END AS is_valid_order,

    p.order_payment_amount,

    CASE
        WHEN p.order_payment_amount > 0
        THEN 1 ELSE 0
    END AS has_positive_payment,

    CASE
        WHEN o.order_status = 'delivered'
         AND p.order_payment_amount > 0
        THEN 1 ELSE 0
    END AS is_paid_delivered_order,

    fp.first_delivered_purchase_timestamp,
    SUBSTR(
        fp.first_delivered_purchase_timestamp,
        1,
        7
    ) AS first_delivered_purchase_month,

    CASE
        WHEN o.order_status = 'delivered'
         AND fp.first_delivered_purchase_timestamp IS NOT NULL
         AND STRFTIME('%Y-%m', o.order_purchase_timestamp)
             = SUBSTR(fp.first_delivered_purchase_timestamp, 1, 7)
        THEN 1 ELSE 0
    END AS is_first_delivered_month,

    d.delivery_days,

    CASE
        WHEN o.order_status = 'delivered'
         AND d.order_id IS NOT NULL
         AND o.order_estimated_delivery_date IS NOT NULL
         AND JULIANDAY(o.order_estimated_delivery_date) IS NOT NULL
        THEN 1 ELSE 0
    END AS is_delivery_evaluable,

    CASE
        WHEN o.order_status = 'delivered'
         AND d.order_id IS NOT NULL
         AND o.order_estimated_delivery_date IS NOT NULL
         AND JULIANDAY(o.order_estimated_delivery_date) IS NOT NULL
        THEN CASE
            WHEN JULIANDAY(o.order_delivered_customer_date)
               > JULIANDAY(o.order_estimated_delivery_date)
            THEN 1 ELSE 0
        END
        ELSE NULL
    END AS is_late_delivery,

    r.review_score,

    CASE
        WHEN o.order_status = 'delivered'
         AND r.order_id IS NOT NULL
        THEN 1 ELSE 0
    END AS has_valid_review,

    CASE
        WHEN o.order_status = 'delivered'
         AND r.order_id IS NOT NULL
        THEN CASE
            WHEN r.review_score >= 4
            THEN 1 ELSE 0
        END
        ELSE NULL
    END AS is_positive_review

FROM vw_orders_clean AS o

INNER JOIN customers AS c
    ON c.customer_id = o.customer_id

LEFT JOIN payment_by_order AS p
    ON p.order_id = o.order_id

LEFT JOIN first_delivered_purchase AS fp
    ON fp.customer_unique_id = c.customer_unique_id

LEFT JOIN vw_delivery_analysis_clean AS d
    ON d.order_id = o.order_id

LEFT JOIN vw_order_reviews_order_level AS r
    ON r.order_id = o.order_id

ORDER BY
    o.order_purchase_timestamp,
    o.order_id;
"""


def get_existing_objects(
    connection: sqlite3.Connection,
) -> set[str]:
    """Return table and view names available in SQLite."""
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type IN ('table', 'view');
        """
    ).fetchall()
    return {row[0] for row in rows}


def validate_required_objects(
    connection: sqlite3.Connection,
) -> None:
    """Confirm that all Stage 1 prerequisites exist."""
    existing = get_existing_objects(connection)
    missing = REQUIRED_OBJECTS - existing

    if missing:
        missing_text = ", ".join(sorted(missing))
        raise RuntimeError(
            "Required Stage 1 objects are missing: "
            f"{missing_text}\n"
            "Run sql/02_data_cleaning/"
            "data_cleaning_rules.sql first."
        )


def load_order_base(
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """Load the Stage 1 one-row-per-order base."""
    return pd.read_sql_query(
        ORDER_BASE_QUERY,
        connection,
    )


def validate_order_base(
    order_base: pd.DataFrame,
) -> dict[str, float | int]:
    """Validate grain, metric cohorts, and key invariants."""
    if order_base.empty:
        raise ValueError(
            "Stage 1 order base query returned no rows."
        )

    required_columns = {
        "order_id",
        "customer_unique_id",
        "order_status",
        "order_purchase_timestamp",
        "purchase_month",
        "is_valid_order",
        "order_payment_amount",
        "is_paid_delivered_order",
        "first_delivered_purchase_timestamp",
        "delivery_days",
        "is_delivery_evaluable",
        "is_late_delivery",
        "review_score",
        "has_valid_review",
        "is_positive_review",
    }

    missing_columns = (
        required_columns - set(order_base.columns)
    )

    if missing_columns:
        raise ValueError(
            "Stage 1 order base is missing columns: "
            + ", ".join(sorted(missing_columns))
        )

    duplicate_order_ids = int(
        order_base.duplicated(
            subset=["order_id"]
        ).sum()
    )

    if duplicate_order_ids:
        raise ValueError(
            "Duplicate order_id rows found: "
            f"{duplicate_order_ids}"
        )

    essential_columns = [
        "order_id",
        "order_status",
        "order_purchase_timestamp",
        "purchase_month",
    ]

    null_counts = (
        order_base[essential_columns]
        .isna()
        .sum()
    )
    null_counts = null_counts[
        null_counts > 0
    ]

    if not null_counts.empty:
        raise ValueError(
            "Unexpected null values found:\n"
            + null_counts.to_string()
        )

    payment_values = order_base[
        "order_payment_amount"
    ].dropna()

    if (payment_values <= 0).any():
        raise ValueError(
            "Non-positive aggregated payment values found."
        )

    delivery_values = order_base[
        "delivery_days"
    ].dropna()

    if (delivery_values < 0).any():
        raise ValueError(
            "Negative delivery_days values found."
        )

    review_values = order_base[
        "review_score"
    ].dropna()

    if (
        (review_values < 1)
        | (review_values > 5)
    ).any():
        raise ValueError(
            "Review scores outside 1..5 found."
        )

    valid_orders = order_base.loc[
        order_base["is_valid_order"] == 1
    ]

    paid_delivered = order_base.loc[
        order_base["is_paid_delivered_order"] == 1
    ]

    canceled_orders = order_base.loc[
        order_base["order_status"] == "canceled"
    ]

    return {
        "all_orders": int(
            order_base["order_id"].nunique()
        ),
        "valid_orders": int(
            valid_orders["order_id"].nunique()
        ),
        "paid_delivered_orders": int(
            paid_delivered["order_id"].nunique()
        ),
        "active_customers": int(
            valid_orders[
                "customer_unique_id"
            ].nunique()
        ),
        "gmv": round(
            float(
                paid_delivered[
                    "order_payment_amount"
                ].sum()
            ),
            2,
        ),
        "canceled_orders": int(
            canceled_orders[
                "order_id"
            ].nunique()
        ),
    }


def export_order_base(
    order_base: pd.DataFrame,
) -> None:
    """Export the validated Stage 1 base as UTF-8 CSV."""
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    order_base.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )


def main() -> None:
    """Build, validate, and export the Stage 1 order base."""
    print("Preparing Stage 1 order metric base...")

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            "Database not found:\n"
            f"{DATABASE_PATH}"
        )

    with sqlite3.connect(
        DATABASE_PATH
    ) as connection:
        validate_required_objects(connection)
        order_base = load_order_base(connection)

    summary = validate_order_base(order_base)
    export_order_base(order_base)

    print("\nValidation passed.")
    print(
        "  All cleaned orders: "
        f"{summary['all_orders']:,}"
    )
    print(
        "  Valid delivered orders: "
        f"{summary['valid_orders']:,}"
    )
    print(
        "  Paid delivered orders: "
        f"{summary['paid_delivered_orders']:,}"
    )
    print(
        "  Active delivered users: "
        f"{summary['active_customers']:,}"
    )
    print(
        "  GMV: BRL "
        f"{summary['gmv']:,.2f}"
    )
    print(
        "  Canceled orders: "
        f"{summary['canceled_orders']:,}"
    )
    print("\nCSV exported:")
    print(f"  {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
