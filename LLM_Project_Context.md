# AxieOS — LLM Project Context

Last updated: **2026-08-22**

---

## 0. Current Checkpoint

AxieOS is an AI-assisted decision-support, accounting, analytics, and optimization system for the Axie Infinity / GameFi ecosystem.

The project is now organized into specialized workstreams coordinated through a master Control Center.

### Project Chat Map

| Chat                                       | Responsibility                                                                                        |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `00 — AxieOS Project Control Center`       | Overall priorities, roadmap, cross-workstream decisions, project status, and recovery context         |
| `01 — AxieOS Bounty Board Strategy`        | Daily Bounty Board execution, rerolls, Fortune Slips, BP optimization, and live task decisions        |
| `02 — AxieOS Development & Python`         | Python implementation, schemas, parsers, optimizer development, accounting logic, and automation      |
| `03 — AxieOS Marketplace & NFT Strategy`   | Axie, land, accessory, consumable, purchase/sale/release decisions and marketplace strategy           |
| `04 — AxieOS Wallet, Staking & Terrariums` | Wallet activity, AXS/bAXS, staking, claims, Terrariums, Homeland, and reward snapshots                |
| `05 — AxieOS Data & Engineering Journal`   | Canonical EOD logs, engineering journal, datasets, reconciliation, data quality, and decision history |

### Current Operating Priorities

1. Preserve and expand the canonical AxieOS data layer.
2. Continue development of the Bounty Board optimizer using real daily data.
3. Complete current transaction-accounting and cost-basis reconciliation.
4. Establish a reusable Ronin CSV transaction-ingestion workflow.
5. Preserve raw Ronin exports unchanged, even when exports overlap.
6. Deduplicate and normalize blockchain records programmatically.
7. Add owned-Axie inventory and bounty-qualification matching.
8. Build better asset-level ROI tracking for Axies, land, consumables, staking, and Terrariums.
9. Keep this file updated so a fresh LLM session can resume AxieOS without reconstructing the project from chat history.

### Current Development Checkpoint

The project has progressed significantly beyond the original August 8 blockchain-analytics baseline.

Current accounting dataset:

```text
Approximately 320 accounting records
```

Recent cost-basis audit identified:

```text
51 unresolved sales
```

Initial classification:

```text
43 inventory-pool cases
7 Axie inbound-review cases
1 no-prior-evidence case
```

Recent V0.7 development progress:

```text
Tasks 85–87   Complete
Task 88       Cost-basis reconciliation / finalization
Task 89       Swaps — next major accounting area
```

Recent reconciliation work resolved 18 CocoChoco sales using FIFO methodology.

Remaining review work at the latest checkpoint included:

```text
25 CocoChoco sales
8 Axie sales
```

The immediate development objective is to finish the remaining Task 88 cost-basis review before proceeding to swap accounting.

### August 22 Bounty Board Checkpoint

All six tasks were completed.

```text
Raw task BP:                 1,758
6/6 milestone bonuses:        550
---------------------------------
Total board contribution:    2,308 BP
```

Fortune Slips:

```text
Observed before pouch opening: 1,524
10 Regular Lucky Pouches:      -100
Expected remaining:            1,424
```

Consumable inventory after execution:

```text
Regular CocoChoco: 15 usable
Premium CocoChoco: 12 usable
```

### Recovery Rule

This document is the compact project-resumption context.

Detailed chronology belongs in:

```text
05 — AxieOS Data & Engineering Journal
```

Canonical facts should increasingly live in:

* SQLite
* normalized CSV datasets
* transaction ledgers
* asset ledgers
* structured gameplay records

---

## 1. Project Overview

**AxieOS** is an AI-assisted decision-support and analytics system for the Axie Infinity / GameFi ecosystem.

The project is intended to transform:

* blockchain history
* gameplay activity
* Bounty Board decisions
* marketplace transactions
* NFT ownership
* consumable inventory
* staking activity
* Terrarium activity
* reward claims

into structured data that can support:

* portfolio analytics
* wallet analytics
* profitability analysis
* Bounty Board optimization
* Terrarium optimization
* staking analysis
* marketplace ROI tracking
* NFT / Axie inventory analysis
* explainable recommendations
* future machine-learning models

The project should prioritize reliable data and analytics before introducing machine learning.

---

## 2. Core Design Principles

AxieOS follows these principles:

