# AxieOS Roadmap

# AxieOS Engineering Roadmap

**Version:** 1.3
**Last Updated:** 2026-10-30
**Current Engineering Release: V0.13 - Inventory Optimization and ForRel Farming Analytics (scoped analytical release validated)**

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
| Bounty Optimizer Integration | ✅ Complete |
| Marketplace Strategy Analytics | ✅ Complete |
| Terrarium Analytics | ✅ Complete |
| Staking Analytics | ✅ V0.12 committed per user; remote state not independently verified |
| V0.13 Inventory / ForRel Reporting | PASS - Five historical report areas and Checkpoint 95 Dojo register validated |
| Task 135H Provisional Finance Evidence | 🔄 Offline views through 96CL; incomplete metrics remain unknown |
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

# V0.9 — Bounty Optimizer Integration ✅ COMPLETE

## Objective

Connect the Bounty Board optimization engine to the verified V0.8 gameplay-data layer and structured AxieOS state.

The release focused on eliminating manual Axie qualification, improving inventory and Fortune Slip state, adding task economics, and establishing recommendation-performance tracking.

## Completed

### Bounty Requirement Model

- Structured Bounty task requirements
- Task-name normalization
- Parameterized task resolution
- Historical task compatibility
- Mapping to V0.8 Axie qualification criteria

### Owned-Axie Integration

- Connected owned-Axie qualification directly to the optimizer
- Returned exact eligible Axie IDs
- Prevented use of Axies that are no longer owned
- Supported class, level, breed, evolution, collectible, collection, part, and ownership-duration requirements

### Gameplay Inventory

- Structured Regular and Premium CocoChoco inventory
- `on_hand`
- `reserved`
- `available`
- Gameplay-database inventory source
- Verified snapshot + subsequent inventory-event derivation
- Reserve-aware recommendation validation

### Fortune Slips

- Structured Fortune Slip state
- Protected reserves
- Projected reroll spend
- Projected remaining balance
- Reserve-aware reroll decisions

### Bounty Economics

- Explicit task economic inputs
- Gross cost
- Expected recovery
- Net WETH cost
- BP efficiency
- Non-WETH costs
- `INPUT_REQUIRED` handling for missing evidence
- Explicit COMBO economics to avoid double-counting

### Recommendation vs Actual

Tracked:

- KEEP recommendations
- REROLL recommendations
- COMBO recommendations
- planned BP
- actual BP
- planned Fortune Slip spend
- actual Fortune Slip spend
- expected net cost
- actual net cost
- recommendation-followed status

Actual states include:

- PENDING
- COMPLETED
- REROLLED
- SKIPPED
- PARTIAL

### Historical Task Resolution

Production historical Bounty records were normalized through the current task resolver plus historical compatibility aliases.

Final validation:

```text
Final selected historical tasks      72
Resolved                             72
Unresolved                            0
Resolution rate                     100%
```

### Optimizer Decision Persistence

Added:

```text
bounty_optimizer_runs
bounty_optimizer_decisions
```

Recommendations are stored initially as `PENDING` and can later be reconciled against actual gameplay evidence.

Persistence is atomic.

Historical gameplay outcomes are not retroactively treated as historical AxieOS recommendations.

Normal optimizer execution remains read-only unless recommendation persistence is explicitly requested.

### Final Validation

```text
V0.9 tests                     25 / 25 PASS
Historical task resolution            PASS
Current daily plan                    PASS
Production history safety             PASS

V0.9 Integration Validation           PASS
```

Production optimizer-history rows remained unchanged during synthetic validation:

```text
Optimizer runs                  0 -> 0
Optimizer decisions             0 -> 0
```

## Result

V0.9 provides an integrated Bounty Board decision-support system capable of combining structured task requirements, owned-Axie eligibility, gameplay inventory, Fortune Slip economics, task economics, and recommendation-performance tracking.

---

# V0.10 — Marketplace Strategy Analytics

## Objective

Go beyond transaction accounting and support marketplace decision-making.

## Completed

- inventory_report.py
- capital recovery reporting (historical roadmap label; `capital_management.py` does not exist in the user-provided script inventory)
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

# V0.11 — Terrarium Analytics ✅

## Objective

Build an evidence-preserving Terrarium analytics layer that reconstructs historical observations, measures cumulative bAXS accumulation, analyzes competitive position, and supports transparent projection and financial ROI analysis without inventing missing data.

## Completed

