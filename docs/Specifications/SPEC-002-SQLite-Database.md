# SPEC-002: SQLite Database Design

## Status

Draft

## Version

1.0

## Date

2026-07-25

---

# Purpose

The SQLite database serves as the central data repository for AxieOS.

Its objectives are to:

- Store normalized blockchain transactions.
- Preserve historical game data.
- Support analytics and reporting.
- Provide structured data for machine learning.
- Serve as the single source of truth for all AxieOS modules.

---

# Database Name

AxieOS.db

---

# Design Principles

- One Wallet → One Timeline
- Normalize once, analyze many times.
- Preserve raw values whenever possible.
- Never modify imported blockchain records.
- Derived metrics belong in separate tables.

---

# Core Tables

The initial database consists of six primary tables.

---

## 1. wallet_transactions

Purpose

Stores the canonical blockchain transaction ledger.

Primary Key

transaction_hash

Fields

- transaction_hash
- timestamp
- blockchain
- wallet_address
- from_address
- to_address
- token
- amount
- gas_fee
- transaction_type
- source_file
- imported_at

Description

Every blockchain transaction imported into AxieOS appears exactly once in this table.

---

## 2. marketplace_transactions

Purpose

Stores NFT marketplace activity.

Primary Key

marketplace_id

Fields

- marketplace_id
- transaction_hash
- timestamp
- axie_id
- action
- price
- currency
- marketplace_fee
- buyer
- seller

Description

Contains only marketplace transactions.

One blockchain transaction may produce one marketplace record.

---

## 3. staking_history

Purpose

Stores staking snapshots.

Primary Key

date

Fields

- date
- staked_axs
- staked_baxs
- claimable_axs
- claimable_baxs
- apr

Description

Captured whenever staking information changes.

---

## 4. terrarium_history

Purpose

Stores Terrarium snapshots.

Primary Key

snapshot_datetime

Fields

- snapshot_datetime
- plot
- atia_flame
- lunium
- next_distribution
- total_acquired_baxs
- hourly_rank
- global_flame

Description

Supports trend analysis and Shrine Buff experiments.

---

## 5. bounty_history

Purpose

Stores weekly Bounty Board results.

Primary Key

week_start

Fields

- week_start
- week_end
- bounty_points
- rank
- reward_baxs
- slips_claimed

Description

One record per completed bounty week.

---

## 6. import_history

Purpose

Stores every blockchain import.

Primary Key

import_id

Fields

- import_id
- import_date
- source
- files_imported
- rows_read
- rows_inserted
- duplicate_count
- error_count

Description

Supports auditing and reproducibility.

---

# Relationships

wallet_transactions

↓

marketplace_transactions

↓

staking_history

↓

terrarium_history

↓

bounty_history

Import history remains independent.

---

# Indexes

Indexes should exist on:

wallet_transactions

- transaction_hash
- timestamp
- token
- blockchain

marketplace_transactions

- axie_id
- timestamp

terrarium_history

- snapshot_datetime

staking_history

- date

bounty_history

- week_start

---

# Data Integrity Rules

Transaction Hash must be unique.

Marketplace records must reference a valid transaction hash.

Dates must use ISO-8601 format.

Amounts must use REAL.

Addresses should be stored in lowercase.

---

# Future Tables

The following are intentionally excluded from Version 1.0.

- Inventory
- Consumables
- Materials
- Price History
- AI Recommendations
- Forecast Models
- Marketplace Listings
- Daily Journal

These will be added when their respective modules are implemented.

---

# Migration Strategy

The schema should support future upgrades without modifying historical data.

New tables should be added through migration scripts rather than editing existing data.

---

# Expected Workflow

Blockchain CSV

↓

Validation

↓

Normalization

↓

SQLite

↓

EDA

↓

Feature Engineering

↓

Machine Learning

↓

Decision Support
