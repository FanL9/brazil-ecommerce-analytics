"""
Prepare the order-payment detail dataset used by the interactive dashboard.

Output
------
outputs/data/02_business_overview/dashboard_order_payment_detail.csv

Data grain
----------
One row per order_id + payment_type.

Why this grain is used
----------------------
A small number of orders use more than one payment method. Keeping one row
per order-payment-method preserves the actual GMV split by payment method,
while distinct order_id and customer_unique_id can still be used for order
and user KPIs.

Prerequisites
-------------
1. database/brazil_ecommerce.db exists.
2. sql/02_business_overview/04_business_structure.sql has been executed.
3. The following tables exist:
   - business_structure_order_base
   - business_structure_order_payment_type
   - business_structure_primary_payment
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
    / "02_business_overview"
    / "dashboard_order_payment_detail.csv"
)

REQUIRED_TABLES = {
    "business_structure_order_base",
    "business_structure_order_payment_type",
    "business_structure_primary_payment",
}


DETAIL_QUERY = """
WITH first_paid_purchase AS (
    SELECT
        customer_unique_id,
        MIN(order_purchase_timestamp)
            AS first_paid_purchase_timestamp
    FROM business_structure_order_base
    WHERE is_paid_delivered_order = 1
      AND customer_unique_id IS NOT NULL
    GROUP BY customer_unique_id
)
SELECT
    b.order_id,
    b.customer_id,
    b.customer_unique_id,
    b.customer_state,

    b.order_purchase_timestamp,
    DATE(b.order_purchase_timestamp)
        AS purchase_date,
    b.purchase_month,
    b.purchase_year,

    CASE
        WHEN CAST(SUBSTR(b.purchase_month, 6, 2) AS INTEGER)
             BETWEEN 1 AND 3
        THEN 'Q1'
        WHEN CAST(SUBSTR(b.purchase_month, 6, 2) AS INTEGER)
             BETWEEN 4 AND 6
        THEN 'Q2'
        WHEN CAST(SUBSTR(b.purchase_month, 6, 2) AS INTEGER)
             BETWEEN 7 AND 9
        THEN 'Q3'
        ELSE 'Q4'
    END AS purchase_quarter,

    b.order_payment_amount,
    b.order_value_band,

    opt.payment_type,
    opt.payment_type_amount
        AS payment_gmv,

    ROUND(
        opt.payment_type_amount
        / NULLIF(b.order_payment_amount, 0),
        6
    ) AS payment_share_of_order,

    b.payment_type_count,
    b.is_mixed_payment,

    p.primary_payment_type,

    CASE
        WHEN opt.payment_type = p.primary_payment_type
        THEN 1
        ELSE 0
    END AS is_primary_payment_type,

    CASE
        WHEN opt.payment_type = p.primary_payment_type
        THEN b.order_payment_amount
        ELSE 0
    END AS primary_attributed_order_gmv,

    fp.first_paid_purchase_timestamp,

    SUBSTR(
        fp.first_paid_purchase_timestamp,
        1,
        7
    ) AS first_paid_purchase_month,

    CASE
        WHEN b.purchase_month = SUBSTR(
            fp.first_paid_purchase_timestamp,
            1,
            7
        )
        THEN 1
        ELSE 0
    END AS is_new_user_order_month

FROM business_structure_order_base AS b

INNER JOIN business_structure_order_payment_type AS opt
    ON opt.order_id = b.order_id

INNER JOIN business_structure_primary_payment AS p
    ON p.order_id = b.order_id

LEFT JOIN first_paid_purchase AS fp
    ON fp.customer_unique_id = b.customer_unique_id

WHERE b.is_paid_delivered_order = 1
  AND b.order_payment_amount > 0
  AND b.order_value_band IS NOT NULL
  AND b.customer_state IS NOT NULL
  AND TRIM(b.customer_state) <> ''

ORDER BY
    b.order_purchase_timestamp,
    b.order_id,
    opt.payment_type;
