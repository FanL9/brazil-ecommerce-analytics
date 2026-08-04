"""Build and validate the local SQLite database from the nine raw Olist CSVs."""

from __future__ import annotations

import math
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pandas as pd


CHUNK_SIZE = 50_000
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DATABASE_DIR = PROJECT_ROOT / "database"
SCHEMA_PATH = DATABASE_DIR / "schema.sql"
DATABASE_PATH = DATABASE_DIR / "brazil_ecommerce.db"
TEMP_DATABASE_PATH = DATABASE_DIR / "brazil_ecommerce.tmp.db"


@dataclass(frozen=True)
class TableSpec:
    """Describe one strict CSV-to-SQLite table import."""

    csv_filename: str
    expected_rows: int
    columns: tuple[str, ...]
    primary_key: tuple[str, ...]
    integer_columns: tuple[str, ...] = ()
    real_columns: tuple[str, ...] = ()
    internal_columns: tuple[str, ...] = ()

    @property
    def text_columns(self) -> tuple[str, ...]:
        numeric_columns = set(self.integer_columns) | set(self.real_columns)
        return tuple(column for column in self.columns if column not in numeric_columns)

    @property
    def database_columns(self) -> tuple[str, ...]:
        return self.internal_columns + self.columns


TABLE_SPECS: dict[str, TableSpec] = {
    "customers": TableSpec(
        "olist_customers_dataset.csv",
        99_441,
        (
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ),
        ("customer_id",),
    ),
    "product_category_name_translation": TableSpec(
        "product_category_name_translation.csv",
        71,
        ("product_category_name", "product_category_name_english"),
        ("product_category_name",),
    ),
    "products": TableSpec(
        "olist_products_dataset.csv",
        32_951,
        (
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ),
        ("product_id",),
        integer_columns=(
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ),
    ),
    "sellers": TableSpec(
        "olist_sellers_dataset.csv",
        3_095,
        ("seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"),
        ("seller_id",),
    ),
    "geolocation": TableSpec(
        "olist_geolocation_dataset.csv",
        1_000_163,
        (
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state",
        ),
        ("geolocation_id",),
        real_columns=("geolocation_lat", "geolocation_lng"),
        internal_columns=("geolocation_id",),
    ),
    "orders": TableSpec(
        "olist_orders_dataset.csv",
        99_441,
        (
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ),
        ("order_id",),
    ),
    "order_items": TableSpec(
        "olist_order_items_dataset.csv",
        112_650,
        (
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ),
        ("order_id", "order_item_id"),
        integer_columns=("order_item_id",),
        real_columns=("price", "freight_value"),
    ),
    "order_payments": TableSpec(
        "olist_order_payments_dataset.csv",
        103_886,
        (
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ),
        ("order_id", "payment_sequential"),
        integer_columns=("payment_sequential", "payment_installments"),
        real_columns=("payment_value",),
    ),
    "order_reviews": TableSpec(
        "olist_order_reviews_dataset.csv",
        99_224,
        (
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ),
        ("review_id", "order_id"),
        integer_columns=("review_score",),
    ),
}

EXPECTED_INDEXES = {
    "idx_customers_customer_unique_id",
    "idx_customers_zip_code_prefix",
    "idx_geolocation_zip_code_prefix",
    "idx_order_items_product_id",
    "idx_order_items_seller_id",
    "idx_order_reviews_order_id",
    "idx_orders_customer_id",
    "idx_orders_purchase_timestamp",
    "idx_orders_status",
    "idx_products_category_name",
    "idx_sellers_zip_code_prefix",
}

EXPECTED_FOREIGN_KEYS = {
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("order_items", "seller_id", "sellers", "seller_id"),
    ("order_payments", "order_id", "orders", "order_id"),
    ("order_reviews", "order_id", "orders", "order_id"),
}


