# Data Dictionary

## Purpose

This document defines every data field used throughout AxieOS.

## This document answers

- What does each field mean?
- What data type is expected?
- Which module uses it?
- Where does the data come from?

## Sources

Data may originate from:

- Blockchain
- Sky Mavis API
- Manual Input
- Calculated Fields

  
## Audience

- Project Owner
- Contributors
- Future AI assistants
- Future developers

## Update Rules

- Every new data field should be documented before it is added to the workbook or database.
- Field names should remain stable whenever possible.
- If a field changes meaning, update this document and record the change in the Engineering Journal.

---

# Field Definitions

| Field | Data Type | Module | Description | Source |
|--------|-----------|--------|-------------|--------|

*(No fields have been defined yet. They will be added during Sprint 1.)*

---
| Field        | Type | Required | Source     | Description                     |
| ------------ | ---- | -------- | ---------- | ------------------------------- |
| WalletID     | Text | Yes      | Manual     | Unique identifier (ex. WAL-001) |
| WalletName   | Text | Yes      | Manual     | Friendly name                   |
| Blockchain   | Text | Yes      | Manual     | Ronin                           |
| Address      | Text | Yes      | Blockchain | Wallet address                  |
| Purpose      | Text | Yes      | Manual     | Gameplay, Treasury, Trading...  |
| OwnerAccount | Text | Yes      | Manual     | Parent Account                  |
| Status       | Enum | Yes      | Manual     | Active / Archived               |
| RiskLevel    | Enum | No       | Manual     | Low / Medium / High             |
| CreatedDate  | Date | No       | Manual     | Date added                      |
| Notes        | Text | No       | Manual     | Comments                        |

---

# AxieOS Data Dictionary

## Purpose
...

## Sources
...

## Data Standards          ← (We'll add this later)

## Master Data             ← (Section)

### Wallet                ← AO-014 ✅

| Field | Type | Required | Source | Description |
|--------|------|----------|--------|-------------|
...

### Portfolio             ← AO-015 ✅

| Field | Type | Required | Source | Description |
|--------|------|----------|--------|-------------|
...

### Asset Registry        ← AO-016 (Next)

...

## Operational Data

### Transactions

...

### Daily Bounty

...

### Weekly Snapshot

...

## Calculated Fields

ROI

APR

Efficiency

...

## Revision History

----

# Naming Conventions

## Dates

Use ISO 8601 format whenever possible.

Example:

2026-07-19

---

## Currency / Tokens

Use official token symbols.

Examples:

- AXS
- bAXS
- RON
- SLP

---

## IDs

Every unique object should have an ID where appropriate.

Examples:

- Task ID
- Axie ID
- Wallet Address
- Transaction ID

---

# Notes

The Data Dictionary is the single source of truth for all data collected and analyzed by AxieOS.

## Status

Version: 0.1

This document will evolve throughout the project.