- Added canonical Terrarium summary, validation, trend, change, accumulation, Flame-share, and Next Distribution analytics.
- Added dedicated Terrarium snapshot, plot, and ranking evidence tables.
- Added `scripts/add_terrarium_evidence.py`.
- Recovered canonical and partial historical observations without filling missing fields.
- Added evidence-aware metric-level analytics.
- Added adjacent-versus-bridged change analysis.
- Changed unknown Terrarium buff state to remain `NULL`.
- Removed the false default from `estimated_unbuffed_hours`.
- Preserved all 17 historical legacy zero values without rewriting historical evidence.
- Added `scripts/terrarium_projection.py`.
- Added calendar-date-span projections using Decimal arithmetic.
- Added conservative / base / upside sensitivity scenarios at 75%, 100%, and 125% of observed pace.
- Added `scripts/terrarium_roi.py`.
- Kept financial assumptions separate from historical Terrarium yield.
- Added required runtime AXS-price input.
- Applied the repo-confirmed 70% bAXS → AXS conversion assumption.
- Applied the corrected Forest acquisition reference of 871.81 RON.
- Added ROI input guardrails and regression validation.

## Final Data Coverage

```text
Canonical Terrarium snapshots              17
Canonical plot rows                        51
Canonical ranking rows                     34

Partial evidence observations              13
Evidence plot rows                         29
Evidence ranking rows                      12

Evidence-aware observations                30
Represented calendar dates                 18
Historical range             2026-08-07 → 2026-08-27
```

## Accumulation Basis

```text
Forest #1                    +19.6300 bAXS
Savannah #1                   +1.6200 bAXS
Savannah #2                   +1.9800 bAXS
Combined                     +23.2300 bAXS

Calendar-date span                  20 days
Combined nominal pace         1.1615 bAXS/day
```

The nominal pace is a **calendar-date-span average**, not a precise 24-hour normalized yield.

## Financial ROI References

```text
Forest plot                    (-123, 9)
Purchase price                 0.06841 ETH
Historical RON reference       871.81 RON
bAXS → AXS conversion          70%
Conversion haircut             30%
```

AXS market price is supplied at runtime rather than stored as a fixed historical value.

## Result

V0.11 provides an evidence-aware Terrarium analytics, projection, and ROI layer while preserving the distinction between historical observations and financial assumptions.

---

# V0.12 — Staking & Reward Analytics ✅ VALIDATED

## Objective

Build an evidence-preserving analytics layer for AXS and bAXS staking operations, reward claims, immediate restaking, historical reward trends, and reward-source attribution.

## Completed

- Added `scripts/staking_event_resolver.py`.
- Added `scripts/staking_summary.py`.
- Added `scripts/reward_history.py`.
- Reused blockchain transactions, accounting records, and wallet-registry evidence.
- Normalized staking activity by transaction hash and accounting event.
- Identified CLAIM, STAKE, UNSTAKE, and RESTAKE_REWARD operations.
- Reconstructed older transactions with missing methods using conservative token-flow inference.
- Preserved explicit-method HIGH confidence and inferred MEDIUM confidence.
- Attributed bAXS rewards to Bounty Board and Terrariums using corroborated contract addresses.
- Separated AXS staking rewards from principal movements.
- Implemented daily, ISO-weekly, and monthly reward-history reporting.
- Used Decimal arithmetic for financial quantities.
- Kept analytics read-only without modifying production records.

## Validated Coverage

- Normalized staking events: **34**
- HIGH-confidence events: **12**
- MEDIUM-confidence events: **22**
- Unresolved events: **0**
- Multi-leg staking transaction hashes: **4**
- Reward events: **18**
- Reward events HIGH / MEDIUM: **6 / 12**

## Validated Historical Reward Totals

- Bounty Board: **60.310335038216979400 bAXS**
- Terrariums: **42.624047319087398186 bAXS**
- Combined bAXS rewards: **102.934382357304377586 bAXS**
- Claimed AXS rewards: **0.646876807361839655 AXS**
- Immediately restaked AXS rewards: **0.597635044539543860 AXS**
- Combined AXS rewards: **1.244511851901383515 AXS**

Historical reward coverage: July 20 through August 19, 2026, using stored timestamps.

## Validation

- Python syntax compilation: PASS
- Staking event normalization: PASS
- Reward-source attribution: PASS
- Multi-leg transaction deduplication: PASS
- Decimal aggregation: PASS
- Daily reward totals: PASS
- Weekly reward reconciliation: PASS
- Monthly reward reconciliation: PASS
- Read-only operation: PASS

## Limitations and Deferred Work

- Imported blockchain and accounting data currently extend through August 22, 2026.
- Reports are historical, not live balances or lifetime earnings.
- Historical staked-principal snapshots have not been established.
- Reliable historical APR calculations are deferred until principal and time-weighted balance evidence become available.
- Older method-null transactions retain MEDIUM confidence.
- AXS and bAXS are not combined using an assumed conversion rate.
- Stored timestamps are not converted to another timezone.
- Immediate reward restakes are counted as one economic operation, not as separate claim and stake rewards.

## Release Status

Implementation and analytical regression validation complete.

The user confirmed committing and pushing the V0.12 release. Commit `c5b49f7` is recorded in the project context; a fresh remote check has not been performed for this roadmap update.

---
# V0.13 - Inventory Optimization and ForRel Farming Analytics (SCOPED ANALYTICAL RELEASE VALIDATED)

