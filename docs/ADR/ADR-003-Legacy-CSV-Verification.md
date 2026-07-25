# ADR-003: Legacy CSV Verification

## Status

Accepted

## Date

2026-07-25

---

# Context

The Legacy Ronin Explorer provides three export options:

- Transactions
- Transfers
- Internal Transactions

It was unknown whether these contained different information.

---

# Verification

The following files were compared:

- legacy_transactions_2021.csv
- legacy_transfers_2021.csv
- legacy_internal_transactions_2021.csv

Comparison included:

- row count
- column names
- field values

Result:

All three exports were identical for the verified dataset.

---

# Decision

The Legacy Transactions export becomes the canonical source for Legacy Ronin imports.

Transfers and Internal Transactions will not be archived separately unless future verification detects differences.

---

# Consequences

Benefits

- Reduces duplicate data.
- Simplifies import pipeline.
- Reduces storage requirements.

Trade-offs

- Future explorer changes should be periodically revalidated.