1. **Data before AI**
2. **Measure before optimize**
3. **Reusable tools**
4. **Explain recommendations**
5. **Validate using real player data**
6. **Preserve raw evidence**
7. **Separate operational decisions from canonical accounting**
8. **Do not invent missing transaction data**

The system should avoid making recommendations based only on assumptions when historical or blockchain data can be collected and measured.

---

## 3. Development Environment

Primary development environment:

* Windows
* Visual Studio Code
* Python
* SQLite
* Git
* GitHub
* GitHub Desktop

Repository:

```text
AxieOS
```

Python scripts are stored primarily under:

```text
scripts/
```

Documentation is stored under:

```text
docs/
```

Existing blockchain data is stored under:

```text
data/blockchain/
```

Future Ronin raw-export storage may also use a dedicated structure such as:

```text
data/ronin/
```

---

## 4. Blockchain Data Layer

### Canonical SQLite Database

The canonical populated AxieOS database established during the first development phase is:

```text
data/blockchain/database/axieos.db
```

Initial database size after the legacy import:

```text
40,960 bytes
```

### Initial Imported Dataset

The original legacy blockchain dataset contained:

```text
37 blockchain transactions
```

Date range:

```text
2021-06-29 to 2021-12-15
```

Unique wallet / contract addresses:

```text
10
```

Source CSV:

```text
data/blockchain/raw/legacy_internal_transactions_2021.csv
```

Primary table:

```text
blockchain_transactions
```

Important columns include:

```text
id
txhash
blockno
unixtimestamp
datetime
from_address
to_address
method
token_collectibles
value_in
value_out
txn_fee_ron
status
source_row_hash
imported_at
```

This original 37-row dataset should be treated as the historical first validated blockchain dataset, not as the complete present-day AxieOS transaction history.

---

## 5. Database Cleanup

An accidental empty database previously existed at:

```text
data/axieos.db
```

It was verified on **2026-08-08** to contain:

```text
0 bytes
```

A repository-wide search confirmed that project scripts did not depend on it.

The empty database was deleted.

The canonical AxieOS database remains:

```text
data/blockchain/database/axieos.db
```

---

## 6. Shared Database Connection

Implemented:

```text
scripts/database.py
```

This module provides the shared database connection used by analytics scripts.

New analytics scripts should use:

```python
from database import connect_database
```

when executed according to the current `scripts` directory convention.

The purpose is to prevent individual scripts from defining inconsistent database paths.

---

## 7. Blockchain Import Pipeline

### `create_database_schema.py`

Location:

```text
scripts/create_database_schema.py
```

Purpose:

* create SQLite schema
* create blockchain transaction tables
* prepare the canonical database

### `import_blockchain_csv.py`

Location:

```text
scripts/import_blockchain_csv.py
```

Implemented capabilities include:

* CSV import
* header normalization
* idempotent imports
* SHA-256 row hashing
* duplicate-row prevention
* consistent database insertion

Each imported source row receives a deterministic hash stored in:

```text
source_row_hash
```

This permits repeated imports without duplicating identical source rows.

### `verify_dataset_equivalence.py`

Location:

```text
scripts/verify_dataset_equivalence.py
```

Purpose:

* verify equivalent blockchain datasets
* support migration validation
* compare imported datasets

### `inspect_database.py`

Location:

```text
scripts/inspect_database.py
```

Purpose:

* inspect SQLite database contents
* verify imported records
* inspect schema state

### `validate_import.py`

Location:

```text
scripts/validate_import.py
```

Purpose:

* validate blockchain imports
* compare database state with expected source data

---

## 8. Wallet Analytics

### `wallet_summary.py` v1.0

Location:

```text
scripts/wallet_summary.py
```

Provides:

* total transaction count
* first transaction date
* latest transaction date
* unique wallet / contract count
* transaction-method counts
* token / collectible counts
* recorded RON network fees

Initial validated dataset results:

```text
Total transactions: 37
Unique addresses: 10
```

Transaction methods:

| Method                   | Count |
| ------------------------ | ----: |
| transfer                 |    16 |
| checkpoint               |    12 |
| swapExactTokensForTokens |     4 |
| safeTransferFrom         |     3 |
| approve                  |     1 |
| 0xbec24050               |     1 |

All 37 original source rows contained:

```text
TxnFee(RON) = 0.0
```