## Objective

Optimize owned-Axie utilization across Terrariums, Origins, marketplace recovery, collectible evolution, and Release Farming (`ForRel`).

## Planning Baseline — October 26, 2026

- Reported Axies not listed for sale: **132**
- Terrarium operating requirement: **120**
- Potential flexible inventory: **12**

The 12-Axie difference is not an automatic sale or release target. Individual Axie productivity, strategic value, acquisition economics, and evolution potential must be evaluated.

## Development Tasks (original plan; scoped analytical delivery)

- **Task 135A — Feasibility and Data-Quality Audit:** Inspect schemas, `inventory_report.py`, gameplay integration, live-data limitations, and acquisition/cost-basis coverage. Reconcile the reported 132 unlisted Axies.
- **Task 135B — Canonical Inventory:** Combine IDs, classes, levels, genes, evolution stages, collectible status, AXP, Flame, Terrarium assignment, acquisition history, marketplace evidence, Origins value, and ForRel eligibility.
- **Task 135C — Terrarium Roster Optimization:** Recommend a 120-Axie roster while preserving productive collectibles, competitive Origins Axies, and strategically useful farming candidates.
- **Task 135D — Surplus Classification:** Recommend RETAIN, ORIGINS, FORREL, SELL, RELEASE, or REVIEW.
- **Task 135E — ForRel Farming Analytics:** Track acquisition costs, AXP, ascension readiness, part classes, release materials, and effective Memento costs.
- **Task 135F — Buy-versus-Breed Economics:** Compare high-breed marketplace purchases against internal breeding, including SLP, bAXS, gas, and marketplace expenses.
- **Task 135G - Reporting:** Five selected historical CSVs cover inventory, Terrarium membership, portfolio decisions, ForRel priorities and class-weighted Memento sensitivity. Their row counts, ID crosswalks and no-approval safeguards passed; Checkpoint 95 records five Dojo trainees. These are dated analytical snapshots, not live executable recommendations.
- **Task 135H — Provisional Capital and Finance Evidence:** Checkpoint 96 assembled a partial capital register and scoped offline views for contributions, reward quantities, marketplace proceeds, purchase outlays and candidate raw gas. Through 96CL, the user-run helpers and report checks passed within their stated limits. Complete capital recovery, realized profit, PHP income/expenses and all-time gas remain unknown. These views are not the V0.14 Unified Finance implementation.

## ForRel Naming Convention

`ForRel_YYYYMMDD_B##_PRICE`

The date represents actual acquisition date, `B##` represents breed count out of seven, and the price represents WETH acquisition cost in the established naming format.

## Engineering Safeguards

- Start with schema and data-quality audits before coding.
- Reuse existing database architecture and gameplay scripts.
- Treat current marketplace listing status as unverified until refreshed.
- Do not infer missing cost basis, acquisition dates, or live status.
- Do not automatically list, sell, breed, ascend, or release Axies.
- Keep recommendations separate from operational and accounting records.

## First Deliverable

**AxieOS Inventory Optimization V1.0 — Feasibility Assessment, Database Coverage Review, and Phased Implementation Plan.**

## Release Closeout

- The selected package contains five historical report CSVs, supporting provenance, the Checkpoint 95 bundle, five scripts and two documentation files. Database backups and Checkpoint 96 evidence remain outside the selected release.
- Validation passed for report row counts, unique IDs, crosswalks, no approvals or automatic execution, Dojo roster/manifest consistency, script syntax and staged whitespace. Full buy-versus-breed and Unified Finance economics remain unresolved.
- Git publication is identified by its release commit. Remaining untracked historical evidence does not imply a clean working tree.
- Carry incomplete acquisition evidence, capital/recovery, cost basis, gas units and PHP valuation to V0.14 without replacing unknown values with zero.

## Prerequisites

V0.12 release was user-confirmed committed and pushed. This section's earlier planned state is superseded by the current V0.13 closeout status.

# V0.14 — Unified Finance

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

# V0.15 — Dashboards

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

Complete the V0.12 Staking & Reward Analytics release documentation, validate the final repository state, commit, and push to main.

## Completed

- [x] Task 132 — Staking and reward foundation audit
- [x] Task 133 — Normalized staking event resolver and reward-source attribution
- [x] Task 134A — Staking summary
- [x] Task 134B — Historical reward analytics and daily/weekly/monthly validation
- [x] Task 134C1 — Repository audit and Python compilation

## Current Task

- [ ] Task 134C2 — Release documentation
- [ ] Task 134C3 — Final regression and selective Git staging
- [ ] Task 134C4 — V0.12 commit and push

## Immediate Next Step

Complete documentation updates, review the repository diff, verify production database and unrelated capital-recovery files remain excluded, selectively stage V0.12 release files, then commit and push.

## Upcoming Work

Task 135A — V0.13 Inventory Optimization & ForRel Farming Analytics feasibility and database coverage audit.


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