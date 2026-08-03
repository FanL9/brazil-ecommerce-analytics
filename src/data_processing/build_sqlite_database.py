"""Build the local SQLite database from the project's raw CSV files."""

from __future__ import annotations

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
    """Describe one CSV-to-SQLite table import."""

    csv_filename: str
    expected_rows: int
    string_columns: tuple[str, ...] = ()


TABLE_SPECS: dict[str, TableSpec] = {
    "customers": TableSpec(
        "olist_customers_dataset.csv", 99_441, ("customer_zip_code_prefix",)
    ),
    "geolocation": TableSpec(
        "olist_geolocation_dataset.csv", 1_000_163, ("geolocation_zip_code_prefix",)
    ),
    "order_items": TableSpec("olist_order_items_dataset.csv", 112_650),
    "order_payments": TableSpec("olist_order_payments_dataset.csv", 103_886),
    "order_reviews": TableSpec("olist_order_reviews_dataset.csv", 99_224),
    "orders": TableSpec("olist_orders_dataset.csv", 99_441),
    "products": TableSpec("olist_products_dataset.csv", 32_951),
    "sellers": TableSpec(
        "olist_sellers_dataset.csv", 3_095, ("seller_zip_code_prefix",)
    ),
    "product_category_name_translation": TableSpec(
        "product_category_name_translation.csv", 71
    ),
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


def create_schema(connection: sqlite3.Connection) -> None:
    """Create all tables using the repository's canonical schema file."""

    try:
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        connection.executescript(schema_sql)
    except (OSError, sqlite3.Error) as exc:
        raise RuntimeError(f"Could not create tables from {SCHEMA_PATH}: {exc}") from exc

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


def table_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    """Return columns from a SQLite table in schema order."""

    quoted_table = quote_identifier(table_name)
    return [
        row[1] for row in connection.execute(f"PRAGMA table_info({quoted_table})")
    ]


def read_csv_header(csv_path: Path, string_columns: tuple[str, ...]) -> list[str]:
    """Read a CSV header with the same strict parser settings used for data."""

    dtype = {column: str for column in string_columns}
    header = pd.read_csv(
        csv_path,
        encoding="utf-8",
        header=0,
        quotechar='"',
        nrows=0,
        dtype=dtype,
        on_bad_lines="error",
    )
    return header.columns.tolist()


def read_csv_chunks(csv_path: Path, string_columns: tuple[str, ...]) -> Iterator[pd.DataFrame]:
    """Yield strictly parsed CSV data frames without skipping malformed rows."""

    dtype = {column: str for column in string_columns}
    yield from pd.read_csv(
        csv_path,
        encoding="utf-8",
        header=0,
        quotechar='"',
        chunksize=CHUNK_SIZE,
        dtype=dtype,
        on_bad_lines="error",
    )


def insert_chunk(
    connection: sqlite3.Connection, table_name: str, frame: pd.DataFrame
) -> None:
    """Insert one data frame into SQLite while preserving CSV nulls as SQL NULL."""

    if frame.empty:
        return

    quoted_table = quote_identifier(table_name)
    quoted_columns = ", ".join(quote_identifier(column) for column in frame.columns)
    placeholders = ", ".join("?" for _ in frame.columns)
    insert_sql = (
        f"INSERT INTO {quoted_table} ({quoted_columns}) VALUES ({placeholders})"
    )
    sql_values = frame.astype(object).where(frame.notna(), None)
    connection.executemany(
        insert_sql, sql_values.itertuples(index=False, name=None)
    )


def import_table(
    connection: sqlite3.Connection, table_name: str, spec: TableSpec
) -> tuple[int, int]:
    """Import one complete CSV and validate its parsed and stored row counts."""

    csv_path = RAW_DATA_DIR / spec.csv_filename
    expected_columns = table_columns(connection, table_name)

    try:
        csv_columns = read_csv_header(csv_path, spec.string_columns)
        if csv_columns != expected_columns:
            raise ValueError(
                f"Column mismatch for {table_name}. "
                f"CSV columns: {csv_columns}; schema columns: {expected_columns}."
            )

        csv_rows = 0
        for frame in read_csv_chunks(csv_path, spec.string_columns):
            if frame.columns.tolist() != expected_columns:
                raise ValueError(
                    f"Column mismatch while reading {csv_path.name}: "
                    f"{frame.columns.tolist()}"
                )
            insert_chunk(connection, table_name, frame)
            csv_rows += len(frame)
    except (OSError, UnicodeError, pd.errors.ParserError, ValueError, sqlite3.Error) as exc:
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


def build_database() -> None:
    """Rebuild the database transactionally and publish it only after validation."""

    validate_input_files()
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    if TEMP_DATABASE_PATH.exists():
        TEMP_DATABASE_PATH.unlink()

    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(TEMP_DATABASE_PATH, isolation_level=None)
        create_schema(connection)
        connection.execute("BEGIN IMMEDIATE")

        for table_name, spec in TABLE_SPECS.items():
            csv_rows, db_rows = import_table(connection, table_name, spec)
            print(
                f"{table_name:<41} "
                f"CSV: {csv_rows:>9,} DB: {db_rows:>9,} OK"
            )

        connection.commit()
        connection.close()
        connection = None
        TEMP_DATABASE_PATH.replace(DATABASE_PATH)
    except BaseException:
        if connection is not None:
            if connection.in_transaction:
                connection.rollback()
            connection.close()
        TEMP_DATABASE_PATH.unlink(missing_ok=True)
        raise

    relative_output = DATABASE_PATH.relative_to(PROJECT_ROOT).as_posix()
    print(f"\nDatabase successfully created:\n{relative_output}")


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
