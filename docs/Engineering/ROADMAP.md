# AxieOS Roadmap

# AxieOS Engineering Roadmap

**Version:** 1.1  
**Last Updated:** 2026-08-23  
**Current Engineering Release:** V0.7

---

# Vision

AxieOS is an AI-powered decision-support platform for Axie Infinity players.

Rather than simply tracking transactions, AxieOS transforms blockchain data, marketplace activity, staking, Terrariums, Bounty Board activity, collectibles, inventory, and player behavior into structured information and actionable recommendations.

The long-term objective is to build a reusable GameFi operating system that can:

- collect data automatically,
- maintain reliable historical records,
- understand wallet and asset activity,
- calculate economic outcomes,
- track gameplay resources,
- evaluate strategic choices,
- recommend actions,
- and explain why each recommendation was made.

## Core Principles

- Data before AI
- Measure before optimize
- Explain every recommendation
- Preserve source evidence
- Never invent missing accounting data
- Reusable analytics
- Automation where practical
- Human remains in control
- Separate raw data from interpreted data
- Prefer deterministic rules before machine learning

---

# Current Status

| Area | Status |
|---|---|
| Development Foundation | ✅ Complete |
| SQLite Database Foundation | ✅ Complete |
| Import Pipeline | ✅ Complete |
| Ronin API Sync | ✅ Complete |
| Historical Blockchain Backfill | 🔄 Operational / Continuing |
| Transaction Classification | ✅ Complete |
| Asset & Wallet Intelligence | ✅ Complete |
| Marketplace Transaction Economics | ✅ Complete |
| Automated Accounting Pipeline | ✅ Complete |
| Accounting Review & Reporting | ✅ Complete |
| Gameplay Data Model | ⏭️ Next |
| Owned Axie Inventory | ⏭️ Next |
| Bounty Optimizer Integration | 🟡 Partially Built |
| Marketplace Strategy Analytics | ⏳ Planned |
| Terrarium Analytics | ⏳ Planned |
| Staking Analytics | ⏳ Planned |
| Unified Finance Reporting | ⏳ Planned |
| Dashboards | ⏳ Planned |
| AI Recommendation Engine | ⏳ Planned |

---

# Engineering Release History

# V0.1 — Ronin API Sync ✅

## Objective

Replace manual blockchain data collection with automated Ronin API ingestion.

## Completed

- Ronin API connectivity
- Transaction retrieval
- Token transfer retrieval
- Pagination
- API response normalization
- Raw transaction storage
- Raw transfer storage
- Idempotent database writes
- Duplicate protection
- Initial sync validation

## Result

AxieOS can retrieve and persist wallet activity directly from Ronin infrastructure instead of relying only on manually exported transaction files.

---

# V0.2 — Transaction Classification ✅

## Objective

Translate raw blockchain transactions into understandable economic and gameplay activity.

## Completed

- Group blockchain movements by transaction hash
- Transaction direction detection
- Marketplace purchase classification
- Marketplace sale classification
- Transfers
- Burns
- Claims
- Staking-related activity
- Token swaps
- Unknown transaction preservation
- Classification validation

## Result

Raw blockchain activity can be converted into structured transaction events.

---

# V0.3 — Transaction Economics ✅

## Objective

Extract economic meaning from marketplace transactions.

## Completed

- Marketplace purchase economics
- Marketplace sale economics
- Gross sale reconstruction
- Marketplace fee calculation
- Net proceeds
- Exact NFT acquisition matching
- Realized Axie P/L
- Chronological acquisition matching
- Economic reconciliation

## Marketplace Accounting Rules

### Purchases

Buyer acquisition cost is the total WETH paid.

Marketplace seller-side fee is not added again to the buyer's acquisition cost.

### Sales

Recorded fields include:

- gross sale value,
- marketplace fee,
- net WETH received,
- cost basis when provable,
- realized P/L when provable.

## Result

AxieOS can calculate exact realized economics for supported marketplace trades.

---

# V0.4 — Historical + Incremental Sync ✅

## Objective

Maintain the blockchain ledger automatically while progressively reconstructing older wallet history.

## Completed

- Incremental transaction sync
- Incremental transfer sync
- Persistent sync state
- Historical transaction backfill
- Historical transfer backfill
- Batch-limited backfill
- Duplicate-safe ingestion
- Ledger rebuild
- Historical validation
- Production sync workflow

## Operational Note

The V0.4 architecture is complete.

Historical backfill may continue during normal production runs until the configured historical boundary is reached.

