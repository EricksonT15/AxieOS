# ADR-004: Canonical Wallet Ledger

## Status

Accepted

## Date

2026-07-25

---

# Context

AxieOS collects blockchain data from multiple sources.

Current sources include:

- Legacy Ronin
- Ronin OP Chain

Future blockchain migrations or additional wallet integrations are expected.

Without a unified data model, every analytics module would need to understand multiple blockchain formats, increasing complexity and maintenance.

---

# Decision

AxieOS will maintain a single canonical transaction ledger.

All supported blockchain exports will be imported into one normalized transaction table.

The originating blockchain will be preserved as metadata but will not determine how analytics are performed.

Users interact with one continuous wallet history rather than separate blockchain datasets.

---

# Data Flow

Raw Data

Legacy Ronin CSV
        +
Ronin OP Chain CSV
        +
Future Supported Sources

↓

Validation

↓

Normalization

↓

Duplicate Detection

↓

Chronological Merge

↓

Canonical Wallet Ledger

↓

SQLite Database

↓

Analytics

↓

Machine Learning

↓

AI Decision Support

---

# Canonical Transaction Fields

Every imported transaction should expose a common schema.

Minimum fields include:

- transaction_hash
- timestamp
- blockchain
- wallet_address
- token
- amount
- transaction_type
- gas_fee
- source_file
- imported_at

Additional blockchain-specific fields may be stored without affecting the canonical model.

---

# Duplicate Detection

The transaction hash will serve as the primary identifier whenever available.

During import:

- Existing transaction hashes are skipped.
- Duplicate events are logged.
- Import continues without interruption.

---

# Import History

Every import operation should generate an import log.

Suggested fields:

- Import Date
- Source
- Files Imported
- Rows Read
- Rows Inserted
- Duplicate Count
- Error Count

This provides traceability and simplifies future audits.

---

# Future Expansion

The canonical ledger is designed to support additional blockchain sources without requiring changes to analytics modules.

Examples:

- Future Ronin migrations
- Additional GameFi blockchains
- Multiple wallets

New importers should normalize data into the same canonical schema.

---

# Consequences

Benefits

- Single source of truth for wallet history.
- Simplifies analytics and reporting.
- Simplifies machine learning feature engineering.
- Supports future blockchain migrations.
- Enables long-term historical analysis across multiple blockchain generations.

Trade-offs

- Additional normalization logic during import.
- Import pipeline becomes more sophisticated.
- Blockchain-specific fields may require separate extension tables when necessary.

---

# Rationale

AxieOS is intended to function as a decision-support platform rather than a blockchain explorer.

Blockchain networks are treated as data sources.

The wallet history is treated as the primary business object.

Analytics, reporting, and machine learning operate on the unified wallet ledger instead of individual blockchain datasets.
