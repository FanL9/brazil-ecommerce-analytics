"""Rebuild, validate, and export the stage-four category common layer."""

from __future__ import annotations

import argparse
import math
import sqlite3
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE = PROJECT_ROOT / "database" / "brazil_ecommerce.db"
CLEANING_SQL = PROJECT_ROOT / "sql" / "02_data_cleaning" / "data_cleaning_rules.sql"
CATEGORY_SQL = (
    PROJECT_ROOT / "sql" / "06_product_analysis" / "category_order_base.sql"
)
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "data" / "06_product_analysis"

QUERY_MAP = {
    "category_sales_base": """
        SELECT
            category_name,
            sales_amount,
            sales_share,
            category_order_count,
            item_count,
            avg_item_price,
            items_per_order,
            sales_rank
        FROM category_sales_base
        ORDER BY sales_rank, category_name
    """,
    "category_monthly_sales_base": """
        SELECT
            purchase_month,
            category_name,
            monthly_sales_amount,
            monthly_order_count,
            monthly_item_count,
            avg_item_price,
            items_per_order
        FROM category_monthly_sales_base
        ORDER BY purchase_month, category_name
    """,
}


def scalar(connection: sqlite3.Connection, query: str) -> int | float | None:
    """Return the first column of a one-row validation query."""

    return connection.execute(query).fetchone()[0]


def rebuild_common_layer(database_path: Path) -> None:
    """Recreate cleaning views and the four category common-layer tables."""

    required_paths = (database_path, CLEANING_SQL, CATEGORY_SQL)
    missing = [path for path in required_paths if not path.is_file()]
    if missing:
        joined = "\n".join(f"  - {path}" for path in missing)
        raise FileNotFoundError(f"Required file(s) not found:\n{joined}")

    with sqlite3.connect(database_path) as connection:
        connection.executescript(CLEANING_SQL.read_text(encoding="utf-8-sig"))
        connection.executescript(CATEGORY_SQL.read_text(encoding="utf-8-sig"))


