# Blockchain Data Pipeline

Version: 1.0

---

# Purpose

This document defines the standard architecture for importing, storing, processing, and analyzing blockchain transaction data within AxieOS.

The objective is to preserve original blockchain data while creating reusable datasets for analytics, dashboards, and AI-powered decision support.

---

# Design Principles

- Preserve raw data.
- Never modify original exports.
- Build reusable processed datasets.
- Separate storage from analysis.
- Make every transformation reproducible.

---

# Overall Architecture

Blockchain

↓

Raw CSV

↓

SQLite Database

↓

Processed Tables

↓

Dashboard

↓

AI Analysis

---

# Phase 1 — Data Acquisition

Source

- Ronin Wallet
- Ronin Explorer
- Future APIs

Export transactions in chronological batches.

Current limitation:

- Maximum of 100 transactions per CSV export.

Each exported file should be stored without modification.

Repository

data/
└── blockchain/
    └── raw/

Example

wallet_001.csv

wallet_002.csv

wallet_003.csv

---

# Phase 2 — Raw Data Preservation

Rules

- Never edit raw CSV files.
- Never rename columns.
- Never remove rows.
- Never clean data directly.

Raw data serves as the permanent source of truth.

---

# Phase 3 — SQLite Import

Import all raw CSV files into SQLite.

Database

data/blockchain/axieos.db

Benefits

- Fast queries
- Unlimited transaction history
- Supports Python
- Supports dashboards
- Supports AI

---

# Phase 4 — Transaction Classification

Convert blockchain events into AxieOS business events.

Examples

Swap

↓

Marketplace Purchase

Marketplace Sale

↓

Revenue

Staking Deposit

↓

Investment

Terrarium Claim

↓

Passive Income

Evolution Cost

↓

Operating Expense

Marketplace Fee

↓

Transaction Cost

---

# Phase 5 — Processed Tables

Examples

Purchases

Marketplace Sales

Swaps

Rewards

Staking

Terrariums

Evolution

Accessories

Collectibles

These tables become the foundation of AxieOS.

---

# Phase 6 — Dashboard

Future dashboard modules

Wallet

Marketplace

Terrariums

Bounty Board

Evolution

Strategies

Performance

---

# Phase 7 — AI Layer

The AI layer will answer questions such as

- Which strategy generated the highest ROI?
- How much was spent on Fortune Slips?
- What is the average cost per Bounty Point?
- Should a task be rerolled?
- Which assets should be sold?
- What should be compounded?

---

# Repository Structure

data/

├── blockchain/

│   ├── raw/

│   ├── processed/

│   └── axieos.db

---

# Guiding Principle

Data flows in one direction.

Blockchain

↓

Raw CSV

↓

SQLite

↓

Processed Data

↓

Dashboard

↓

AI

Raw data is never modified.

Every report, visualization, recommendation, and AI insight must ultimately be traceable back to the original blockchain transaction.