Therefore zero network fees reported for that specific historical dataset were consistent with the source data.

---

## 9. Transaction Analytics

### `transaction_summary.py` v1.0

Location:

```text
scripts/transaction_summary.py
```

Provides:

* transaction-status summary
* transaction-method summary
* monthly transaction activity
* wallet-direction analysis
* latest transactions
* duplicate transaction-hash detection

The original version was validated against the 37-row legacy blockchain dataset.

---

## 10. Token Analytics

### `token_summary.py` v1.0

Location:

```text
scripts/token_summary.py
```

Completed and committed on:

```text
2026-08-08
```

Calculates per token / collectible:

* transaction count
* incoming count
* outgoing count
* zero-movement count
* total received
* total sent
* net movement

Python `Decimal` is used instead of ordinary floating-point arithmetic for safer financial and token calculations.

### Initial Validated Results

| Token / Collectible | Transactions |
| ------------------- | -----------: |
| Axie                |            3 |
| RON                 |            1 |
| Ronin Wrapped Ether |            3 |
| Smooth Love Potion  |           30 |
| **Total**           |       **37** |

These figures refer specifically to the original 37-row legacy dataset.

---

## 11. Wallet Ownership Rules

### Original Ronin Wallet

Canonical user-owned Ronin address:

```text
0x5c32ce3b21e786dcaf11d9c64dec31b21a2c6610
```

This is the user's **original Ronin wallet**.

It is distinct from the **Ronin Gamer wallet**.

Transfers between these user-owned wallets must be classified as:

```text
internal transfer
```

They must **not** be counted as:

```text
external income
external expense
purchase
sale
```

unless another independent economic event occurred within the same transaction.

Wallet ownership should therefore be part of transaction reconciliation.

---

## 12. Ronin Transaction Ledger

AxieOS should maintain a durable transaction-history dataset based on official Ronin exports and blockchain evidence.

### Recommended Structure

```text
data/
└── ronin/
    ├── raw/
    │   ├── <original downloaded CSV files>
    │   └── ...
    ├── processed/
    │   └── ronin_transaction_ledger.csv
    └── import_manifest.csv
```

### Raw-Data Policy

Downloaded Ronin CSV files are immutable source evidence.

Rules:

* Never manually delete overlapping rows from raw exports.
* Never manually modify transaction values in raw files.
* Preserve original filenames.
* Preserve every downloaded file.
* Overlapping exports are acceptable.
* Prefer overlap over accidentally leaving gaps in transaction history.

Ronin currently limits CSV exports to relatively small batches, so overlapping files are expected.

### Import Workflow

The eventual importer should:

1. Discover all raw Ronin CSV files.
2. Read each file.
3. Normalize headers.
4. Normalize data types.
5. Preserve source filename.
6. Add import metadata.
7. Combine rows.
8. Identify duplicates safely.
9. Produce a normalized canonical transaction ledger.
10. Record import statistics in an import manifest.
11. Flag ambiguous or conflicting records instead of silently resolving them.

### Deduplication Rule

Do not automatically assume:

```text
transaction_hash
```

is always the complete unique key.

If each CSV row represents one blockchain transaction, transaction hash may be sufficient.

If a blockchain transaction produces several event / transfer rows, use a composite identity based on the actual Ronin export schema.

Possible components include:

```text
transaction_hash
log_index
event_index
token_contract
token_id
from_address
to_address
amount
```

The final deduplication key must be designed **after inspecting real Ronin CSV exports**.

### Import Manifest

A useful import manifest may track:

```text
source_file
imported_at
raw_rows
unique_rows
duplicate_rows
new_rows
date_range
validation_status
```

This allows AxieOS to know what has already been imported without modifying the original evidence.

---

## 13. Axie Identity Rule

Axies must be identified by their immutable:

```text
asset_id
```

or Axie/NFT number.

Do **not** use mutable Axie names as canonical identifiers.

Owners can rename Axies, while the blockchain NFT identifier remains stable.

---

## 14. Gameplay Data Model

The gameplay database should represent daily Axie activity.

### Daily Session

Useful fields include:

```text
date
player_id
shrine_streak
starting_fortune_slips
claimed_fortune_slips
fortune_slips_spent
ending_fortune_slips
weekly_bp_start
weekly_bp_end
rank_start
rank_end
notes
```

### Bounty Board Task

Each task should eventually track:

```text
date
task_number
game
difficulty
action
requirement
initial_reward_bp
final_reward_bp
reroll_count
reroll_slip_cost
completion_status
direct_cost
consumables_used
related_asset_id
time_required
notes
```

This should allow calculations such as:

* BP per Fortune Slip
* reroll success rate
* task-category value
* task completion cost
* task combinations
* expected economic value
* capital required
* recoverable capital
* play-time requirements

---

## 15. Bounty Board Strategy

### Rank Goals

Primary operating target:

```text
Top 500
```

Long-term target:

```text
Top 200
```

### Reroll Mechanics

| Reroll |      Cost | Basic | Intermediate | Advanced | Master |
| ------ | --------: | ----: | -----------: | -------: | -----: |
| 1–3    |  10 slips |   35% |          50% |      13% |     2% |
| 4–6    |  20 slips |   20% |          60% |      17% |     3% |
| 7–8    |  30 slips |    0% |          60% |      36% |     4% |
| 9–10   | 100 slips |    0% |           0% |      92% |     8% |

### Current Operating Rules

* Avoid Den of Mysteries.
* Weak low-BP tasks are candidates for reroll.
* Preserve Fortune Slips when expected improvement does not justify the cost.
* Prefer actions that satisfy multiple tasks.
* Consider real marketplace cost, not BP alone.
* Existing inventory should be checked before recommending a purchase.
* Capital preservation takes priority over chasing BP unnecessarily.

### Consumable Reserve Strategy

Current working targets:

```text
Regular CocoChoco reserve: 10
Premium CocoChoco reserve: approximately 10–15
```

Lucky Pouches should generally be opened in useful batches unless a bounty specifically requires another action.

---

## 16. Bounty Optimizer

The Bounty Optimizer has progressed beyond the original planned stage.

Implemented / established capabilities include:

```text
KEEP
REROLL
COMBO
```

Additional capabilities include:

* overlap detection
* consumable inventory checks
* reroll guardrails
* sequential rerolls
* projected versus actual reroll handling
* plan validation
* rank-bonus targeting
* reserve validation
* daily input builder
* integrated plan generation

Strategy modes include:

```text
conserve
rank_push
master_chase
```

### Owned-Axie Inventory Requirement

A major next capability is an owned-Axie inventory layer.

Before recommending that an Axie be purchased, the optimizer should determine whether an existing owned Axie already satisfies the bounty.

Useful fields include:

```text
asset_id
class
level
breed_count
collectible_status
evolved_status
listing_status
release_eligibility
parts
traits
acquisition_cost
current_status
```

Examples of questions this should answer:

* Do I already own a Beast Axie that satisfies the task?
* Do I own an Axie eligible for release?
* Is an eligible Axie currently listed for sale?
* Does one Axie satisfy multiple simultaneous bounty requirements?
* Would using an owned Axie create a larger economic loss than buying another one?

---

## 17. Marketplace Analytics

Marketplace records should track:

```text
asset_id
asset_type
class
breed_count
level
purchase_date
purchase_price
purchase_currency
purchase_fee
purchase_gas
listing_date
listing_price
sale_date
sale_price
marketplace_fee
net_proceeds
gross_profit
net_profit
holding_period
bounty_task_id
release_value
status
```

Economic analysis should distinguish:

```text
Bounty reward
+
Marketplace result
+
Release value
-
Purchase cost
-
Marketplace fees
-
Gas
-
Consumable cost
-
Opportunity cost
=
True economic result
```

Marketplace decisions belong operationally in:

```text
03 — AxieOS Marketplace & NFT Strategy
```

Final transaction/accounting records belong in the canonical data layer and:

```text
05 — AxieOS Data & Engineering Journal
```

---

## 18. Consumable Inventory

Canonical Axie Consumable Item mappings:

```text
Token ID 1 = Regular CocoChoco
Token ID 2 = Premium CocoChoco
```

These mappings must be used for:

* purchase classification
* sale classification
* inventory
* cost basis
* feeding
* bounty-cost calculations

Inventory events may include:

```text
purchase
sale
feed
pouch reward
craft
release reward
transfer
```

Consumable inventory should eventually be transaction/event-based rather than manually reconciled.

---

## 19. Cost-Basis Accounting

AxieOS is building transaction-level cost-basis accounting.

Important principles:

* Do not invent acquisition cost.
* Use blockchain / marketplace evidence when available.
* Preserve unresolved items for review.
* Separate owned-wallet transfers from purchases/sales.
* Use appropriate inventory accounting for fungible consumables.
* Link NFT sales to specific NFT acquisitions where evidence permits.
* Record fees separately from gross purchase/sale value.
* Use high-precision decimal arithmetic.

### CocoChoco

FIFO methodology has been used for resolved CocoChoco inventory-pool sales.

### Axies

Axie transactions should preferably reconcile using:

```text
asset_id
```

and transaction history.

If a sale exists without a confidently identified acquisition, classify it as unresolved rather than guessing.

### Swaps

Swap accounting is a major next development area after the current cost-basis reconciliation phase.

---

## 20. Land Asset Accounting

Land should be tracked as an owned NFT asset with acquisition basis and lifetime economics.

### Forest Plot

Canonical known record:

```text
Asset: Forest Land
Coordinates: (-123, 9)
Purchase date: 2025-11-18
Purchase price: 0.06841 ETH
Transaction: 0x59a4f8…b8a86b
Funding source: Erick D. Funds
Status: Owned
```

The complete transaction should eventually be reconstructed from the canonical Ronin transaction ledger, including:

```text
full transaction hash
timestamp
buyer wallet
seller wallet
marketplace
gas
fees
token / land identifier
```

Terrarium rewards associated with this Forest plot should eventually be connected to its asset ledger.

This allows analysis of:

* lifetime bAXS earned
* effective bAXS after conversion deductions
* capital recovery
* ROI
* yield on original cost
* current asset value versus historical acquisition value

---

## 21. Terrarium Analytics

Terrarium information is currently recorded through manual snapshots.

### Global

```text
Global Lunium
Claimable bAXS
```

### Forest

```text
Flame
Next distribution
Total acquired
Rank
Global Forest Flame
```

### Savannah

For each plot:

```text
Flame
Next distribution
Total acquired
```

Combined Savannah:

```text
Rank
Global Savannah Flame
```

### Buff Tracking

Future structured records should include:

```text
buff_activation_time
buff_duration
buff_expiry_time
fortune_slip_cost
unbuffed_hours
buff_active_at_snapshot
```

Raw Terrarium morning/EOD snapshots belong in:

```text
04 — AxieOS Wallet, Staking & Terrariums
```

Finalized daily summaries belong in:

```text
05 — AxieOS Data & Engineering Journal
```

---

## 22. Terrarium Buff Strategy

Observed working daily buff cost:

```text
Forest:       8 Fortune Slips
Savannah #1:  3 Fortune Slips
Savannah #2:  3 Fortune Slips
--------------------------------
Total:       14 Fortune Slips/day
```

Buff duration is stackable.

A weekly multi-day activation strategy is preferable when it:

* reduces repetitive work
* lowers risk of forgotten activation
* prevents unbuffed periods
* simplifies analysis
* makes reward comparisons cleaner

---

## 23. Reward and Staking Analytics

AxieOS should track:

```text
reward_source
claim_date
claim_amount
token
staking_date
amount_staked
amount_unstaked
yield
APR
claim_delay
idle_period
transaction_hash
gas
```

Relevant reward sources include:

```text
Bounty Board
Terrariums
AXS staking
bAXS staking
```

The objective is to measure:

* reward accumulation
* idle capital
* claiming frequency
* compounding frequency
* staking yield
* opportunity cost
* transaction costs

Operational staking and claiming belong in:

```text
04 — AxieOS Wallet, Staking & Terrariums
```

---

## 24. Fortune Slip Accounting

Fortune Slips are operationally managed in:

```text
01 — AxieOS Bounty Board Strategy
```

Track:

```text
starting balance
claim amount
reroll spending
Lucky Pouch spending
Terrarium buff spending
ending balance
```

Important rule:

An estimated balance should be labeled as:

```text
projected / expected
```

until an authoritative observed in-game balance is available.

Observed balances override projections.

---

## 25. Data Collection Philosophy

Detailed gameplay logs are being collected throughout August 2026.

The purpose is to build a reliable real-player dataset before deeper automation.

Current logs include examples of:

* initial Bounty Boards
* rerolls
* Fortune Slip usage
* task combinations
* marketplace purchases
* marketplace sales
* consumable use
* Axie evolution
* Axie ascension
* Axie releases
* staking
* reward claims
* Terrarium snapshots
* Terrarium buffs
* cost-basis reconciliation
* internal wallet transfers

