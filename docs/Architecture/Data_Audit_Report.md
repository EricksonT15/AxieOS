# Data Audit Report

Version: 1.0

Status: In Progress

---

# Purpose

This document records the verification process for all blockchain datasets imported into AxieOS.

The objective is to ensure that every transaction stored in the AxieOS database can be traced back to an original blockchain export and that the dataset is complete, consistent, and reproducible.

---

# Audit Scope

Current Audit

- Legacy Ronin Explorer
- Wallet Transaction History

Future Audits

- Ronin OP Chain
- Future APIs
- Game-specific datasets

---

# Data Sources

## Legacy Ronin Explorer

Transaction Types

- Transactions
- Transfers
- Internal Transactions

Export Format

- CSV

---

# Raw Dataset Inventory

## Transactions

| File | Status |
|------|--------|
| legacy_transactions_2021.csv | ✅ |
| legacy_transactions_2022.csv | ✅ |
| legacy_transactions_2023.csv | ✅ |
| legacy_transactions_2024.csv | ✅ |
| legacy_transaction_2024_Dec30to31_check.csv | ✅ |
| legacy_transactions_2025.csv | ✅ |
| legacy_transactions_2025_H1.csv | ✅ |
| legacy_transactions_2025_H2.csv | ✅ |
| legacy_transactions_2026.csv | ✅ |

Transfers

- Pending

Internal Transactions

- Pending

---

# Verification Checklist

## File Integrity

| Test | Status |
|------|--------|
| CSV readable | ✅ |
| Headers detected | ✅ |
| UTF-8 encoding | ⬜ |
| Corrupted rows | ⬜ |

---

## Dataset Validation

| Test | Status |
|------|--------|
| Duplicate Txhash check | ⬜ |
| Missing date ranges | ⬜ |
| Earliest transaction verified | ⬜ |
| Latest transaction verified | ⬜ |
| Wallet consistency | ⬜ |
| Status field validation | ⬜ |

---

# Current Findings

## 2024 Validation

A supplementary export covering December 30–31, 2024 was performed because the yearly export could not include December 31.

Result

- December 31 transactions successfully recovered.
- Expected overlap with December 30 confirmed.
- No data loss detected.

---

## 2025 Validation

The yearly export appeared to be affected by the explorer export limit.

Additional exports were created:

- 2025 H1
- 2025 H2

These exports recovered additional unique transaction hashes not present in the original yearly export.

---

# Outstanding Investigation

Legacy Explorer reports

- 6,713 transactions

Current merged dataset contains

- 7,059 unique transaction hashes

Difference

- 346 records

Possible explanations

- Explorer summary excludes certain transaction types.
- Explorer counter uses different counting rules.
- CSV exports include additional contract interactions.
- Additional validation required.

Status

Investigation ongoing.

---

# Acceptance Criteria

The Legacy dataset will be considered complete when:

- Every date range is covered.
- Duplicate transaction hashes are understood.
- Missing transactions are ruled out.
- Explorer discrepancy is explained.
- Dataset is approved for SQLite import.

---

# Audit Status

Current Phase

Data Acquisition & Validation

Next Phase

SQLite Schema Design

---

# Guiding Principle

No transaction enters the AxieOS database until the raw dataset has been verified.

Raw blockchain data is the single source of truth.
