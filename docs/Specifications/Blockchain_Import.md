# Blockchain Import Pipeline

## Status

Draft

## Version

1.0

## Date

2026-07-25

---

# Purpose

The Blockchain Import Pipeline imports blockchain transaction exports into the AxieOS SQLite database.

Its objectives are:

- Import blockchain exports from supported sources.
- Validate data quality.
- Prevent duplicate imports.
- Normalize blockchain formats.
- Build one canonical wallet ledger.

---

# Supported Sources

## Legacy Ronin

Folder

data/raw/legacy/

Accepted Files

ronin_legacy_transactions_*.csv

---

## Ronin OP Chain

Folder

data/raw/op_chain/

Accepted Files

ronin_op_transactions_*.csv

---

# Import Workflow

1. Scan data folders.

2. Detect all CSV files.

3. Validate file structure.

4. Read transactions.

5. Normalize fields.

6. Detect duplicates.

7. Insert new transactions.

8. Generate import report.

---

# Folder Discovery

The importer shall automatically discover files.

Example

data/raw/legacy/
    ronin_legacy_transactions_2021.csv
    ronin_legacy_transactions_2022.csv
    ...

No filenames are hardcoded.

---

# Validation Rules

Every file must pass:

✓ Required columns exist.

✓ Transaction Hash exists.

✓ Timestamp exists.

✓ File is readable.

If validation fails:

- stop importing that file
- continue with remaining files
- record error

---

# Required Columns

Minimum required:

Transaction Hash

Timestamp

From

To

Token

Amount

Additional columns are preserved when available.

---

# Normalization

The importer converts all supported blockchains into one canonical schema.

Examples

Timestamp

↓

ISO 8601

Amounts

↓

Decimal

Addresses

↓

Lowercase

Blockchain

↓

Legacy / OP Chain

---

# Duplicate Detection

Primary key

Transaction Hash

If duplicate:

- Skip transaction.
- Record duplicate.
- Continue import.

---

# Import Order

1. Legacy Ronin

2. OP Chain

3. Future Sources

Chronological ordering is handled by timestamps after import.

---

# Import Report

Example

Import Date

Files Imported

Rows Read

Rows Inserted

Duplicates

Errors

Database Total

The report should be saved for future auditing.

---

# Error Handling

Importer should never terminate because of one bad file.

Errors are logged.

Remaining files continue importing.

---

# Logging

Generate

logs/import_YYYYMMDD.log

Include

- Imported files
- Validation failures
- Duplicate count
- Exceptions

---

# Future Support

Designed to support

- Multiple wallets
- Additional blockchains
- Incremental imports
- Re-import after explorer updates

No redesign of analytics should be required.

---

# Output

The importer populates

wallet_transactions

inside the AxieOS SQLite database.

Analytics modules must use the database instead of raw CSV files.
