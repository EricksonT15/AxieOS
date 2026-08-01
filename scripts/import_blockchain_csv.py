from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CSV_PATH = (
    PROJECT_ROOT
    / "data"
    / "blockchain"
    / "raw"
    / "legacy_transactions_2021.csv"
)

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "blockchain"
    / "database"
    / "axieos.db"
)

TABLE_NAME = "blockchain_transactions"


# ---------------------------------------------------------
# Expected CSV columns
# ---------------------------------------------------------

EXPECTED_COLUMNS = [
    "txhash",
    "blockno",
    "unixtimestamp",
    "datetime",
    "from",
    "to",
    "method",
    "token_collectibles",
    "value_in",
    "value_out",
    "txn_fee_ron",
    "status",
]

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def clean_column_name(column: str) -> str:
    """
    Convert CSV column names into SQLite-friendly names.
    """

    mapping = {
        "token_/_collectibles": "token_collectibles",
        "txnfee(ron)": "txn_fee_ron",
    }

    return mapping.get(column, column)


def clean_value(value: object) -> str | None:
    """
    Convert pandas values into safe SQLite values.
    """

    if pd.isna(value):
        return None

    return str(value).strip()


def create_row_hash(row: pd.Series) -> str:
    """
    Create a unique fingerprint for the complete CSV row.

    Transaction hashes alone cannot be used as unique identifiers because
    one blockchain transaction may contain multiple asset-transfer rows.
    """

    row_text = "|".join(
        "" if pd.isna(value) else str(value).strip()
        for value in row.tolist()
    )

    return hashlib.sha256(row_text.encode("utf-8")).hexdigest()


def validate_csv_columns(dataframe: pd.DataFrame) -> None:
    """
    Confirm that the CSV contains all expected columns.
    """

    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in dataframe.columns
    ]

    if missing_columns:
        missing_text = ", ".join(missing_columns)

        raise ValueError(
            f"CSV is missing required columns: {missing_text}"
        )


def create_table_if_missing(connection: sqlite3.Connection) -> None:
    """
    Create the blockchain table without deleting existing data.
    """

    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            txhash TEXT,
            blockno INTEGER,
            unixtimestamp INTEGER,
            datetime TEXT,
            from_address TEXT,
            to_address TEXT,
            method TEXT,
            token_collectibles TEXT,
            value_in TEXT,
            value_out TEXT,
            txn_fee_ron TEXT,
            status TEXT,
            source_row_hash TEXT NOT NULL UNIQUE,
            imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_txhash
        ON {TABLE_NAME}(txhash)
        """
    )

    connection.execute(
        f"""
        CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_datetime
        ON {TABLE_NAME}(datetime)
        """
    )


def prepare_records(dataframe: pd.DataFrame) -> list[tuple]:
    """
    Convert the pandas DataFrame into records for SQLite insertion.
    """

    records: list[tuple] = []

    for _, row in dataframe.iterrows():
        records.append(
            (
                clean_value(row["txhash"]),
                clean_value(row["blockno"]),
                clean_value(row["unixtimestamp"]),
                clean_value(row["datetime"]),
                clean_value(row["from"]),
                clean_value(row["to"]),
                clean_value(row["method"]),
                clean_value(row["token_collectibles"]),
                clean_value(row["value_in"]),
                clean_value(row["value_out"]),
                clean_value(row["txn_fee_ron"]),
                clean_value(row["status"]),
                create_row_hash(row),
            )
        )

    return records


def import_records(
    connection: sqlite3.Connection,
    records: list[tuple],
) -> int:
    """
    Insert new rows while ignoring rows that were already imported.
    """

    rows_before = connection.execute(
        f"SELECT COUNT(*) FROM {TABLE_NAME}"
    ).fetchone()[0]

    connection.executemany(
        f"""
        INSERT OR IGNORE INTO {TABLE_NAME} (
            txhash,
            blockno,
            unixtimestamp,
            datetime,
            from_address,
            to_address,
            method,
            token_collectibles,
            value_in,
            value_out,
            txn_fee_ron,
            status,
            source_row_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        records,
    )

    rows_after = connection.execute(
        f"SELECT COUNT(*) FROM {TABLE_NAME}"
    ).fetchone()[0]

    return rows_after - rows_before

def normalize_column_name(column: str) -> str:
    """
    Convert exported CSV headers into consistent internal column names.
    """

    normalized = column.strip().lower()

    replacements = {
        "token / collectibles": "token_collectibles",
        "value in": "value_in",
        "value out": "value_out",
        "txnfee(ron)": "txn_fee_ron",
    }

    return replacements.get(normalized, normalized)

# ---------------------------------------------------------
# Main program
# ---------------------------------------------------------

def main() -> None:
    print("AxieOS Blockchain CSV Import")
    print("=" * 40)

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"CSV file not found:\n{CSV_PATH}"
        )

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    dataframe = pd.read_csv(CSV_PATH)

    dataframe.columns = [
    normalize_column_name(column)
    for column in dataframe.columns
]

    validate_csv_columns(dataframe)

    print(f"CSV file: {CSV_PATH.name}")
    print(f"CSV rows found: {len(dataframe)}")

    records = prepare_records(dataframe)

    with sqlite3.connect(DATABASE_PATH) as connection:
        try:
            create_table_if_missing(connection)

            inserted_count = import_records(
                connection=connection,
                records=records,
            )

            connection.commit()

            total_rows = connection.execute(
                f"SELECT COUNT(*) FROM {TABLE_NAME}"
            ).fetchone()[0]

        except Exception:
            connection.rollback()
            raise

    skipped_count = len(records) - inserted_count

    print(f"New rows inserted: {inserted_count}")
    print(f"Existing rows skipped: {skipped_count}")
    print(f"Total database rows: {total_rows}")
    print(f"Database: {DATABASE_PATH}")
    print("Import completed successfully.")


if __name__ == "__main__":
    main()