The long-term objective is to reduce manual logging once these activities can be reconstructed from structured gameplay and blockchain data.

---

## 26. Future AI / ML Direction

Machine learning is not the immediate priority.

Expected progression:

```text
Raw Data
→ Structured Database
→ Descriptive Analytics
→ Rule-Based Recommendations
→ Statistical Models
→ Machine Learning
→ Explainable AI
```

Potential future models include:

* Bounty task expected-value model
* reroll recommendation model
* marketplace-sale probability model
* Axie holding-period model
* Terrarium reward forecast
* strategy simulation
* NFT ROI estimation
* capital-efficiency model

Explainability should remain a core requirement.

Potential future tooling may include:

```text
SHAP
```

for explaining recommendation or prediction drivers.

---

## 27. Documentation

Important repository documentation includes:

```text
README.md
CHANGELOG.md
LLM_Project_Context.md
docs/
```

Engineering roadmap:

```text
docs/Engineering/ROADMAP.md
```

Architecture and specification documents exist under:

```text
docs/Architecture/
docs/Specifications/
```

### Documentation Responsibilities

Use:

```text
LLM_Project_Context.md
```

for project recovery context.

Use:

```text
05 — AxieOS Data & Engineering Journal
```

for chronological engineering and EOD history.

Use structured databases / CSVs for canonical machine-readable records.

Do not turn `LLM_Project_Context.md` into a full daily transcript.

---

## 28. Git Workflow

Typical repository workflow:

```text
Edit
→ Test
→ Validate
→ Commit
→ Push
```

Analytics or accounting changes should not be committed until outputs have been checked against source evidence.

When possible, meaningful development milestones should also update:

```text
CHANGELOG.md
LLM_Project_Context.md
```

and relevant documentation.

---

## 29. Current Project Position

AxieOS has moved beyond the initial blockchain-summary stage into operational decision support and transaction-level economic accounting.

Current high-level position:

```text
Blockchain Import                 ✅
Database Schema                   ✅
Import Validation                 ✅
Shared Database Connection        ✅
Wallet Analytics                  ✅
Transaction Analytics             ✅
Token Analytics                   ✅
Bounty Optimizer V1               ✅ Operational / improving
Daily Board Input                 ✅
Sequential Reroll Logic           ✅
Inventory Reserve Validation      ✅
Rank Strategy Modes               ✅
Marketplace Accounting            🔄 Active
Cost-Basis Reconciliation         🔄 Active
Ronin CSV Ledger                  ⏭️ Next data-layer expansion
Owned-Axie Inventory Matching     ⏭️ Planned
Swap Accounting                   ⏭️ Next accounting phase
Terrarium Structured Analytics    🔄 Manual data collection
Staking Analytics                 🔄 Manual / structured records developing
Automated Gameplay Import         Planned
AI Recommendations                Future
Machine Learning                  Future
```

### Immediate Engineering Sequence

```text
Finish remaining cost-basis review
→ Task 89 swap accounting
→ Ronin CSV ingestion / normalization
→ Asset and wallet reconciliation
→ Owned-Axie inventory integration
→ Expand automated economic analytics
```

---

## 30. LLM Context Maintenance Procedure

Update `LLM_Project_Context.md` after:

* major architecture decisions
* major schema changes
* meaningful development milestones
* major EOD checkpoints
* changes to canonical wallet ownership
* changes to asset identification rules
* important optimizer changes
* creation of major datasets
* large transaction-reconciliation milestones
* before abandoning a very long project chat

The file does **not** need to be updated after every conversation.

A useful rule is:

```text
Operational work happens in Chats 01–04.
Canonical EOD / engineering history goes to Chat 05.
Overall priorities and recovery coordination belong to Chat 00.
LLM_Project_Context.md stores the compact state required to resume the project.
```

---

## 31. Fresh-Chat Recovery Instruction

When an AxieOS chat becomes too long or a new project conversation must be started, provide this file and instruct:

> Continue AxieOS from the Current Checkpoint. Treat `LLM_Project_Context.md` as the compact project-recovery context. Use the canonical datasets, transaction records, and EOD / Engineering Journal for detailed evidence. Preserve established wallet ownership, accounting, asset-identification, and strategy rules unless newer source evidence explicitly supersedes them.

---

:::