def validate_input_files() -> None:
    """Raise a clear error when a required schema or CSV file is missing."""

    required_paths = [SCHEMA_PATH]
    required_paths.extend(
        RAW_DATA_DIR / spec.csv_filename for spec in TABLE_SPECS.values()
    )
    missing_paths = [path for path in required_paths if not path.is_file()]
    if missing_paths:
        missing = "\n".join(f"  - {path}" for path in missing_paths)
        raise FileNotFoundError(f"Required input file(s) not found:\n{missing}")


def quote_identifier(identifier: str) -> str:
    """Return a safely quoted SQLite identifier."""

    return '"' + identifier.replace('"', '""') + '"'


def remove_temporary_database() -> None:
    """Remove only generated files belonging to the temporary build database."""

    for suffix in ("", "-journal", "-wal", "-shm"):
        Path(f"{TEMP_DATABASE_PATH}{suffix}").unlink(missing_ok=True)


def enable_foreign_keys(connection: sqlite3.Connection) -> None:
    """Enable SQLite foreign-key enforcement and prove that it is active."""

    connection.execute("PRAGMA foreign_keys = ON")
    enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
    if enabled != 1:
        raise RuntimeError("SQLite foreign-key enforcement could not be enabled.")


def table_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    """Return columns from a SQLite table in schema order."""

    quoted_table = quote_identifier(table_name)
    return [
        row[1] for row in connection.execute(f"PRAGMA table_info({quoted_table})")
    ]


def validate_schema(connection: sqlite3.Connection) -> None:
    """Validate table names, column mappings, indexes, and foreign keys."""

    actual_tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    expected_tables = set(TABLE_SPECS)
    if actual_tables != expected_tables:
        missing = sorted(expected_tables - actual_tables)
        unexpected = sorted(actual_tables - expected_tables)
        raise RuntimeError(
            "Schema table mismatch. "
            f"Missing tables: {missing or 'none'}; "
            f"unexpected tables: {unexpected or 'none'}."
        )

    for table_name, spec in TABLE_SPECS.items():
        actual_columns = table_columns(connection, table_name)
        if actual_columns != list(spec.database_columns):
            raise RuntimeError(
                f"Schema column mismatch for {table_name}. "
                f"Expected {list(spec.database_columns)}; got {actual_columns}."
            )

    actual_indexes = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'index' AND sql IS NOT NULL"
        )
    }
    if actual_indexes != EXPECTED_INDEXES:
        raise RuntimeError(
            "Schema index mismatch. "
            f"Missing: {sorted(EXPECTED_INDEXES - actual_indexes) or 'none'}; "
            f"unexpected: {sorted(actual_indexes - EXPECTED_INDEXES) or 'none'}."
        )

    actual_foreign_keys: set[tuple[str, str, str, str]] = set()
    for table_name in TABLE_SPECS:
        quoted_table = quote_identifier(table_name)
        for row in connection.execute(f"PRAGMA foreign_key_list({quoted_table})"):
            actual_foreign_keys.add((table_name, row[3], row[2], row[4]))
    if actual_foreign_keys != EXPECTED_FOREIGN_KEYS:
        raise RuntimeError(
            "Schema foreign-key mismatch. "
            f"Missing: {sorted(EXPECTED_FOREIGN_KEYS - actual_foreign_keys) or 'none'}; "
            f"unexpected: {sorted(actual_foreign_keys - EXPECTED_FOREIGN_KEYS) or 'none'}."
        )


def create_schema(connection: sqlite3.Connection) -> None:
    """Create all tables and indexes from the canonical schema file."""

    try:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8-sig")
        connection.executescript(schema_sql)
    except (OSError, UnicodeError, sqlite3.Error) as exc:
        raise RuntimeError(f"Could not apply {SCHEMA_PATH}: {exc}") from exc
    enable_foreign_keys(connection)
    validate_schema(connection)


def read_csv_header(csv_path: Path) -> list[str]:
    """Read a UTF-8 CSV header with the strict parser used for its data."""

    header = pd.read_csv(
        csv_path,
        encoding="utf-8-sig",
        header=0,
        quotechar='"',
        nrows=0,
        on_bad_lines="error",
    )
    return header.columns.tolist()


