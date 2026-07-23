# Data Auditor

Version: 1.0

Status: Planned

---

# Purpose

The Data Auditor verifies every dataset before it is imported into the AxieOS database.

Its objective is to detect missing data, duplicates, inconsistencies, and structural issues automatically.

Only audited datasets may be imported into SQLite.

---

# Design Principles

- Never modify raw data.
- Validate before importing.
- Produce repeatable results.
- Generate machine-readable reports.
- Detect problems automatically.

---

# Inputs

Current

- Legacy Ronin Transactions
- Legacy Ronin Transfers
- Legacy Ronin Internal Transactions

Future

- OP Chain Transactions
- Marketplace Exports
- Terrariums
- Bounty Board
- Other AxieOS datasets

---

# Validation Modules

## 1. File Integrity

Verify

- File readable
- UTF-8 encoding
- CSV structure
- Header detection

---

## 2. Schema Validation

Verify

- Column names
- Column order
- Missing columns
- Unexpected columns

---

## 3. Date Coverage

Verify

- Earliest record
- Latest record
- Missing date ranges
- Overlapping exports

---

## 4. Transaction Validation

Verify

- Unique Txhash
- Duplicate Txhash
- Missing hashes
- Wallet consistency

---

## 5. Status Validation

Count

- Success
- Failed
- Pending

---

## 6. Dataset Statistics

Generate

- Total records
- Unique transactions
- Duplicate transactions
- Records per year
- Records per month

---

## 7. Audit Report

Generate

- Summary
- Warnings
- Errors
- Recommendations

---

# Output

The Data Auditor does not modify data.

It produces an audit report that determines whether the dataset is approved for SQLite import.

---

# Approval Rule

Only datasets that pass every validation step may proceed to database import.

---

# Future Expansion

The Data Auditor is designed as a reusable validation framework for every dataset used by AxieOS.
