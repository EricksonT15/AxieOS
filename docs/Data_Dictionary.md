# AxieOS Data Dictionary

Version: 1.0 (Draft)

---

# Purpose

The Data Dictionary is the single source of truth for all data used by AxieOS.

It defines every entity, field, data type, source, and naming convention used throughout the project.

All spreadsheets, databases, Python scripts, APIs, dashboards, and machine learning models must follow this specification.

---

# This Document Answers

- What data does AxieOS store?
- What does each field mean?
- What data type is expected?
- Where does the data originate?
- Which entity owns the field?

---

# Data Sources

Data within AxieOS may originate from one of the following sources:

| Source | Description |
|---------|-------------|
| Blockchain | Ronin blockchain transactions and balances |
| Sky Mavis API | Official Axie ecosystem data |
| Manual | Entered by the user |
| Calculated | Derived from existing data |

---

# Data Standards

## Dates

Use ISO 8601.

Example

2026-07-19

---

## Token Symbols

Always use official symbols.

Examples

- AXS
- bAXS
- RON
- SLP
- WETH
- USDC

---

## Naming Convention

Entity IDs should remain permanent.

Examples

| Entity | Example |
|---------|----------|
| Wallet | WAL-001 |
| Asset | TOK-AXS |
| Portfolio | PORT-001 |
| Transaction | TXN-000001 |
| Weekly Snapshot | WKS-2026-30 |

---

# Reference Data

Reference Data changes infrequently.

## Wallet

| Field | Type | Required | Source | Description |
|---------|------|----------|---------|-------------|
| WalletID | Text | Yes | Manual | Internal unique identifier |
| WalletName | Text | Yes | Manual | Friendly wallet name |
| Blockchain | Text | Yes | Manual | Ronin |
| Address | Text | Yes | Blockchain | Wallet address |
| Purpose | Text | Yes | Manual | Primary wallet purpose |
| OwnerAccount | Text | Yes | Manual | Parent account |
| Status | Enum | Yes | Manual | Active / Archived |
| RiskLevel | Enum | No | Manual | Low / Medium / High |
| CreatedDate | Date | No | Manual | Date added |
| Notes | Text | No | Manual | Additional remarks |

---

## Asset Registry

The Asset Registry defines every asset recognized by AxieOS.

Operational entities should reference AssetID instead of storing asset names directly.

| Field | Type | Required | Source | Description |
|---------|------|----------|---------|-------------|
| AssetID | Text | Yes | Manual | Unique asset identifier |
| AssetName | Text | Yes | Manual | Human-readable name |
| AssetType | Enum | Yes | Manual | Token, NFT, Land, Item, Position |
| Blockchain | Text | Yes | Manual | Ronin |
| Symbol | Text | No | Manual | Official token symbol |
| Decimals | Integer | No | Blockchain | Token decimals |
| Tradable | Boolean | Yes | Manual | Tradable asset |
| Active | Boolean | Yes | Manual | Active within AxieOS |
| Notes | Text | No | Manual | Additional remarks |

---

# Operational Data

Operational Data changes frequently during gameplay.

## Portfolio

| Field | Type | Required | Source | Description |
|---------|------|----------|---------|-------------|
| PortfolioID | Text | Yes | Generated | Portfolio record identifier |
| WalletID | Text | Yes | Reference | References Wallet |
| AssetID | Text | Yes | Reference | References Asset Registry |
| AssetType | Enum | Yes | Reference | Token, NFT, Stake, Position |
| Quantity | Decimal | Yes | Blockchain / Manual | Current quantity |
| Unit | Text | Yes | Reference | Token, NFT, Plot, Item |
| Location | Enum | Yes | Manual | Wallet, Staked, Delegated, Marketplace |
| LastUpdated | DateTime | Yes | Generated | Last synchronization |
| Remarks | Text | No | Manual | Notes |

---

## Transactions

*To be defined during Sprint 1.*

---

## Daily Bounty

*To be defined during Sprint 1.*

---

## Weekly Snapshot

*To be defined during Sprint 1.*

---

# Calculated Data

Calculated entities are generated automatically from operational data.

Examples include:

- Portfolio Value
- ROI
- APR
- Weekly Efficiency
- Slip Efficiency
- Prediction Scores

---

# Design Principles

- Every entity has a unique ID.
- Raw data should never be overwritten.
- Historical records should remain immutable.
- Analytics are derived from raw data.
- Asset names should never be duplicated across entities.

---

# Revision History

| Version | Date | Notes |
|----------|------|-------|
| 1.0 | 2026-07-19 | Initial refactored Data Dictionary |