def read_csv_chunks(csv_path: Path, spec: TableSpec) -> Iterator[pd.DataFrame]:
    """Yield strictly parsed CSV chunks while preserving all text fields as text."""

    text_dtypes = {column: "string" for column in spec.text_columns}
    yield from pd.read_csv(
        csv_path,
        encoding="utf-8-sig",
        header=0,
        quotechar='"',
        chunksize=CHUNK_SIZE,
        dtype=text_dtypes,
        on_bad_lines="error",
    )


def validate_csv_columns(
    table_name: str, csv_columns: list[str], expected_columns: tuple[str, ...]
) -> None:
    """Reject missing, extra, renamed, or reordered CSV columns clearly."""

    expected = list(expected_columns)
    missing = [column for column in expected if column not in csv_columns]
    extra = [column for column in csv_columns if column not in expected]
    if missing or extra:
        raise ValueError(
            f"Column mismatch for {table_name}. "
            f"Missing: {missing or 'none'}; extra: {extra or 'none'}."
        )
    if csv_columns != expected:
        raise ValueError(
            f"Column order mismatch for {table_name}. "
            f"Expected {expected}; got {csv_columns}."
        )


def normalize_numeric_columns(frame: pd.DataFrame, spec: TableSpec) -> pd.DataFrame:
    """Convert declared numeric columns and reject invalid or fractional integers."""

    normalized = frame.copy()
    for column in spec.integer_columns:
        numeric = pd.to_numeric(normalized[column], errors="raise")
        non_null = numeric.dropna()
        if not non_null.map(math.isfinite).all():
            raise ValueError(f"Non-finite value found in integer column {column}.")
        if not (non_null % 1 == 0).all():
            raise ValueError(f"Fractional value found in integer column {column}.")
        normalized[column] = numeric.astype("Int64")

    for column in spec.real_columns:
        numeric = pd.to_numeric(normalized[column], errors="raise")
        non_null = numeric.dropna()
        if not non_null.map(math.isfinite).all():
            raise ValueError(f"Non-finite value found in real column {column}.")
        normalized[column] = numeric.astype(float)
    return normalized


def insert_chunk(
    connection: sqlite3.Connection,
    table_name: str,
    spec: TableSpec,
    frame: pd.DataFrame,
) -> None:
    """Insert one chunk by explicit CSV column names, mapping pandas nulls to NULL."""

    if frame.empty:
        return

    normalized = normalize_numeric_columns(frame, spec)
    quoted_table = quote_identifier(table_name)
    quoted_columns = ", ".join(quote_identifier(column) for column in spec.columns)
    placeholders = ", ".join("?" for _ in spec.columns)
    insert_sql = (
        f"INSERT INTO {quoted_table} ({quoted_columns}) VALUES ({placeholders})"
    )
    sql_values = normalized.astype(object).where(normalized.notna(), None)
    connection.executemany(
        insert_sql, sql_values.itertuples(index=False, name=None)
    )


def import_table(
    connection: sqlite3.Connection, table_name: str, spec: TableSpec
) -> tuple[int, int]:
    """Import one complete CSV and validate its parsed and stored row counts."""

    csv_path = RAW_DATA_DIR / spec.csv_filename
    try:
        validate_csv_columns(table_name, read_csv_header(csv_path), spec.columns)
        csv_rows = 0
        for frame in read_csv_chunks(csv_path, spec):
            validate_csv_columns(table_name, frame.columns.tolist(), spec.columns)
            insert_chunk(connection, table_name, spec, frame)
            csv_rows += len(frame)
    except (
        OSError,
        UnicodeError,
        pd.errors.ParserError,
        TypeError,
        ValueError,
        sqlite3.Error,
    ) as exc:
        raise RuntimeError(
            f"Failed to import {csv_path} into table {table_name}: {exc}"
        ) from exc

    quoted_table = quote_identifier(table_name)
    db_rows = connection.execute(
        f"SELECT COUNT(*) FROM {quoted_table}"
    ).fetchone()[0]
    if csv_rows != db_rows or csv_rows != spec.expected_rows:
        raise RuntimeError(
            f"Row-count validation failed for {table_name}: "
            f"CSV={csv_rows:,}, DB={db_rows:,}, expected={spec.expected_rows:,}."
        )
    return csv_rows, db_rows


