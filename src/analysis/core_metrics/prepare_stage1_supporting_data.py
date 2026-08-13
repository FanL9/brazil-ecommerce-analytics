"""
Prepare supporting datasets for the Stage 1 core-metrics dashboard.

Outputs
-------
1. outputs/data/01_core_metrics/stage1_cohort_retention.csv
2. outputs/data/01_core_metrics/stage1_category_item_base.csv

Purpose
-------
The order-level Stage 1 base safely supports most metrics, but two metrics
require different grains:

- M09 Customer Retention Rate:
  cohort_month + retention_month_number.
- M18 Category Sales Share:
  order_id + order_item_id.

These outputs preserve those formal grains instead of forcing one-to-many
data into the order-level dashboard base.

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

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "data"
    / "01_core_metrics"
)

COHORT_OUTPUT_PATH = (
    OUTPUT_DIR
    / "stage1_cohort_retention.csv"
)

CATEGORY_OUTPUT_PATH = (
    OUTPUT_DIR
    / "stage1_category_item_base.csv"
)

REQUIRED_OBJECTS = {
    "customers",
    "products",
    "vw_orders_clean",
    "vw_order_items_clean",
}


COHORT_QUERY = """
WITH RECURSIVE user_month_activity AS (
    SELECT
        c.customer_unique_id,
        DATE(
            o.order_purchase_timestamp,
            'start of month'
        ) AS activity_month
    FROM vw_orders_clean AS o
    INNER JOIN customers AS c
        ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
      AND o.order_purchase_timestamp IS NOT NULL
      AND c.customer_unique_id IS NOT NULL
    GROUP BY
        c.customer_unique_id,
        activity_month
),
user_cohort AS (
    SELECT
        customer_unique_id,
        MIN(activity_month) AS cohort_month
    FROM user_month_activity
    GROUP BY customer_unique_id
),
cohort_size AS (
    SELECT
        cohort_month,
        COUNT(*) AS cohort_customer_count
    FROM user_cohort
    GROUP BY cohort_month
),
observation_limit AS (
    SELECT
        MAX(activity_month) AS last_observed_month
    FROM user_month_activity
),
cohort_month_grid AS (
    SELECT
        c.cohort_month,
        c.cohort_month AS activity_month,
        o.last_observed_month
    FROM cohort_size AS c
    CROSS JOIN observation_limit AS o

    UNION ALL

    SELECT
        cohort_month,
        DATE(activity_month, '+1 month'),
        last_observed_month
    FROM cohort_month_grid
    WHERE activity_month < last_observed_month
),
retained AS (
    SELECT
        u.cohort_month,
        a.activity_month,
        COUNT(*) AS retained_customer_count
    FROM user_month_activity AS a
    INNER JOIN user_cohort AS u
        ON u.customer_unique_id = a.customer_unique_id
    GROUP BY
        u.cohort_month,
        a.activity_month
)
SELECT
    STRFTIME(
        '%Y-%m',
        g.cohort_month
    ) AS cohort_month,

    CAST(
        (
            CAST(
                STRFTIME('%Y', g.activity_month)
                AS INTEGER
            )
            - CAST(
                STRFTIME('%Y', g.cohort_month)
                AS INTEGER
            )
        ) * 12
        + CAST(
            STRFTIME('%m', g.activity_month)
            AS INTEGER
        )
        - CAST(
            STRFTIME('%m', g.cohort_month)
            AS INTEGER
        )
        AS INTEGER
    ) AS retention_month_number,

    c.cohort_customer_count,

    COALESCE(
        r.retained_customer_count,
        0
    ) AS retained_customer_count,

    1.0 * COALESCE(
        r.retained_customer_count,
        0
    )
    / NULLIF(
        c.cohort_customer_count,
        0
    ) AS customer_retention_rate

FROM cohort_month_grid AS g

INNER JOIN cohort_size AS c
    ON c.cohort_month = g.cohort_month

LEFT JOIN retained AS r
    ON r.cohort_month = g.cohort_month
   AND r.activity_month = g.activity_month

ORDER BY
    g.cohort_month,
    retention_month_number;
"""


CATEGORY_ITEM_QUERY = """
SELECT
    o.order_id,
    i.order_item_id,
    o.order_purchase_timestamp,
    DATE(
        o.order_purchase_timestamp
    ) AS purchase_date,
    STRFTIME(
        '%Y-%m',
        o.order_purchase_timestamp
    ) AS purchase_month,

    CASE
        WHEN p.product_category_name IS NULL
          OR TRIM(p.product_category_name) = ''
        THEN 'unknown'
        ELSE p.product_category_name
    END AS product_category,

    i.price

FROM vw_order_items_clean AS i

INNER JOIN vw_orders_clean AS o
    ON o.order_id = i.order_id

INNER JOIN products AS p
    ON p.product_id = i.product_id

WHERE o.order_status = 'delivered'
  AND i.price IS NOT NULL
  AND i.price >= 0

ORDER BY
    o.order_purchase_timestamp,
    o.order_id,
    i.order_item_id;
