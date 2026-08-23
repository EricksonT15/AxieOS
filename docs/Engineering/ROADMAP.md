# AxieOS Roadmap

# AxieOS Engineering Roadmap

**Version:** 1.1  
**Last Updated:** 2026-08-23  
**Current Engineering Release: V0.9 — Bounty Optimizer Integration**

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
| Gameplay Data Model | ✅ Complete |
| Owned Axie Inventory | ✅ Complete |
| Bounty Optimizer Integration | 🚧 Active |
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
- V0.8 — PASS

---

# V0.8 — Gameplay Data Model & Owned-Axie Inventory ✅ COMPLETE

## Objective

Build the structured gameplay-data foundation required to connect AxieOS blockchain/accounting infrastructure to actual gameplay decision-making.

Blockchain ownership alone is not enough for Bounty Board optimization.

AxieOS must understand the player's current Axies, their gameplay attributes, collectible characteristics, body parts, ownership state, and eligibility for bounty requirements.

## Completed

### Owned Axie Registry

Built a persistent owned-Axie registry with support for:

- Axie ID
- wallet address
- ownership status
- class
- gameplay level
- breed count
- collectible status
- evolved status
- acquisition transaction
- acquisition datetime
- acquisition cost
- ownership-date provenance
- last-seen state
- data source

Current ownership is derived from live Ronin contract state rather than accounting history alone.

Final current roster:

- 136 currently owned Axies
- 137 total historical registry records
- Axie #7087631 correctly resolved as SOLD

### Origins / Sky Mavis Gameplay Integration

Integrated the official Sky Mavis Origins API.

Implemented:

- Origins API authentication
- current Ronin fighter retrieval
- full fighter roster synchronization
- class synchronization
- gameplay level synchronization
- six-part Axie profiles
- part class
- part type
- part value
- part stage
- Origins card catalog integration
- human-readable body-part names

Final body-part coverage:

- 136 / 136 current Axies with complete six-part profiles
- 816 / 816 current body parts named
- 285 Origins part families resolved

### On-Chain Axie Metadata

Integrated direct Ronin Axie contract reads for:

- breed count
- Axie genes
- genetic collectible signals

The contract-level field was tested and intentionally rejected as a gameplay-level source.

Origins `xp.currentLevel` remains authoritative for gameplay level.

### Evolution Detection

Implemented evolution-state detection from Origins part-stage data.

Final current roster:

- 65 evolved Axies
- 71 non-evolved Axies

### Collectible Intelligence

Implemented Axie genetic decoding and collectible classification.

Supported collection signals include:

- Mystic
- Bionic
- Japanese
- XMAS
- Summer
- Nightmare
- Shiny
- Origin
- Meo Corp I
- Meo Corp II

Multi-collection Axies are supported.

Final current roster:

- 16 collectible Axies
- 120 non-collectible Axies
- 17 collection trait rows
- 1 multi-collection Axie
- 0 unmapped special genetic signals

### Gameplay Qualification Layer

Built a reusable qualification engine for currently owned Axies.

Supported criteria:

- specific class
- minimum level
- maximum level
- minimum breed count
- maximum breed count
- evolved requirement
- collectible requirement
- required collection
- any allowed collection
- required named body part
- any allowed named body part
- minimum ownership duration

The qualification engine uses three states:

- QUALIFIED
- DISQUALIFIED
- UNKNOWN

`UNKNOWN` is used when required underlying data cannot be verified safely.

Validated examples include:

- Level 20+ qualification
- Plant Level 20+ qualification
- evolved collectible qualification
- Japanese collectible qualification
- Mystic collectible qualification
- Pincer body-part qualification
- evolved + Pincer qualification
- ownership-duration qualification

Current Pincer-qualified Axies:

- #3576345
- #6251324
- #11755726

Current evolved + Pincer-qualified Axies:

- #3576345
- #6251324

### Ownership-Duration Intelligence

Validated Origins `ownership.lastTransferTime` against local blockchain acquisition timestamps.

Validation result:

- 9 / 9 exact matches

Ownership-start provenance for the current roster:

- 9 `RONIN_LOCAL_TRANSFER`
- 115 `SKYMAVIS_ORIGINS_LAST_TRANSFER`
- 12 `LEGACY_HISTORY_UNRESOLVED`

Exact ownership-start dates are available for 124 / 136 current Axies.

The remaining 12 Axies appear to require historical reconciliation with legacy Ronin-chain data.

AxieOS deliberately does not fabricate ownership dates for these records.

Ownership-duration qualification therefore returns `UNKNOWN` for those Axies.

### Ronin RPC Reliability

Hardened live Ronin reads for production use.

Implemented:

- request pacing
- retry logic
- exponential backoff
- HTTP 429 rate-limit handling
- shared Axie-core caching

The shared Axie-core cache allows breed-count and collectible-genetics stages to reuse the same blockchain reads rather than querying every Axie twice.

### V0.8 Production Pipeline

Implemented the production runner:

`run_gameplay_data_v08()`

Production stages:

1. Current ownership synchronization
2. Origins gameplay metadata
3. On-chain breed counts
4. Collectible intelligence
5. Human-readable body-part names
6. Ownership-start provenance
7. Final database validation

## Final Production Validation