This continuing backfill is an operational data process, not an unfinished V0.4 engineering task.

---

# V0.5 — Asset & Wallet Intelligence ✅

## Objective

Teach AxieOS to understand assets, counterparties, wallet ownership, and protocol roles.

## Completed

### Wallet Registry

Supports wallet ownership and role classification including:

- USER_OWNED
- EXTERNAL
- CONTRACT

Roles include:

- PRIMARY
- SECONDARY
- MARKETPLACE
- STAKING
- DEX
- BURN
- SYSTEM
- UNKNOWN

### Asset Registry

Supports asset categories including:

- AXIE_NFT
- CONSUMABLE
- MATERIAL
- FUNGIBLE_TOKEN
- NFT
- MULTI_TOKEN
- UNKNOWN

### Transaction Intelligence

Completed:

- counterparty discovery,
- wallet relationships,
- owned-wallet detection,
- protocol-role classification,
- internal-transfer architecture,
- zero-address semantics,
- staking intelligence,
- release-contract intelligence,
- burn intelligence,
- historical-intelligence validation.

## Result

AxieOS now reasons about who or what a blockchain transaction interacts with, instead of looking only at token movement.

---

# V0.6 — Automated Accounting Pipeline ✅

## Objective

Convert blockchain intelligence into persistent accounting records.

## Completed

- Unified accounting record
- Accounting event taxonomy
- Accounting validation
- Marketplace economics enrichment
- Non-marketplace accounting enrichment
- Internal-transfer accounting treatment
- Accounting persistence
- Idempotent UPSERT
- Accounting reconciliation
- Production pipeline integration

## Accounting Event Types

- ASSET_PURCHASE
- ASSET_SALE
- TOKEN_SWAP
- TRANSFER_IN
- TRANSFER_OUT
- INTERNAL_TRANSFER
- ASSET_BURN
- MINT_OR_CLAIM
- STAKING_OR_REWARD
- UNKNOWN

## Accounting Statuses

- READY
- REVIEW
- NON_TAXABLE_INTERNAL
- INFORMATIONAL

## Important Design Rule

Missing economic information is never silently invented.

Records remain in `REVIEW` when cost basis, ownership, classification, or economic treatment cannot be proven.

---

# V0.7 — Accounting Review & Reporting ✅

## Objective

Turn the automated accounting pipeline into an auditable review and reporting system.

## Completed

### Accounting Review Queue

- Load all REVIEW records
- Reconcile review counts
- Group records by event type

### Review Reason Engine

Reason codes include:

- MISSING_COST_BASIS
- MISSING_REALIZED_PL
- TRANSFER_OWNERSHIP_UNRESOLVED
- SWAP_COST_BASIS_PENDING
- UNRESOLVED_CLASSIFICATION

### Counterparty Resolution

Completed:

- known owned-wallet registration,
- unresolved counterparty history,
- release-contract detection,
- staking-role resolution,
- zero-address handling,
- token-burn classification,
- NFT-burn classification,
- known-role reconciliation.

### Historical Cost-Basis Review

Completed:

- cost-basis evidence audit,
- NFT vs inventory basis separation,
- unresolved Axie acquisition review,
- formal unresolved cost-basis queue.

### CocoChoco Inventory Accounting

Token mapping:

- Token ID 1 = Regular CocoChoco
- Token ID 2 = Premium CocoChoco

Completed:

- quantity-aware inventory reconstruction,
- FIFO lot tracking,
- known vs unknown acquisition basis,
- FIFO cost basis,
- realized CocoChoco P/L,
- preservation of unresolved inventory history.

### Swap Review

- Historical SLP → WETH swaps identified
- Reward/claim origin recognized
- Unsupported historical SLP cost basis remains REVIEW
- No artificial zero-cost assumption

### Accounting Summary

Reports:

- total accounting records,
- accounting status,
- event type,
- cost-basis coverage,
- realized-P/L coverage,
- review population.

### Marketplace & Realized P/L Report

Reports:

- marketplace purchases,
- marketplace sales,
- gross sales,
- marketplace fees,
- net proceeds,
- cost basis,
- realized P/L,
- realized ROI,
- asset-level P/L.

### Production Validation

V0.7 production validation includes:

- review queue reconciliation,
- cost-basis queue reconciliation,
- READY sale basis integrity,
- REVIEW preservation,
- swap review preservation,
- marketplace net reconciliation,
- realized P/L reconciliation,
- realized sale reconciliation.

## Current Production Validation

All layers pass:

- V0.4 — PASS
- V0.5 — PASS
- V0.6 — PASS
- V0.7 — PASS

---

# V0.8 — Gameplay Data Model & Owned-Axie Inventory ⏭️ NEXT

## Objective

Connect AxieOS blockchain/accounting infrastructure to actual gameplay decision-making.

The next major engineering requirement is a structured model of the player's current Axies and gameplay assets.

Blockchain ownership alone is not enough for Bounty Board optimization.

AxieOS must understand characteristics such as:

- Axie ID
- class
- level
- breed count
- collectible status
- collectible type
- evolved status
- body parts
- special parts
- eligibility for bounty requirements
- acquisition state
- release eligibility
- current ownership

## Planned

### Owned Axie Registry

Create a persistent owned-Axie dataset.

Possible fields:

- axie_id
- wallet_address
- class
- level
- breed_count
- collectible_type
- is_collectible
- is_evolved
- ownership_status
- acquisition_txhash
- acquisition_datetime
- acquisition_cost
- current_status
- last_updated

### Gameplay Qualification Layer

Determine whether an owned Axie satisfies requirements such as:

- specific class,
- minimum level,
- collectible requirement,
- evolved requirement,
- specific body part,
- Japanese collectible,
- Mystic collectible,
- ownership-duration requirement.

### Inventory State

Begin moving gameplay inventory from manually entered balances toward event-based state.

Priority assets:

- Regular CocoChoco
- Premium CocoChoco
- Fortune Slips
- Lucky Pouches
- release materials

### Blockchain ↔ Gameplay Linking

Connect:

- marketplace purchases,
- marketplace sales,
- Axie ownership,
- consumable acquisition,
- consumable sale,
- release events,
- gameplay inventory.

## Expected Deliverable

AxieOS should be able to answer:

> Which Axies do I currently own, and which current Bounty Board tasks can each Axie satisfy?

---

# V0.9 — Bounty Optimizer Integration

## Objective

Connect the existing Bounty Board optimization engine to live structured AxieOS data.

## Existing Capabilities

The Bounty optimizer already supports:

- KEEP / REROLL / COMBO decisions
- reroll costs
- reroll probabilities
- Fortune Slip conservation
- rank-push strategy
- Master-chance strategy
- inventory requirements
- Regular CocoChoco reserve
- Premium CocoChoco reserve
- overlapping task detection
- projected vs actual reroll balance
- daily board input
- plan validation
- rank bonus targeting

## Planned

- Replace manual Axie qualification inputs
- Pull eligible Axies from owned-Axie registry
- Pull CocoChoco inventory from gameplay inventory
- Pull Fortune Slip balance from structured state
- Integrate marketplace acquisition cost
- Integrate release economics
- Track actual daily BP outcome
- Track optimizer recommendation vs actual result
- Store historical bounty decisions

## Expected Deliverable

A daily Bounty Board recommendation generated from live AxieOS state.

---

# V0.10 — Marketplace Strategy Analytics

## Objective

Go beyond transaction accounting and support marketplace decision-making.

## Planned

- inventory_report.py
- capital_management.py
- marketplace_strategy.py
- holding-period analysis
- realized ROI
- unrealized inventory
- turnover
- acquisition efficiency
- release candidates
- resale candidates
- accessory monitoring
- capital allocation

## Metrics

- Acquisition cost
- Gross sale
- Marketplace fee
- Net proceeds
- Realized P/L
- ROI
- Holding period
- Win rate
- Capital utilization
- Inventory value

---

# V0.11 — Terrarium Analytics

## Objective

Track land and Terrarium performance over time.

## Planned

- terrarium_summary.py
- terrarium_projection.py
- structured snapshot storage
- rank history
- flame history
- bAXS distribution history
- land-level yield tracking
- ROI tracking

## Metrics

- Global Lunium
- Flame
- Rank
- Total Flame
- Daily bAXS
- Claimable bAXS
- Total acquired bAXS
- Monthly yield
- Historical yield
- Land ROI

---

# V0.12 — Staking & Reward Analytics

## Objective

Track Axie ecosystem staking positions and reward flows.

## Planned

- staking_summary.py
- reward_history.py
- staking yield history
- bAXS staking
- AXS staking
- reward claims
- restaking activity
- APR history
- reward-source attribution

## Metrics

- AXS staked
- bAXS staked
- Rewards claimed
- Rewards restaked
- Effective yield
- APR trend
- Total staking income

---

# V0.13 — Unified Finance

## Objective

Combine all AxieOS economic activity into one finance layer.