def validate_common_layer(database_path: Path) -> dict[str, int | float]:
    """Run strict grain, reconciliation, unknown-category, and NULL checks."""

    with sqlite3.connect(database_path) as connection:
        report: dict[str, int | float] = {
            "category_count": scalar(
                connection, "SELECT COUNT(*) FROM category_sales_base"
            ),
            "monthly_category_rows": scalar(
                connection, "SELECT COUNT(*) FROM category_monthly_sales_base"
            ),
            "item_base_rows": scalar(
                connection, "SELECT COUNT(*) FROM category_item_base"
            ),
            "order_category_rows": scalar(
                connection, "SELECT COUNT(*) FROM category_order_base"
            ),
            "category_sales_amount": scalar(
                connection,
                "SELECT SUM(sales_amount) FROM category_sales_base",
            ),
            "item_base_sales_amount": scalar(
                connection, "SELECT SUM(price) FROM category_item_base"
            ),
            "monthly_sales_amount": scalar(
                connection,
                "SELECT SUM(monthly_sales_amount) "
                "FROM category_monthly_sales_base",
            ),
            "category_item_count": scalar(
                connection, "SELECT SUM(item_count) FROM category_sales_base"
            ),
            "monthly_item_count": scalar(
                connection,
                "SELECT SUM(monthly_item_count) FROM category_monthly_sales_base",
            ),
            "category_order_count": scalar(
                connection,
                "SELECT SUM(category_order_count) FROM category_sales_base",
            ),
            "sales_share_sum": scalar(
                connection, "SELECT SUM(sales_share) FROM category_sales_base"
            ),
            "unknown_item_rows": scalar(
                connection,
                "SELECT COUNT(*) FROM category_item_base "
                "WHERE category_name = 'unknown'",
            ),
            "unknown_category_rows": scalar(
                connection,
                "SELECT COUNT(*) FROM category_sales_base "
                "WHERE category_name = 'unknown'",
            ),
            "unknown_monthly_rows": scalar(
                connection,
                "SELECT COUNT(*) FROM category_monthly_sales_base "
                "WHERE category_name = 'unknown'",
            ),
            "boundary_month_rows": scalar(
                connection,
                "SELECT COUNT(*) FROM category_monthly_sales_base "
                "WHERE purchase_month IN ('2016-09', '2018-08')",
            ),
        }

        duplicate_categories = scalar(
            connection,
            "SELECT COUNT(*) FROM ("
            "SELECT category_name FROM category_sales_base "
            "GROUP BY category_name HAVING COUNT(*) > 1)",
        )
        duplicate_month_categories = scalar(
            connection,
            "SELECT COUNT(*) FROM ("
            "SELECT purchase_month, category_name "
            "FROM category_monthly_sales_base "
            "GROUP BY purchase_month, category_name HAVING COUNT(*) > 1)",
        )
        duplicate_order_categories = scalar(
            connection,
            "SELECT COUNT(*) FROM ("
            "SELECT order_id, category_name FROM category_order_base "
            "GROUP BY order_id, category_name HAVING COUNT(*) > 1)",
        )
        null_or_blank_category_rows = scalar(
            connection,
            "SELECT COUNT(*) FROM category_sales_base "
            "WHERE category_name IS NULL OR TRIM(category_name) = ''",
        )
        null_category_metrics = scalar(
            connection,
            "SELECT COUNT(*) FROM category_sales_base WHERE "
            "sales_amount IS NULL OR sales_share IS NULL OR "
            "category_order_count IS NULL OR item_count IS NULL OR "
            "avg_item_price IS NULL OR items_per_order IS NULL OR "
            "sales_rank IS NULL OR category_order_count <= 0 OR item_count <= 0",
        )
        null_monthly_metrics = scalar(
            connection,
            "SELECT COUNT(*) FROM category_monthly_sales_base WHERE "
            "purchase_month IS NULL OR purchase_month NOT GLOB '????-??' OR "
            "category_name IS NULL OR TRIM(category_name) = '' OR "
            "monthly_sales_amount IS NULL OR monthly_order_count IS NULL OR "
            "monthly_item_count IS NULL OR avg_item_price IS NULL OR "
            "items_per_order IS NULL OR monthly_order_count <= 0 OR "
            "monthly_item_count <= 0",
        )
        order_count_mismatches = scalar(
            connection,
            "WITH expected AS ("
            "SELECT category_name, COUNT(*) AS category_order_count "
            "FROM category_order_base GROUP BY category_name), "
            "mismatches AS ("
            "SELECT s.category_name FROM category_sales_base AS s "
            "LEFT JOIN expected AS e ON e.category_name = s.category_name "
            "WHERE e.category_name IS NULL "
            "OR e.category_order_count <> s.category_order_count "
            "UNION ALL "
            "SELECT e.category_name FROM expected AS e "
            "LEFT JOIN category_sales_base AS s "
            "ON s.category_name = e.category_name "
            "WHERE s.category_name IS NULL) "
            "SELECT COUNT(*) FROM mismatches",
        )
        monthly_count_mismatches = scalar(
            connection,
            "WITH expected AS ("
            "SELECT purchase_month, category_name, COUNT(*) AS order_count, "
            "SUM(category_item_count) AS item_count "
            "FROM category_order_base GROUP BY purchase_month, category_name) "
            "SELECT COUNT(*) FROM category_monthly_sales_base AS m "
            "JOIN expected AS e "
            "ON e.purchase_month = m.purchase_month "
            "AND e.category_name = m.category_name "
            "WHERE m.monthly_order_count <> e.order_count "
            "OR m.monthly_item_count <> e.item_count",
        )
        sales_rank_mismatches = scalar(
            connection,
            "WITH expected AS ("
            "SELECT category_name, ROW_NUMBER() OVER ("
            "ORDER BY sales_amount DESC, category_name ASC) AS expected_rank "
            "FROM category_sales_base) "
            "SELECT COUNT(*) FROM category_sales_base AS s "
            "JOIN expected AS e ON e.category_name = s.category_name "
            "WHERE s.sales_rank <> e.expected_rank",
        )
        non_delivered_item_rows = scalar(
            connection,
            "SELECT COUNT(*) FROM category_item_base AS c "
            "JOIN orders AS o ON o.order_id = c.order_id "
            "WHERE o.order_status <> 'delivered'",
        )
        purchase_timestamp_mismatches = scalar(
            connection,
            "SELECT COUNT(*) FROM category_item_base AS c "
            "JOIN orders AS o ON o.order_id = c.order_id "
            "WHERE c.purchase_timestamp <> o.order_purchase_timestamp "
            "OR c.purchase_month <> STRFTIME('%Y-%m', "
            "o.order_purchase_timestamp)",
        )

    exact_zero_checks = {
        "duplicate category_name": duplicate_categories,
        "duplicate purchase_month + category_name": duplicate_month_categories,
        "duplicate order_id + category_name": duplicate_order_categories,
        "NULL or blank category_name": null_or_blank_category_rows,
        "invalid category summary metrics": null_category_metrics,
        "invalid monthly summary metrics": null_monthly_metrics,
        "category order-count mismatches": order_count_mismatches,
        "monthly order/item-count mismatches": monthly_count_mismatches,
        "sales-rank mismatches": sales_rank_mismatches,
        "non-delivered item rows": non_delivered_item_rows,
        "purchase timestamp mismatches": purchase_timestamp_mismatches,
    }
    failed = {name: value for name, value in exact_zero_checks.items() if value != 0}
    if failed:
        raise RuntimeError(f"Category common-layer validation failed: {failed}")

    amount_tolerance = 1e-6
    if not math.isclose(
        float(report["category_sales_amount"]),
        float(report["item_base_sales_amount"]),
        rel_tol=0.0,
        abs_tol=amount_tolerance,
    ):
        raise RuntimeError("Category sales do not reconcile to category_item_base.")
    if not math.isclose(
        float(report["monthly_sales_amount"]),
        float(report["category_sales_amount"]),
        rel_tol=0.0,
        abs_tol=amount_tolerance,
    ):
        raise RuntimeError("Monthly category sales do not reconcile to category sales.")
    if report["category_item_count"] != report["item_base_rows"]:
        raise RuntimeError("Category item counts do not reconcile to item-base rows.")
    if report["monthly_item_count"] != report["category_item_count"]:
        raise RuntimeError("Monthly item counts do not reconcile to category item counts.")
    if report["category_order_count"] != report["order_category_rows"]:
        raise RuntimeError(
            "Category order counts do not reconcile to order-category rows."
        )
    if not math.isclose(
        float(report["sales_share_sum"]), 1.0, rel_tol=0.0, abs_tol=1e-12
    ):
        raise RuntimeError("Category sales shares do not sum to approximately 1.")
    if report["unknown_item_rows"] > 0 and (
        report["unknown_category_rows"] != 1
        or report["unknown_monthly_rows"] == 0
    ):
        raise RuntimeError("Source unknown categories were not retained in summaries.")
    if report["boundary_month_rows"] == 0:
        raise RuntimeError("Boundary-month category rows were not retained.")

    return report