def validate_primary_keys(connection: sqlite3.Connection) -> None:
    """Prove every declared primary key is non-null and duplicate-free."""

    for table_name, spec in TABLE_SPECS.items():
        quoted_table = quote_identifier(table_name)
        quoted_key = [quote_identifier(column) for column in spec.primary_key]
        null_condition = " OR ".join(f"{column} IS NULL" for column in quoted_key)
        null_count = connection.execute(
            f"SELECT COUNT(*) FROM {quoted_table} WHERE {null_condition}"
        ).fetchone()[0]
        key_expression = ", ".join(quoted_key)
        duplicate = connection.execute(
            f"SELECT 1 FROM {quoted_table} "
            f"GROUP BY {key_expression} HAVING COUNT(*) > 1 LIMIT 1"
        ).fetchone()
        if null_count or duplicate is not None:
            raise RuntimeError(
                f"Primary-key validation failed for {table_name}{spec.primary_key}."
            )


def validate_database(connection: sqlite3.Connection) -> dict[str, int | str]:
    """Run structural, integrity, relationship, and smoke-query validation."""

    enable_foreign_keys(connection)
    validate_schema(connection)
    validate_primary_keys(connection)

    integrity_result = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity_result != "ok":
        raise RuntimeError(f"PRAGMA integrity_check failed: {integrity_result}")

    foreign_key_violations = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()
    if foreign_key_violations:
        raise RuntimeError(
            f"PRAGMA foreign_key_check found {len(foreign_key_violations)} violation(s)."
        )

    geolocation_rows, geolocation_ids, first_id, last_id = connection.execute(
        "SELECT COUNT(*), COUNT(DISTINCT geolocation_id), "
        "MIN(geolocation_id), MAX(geolocation_id) FROM geolocation"
    ).fetchone()
    if (geolocation_rows, geolocation_ids, first_id, last_id) != (
        TABLE_SPECS["geolocation"].expected_rows,
        TABLE_SPECS["geolocation"].expected_rows,
        1,
        TABLE_SPECS["geolocation"].expected_rows,
    ):
        raise RuntimeError("Generated geolocation_id values are incomplete or misaligned.")

    non_text_zip_values = sum(
        connection.execute(
            f"SELECT COUNT(*) FROM {quote_identifier(table_name)} "
            f"WHERE typeof({quote_identifier(column_name)}) <> 'text'"
        ).fetchone()[0]
        for table_name, column_name in (
            ("customers", "customer_zip_code_prefix"),
            ("geolocation", "geolocation_zip_code_prefix"),
            ("sellers", "seller_zip_code_prefix"),
        )
    )
    if non_text_zip_values:
        raise RuntimeError("One or more postal-code values were not stored as TEXT.")

    untranslated_product_rows, untranslated_categories = connection.execute(
        "SELECT COUNT(*), COUNT(DISTINCT p.product_category_name) "
        "FROM products AS p "
        "LEFT JOIN product_category_name_translation AS t "
        "ON t.product_category_name = p.product_category_name "
        "WHERE p.product_category_name IS NOT NULL "
        "AND t.product_category_name IS NULL"
    ).fetchone()

    uncovered_customer_zips = connection.execute(
        "SELECT COUNT(*) FROM customers AS c "
        "WHERE NOT EXISTS ("
        "SELECT 1 FROM geolocation AS g "
        "WHERE g.geolocation_zip_code_prefix = c.customer_zip_code_prefix)"
    ).fetchone()[0]
    uncovered_seller_zips = connection.execute(
        "SELECT COUNT(*) FROM sellers AS s "
        "WHERE NOT EXISTS ("
        "SELECT 1 FROM geolocation AS g "
        "WHERE g.geolocation_zip_code_prefix = s.seller_zip_code_prefix)"
    ).fetchone()[0]

    join_counts = {
        "orders_customers": connection.execute(
            "SELECT COUNT(*) FROM orders AS o "
            "JOIN customers AS c ON c.customer_id = o.customer_id"
        ).fetchone()[0],
        "items_products_sellers": connection.execute(
            "SELECT COUNT(*) FROM order_items AS i "
            "JOIN products AS p ON p.product_id = i.product_id "
            "JOIN sellers AS s ON s.seller_id = i.seller_id"
        ).fetchone()[0],
        "orders_payments_reviews": connection.execute(
            "SELECT COUNT(*) FROM orders AS o "
            "JOIN order_payments AS p ON p.order_id = o.order_id "
            "JOIN order_reviews AS r ON r.order_id = o.order_id"
        ).fetchone()[0],
    }
    if any(count == 0 for count in join_counts.values()):
        raise RuntimeError(f"A JOIN smoke test returned no rows: {join_counts}")

    return {
        "integrity_check": integrity_result,
        "foreign_key_violations": len(foreign_key_violations),
        "untranslated_product_rows": untranslated_product_rows,
        "untranslated_categories": untranslated_categories,
        "uncovered_customer_zips": uncovered_customer_zips,
        "uncovered_seller_zips": uncovered_seller_zips,
        **join_counts,
    }