## Sources

- Marketplace
- Bounty Board
- Terrariums
- Staking
- Token swaps
- Consumables
- Axie releases
- Gas
- Internal transfers

## Planned

- income_report.py
- expense_report.py
- capital_flow.py
- portfolio_summary.py

## Important Accounting Goals

Separate:

- realized profit,
- unrealized value,
- rewards,
- internal transfers,
- gameplay expenses,
- capital purchases,
- gas costs.

---

# V0.14 — Dashboards

## Objective

Provide concise daily, weekly, and monthly operational views.

## Planned

- daily_dashboard.py
- weekly_dashboard.py
- monthly_report.py

## Dashboard Areas

- Bounty Board
- Marketplace
- Owned Axies
- CocoChoco inventory
- Fortune Slips
- Terrariums
- Staking
- Wallet activity
- Realized P/L
- Capital allocation

---

# V1.0 — AI Recommendation Engine

## Objective

Turn the structured AxieOS data platform into an explainable decision engine.

## Planned

- recommendation_engine.py
- strategy_engine.py
- opportunity_scoring.py
- prediction modules where justified by sufficient data

## Future Capabilities

- Marketplace recommendations
- Capital allocation
- Axie purchase recommendations
- Axie resale recommendations
- Evolution planning
- Release recommendations
- Bounty optimization
- Reroll recommendations
- Terrarium optimization
- Staking decisions
- Opportunity ranking
- Personalized gameplay strategy

## AI Design Principle

AI should operate on verified structured data produced by AxieOS.

Recommendations should include:

1. Recommendation
2. Supporting data
3. Expected benefit
4. Expected cost
5. Risk
6. Confidence
7. Alternative action

---

# Utility & Infrastructure Roadmap

## Planned

- [ ] backup_database.py
- [ ] export_to_excel.py
- [ ] export_to_csv.py
- [ ] database migration framework
- [ ] automated regression test suite
- [ ] configurable production settings
- [ ] structured logging
- [ ] error reporting
- [ ] scheduled production sync

---

# Documentation Roadmap

## Current Documents

- README.md
- LLM_Project_Context.md
- Decision_Log.md
- CHANGELOG.md
- Engineering_Journal.md
- ROADMAP.md

## Planned / Expand

- Architecture.md
- Database_Schema.md
- Accounting_Model.md
- Marketplace_Model.md
- Gameplay_Data_Model.md
- Bounty_Model.md
- Terrarium_Model.md
- AI_Design.md

---

# Current Sprint

## Sprint Goal

Begin **V0.8 — Gameplay Data Model & Owned-Axie Inventory**.

## Completed Before This Sprint

- [x] Development foundation
- [x] SQLite database foundation
- [x] Import pipeline
- [x] Ronin API Sync V0.1
- [x] Transaction Classification V0.2
- [x] Transaction Economics V0.3
- [x] Historical + Incremental Sync V0.4
- [x] Asset & Wallet Intelligence V0.5
- [x] Automated Accounting Pipeline V0.6
- [x] Accounting Review & Reporting V0.7
- [x] V0.7 production validation
- [x] V0.7 commit and push

## Current Tasks

- [x] Modernize ROADMAP.md
- [ ] Define V0.8 gameplay data model
- [ ] Design owned-Axie registry schema
- [ ] Build owned-Axie persistence layer
- [ ] Import / synchronize owned Axie state
- [ ] Add Axie gameplay attributes
- [ ] Build bounty qualification matcher
- [ ] Connect CocoChoco inventory identity
- [ ] Validate owned-Axie state
- [ ] Integrate with Bounty optimizer
- [ ] Update LLM_Project_Context.md
- [ ] Update CHANGELOG.md
- [ ] Update Engineering_Journal.md

---

# Immediate Next Step

Begin **V0.8 Task 93 — Gameplay Data Model Design**.

The first engineering decision is to define the persistent owned-Axie schema before writing synchronization or qualification logic.

---

# Long-Term Vision

AxieOS should evolve into a complete GameFi decision-support platform capable of:

- automatically importing blockchain transactions,
- maintaining historical wallet state,
- understanding assets and counterparties,
- tracking current owned assets,
- calculating profitability,
- reconstructing inventory,
- measuring ROI,
- tracking gameplay performance,
- forecasting outcomes where sufficient data exists,
- recommending optimal actions,
- and explaining every recommendation using supporting evidence.

The goal is not to replace the player.

The goal is to augment player decision-making with reliable data, transparent economics, automation, and explainable AI.