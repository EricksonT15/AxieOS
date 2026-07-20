# AO-014 — Domain Model

## Purpose

The Domain Model defines the core business entities of AxieOS and the relationships between them.

It provides the conceptual blueprint for the entire system and serves as the foundation for the database, analytics engine, machine learning models, and future AI agent.

---

# Scope

This document defines:

- Core entities
- Entity relationships
- Ownership rules
- Module boundaries

This document does not define implementation details or database schemas.

---

# Design Principles

The AxieOS domain model follows these principles:

- Every object has a single source of truth.
- Every object has a unique identifier.
- Relationships should be explicit.
- Business entities remain independent from implementation.
- New modules should extend the domain rather than modify existing entities whenever possible.

---

# Core Domain

```
Player
│
├── Wallet
│     ├── Asset
│     ├── Transaction
│     ├── Stake
│     └── Plot
│
├── Axie
│     ├── Progress
│     ├── Assignment
│     └── Marketplace Listing
│
├── Bounty
│     └── Task
│
└── Analytics
      ├── Weekly Snapshot
      ├── Daily Snapshot
      └── Portfolio Metrics
```

---

# Entity Status

| Entity | Module | Status |
|---------|--------|--------|
| Player | Core | Active |
| Wallet | Core | Active |
| Asset | Core | Active |
| Transaction | Wallet Analytics | Planned |
| Stake | Staking | Planned |
| Plot | Terrariums | Active |
| Axie | Core | Active |
| Axie Progress | Gameplay | Planned |
| Assignment | Terrariums | Planned |
| Marketplace Listing | Marketplace | Planned |
| Bounty | Bounty Board | Planned |
| Task | Bounty Board | Planned |
| Weekly Snapshot | Analytics | Planned |
| Daily Snapshot | Analytics | Planned |

---

# Entity Definitions

## Player

Represents the owner of one or more wallets.

A player owns all associated blockchain assets, Axies, land plots, staking positions, and gameplay progress.

---

## Wallet

Represents one blockchain wallet.

A wallet stores:

- Tokens
- NFTs
- Land
- Marketplace listings
- Transactions

A player may own multiple wallets.

---

## Asset

Represents any blockchain asset.

Examples:

- RON
- AXS
- bAXS
- WETH
- SLP
- USDC

---

## Transaction

Represents any movement of assets.

Examples:

- Marketplace purchase
- Marketplace sale
- Reward claim
- Token swap
- Wallet transfer
- Staking deposit
- Staking withdrawal

---

## Stake

Represents assets committed to staking.

Current supported assets:

- AXS
- bAXS (future if supported)

---

## Plot

Represents one Terrariums land plot.

A plot contains:

- Shrine
- Dojo
- Assigned Axies
- Atia Flame
- Lunium
- bAXS production

---

## Axie

Represents an NFT.

Each Axie has:

- Collectible properties
- Evolution
- Accessories
- Level
- Experience
- Atia Flame contribution

An Axie may simultaneously participate in multiple systems.

---

## Axie Progress

Represents the progression state of an Axie.

Includes:

- Level
- AXP
- Evolution
- Gameplay progression

AXP may be earned from:

- Terrariums Dojo
- Origins
- Classic
- Axie Quests

---

## Assignment

Represents where an Axie is currently assigned inside Terrariums.

Possible assignments:

- Shrine
- Dojo

Assignment does not prevent gameplay.

---

## Marketplace Listing

Represents an asset currently listed for sale.

Examples:

- Axies
- Premium Cocochoco
- Other supported NFTs

---

## Bounty

Represents one daily Bounty Board.

Contains multiple Tasks.

---

## Task

Represents one individual objective.

Examples:

- Feed Cocochoco
- Buy Consumables
- Origins Battles
- Quests
- Marketplace

---

## Weekly Snapshot

Stores weekly performance.

Examples:

- Bounty Points
- Rewards
- Rank
- Efficiency

---

## Daily Snapshot

Stores daily operational metrics.

Examples:

- bAXS earned
- AXS earned
- Staking rewards
- Marketplace profit
- Gameplay statistics

---

# Relationship Rules

## Player

Owns

- Wallets
- Axies

---

## Wallet

Contains

- Assets
- Transactions
- Stakes
- Plots

---

## Plot

Contains

- Shrine
- Dojo
- Assigned Axies

---

## Axie

May simultaneously:

- Earn passive AXP in the Dojo
- Earn active AXP in Origins
- Earn active AXP in Classic
- Earn active AXP in Axie Quests

---

# Future Expansion

The domain model is designed to support future modules including:

- Marketplace Analytics
- Battle Intelligence
- Digital Twin
- AI Decision Engine
- Machine Learning Models
- SHAP Explainability
- Autonomous AI Agent

---

# Revision History

Version: 1.0

Status: Approved

Author: AxieOS Engineering

Last Updated: July 2026