def build_database() -> None:
    """Build a temporary database, validate it, then atomically publish it."""

    validate_input_files()
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    remove_temporary_database()

    connection: sqlite3.Connection | None = None
    try:
        print(f"Building temporary database: {TEMP_DATABASE_PATH.name}")
        connection = sqlite3.connect(TEMP_DATABASE_PATH)
        connection.execute("PRAGMA journal_mode = DELETE")
        enable_foreign_keys(connection)
        print("Foreign-key enforcement: ON")
        create_schema(connection)

        connection.execute("BEGIN IMMEDIATE")
        for table_name, spec in TABLE_SPECS.items():
            csv_rows, db_rows = import_table(connection, table_name, spec)
            print(
                f"{table_name:<41} CSV: {csv_rows:>9,} DB: {db_rows:>9,} OK"
            )
        connection.commit()

        report = validate_database(connection)
        connection.close()
        connection = None

        os.replace(TEMP_DATABASE_PATH, DATABASE_PATH)
    except BaseException:
        if connection is not None:
            if connection.in_transaction:
                connection.rollback()
            connection.close()
        remove_temporary_database()
        raise

    relative_output = DATABASE_PATH.relative_to(PROJECT_ROOT).as_posix()
    print("\nValidation: 9 tables, 11 explicit indexes, 6 foreign keys OK")
    print(f"PRAGMA integrity_check: {report['integrity_check']}")
    print(
        "PRAGMA foreign_key_check: "
        f"{report['foreign_key_violations']} violation(s)"
    )
    print(
        "Source-data note: "
        f"{report['untranslated_product_rows']} product row(s) in "
        f"{report['untranslated_categories']} non-null category value(s) lack a "
        "translation; this optional relationship is intentionally not an FK."
    )
    print(
        "Source-data note: geolocation lacks coverage for "
        f"{report['uncovered_customer_zips']} customer row(s) and "
        f"{report['uncovered_seller_zips']} seller row(s); postal codes are "
        "indexed TEXT values, not foreign keys."
    )
    print(
        "JOIN smoke tests: "
        f"orders/customers={report['orders_customers']:,}, "
        f"items/products/sellers={report['items_products_sellers']:,}, "
        f"orders/payments/reviews={report['orders_payments_reviews']:,}"
    )
    print(f"Database successfully created: {relative_output}")


def main() -> int:
    """Run the database build and return a process exit code."""

    try:
        build_database()
    except Exception as exc:
        print(f"Database build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
