# AO-015 — Data Dictionary

## Purpose

The Data Dictionary is the single source of truth for all data used throughout AxieOS.

It defines every field, data type, source, and business meaning to ensure consistency across spreadsheets, databases, dashboards, machine learning models, and future APIs.

---

# Scope

This document defines:

- Standard field names
- Data types
- Data sources
- Business definitions
- Naming conventions

Every new field introduced into AxieOS must first be documented here.

---

# Design Principles

The Data Dictionary follows these principles:

- One field = one meaning.
- Field names remain stable whenever possible.
- Business meaning is more important than implementation.
- Every table references standardized field names.

---

# Data Sources

Data may originate from:

- Blockchain
- Sky Mavis API
- Manual Entry
- Gameplay
- Marketplace
- Calculated Fields

---

# Module Organization

The Data Dictionary is organized by module.

```
Wallet

Portfolio

Asset Registry

Marketplace

Terrariums

Staking

Bounty Board

Analytics
```

---

# 1. Wallet

| Field | Type | Required | Source | Description |
|------|------|----------|--------|-------------|
| WalletID | Text | Yes | Manual | Unique wallet identifier |
| WalletName | Text | Yes | Manual | Friendly wallet name |
| Blockchain | Enum | Yes | Manual | Ronin, Ethereum, etc. |
| Address | Text | Yes | Blockchain | Wallet address |
| Purpose | Text | Yes | Manual | Primary wallet function |
| Owner | Text | Yes | Manual | Wallet owner |
| Status | Enum | Yes | Manual | Active / Archived |
| CreatedDate | Date | No | Manual | Registration date |
| Notes | Text | No | Manual | Additional remarks |

---

# 2. Portfolio

| Field | Type | Required | Source | Description |
|------|------|----------|--------|-------------|
| PortfolioID | Text | Yes | Manual | Portfolio identifier |
| WalletID | Text | Yes | Wallet | Linked wallet |
| AssetValue | Decimal | No | Calculated | Current valuation |
| TotalROI | Decimal | No | Calculated | Portfolio return |
| LastUpdated | DateTime | No | System | Latest synchronization |

---

# 3. Asset Registry

| Field | Type | Required | Source | Description |
|------|------|----------|--------|-------------|
| AssetID | Text | Yes | Manual | Unique asset identifier |
| AssetName | Text | Yes | Manual | Human-readable name |
| AssetType | Enum | Yes | Manual | Token, NFT, Land, Item |
| Symbol | Text | No | Blockchain | Token symbol |
| Blockchain | Text | Yes | Manual | Network |
| Decimals | Integer | No | Blockchain | Token precision |
| Tradable | Boolean | Yes | Manual | Tradable asset |
| Active | Boolean | Yes | Manual | Active status |
| Notes | Text | No | Manual | Remarks |

---

# 4. Marketplace

| Field | Type | Required | Source | Description |
|------|------|----------|--------|-------------|
| ListingID | Text | Yes | System | Marketplace listing |
| AssetID | Text | Yes | Registry | Linked asset |
| PurchasePrice | Decimal | No | Manual | Purchase cost |
| ListingPrice | Decimal | No | Manual | Selling price |
| MarketplaceFee | Decimal | No | Manual | Marketplace fee |
| Status | Enum | Yes | Manual | Listed / Sold |
| ProfitLoss | Decimal | No | Calculated | Net profit |

---

# 5. Terrariums

| Field | Type | Required | Source | Description |
|------|------|----------|--------|-------------|
| PlotID | Text | Yes | Manual | Plot identifier |
| Biome | Enum | Yes | Manual | Forest, Savannah, etc. |
| ShrineAxies | Integer | No | Manual | Assigned Shrine Axies |
| DojoAxies | Integer | No | Manual | Assigned Dojo Axies |
| AtiaFlame | Integer | No | Gameplay | Current Atia Flame |
| HourlybAXS | Decimal | No | Gameplay | Hourly production |
| LuniumMode | Enum | No | Manual | Global / Local |
| CurrentLunium | Integer | No | Gameplay | Plot Lunium |
| LuniumCapacity | Integer | No | Gameplay | Maximum Lunium |

---

# 6. Staking

| Field | Type | Required | Source | Description |
|------|------|----------|--------|-------------|
| StakeID | Text | Yes | System | Stake identifier |
| Token | Text | Yes | Blockchain | Staked asset |
| Amount | Decimal | Yes | Blockchain | Amount staked |
| APR | Decimal | No | API | Annual percentage rate |
| Rewards | Decimal | No | Blockchain | Pending rewards |
| LastCompound | Date | No | Manual | Latest restake |

---

# 7. Bounty Board

| Field | Type | Required | Source | Description |
|------|------|----------|--------|-------------|
| BountyDate | Date | Yes | Gameplay | Daily bounty |
| TaskID | Text | Yes | Gameplay | Task identifier |
| TaskName | Text | Yes | Gameplay | Objective |
| Category | Enum | Yes | Gameplay | Origins, App, Quest |
| Points | Integer | Yes | Gameplay | Reward points |
| Completed | Boolean | Yes | Manual | Completion status |
| Rerolls | Integer | No | Manual | Number of rerolls |

---

# 8. Analytics

| Field | Type | Required | Source | Description |
|------|------|----------|--------|-------------|
| SnapshotDate | Date | Yes | System | Snapshot date |
| DailybAXS | Decimal | No | Calculated | Daily earnings |
| DailyAXS | Decimal | No | Calculated | Daily AXS |
| PortfolioValue | Decimal | No | Calculated | Current valuation |
| NetWorth | Decimal | No | Calculated | Total value |
| ROI | Decimal | No | Calculated | Return on investment |

---

# Naming Standards

## Dates

ISO 8601

Example

2026-07-20

---

## Currency

Use official token symbols.

Examples

- RON
- AXS
- bAXS
- SLP
- WETH
- USDC

---

## IDs

Every major entity shall have a unique identifier.

Examples

- WalletID
- AssetID
- PlotID
- StakeID
- ListingID
- TransactionID

---

# Business Rules

## DD-001

Every table shall contain a primary identifier.

---

## DD-002

Foreign keys shall reference standardized IDs.

---

## DD-003

Calculated fields must never overwrite source data.

---

## DD-004

Field names shall remain stable across all AxieOS modules.

---

# Revision History

Version: 1.0

Status: Approved

Author: AxieOS Engineering

Last Updated: July 2026