"""


def get_existing_objects(
    connection: sqlite3.Connection,
) -> set[str]:
    """Return available SQLite tables and views."""
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
    """Confirm that all supporting-data prerequisites exist."""
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


def load_cohort_retention(
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """Load the formal M09 natural-month cohort result."""
    return pd.read_sql_query(
        COHORT_QUERY,
        connection,
    )


def load_category_item_base(
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """Load the formal M18 item-grain dashboard base."""
    return pd.read_sql_query(
        CATEGORY_ITEM_QUERY,
        connection,
    )


def validate_cohort_retention(
    cohort: pd.DataFrame,
) -> dict[str, int]:
    """Validate M09 grain and core invariants."""
    if cohort.empty:
        raise ValueError(
            "Stage 1 cohort query returned no rows."
        )

    required_columns = {
        "cohort_month",
        "retention_month_number",
        "cohort_customer_count",
        "retained_customer_count",
        "customer_retention_rate",
    }

    missing = required_columns - set(cohort.columns)

    if missing:
        raise ValueError(
            "Cohort output is missing columns: "
            + ", ".join(sorted(missing))
        )

    duplicate_keys = int(
        cohort.duplicated(
            subset=[
                "cohort_month",
                "retention_month_number",
            ]
        ).sum()
    )

    if duplicate_keys:
        raise ValueError(
            "Duplicate cohort-month keys found: "
            f"{duplicate_keys}"
        )

    month_zero = cohort.loc[
        cohort["retention_month_number"] == 0
    ]

    if month_zero.empty:
        raise ValueError(
            "Cohort output contains no Month 0 rows."
        )

    if not (
        month_zero["customer_retention_rate"]
        .round(12)
        .eq(1.0)
        .all()
    ):
        raise ValueError(
            "Not all cohort Month 0 retention rates equal 1."
        )

    if (
        cohort["retained_customer_count"]
        > cohort["cohort_customer_count"]
    ).any():
        raise ValueError(
            "Retained customer count exceeds cohort size."
        )

    if (
        cohort["customer_retention_rate"] < 0
    ).any() or (
        cohort["customer_retention_rate"] > 1
    ).any():
        raise ValueError(
            "Retention rates outside 0..1 found."
        )

    return {
        "cohort_rows": int(len(cohort)),
        "cohort_months": int(
            cohort["cohort_month"].nunique()
        ),
        "max_retention_month": int(
            cohort[
                "retention_month_number"
            ].max()
        ),
    }


def validate_category_item_base(
    category_items: pd.DataFrame,
) -> dict[str, float | int]:
    """Validate M18 grain and full-observation totals."""
    if category_items.empty:
        raise ValueError(
            "Stage 1 category-item query returned no rows."
        )

    required_columns = {
        "order_id",
        "order_item_id",
        "order_purchase_timestamp",
        "purchase_month",
        "product_category",
        "price",
    }

    missing = (
        required_columns
        - set(category_items.columns)
    )

    if missing:
        raise ValueError(
            "Category-item output is missing columns: "
            + ", ".join(sorted(missing))
        )

    duplicate_keys = int(
        category_items.duplicated(
            subset=[
                "order_id",
                "order_item_id",
            ]
        ).sum()
    )

    if duplicate_keys:
        raise ValueError(
            "Duplicate order_id + order_item_id rows found: "
            f"{duplicate_keys}"
        )

    if category_items[
        "product_category"
    ].isna().any():
        raise ValueError(
            "NULL category values remain after unknown mapping."
        )

    if (
        category_items["price"] < 0
    ).any():
        raise ValueError(
            "Negative item price values found."
        )

    category_summary = (
        category_items.groupby(
            "product_category",
            dropna=False,
            as_index=False,
        )
        .agg(
            category_sales_amount=(
                "price",
                "sum",
            )
        )
    )

    total_sales = round(
        float(
            category_summary[
                "category_sales_amount"
            ].sum()
        ),
        2,
    )

    category_summary[
        "category_sales_share"
    ] = (
        category_summary[
            "category_sales_amount"
        ]
        / category_summary[
            "category_sales_amount"
        ].sum()
    )

    share_sum = float(
        category_summary[
            "category_sales_share"
        ].sum()
    )

    if abs(share_sum - 1.0) > 1e-9:
        raise ValueError(
            "Category sales shares do not sum to 1."
        )

    return {
        "item_rows": int(len(category_items)),
        "category_rows": int(
            category_summary[
                "product_category"
            ].nunique()
        ),
        "total_category_sales": total_sales,
    }


def export_data(
    cohort: pd.DataFrame,
    category_items: pd.DataFrame,
) -> None:
    """Export both validated Stage 1 supporting datasets."""
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    cohort.to_csv(
        COHORT_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    category_items.to_csv(
        CATEGORY_OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )


def main() -> None:
    """Build, validate, and export Stage 1 supporting data."""
    print("Preparing Stage 1 supporting dashboard data...")

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            "Database not found:\n"
            f"{DATABASE_PATH}"
        )

    with sqlite3.connect(
        DATABASE_PATH
    ) as connection:
        validate_required_objects(connection)

        cohort = load_cohort_retention(
            connection
        )
        category_items = load_category_item_base(
            connection
        )

    cohort_summary = validate_cohort_retention(
        cohort
    )
    category_summary = validate_category_item_base(
        category_items
    )

    export_data(
        cohort,
        category_items,
    )

    print("\nValidation passed.")

    print(
        "  Cohort result rows: "
        f"{cohort_summary['cohort_rows']:,}"
    )
    print(
        "  Cohort start months: "
        f"{cohort_summary['cohort_months']:,}"
    )
    print(
        "  Max retention month: "
        f"{cohort_summary['max_retention_month']}"
    )

    print(
        "  Category item rows: "
        f"{category_summary['item_rows']:,}"
    )
    print(
        "  Category rows: "
        f"{category_summary['category_rows']:,}"
    )
    print(
        "  Total category sales: BRL "
        f"{category_summary['total_category_sales']:,.2f}"
    )

    print("\nCSVs exported:")
    print(f"  {COHORT_OUTPUT_PATH}")
    print(f"  {CATEGORY_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