def export_common_layer(database_path: Path) -> dict[str, pd.DataFrame]:
    """Export both summary tables as UTF-8 BOM CSVs using project conventions."""

    with sqlite3.connect(database_path) as connection:
        data = {
            name: pd.read_sql_query(query, connection)
            for name, query in QUERY_MAP.items()
        }

    category = data["category_sales_base"]
    category["sales_amount"] = category["sales_amount"].round(2)
    category["sales_share"] = category["sales_share"].round(12)
    category["avg_item_price"] = category["avg_item_price"].round(6)
    category["items_per_order"] = category["items_per_order"].round(6)

    monthly = data["category_monthly_sales_base"]
    monthly["monthly_sales_amount"] = monthly["monthly_sales_amount"].round(2)
    monthly["avg_item_price"] = monthly["avg_item_price"].round(6)
    monthly["items_per_order"] = monthly["items_per_order"].round(6)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, frame in data.items():
        frame.to_csv(
            OUTPUT_DIR / f"{name}.csv",
            index=False,
            encoding="utf-8-sig",
        )
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help="SQLite database path (default: database/brazil_ecommerce.db)",
    )
    args = parser.parse_args()
    database_path = args.database
    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path

    rebuild_common_layer(database_path)
    report = validate_common_layer(database_path)
    data = export_common_layer(database_path)

    print("Stage-four category common layer rebuilt and validated.")
    print(
        "Rows: "
        f"category_sales_base={report['category_count']:,}, "
        f"category_monthly_sales_base={report['monthly_category_rows']:,}"
    )
    print(
        "Reconciliation: "
        f"sales_amount={report['category_sales_amount']:.2f}, "
        f"item_count={report['category_item_count']:,}, "
        f"order-category rows={report['category_order_count']:,}, "
        f"sales_share_sum={report['sales_share_sum']:.12f}"
    )
    print(
        "Unknown category: "
        f"item rows={report['unknown_item_rows']:,}, "
        f"monthly rows={report['unknown_monthly_rows']:,}"
    )
    for name, frame in data.items():
        relative_path = (OUTPUT_DIR / f"{name}.csv").relative_to(PROJECT_ROOT)
        print(f"Exported {len(frame):,} rows: {relative_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