- Current owned Axies: 136
- Class coverage: 136 / 136
- Gameplay level coverage: 136 / 136
- Breed-count coverage: 136 / 136
- Collectible-status coverage: 136 / 136
- Evolution-status coverage: 136 / 136
- Complete named six-part profiles: 136 / 136
- Named body parts: 816 / 816
- Evolved Axies: 65
- Collectible Axies: 16
- Collection trait rows: 17
- Exact ownership-start dates: 124
- Legacy-history unresolved: 12
- Unknown ownership provenance: 0
- Qualification engine: PASS
- V0.8 Database Validation: PASS
- V0.8 Production Pipeline: PASS

## Deferred to V0.9

The following originally planned V0.8 items are intentionally carried forward into Bounty integration:

- event-based CocoChoco inventory state
- Fortune Slip structured state
- Lucky Pouch structured state
- release-material inventory state
- live Bounty Board task mapping
- direct Bounty optimizer integration
- optimizer recommendation vs actual-result tracking

## Final Deliverable

V0.8 provides a verified gameplay-data and qualification foundation capable of answering:

> Which Axies do I currently own, what gameplay characteristics do they have, and which gameplay requirements can each Axie satisfy?

---

# V0.9 — Bounty Optimizer Integration 🚧 ACTIVE

## Objective

Connect the existing Bounty Board optimization engine to the verified V0.8 gameplay-data layer and live structured AxieOS state.

The goal is to remove manual Axie qualification and progressively remove manual gameplay-inventory inputs.

## Existing Capabilities

The Bounty optimizer already supports:

- KEEP / REROLL / COMBO decisions
- sequential rerolls
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

V0.8 now additionally provides:

- authoritative current owned-Axie roster
- Axie class
- gameplay level
- breed count
- evolution status
- collectible status
- collection membership
- named body parts
- ownership-duration qualification
- safe UNKNOWN handling

## Planned

### Live Axie Qualification Integration

- Replace manually entered Axie qualification assumptions
- Pull eligible Axies directly from `gameplay_owned_axies`
- Use the V0.8 qualification engine for live Bounty task requirements
- Return exact qualifying Axie IDs for each applicable task
- Prevent use of Axies that are no longer owned

### Bounty Task Requirement Model

Create structured mappings between Bounty Board tasks and qualification criteria.

Examples:

- class requirement
- minimum level
- evolved requirement
- collectible requirement
- Japanese collectible
- Mystic collectible
- specific body part
- ownership-duration requirement

### Gameplay Inventory State

Move key gameplay inventory away from manually entered balances.

Priority assets:

- Regular CocoChoco
- Premium CocoChoco
- Fortune Slips
- Lucky Pouches
- release materials

### Blockchain ↔ Gameplay Linking

Connect gameplay inventory and Bounty decisions with:

- marketplace purchases
- marketplace sales
- Axie ownership
- consumable acquisition
- consumable sale
- release events
- gameplay consumption

### Bounty Outcome Tracking

- Track actual daily BP outcome
- Track optimizer recommendation vs actual result
- Store historical Bounty decisions
- Record reroll decisions
- Record task completion
- Record resource consumption
- Support later strategy-performance analysis

### Economics Integration

- Integrate marketplace acquisition cost
- Integrate release economics
- Expose economic cost of completing Bounty tasks where relevant
- Preserve capital-conservation guardrails

## Expected Deliverable

AxieOS should generate a daily Bounty Board recommendation from live structured state, including:

1. KEEP / REROLL / COMBO recommendation
2. Exact eligible owned Axie where applicable
3. Required gameplay inventory
4. Expected BP
5. Fortune Slip cost
6. Economic cost where applicable
7. Rank-strategy impact
8. Validation that the recommendation is executable

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

Begin **V0.9 — Bounty Optimizer Integration**.

Connect the completed V0.8 gameplay-data and Axie qualification foundation to the existing Bounty Board optimizer.

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
- [x] Gameplay Data Model & Owned-Axie Inventory V0.8
- [x] 136-Axie current ownership reconciliation
- [x] Origins gameplay metadata integration
- [x] On-chain breed-count and genetic intelligence
- [x] 816 body-part name mappings
- [x] Collectible classification
- [x] Ownership-duration provenance
- [x] Bounty qualification engine
- [x] V0.8 database validation
- [x] V0.8 production pipeline validation
- [x] V0.8 commit and push

## Current Tasks

- [ ] Define V0.9 Bounty task requirement model
- [ ] Map Bounty task types to V0.8 qualification criteria
- [ ] Connect owned-Axie qualification to Bounty optimizer
- [ ] Return exact eligible Axie IDs for relevant tasks
- [ ] Build structured CocoChoco inventory state
- [ ] Build structured Fortune Slip state
- [ ] Connect gameplay inventory to optimizer
- [ ] Integrate Bounty task economics where applicable
- [ ] Track optimizer recommendation vs actual result
- [ ] Store historical Bounty decisions
- [ ] Build V0.9 integration validation
- [ ] Update LLM_Project_Context.md
- [ ] Update CHANGELOG.md
- [ ] Update Engineering_Journal.md

---

# Immediate Next Step

Begin **V0.9 Task 99 — Bounty Task Requirement Model**.

The first V0.9 engineering step is to define how each Bounty Board task translates into structured machine-readable requirements that can be evaluated by the completed V0.8 qualification engine.

Initial mappings should prioritize requirements already supported by V0.8:

- Axie class
- minimum level
- evolved status
- collectible status
- specific collectible collection
- named body part
- ownership duration

This requirement model will become the bridge between live Bounty Board tasks and the owned-Axie qualification engine.

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