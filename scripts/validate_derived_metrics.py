"""Execute and validate sql/03_metrics/derived_metrics.sql against SQLite.

Outputs:
    outputs/metric_validation.csv

The checks deliberately recalculate formulas with independent SQL and never write
to the business database.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "database" / "brazil_ecommerce.db"
DEFAULT_SQL = ROOT / "sql" / "03_metrics" / "derived_metrics.sql"
DEFAULT_OUTPUT = ROOT / "outputs" / "metric_validation.csv"
TOLERANCE = 1e-6

FIELDS = [
    "metric_code",
    "metric_name",
    "validation_item",
    "actual_value",
    "expected_value",
    "tolerance",
    "status",
    "notes",
]

METRIC_NAMES = {
    "GLOBAL": "全局可执行性与数据粒度",
    "D01": "复购用户数与复购率",
    "D02": "月度 Cohort 留存率",
    "D03": "观察期历史 LTV",
    "D04": "平均购买频次",
    "D05": "平均复购间隔",
    "D06": "平均配送时长",
    "D07": "延迟送达率",
    "D08": "好评率",
    "D09": "取消率",
}

EXPECTED_COLUMNS = {
    "D01": ["purchasing_users", "repeat_users", "repeat_purchase_rate"],
    "D02": ["cohort_month", "month_number", "cohort_size", "retained_users", "retention_rate"],
    "D03": ["paying_users", "total_customer_revenue", "observed_ltv"],
    "D04": ["delivered_orders", "purchasing_users", "average_purchase_frequency"],
    "D05": ["repeat_users_with_valid_interval", "valid_repeat_intervals", "average_repurchase_interval_days"],
    "D06": ["valid_delivery_orders", "average_delivery_days", "orders_over_60_days", "orders_over_90_days", "orders_over_180_days"],
    "D07": ["evaluable_orders", "delayed_orders", "delayed_delivery_rate"],
    "D08": ["reviewed_orders", "positive_review_orders", "positive_review_rate"],
    "D09_OVERALL": ["total_orders", "canceled_orders", "cancellation_rate"],
    "D09_MONTHLY": ["order_month", "total_orders", "canceled_orders", "cancellation_rate"],
}


def display(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, float):
        return f"{value:.12g}"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def close_enough(actual: Any, expected: Any, tolerance: float = TOLERANCE) -> bool:
    if actual is None or expected is None:
        return actual is expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=tolerance)
    return actual == expected


def parse_metric_sql(sql_text: str) -> dict[str, str]:
    parts = re.split(r"^-- metric: ([A-Z0-9_]+)\s*$", sql_text, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


def row_dicts(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    columns = [item[0] for item in cursor.description or []]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def scalar(connection: sqlite3.Connection, sql: str) -> Any:
    return connection.execute(sql).fetchone()[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--sql", type=Path, default=DEFAULT_SQL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    validations: list[dict[str, str]] = []

    def add(
        code: str,
        item: str,
        actual: Any,
        expected: Any,
        status: str,
        notes: str = "",
        tolerance: Any = "",
    ) -> None:
        assert status in {"PASS", "WARN", "FAIL", "BLOCKED"}
        base_code = "D09" if code.startswith("D09") else code
        validations.append(
            {
                "metric_code": code,
                "metric_name": METRIC_NAMES.get(base_code, code),
                "validation_item": item,
                "actual_value": display(actual),
                "expected_value": display(expected),
                "tolerance": display(tolerance) if tolerance != "" else "",
                "status": status,
                "notes": notes,
            }
        )

    def check(
        code: str,
        item: str,
        actual: Any,
        expected: Any,
        notes: str = "",
        tolerance: float = TOLERANCE,
    ) -> None:
        add(
            code,
            item,
            actual,
            expected,
            "PASS" if close_enough(actual, expected, tolerance) else "FAIL",
            notes,
            tolerance if isinstance(actual, float) or isinstance(expected, float) else "",
        )

    # Blocking prerequisites still produce a truthful CSV.
    if not args.database.is_file() or not args.sql.is_file():
        missing = [str(p) for p in (args.database, args.sql) if not p.is_file()]
        add("GLOBAL", "required_files_exist", missing, "all present", "BLOCKED", "缺少必需文件。")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(validations)
        return 2

    add("GLOBAL", "database_file_exists", str(args.database), "file exists", "PASS")
    sql_text = args.sql.read_text(encoding="utf-8")
    metric_sql = parse_metric_sql(sql_text)
    required_sections = list(EXPECTED_COLUMNS)
    check("GLOBAL", "all_metric_sections_present", sorted(metric_sql), sorted(required_sections))

    connection = sqlite3.connect(f"file:{args.database.resolve().as_posix()}?mode=ro", uri=True)
    try:
        required_schema = {
            "orders": {"order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"},
            "customers": {"customer_id", "customer_unique_id"},
            "order_payments": {"order_id", "payment_value"},
            "order_reviews": {"review_id", "order_id", "review_score", "review_creation_date", "review_answer_timestamp"},
            "order_items": {"order_id", "order_item_id"},
        }
        schema_errors: list[str] = []
        for table, required_columns in required_schema.items():
            found = {r[1] for r in connection.execute(f'PRAGMA table_info("{table}")')}
            missing_columns = sorted(required_columns - found)
            if not found:
                schema_errors.append(f"missing table: {table}")
            elif missing_columns:
                schema_errors.append(f"{table} missing: {','.join(missing_columns)}")
        check("GLOBAL", "required_tables_and_columns", schema_errors, [])
        if schema_errors:
            raise RuntimeError("; ".join(schema_errors))

        # Execute the complete file once, then every marked result query to capture outputs.
        connection.executescript(sql_text)
        add("GLOBAL", "complete_sqlite_file_execution", "success", "success", "PASS", "SQLite 完整解析并执行全部 SQL。")

        results: dict[str, list[dict[str, Any]]] = {}
        for code in required_sections:
            cursor = connection.execute(metric_sql[code])
            columns = [item[0] for item in cursor.description or []]
            rows = row_dicts(cursor)
            results[code] = rows
            check(code, "stable_output_columns", columns, EXPECTED_COLUMNS[code])
            add(code, "query_returns_rows", len(rows), ">= 1", "PASS" if rows else "FAIL")

        d01 = results["D01"][0]
        d02 = results["D02"]
        d03 = results["D03"][0]
        d04 = results["D04"][0]
        d05 = results["D05"][0]
        d06 = results["D06"][0]
        d07 = results["D07"][0]
        d08 = results["D08"][0]
        d09 = results["D09_OVERALL"][0]
        d09_monthly = results["D09_MONTHLY"]

        # Grain and one-to-many amplification checks.
        order_rows, unique_orders = connection.execute("SELECT COUNT(*), COUNT(DISTINCT order_id) FROM orders").fetchone()
        check("GLOBAL", "orders_order_id_uniqueness", order_rows, unique_orders)
        joined_rows, joined_orders = connection.execute(
            "SELECT COUNT(*), COUNT(DISTINCT o.order_id) FROM orders o JOIN customers c ON c.customer_id=o.customer_id"
        ).fetchone()
        check("GLOBAL", "customer_join_does_not_amplify_orders", joined_rows, order_rows)
        check("GLOBAL", "customer_join_preserves_unique_orders", joined_orders, unique_orders)
        payment_max_rows = scalar(
            connection,
            "WITH p AS (SELECT order_id, SUM(payment_value) v FROM order_payments GROUP BY order_id) "
            "SELECT COALESCE(MAX(n),0) FROM (SELECT order_id, COUNT(*) n FROM p GROUP BY order_id)",
        )
        check("GLOBAL", "payment_aggregation_one_row_per_order", payment_max_rows, 1)
        review_max_rows = scalar(
            connection,
            "WITH r AS (SELECT order_id, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC, review_creation_date DESC, review_id DESC) rn FROM order_reviews) "
            "SELECT COALESCE(MAX(n),0) FROM (SELECT order_id, COUNT(*) n FROM r WHERE rn=1 GROUP BY order_id)",
        )
        check("GLOBAL", "review_dedup_one_row_per_order", review_max_rows, 1)
        raw_payment, aggregated_payment = connection.execute(
            "WITH p AS (SELECT order_id, SUM(CASE WHEN payment_value>0 THEN payment_value ELSE 0 END) v FROM order_payments GROUP BY order_id) "
            "SELECT (SELECT SUM(op.payment_value) FROM order_payments op JOIN orders o ON o.order_id=op.order_id WHERE o.order_status='delivered' AND op.payment_value>0), "
            "(SELECT SUM(p.v) FROM p JOIN orders o ON o.order_id=p.order_id WHERE o.order_status='delivered' AND p.v>0)"
        ).fetchone()
        check("GLOBAL", "payment_amount_not_amplified", aggregated_payment, raw_payment)

        # Ranges and identities.
        rates = [d01["repeat_purchase_rate"], d07["delayed_delivery_rate"], d08["positive_review_rate"], d09["cancellation_rate"]]
        rates += [r["retention_rate"] for r in d02] + [r["cancellation_rate"] for r in d09_monthly]
        invalid_rates = [r for r in rates if r is not None and not 0 <= r <= 1]
        check("GLOBAL", "all_rates_in_unit_interval_or_null", len(invalid_rates), 0)
        check("D01", "repeat_users_le_purchasing_users", d01["repeat_users"] <= d01["purchasing_users"], True)
        check("D02", "retained_users_le_cohort_size", all(r["retained_users"] <= r["cohort_size"] for r in d02), True)
        month_zero = [r for r in d02 if r["month_number"] == 0]
        check("D02", "month_0_retention_equals_one", all(close_enough(r["retention_rate"], 1.0) for r in month_zero), True)
        check("D03", "observed_ltv_nonnegative", d03["observed_ltv"] is None or d03["observed_ltv"] >= 0, True)
        check("D04", "average_purchase_frequency_ge_one", d04["average_purchase_frequency"] is None or d04["average_purchase_frequency"] >= 1, True)
        check("D05", "repurchase_interval_nonnegative", d05["average_repurchase_interval_days"] is None or d05["average_repurchase_interval_days"] >= 0, True)
        check("D06", "delivery_duration_nonnegative", d06["average_delivery_days"] is None or d06["average_delivery_days"] >= 0, True)
        check("D07", "delayed_orders_le_evaluable_orders", d07["delayed_orders"] <= d07["evaluable_orders"], True)
        check("D08", "positive_reviews_le_reviewed_orders", d08["positive_review_orders"] <= d08["reviewed_orders"], True)
        check("D09", "canceled_orders_le_total_orders", d09["canceled_orders"] <= d09["total_orders"], True)
        check("D09", "monthly_totals_equal_same_scope_overall", sum(r["total_orders"] for r in d09_monthly), d09["total_orders"])
        check("D09", "monthly_canceled_equal_same_scope_overall", sum(r["canceled_orders"] for r in d09_monthly), d09["canceled_orders"])
        on_time = d07["evaluable_orders"] - d07["delayed_orders"]
        check("D07", "on_time_plus_delayed_equals_evaluable", on_time + d07["delayed_orders"], d07["evaluable_orders"])
        complement_sum = (on_time / d07["evaluable_orders"] + d07["delayed_delivery_rate"]) if d07["evaluable_orders"] else None
        check("D07", "on_time_rate_plus_delayed_rate_equals_one", complement_sum, 1.0)

        # Independent formula recalculation queries.
        independent_sql = {
            "D01": "WITH u AS (SELECT c.customer_unique_id,COUNT(DISTINCT o.order_id) n FROM orders o JOIN customers c ON c.customer_id=o.customer_id WHERE o.order_status='delivered' AND c.customer_unique_id IS NOT NULL GROUP BY c.customer_unique_id) SELECT 1.0*SUM(n>=2)/NULLIF(COUNT(*),0) FROM u",
            "D03": "WITH p AS (SELECT order_id,SUM(payment_value) v FROM order_payments WHERE payment_value>0 GROUP BY order_id), x AS (SELECT c.customer_unique_id,p.v FROM p JOIN orders o ON o.order_id=p.order_id JOIN customers c ON c.customer_id=o.customer_id WHERE o.order_status='delivered' AND p.v>0) SELECT SUM(v)/NULLIF(1.0*COUNT(DISTINCT customer_unique_id),0) FROM x",
            "D04": "SELECT 1.0*COUNT(DISTINCT o.order_id)/NULLIF(COUNT(DISTINCT c.customer_unique_id),0) FROM orders o JOIN customers c ON c.customer_id=o.customer_id WHERE o.order_status='delivered'",
            "D07": "WITH x AS (SELECT order_id, order_delivered_customer_date>d.order_estimated_delivery_date late FROM orders d WHERE order_status='delivered' AND order_delivered_customer_date IS NOT NULL AND order_estimated_delivery_date IS NOT NULL AND JULIANDAY(order_delivered_customer_date)>=JULIANDAY(order_purchase_timestamp)) SELECT 1.0*SUM(late)/NULLIF(COUNT(*),0) FROM x",
            "D08": "WITH r AS (SELECT order_id,review_score,ROW_NUMBER() OVER(PARTITION BY order_id ORDER BY review_answer_timestamp DESC,review_creation_date DESC,review_id DESC) rn FROM order_reviews), x AS (SELECT r.review_score FROM r JOIN orders o ON o.order_id=r.order_id WHERE r.rn=1 AND r.review_score BETWEEN 1 AND 5 AND o.order_status='delivered') SELECT 1.0*SUM(review_score>=4)/NULLIF(COUNT(*),0) FROM x",
            "D09": "SELECT 1.0*COUNT(DISTINCT CASE WHEN order_status='canceled' THEN order_id END)/NULLIF(COUNT(DISTINCT order_id),0) FROM orders WHERE order_id IS NOT NULL",
        }
        output_rates = {
            "D01": d01["repeat_purchase_rate"],
            "D03": d03["observed_ltv"],
            "D04": d04["average_purchase_frequency"],
            "D07": d07["delayed_delivery_rate"],
            "D08": d08["positive_review_rate"],
            "D09": d09["cancellation_rate"],
        }
        for code, query in independent_sql.items():
            recalculated = scalar(connection, query)
            check(code, "independent_formula_recalculation", output_rates[code], recalculated, "独立 SQL 回算。")

        # Data anomalies are reported, not silently discarded.
        missing_delivery, negative_delivery = connection.execute(
            "SELECT SUM(order_delivered_customer_date IS NULL OR order_purchase_timestamp IS NULL), "
            "SUM(CASE WHEN order_delivered_customer_date IS NOT NULL AND order_purchase_timestamp IS NOT NULL AND JULIANDAY(order_delivered_customer_date)<JULIANDAY(order_purchase_timestamp) THEN 1 ELSE 0 END) "
            "FROM orders WHERE order_status='delivered'"
        ).fetchone()
        add("D06", "excluded_missing_delivery_timestamps", missing_delivery, 0, "WARN" if missing_delivery else "PASS", "缺失时间订单按口径排除。")
        check("D06", "excluded_negative_delivery_durations", negative_delivery, 0)
        last_order_month, last_delivered_month = connection.execute(
            "SELECT STRFTIME('%Y-%m',MAX(order_purchase_timestamp)), STRFTIME('%Y-%m',MAX(CASE WHEN order_status='delivered' THEN order_purchase_timestamp END)) FROM orders"
        ).fetchone()
        tail_status = "WARN" if last_order_month != last_delivered_month else "PASS"
        add("D02", "right_censoring_tail", last_delivered_month, last_order_month, tail_status, "Cohort 仅生成至最后 delivered 活动月，未来月份不补零。")

        # Official full Olist regression references are used only after a completeness fingerprint.
        table_counts = {
            table: scalar(connection, f"SELECT COUNT(*) FROM {table}")
            for table in ("orders", "customers", "order_payments", "order_reviews")
        }
        full_reference = table_counts == {"orders": 99441, "customers": 99441, "order_payments": 103886, "order_reviews": 99224}
        add("GLOBAL", "official_reference_dataset_fingerprint", table_counts, "complete official Olist counts", "PASS" if full_reference else "WARN", "仅匹配完整数据指纹时执行官方参考值回归。")
        if full_reference:
            official = [
                ("D01", "reference_purchasing_users", d01["purchasing_users"], 93358, 0),
                ("D01", "reference_repeat_users", d01["repeat_users"], 2801, 0),
                ("D01", "reference_repeat_purchase_rate", d01["repeat_purchase_rate"], 2801 / 93358, TOLERANCE),
                ("D02", "reference_cohort_rows", len(d02), 278, 0),
                ("D06", "reference_valid_delivery_orders", d06["valid_delivery_orders"], 96470, 0),
                ("D06", "reference_average_delivery_days", d06["average_delivery_days"], 12.56, 0.02),
                ("D07", "reference_evaluable_orders", d07["evaluable_orders"], 96470, 0),
                ("D07", "reference_on_time_orders", on_time, 88644, 0),
                ("D07", "reference_delayed_orders", d07["delayed_orders"], 7826, 0),
                ("D07", "reference_delayed_delivery_rate", d07["delayed_delivery_rate"], 0.0811, 0.0001),
                ("D08", "reference_reviewed_orders", d08["reviewed_orders"], 95832, 0),
                ("D08", "reference_positive_review_orders", d08["positive_review_orders"], 75643, 0),
                ("D08", "reference_positive_review_rate", d08["positive_review_rate"], 0.7893, 0.0001),
                ("D09", "reference_total_orders", d09["total_orders"], 99441, 0),
                ("D09", "reference_canceled_orders", d09["canceled_orders"], 625, 0),
            ]
            for code, item, actual, expected, tolerance in official:
                status = "PASS" if close_enough(actual, expected, tolerance) else "WARN"
                add(code, item, actual, expected, status, "官方值用于回归参考；差异标 WARN，不改公式迎合。", tolerance)

    except (sqlite3.Error, RuntimeError, KeyError, IndexError) as exc:
        add("GLOBAL", "validation_runtime", type(exc).__name__, "successful execution", "BLOCKED", str(exc))
    finally:
        connection.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(validations)

    counts = Counter(row["status"] for row in validations)
    print(f"Validation CSV: {args.output}")
    print("Status counts:", ", ".join(f"{status}={counts.get(status, 0)}" for status in ("PASS", "WARN", "FAIL", "BLOCKED")))
    return 1 if counts.get("FAIL", 0) or counts.get("BLOCKED", 0) else 0


if __name__ == "__main__":
    sys.exit(main())