"""


def get_existing_tables(
    connection: sqlite3.Connection,
) -> set[str]:
    """Return all table and view names in the SQLite database."""
    query = """
    SELECT name
    FROM sqlite_master
    WHERE type IN ('table', 'view');
    """

    rows = connection.execute(query).fetchall()
    return {row[0] for row in rows}


def validate_required_tables(
    connection: sqlite3.Connection,
) -> None:
    """Confirm that the business-structure prerequisite tables exist."""
    existing_tables = get_existing_tables(connection)
    missing_tables = REQUIRED_TABLES - existing_tables

    if missing_tables:
        missing_text = ", ".join(sorted(missing_tables))
        raise RuntimeError(
            "Required business-structure tables are missing: "
            f"{missing_text}\n"
            "Run sql/02_business_overview/"
            "04_business_structure.sql first."
        )


def load_dashboard_detail(
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """Load the dashboard detail dataset from SQLite."""
    return pd.read_sql_query(
        DETAIL_QUERY,
        connection,
    )


def validate_dashboard_detail(
    detail: pd.DataFrame,
) -> dict[str, float | int]:
    """Validate grain, totals, key fields, and payment attribution."""
    if detail.empty:
        raise ValueError(
            "The dashboard detail query returned no rows."
        )

    required_columns = {
        "order_id",
        "customer_unique_id",
        "customer_state",
        "order_purchase_timestamp",
        "purchase_month",
        "order_payment_amount",
        "order_value_band",
        "payment_type",
        "payment_gmv",
        "is_primary_payment_type",
        "primary_attributed_order_gmv",
        "first_paid_purchase_month",
        "is_new_user_order_month",
    }

    missing_columns = required_columns - set(detail.columns)

    if missing_columns:
        raise ValueError(
            "Dashboard detail is missing columns: "
            + ", ".join(sorted(missing_columns))
        )

    duplicate_keys = int(
        detail.duplicated(
            subset=["order_id", "payment_type"]
        ).sum()
    )

    if duplicate_keys:
        raise ValueError(
            "Duplicate order_id + payment_type rows found: "
            f"{duplicate_keys}"
        )

    essential_columns = [
        "order_id",
        "customer_unique_id",
        "customer_state",
        "order_purchase_timestamp",
        "purchase_month",
        "order_payment_amount",
        "order_value_band",
        "payment_type",
        "payment_gmv",
        "primary_payment_type",
        "first_paid_purchase_month",
    ]

    null_counts = (
        detail[essential_columns]
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

    if (detail["order_payment_amount"] <= 0).any():
        raise ValueError(
            "Non-positive order_payment_amount values found."
        )

    if (detail["payment_gmv"] <= 0).any():
        raise ValueError(
            "Non-positive payment_gmv values found."
        )

    primary_count_by_order = (
        detail.groupby("order_id")[
            "is_primary_payment_type"
        ]
        .sum()
    )

    invalid_primary_orders = int(
        (primary_count_by_order != 1).sum()
    )

    if invalid_primary_orders:
        raise ValueError(
            "Orders without exactly one primary payment type: "
            f"{invalid_primary_orders}"
        )

    unique_orders = int(
        detail["order_id"].nunique()
    )

    unique_users = int(
        detail["customer_unique_id"].nunique()
    )

    payment_rows = int(len(detail))

    split_gmv = round(
        float(detail["payment_gmv"].sum()),
        2,
    )

    order_level = (
        detail.groupby(
            "order_id",
            as_index=False,
        )
        .agg(
            order_payment_amount=(
                "order_payment_amount",
                "first",
            ),
            split_payment_amount=(
                "payment_gmv",
                "sum",
            ),
        )
    )

    order_gmv = round(
        float(
            order_level[
                "order_payment_amount"
            ].sum()
        ),
        2,
    )

    aggregate_difference = round(
        split_gmv - order_gmv,
        2,
    )

    if abs(aggregate_difference) > 0.05:
        raise ValueError(
            "Split-payment GMV does not match order-level GMV: "
            f"split={split_gmv:,.2f}, "
            f"order={order_gmv:,.2f}, "
            f"difference={aggregate_difference:,.2f}"
        )

    attributed_gmv = round(
        float(
            detail[
                "primary_attributed_order_gmv"
            ].sum()
        ),
        2,
    )

    if abs(attributed_gmv - order_gmv) > 0.05:
        raise ValueError(
            "Primary-attributed GMV does not match "
            "order-level GMV: "
            f"attributed={attributed_gmv:,.2f}, "
            f"order={order_gmv:,.2f}"
        )

    return {
        "payment_rows": payment_rows,
        "unique_orders": unique_orders,
        "unique_users": unique_users,
        "split_gmv": split_gmv,
        "order_gmv": order_gmv,
        "mixed_payment_orders": int(
            detail.loc[
                detail["is_mixed_payment"] == 1,
                "order_id",
            ].nunique()
        ),
    }


def export_dashboard_detail(
    detail: pd.DataFrame,
) -> None:
    """Export the validated detail dataset as UTF-8 CSV."""
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    detail.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )


def main() -> None:
    """Build, validate, and export the dashboard detail dataset."""
    print("Preparing dashboard order-payment detail data...")

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            "Database not found:\n"
            f"{DATABASE_PATH}\n"
            "Confirm that the script is stored at "
            "src/analysis/business_overview/."
        )

    with sqlite3.connect(DATABASE_PATH) as connection:
        validate_required_tables(connection)
        detail = load_dashboard_detail(connection)

    summary = validate_dashboard_detail(detail)
    export_dashboard_detail(detail)

    print("\nValidation passed.")
    print(
        "  Payment-detail rows: "
        f"{summary['payment_rows']:,}"
    )
    print(
        "  Distinct paid delivered orders: "
        f"{summary['unique_orders']:,}"
    )
    print(
        "  Distinct users: "
        f"{summary['unique_users']:,}"
    )
    print(
        "  Mixed-payment orders: "
        f"{summary['mixed_payment_orders']:,}"
    )
    print(
        "  GMV: BRL "
        f"{summary['order_gmv']:,.2f}"
    )
    print("\nCSV exported:")
    print(f"  {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
