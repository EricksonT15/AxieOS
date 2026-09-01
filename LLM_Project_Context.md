# AxieOS — LLM Project Context

Last updated: **2026-09-01**

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

AxieOS has now completed the core engineering work through V0.10.

Current production data includes:

```text
blockchain_transactions              565 rows
blockchain_accounting_records         405 rows
gameplay_owned_axies                  137 rows
canonical marketplace inventory       171 Axies
```

Current release status:

```text
V0.1  Ronin API Sync                         COMPLETE
V0.2  Transaction Classification             COMPLETE
V0.3  Transaction Economics                  COMPLETE
V0.4  Historical + Incremental Sync          COMPLETE
V0.5  Asset & Wallet Intelligence            COMPLETE
V0.6  Automated Accounting Pipeline          COMPLETE
V0.7  Accounting Review & Reporting          COMPLETE
V0.8  Gameplay Data Model + Owned Axies      COMPLETE
V0.9  Bounty Optimizer Integration           COMPLETE
V0.10 Marketplace Strategy Analytics         CORE ENGINEERING COMPLETE
```

V0.10 established the canonical marketplace inventory and strategy-analysis layer.

Final V0.10 production checkpoint:

```text
Canonical inventory                    171
Unique Axies                           171

OPEN_OWNED                             136
CLOSED_SOLD                             27
CLOSED_RELEASED                          8

Inventory validator                   PASS
Inventory errors                         0

Production sign-off                   PASS
Sign-off errors                           0
```

Marketplace strategy output currently remains advisory and conservative:

```text
STRATEGY_HOLD_PROTECTED                 65
STRATEGY_HOLD_INSUFFICIENT_DATA         65
STRATEGY_REVIEW_EXIT_OPTIONS             6
STRATEGY_NOT_APPLICABLE                 35

Automatic SELL decisions                 0
Automatic RELEASE decisions              0
```

Current V0.10 closeout tasks:

```text
Task 121   Update LLM_Project_Context.md        IN PROGRESS
Task 122   Update CHANGELOG.md                  PENDING
Task 123   Engineering Journal completion       PENDING
```

The immediate development objective is to complete V0.10 documentation, then commit and push the validated V0.10 implementation before beginning the next AxieOS release.


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

AxieOS has progressed from blockchain ingestion and accounting into structured gameplay intelligence and operational Bounty Board decision support.

### Release Status

```text
V0.1  Ronin API Sync                         COMPLETE
V0.2  Transaction Classification             COMPLETE
V0.3  Transaction Economics                  COMPLETE
V0.4  Historical + Incremental Sync          COMPLETE
V0.5  Asset & Wallet Intelligence            COMPLETE
V0.6  Automated Accounting Pipeline          COMPLETE
V0.7  Accounting Review & Reporting          COMPLETE
V0.8  Gameplay Data Model + Owned Axies      COMPLETE
V0.9  Bounty Optimizer Integration           COMPLETE
V0.10 Marketplace Strategy Analytics         CORE ENGINEERING COMPLETE
```

V0.10 core implementation and production validation are complete.

Remaining V0.10 work is documentation closeout:

```text
Task 121   LLM_Project_Context.md             IN PROGRESS
Task 122   CHANGELOG.md                       PENDING
Task 123   Engineering Journal                PENDING
```

### V0.8 Gameplay Foundation

V0.8 established the structured owned-Axie gameplay layer used by the optimizer.

Production checkpoint:

```text
Owned Axies                         136
Gameplay metadata                   136 / 136
Named parts                         816 / 816
Collectibles                        16
Evolved Axies                       65
Exact ownership provenance          124
Legacy-history unresolved           12

V0.8 DB Validation                  PASS
V0.8 Pipeline Validation            PASS
```

Owned-Axie qualification supports class, level, breed count, evolved status, collectible status / collection, required parts, and minimum ownership days.

Qualification results use:

```text
QUALIFIED
DISQUALIFIED
UNKNOWN
```

The `UNKNOWN` state is used when historical provenance is insufficient to make an exact determination.

### V0.9 Bounty Optimizer

V0.9 integrates:

```text
Bounty requirement resolution
Owned-Axie qualification
Exact eligible Axie IDs
Structured CocoChoco inventory
Structured Fortune Slip state
Gameplay inventory integration
Reserve-aware optimization
Bounty economics
KEEP / REROLL / COMBO recommendations
Recommendation-vs-actual tracking
Optimizer decision persistence
Actual-outcome reconciliation
Explicit live recommendation saving
```

The operational flow is:

```text
Daily Board
    ↓
Task Resolution
    ↓
Owned-Axie Qualification
    ↓
Inventory + Fortune Slips
    ↓
Bounty Economics
    ↓
KEEP / REROLL / COMBO
    ↓
Recommendation Tracking
    ↓
Actual Gameplay Evidence
    ↓
Recommendation-vs-Actual Reconciliation
```

### Inventory and Fortune Slips

Optimizer inventory supports:

```text
manual
gameplay_db
```

Gameplay inventory is derived from the latest verified snapshot plus inventory events occurring strictly after that snapshot.

A missing verified snapshot does not default to zero.

CocoChoco state tracks:

```text
on_hand
reserved
available
```

Fortune Slip state tracks balance, protected reserve, projected reroll spend, and projected remaining balance.

### Bounty Economics

Economically applicable tasks can use explicit:

```text
gross_cost_weth
expected_recovery_weth
basis
confidence
non_weth_costs
```

Missing economic evidence does not default to zero. The model can instead return:

```text
INPUT_REQUIRED
```

COMBO economics require an explicit combined profile so shared execution costs are not accidentally double-counted.

### Recommendation vs Actual

V0.9 tracks planned versus actual:

```text
BP
reroll slips
net WETH cost
recommendation followed
```

Actual states include:

```text
PENDING
COMPLETED
REROLLED
SKIPPED
PARTIAL
```

Missing actual evidence remains `PENDING`.

### Historical Task Compatibility

Historical Bounty records contain wording variants from earlier manual logging periods.

V0.9 resolves them using:

```text
1. Current V0.9 task resolver
2. Historical compatibility aliases
```

Historical-only identifiers are kept outside the active `BOUNTY_TASK_CATALOG`.

Production validation:

```text
Final selected historical tasks      72
Resolved                             72
Unresolved                            0
Resolution rate                     100%
```

Some non-final historical reroll rows may remain semantically unresolved. They are retained as slot / roll / slip evidence and do not block unrelated recommendation reconciliation.

### Optimizer Decision Persistence

V0.9 introduced:

```text
bounty_optimizer_runs
bounty_optimizer_decisions
```

Architecture:

```text
gameplay_daily_sessions
        ↓
bounty_optimizer_runs
        ↓
bounty_optimizer_decisions
```

One gameplay session may contain multiple optimizer runs because the Bounty Board can change after rerolls.

Recommendations are persisted first as `PENDING`, then reconciled later using actual gameplay evidence.

Persistence is atomic. If a decision insert fails, the entire optimizer run is rolled back.

Normal execution:

```text
python bounty_optimizer.py
```

does not automatically save optimizer recommendation history.

Saving recommendation history requires the explicit persistence workflow.

### Historical Recommendation Integrity

Do not reconstruct historical AxieOS recommendations from gameplay outcomes alone.

Historical gameplay can prove what happened, but it does not prove what AxieOS recommended unless that recommendation was actually recorded.

The explicit live-save workflow therefore:

```text
blocks historical LIVE_OPTIMIZER attribution
blocks exact duplicate optimizer-plan saves
keeps normal optimizer execution read-only
```

At the V0.9 validation checkpoint:

```text
bounty_optimizer_runs          0 rows
bounty_optimizer_decisions     0 rows
```

This is intentional.

All synthetic persistence tests used in-memory SQLite databases. No fabricated historical optimizer recommendations were inserted into the production database.

Genuine optimizer history should begin accumulating only from explicitly saved live recommendations going forward.

### V0.9 Final Validation

The final V0.9 integration validator covers:

```text
Requirements & Axie qualification
Inventory, Fortune Slips & daily input
Bounty economics
Recommendation-vs-actual tracking
Gameplay actual-outcome adapter
Optimizer persistence
Optimizer reconciliation
Explicit-save safeguards
Production historical task resolution
Current daily-plan regression
Production-history mutation safety
```

Final result:

```text
V0.9 tests                     25 / 25 PASS
Historical task resolution            PASS
Current daily plan                    PASS
Production history safety             PASS

V0.9 Integration Validation           PASS
```

Production optimizer-history counts remained unchanged:

```text
Optimizer runs                  0 -> 0
Optimizer decisions             0 -> 0
```

### Current Regression Fixture

`bounty_daily_input.py` currently contains the historical August 18, 2026 fixture:

```text
DAILY_DATE                      2026-08-18
Observed BP                           2050
Starting Fortune Slips                1712
Ending Fortune Slips                  1402
Strategy                          Conserve
Minimum reserve                         20

Task BP                               1375
Additional BP                          675
Recorded slip spend                    310
Plan Status                          READY
Data Quality                         REVIEW
```

The `REVIEW` state is expected because observed BP contains 675 additional / unattributed BP. It is not a V0.9 optimizer regression failure.

Because this fixture is historical, it must not be saved as a current `LIVE_OPTIMIZER` recommendation.




### Immediate Engineering Sequence

```text
V0.10 core engineering COMPLETE
    ->
Update LLM_Project_Context.md
    ->
Update CHANGELOG.md
    ->
Write V0.10 Engineering Journal completion record
    ->
Commit and push V0.10
    ->
Begin next AxieOS release
```

## 29A. V0.10 Marketplace Strategy Analytics

V0.10 introduced the canonical Axie marketplace inventory and strategy-analysis layer.

Primary implementation:

```text
scripts/inventory_report.py
```

The script is intentionally read-only against the production SQLite database.

Production database:

```text
data/blockchain/database/axieos.db
```

The production database remains local / untracked and must not be committed to Git.

### Canonical Marketplace Inventory

The V0.10 inventory is built from the union of relevant Axie IDs across:

```text
gameplay_owned_axies
marketplace_events
blockchain_accounting_records
```

Production source coverage at final validation:

```text
gameplay_owned_axies rows             137
marketplace distinct Axies             11
accounting distinct Axies              42
canonical Axie inventory              171
canonical unique Axies                171
```

Final canonical position states:

```text
OPEN_OWNED                             136
CLOSED_SOLD                             27
CLOSED_RELEASED                          8
                                      ----
TOTAL                                   171
```

The canonical inventory is not limited to Axies currently present in gameplay inventory. It also retains legitimate historical marketplace / accounting positions so sold and released assets remain available for analytics and reconciliation.

### Ownership and Acquisition Semantics

V0.10 explicitly separates:

```text
ownership start
```

from:

```text
economic acquisition
```

Ownership-start evidence proves when an Axie entered user ownership.

Economic-acquisition evidence requires defensible purchase / cost evidence.

This distinction prevents transfers, legacy ownership history, or incomplete provenance from being treated as proven purchases.

At the V0.10 checkpoint:

```text
Known ownership-start datetime          157
Ownership-start READY                   154
Ownership-start REVIEW                   17

Known economic acquisition cost          34
Known acquisition datetime               34
Known acquisition txhash                 27
```

For current open positions, only 7 of 136 have proven acquisition cost suitable for READY resale / capital analytics.

### Listing and Sale Semantics

Historical marketplace listing records do not prove that an Axie is currently listed.

V0.10 therefore distinguishes:

```text
CLOSED_POSITION                         35
LISTING_RECORDED_UNVERIFIED              1
UNKNOWN                                135
```

No live marketplace source is currently connected that can prove a present active listing.

Sale evidence distinguishes accounting-confirmed sales from weaker historical marketplace records.

At the V0.10 checkpoint:

```text
SOLD_CONFIRMED                          25
SALE_RECORDED_UNVERIFIED                 2
NO_SALE_EVIDENCE                       136
NOT_APPLICABLE_RELEASED                  8
```

### Datetime Policy

Canonical blockchain / accounting timestamps are treated as UTC.

Older manually entered marketplace timestamps may represent Philippine local time and are retained as REVIEW evidence rather than silently shifted.

Example:

```text
Axie #2788135 accounting burn:
2026-08-14 03:57:05 UTC

Legacy marketplace release:
2026-08-14 11:57:05
```

The exact eight-hour difference is consistent with Asia/Manila local time, but V0.10 does not silently rewrite legacy timestamps without explicit source proof.

### Realized Economics

Realized P/L is calculated only when accounting evidence is sufficiently complete.

Final production status:

```text
REALIZED_READY                          14
REALIZED_REVIEW                         11
REALIZED_UNAVAILABLE                     2
REALIZED_NOT_APPLICABLE                144
```

READY realized rows contain exact accounting-backed:

```text
gross sale
marketplace fee
net proceeds
cost basis
realized P/L
realized ROI
```

Historical accounting values are used directly rather than recomputing historical marketplace fees.

### Unrealized Economics

V0.10 does not fabricate current market value.

Because no live Axie marketplace-price source is connected:

```text
current_market_value = unavailable
unrealized_pl        = unavailable
unrealized_roi       = unavailable
```

for all open positions.

This is an intentional data-quality rule.

### Marketplace Fee and Resale Break-Even

A production audit of 25 accounting-backed Axie sales found:

```text
Observed marketplace fee rate: 4.2500%
Minimum observed rate:          4.2500%
Maximum observed rate:          4.2500%
```

V0.10 therefore uses:

```text
4.25%
```

as an explicitly labeled historical marketplace-fee assumption for future resale break-even analysis.

For an open Axie with proven acquisition basis:

```text
break-even gross sale price
=
acquisition cost / (1 - 0.0425)
```

The model does not currently include purchase gas or future sale gas in WETH break-even because those costs may be denominated in RON and no timestamp-specific RON/WETH conversion model has been established.

Final resale status:

```text
RESALE_READY                              7
RESALE_UNAVAILABLE_NO_COST              129
RESALE_NOT_APPLICABLE                    35
```

### Holding-Period Analytics

Holding periods use canonical ownership-start evidence.

For open positions, holding time runs from ownership start to the current UTC report timestamp.

For closed positions, holding time ends at confirmed / recorded sale or release.

Final production state:

```text
HOLDING_READY                           153
HOLDING_REVIEW                            4
HOLDING_UNAVAILABLE                      14
```

The four REVIEW positions are legacy timestamp / provenance cases.

The 14 unavailable positions lack a defensible ownership-start datetime.

Very short holding periods are valid. Historical release candidates were sometimes purchased and released within minutes.

### Release-Candidate Economics

V0.10 introduced the first canonical release-candidate analysis layer.

All 136 currently owned Axies have:

```text
level
breed_count
```

available from `gameplay_owned_axies`.

Current owned-Axie coverage includes:

```text
Collectible Axies                        16
Evolved Axies                            65
Protected collectible/evolved set        65
```

A collectible or evolved Axie is treated as protected from automatic release analysis.

Final release-analysis states:

```text
RELEASE_ANALYSIS_READY                    6
RELEASE_REVIEW_NO_COST_BASIS             65
RELEASE_REVIEW_PROTECTED_ATTRIBUTE       65
RELEASE_NOT_APPLICABLE                   35
```

Only six currently owned, non-protected Axies have sufficient proven capital basis for READY release analysis.

Seven open Axies have proven acquisition basis in total; one of them is evolved and therefore remains protected.

### Release-Economics Limitation

Historical production evidence includes:

```text
7 accounting-backed Axie burns
2 legacy marketplace release records
recorded release material quantities for only 2 releases
```

Examples of recorded historical material recovery include:

```text
Axie #12147655
3 Beast Mementos
2 Aquatic Mementos
5 total

Axie #2788135
18 Bug Mementos
18 Plant Mementos
38 Aquatic Mementos
74 total
```

Production data does not yet contain a defensible Memento / material market-value model.

Therefore V0.10 intentionally leaves:

```text
release_expected_recovery_weth = unavailable
release_expected_pl_weth       = unavailable
```

No synthetic expected material value is inserted.

Historical `ascendLevel` transactions were found shortly before several releases, but the transaction rows do not contain a reliable Axie ID relationship. They are therefore not automatically assigned to individual Axie release economics.

### Capital Utilization

Because only 7 of 136 open positions have proven acquisition basis, V0.10 labels its capital analytics:

```text
PARTIAL_COVERAGE
```

Final fixed-capital checkpoint:

```text
Open positions                           136
Open positions with proven cost            7
Cost-basis coverage                  5.1471%

Proven open capital             0.0037736775 WETH
Protected-attribute capital     0.0008300000 WETH
Release-analysis-ready capital  0.0029436775 WETH

Protected capital share                21.9945%
Release-ready capital share            78.0055%
```

Capital-days exposure and capital-weighted average holding age are dynamic values because open positions continue aging.

Do not interpret `0.0037736775 WETH` as the cost of the full 136-Axie owned inventory. It represents only the seven open positions with proven acquisition basis.

### Marketplace Strategy Layer

V0.10 deliberately uses rule-based strategy states rather than an artificial 0-100 numeric score.

Final production strategy states:

```text
STRATEGY_HOLD_PROTECTED                 65
STRATEGY_HOLD_INSUFFICIENT_DATA         65
STRATEGY_REVIEW_EXIT_OPTIONS             6
STRATEGY_NOT_APPLICABLE                 35
```

Strategy actions:

```text
HOLD                                    130
REVIEW                                    6
NONE                                     35
```

`STRATEGY_REVIEW_EXIT_OPTIONS` means the Axie has sufficient proven acquisition basis and release-analysis inputs to justify comparing exit alternatives.

It does not mean SELL or RELEASE.

V0.10 safety guardrail:

```text
Automatic SELL decisions                 0
Automatic RELEASE decisions              0
```

The six exit-review positions require additional evidence before AxieOS can select an exit path.

In particular:

```text
resale decision
requires live / user-supplied market price

release decision
requires defensible release-recovery valuation
```

### V0.10 Production Validation

Final production validation on September 1, 2026:

```text
Python compile check                   PASS
SQL write-safety scan                  PASS
Canonical inventory                    171
Unique Axies                           171
Inventory validator                   PASS
Inventory errors                         0
Production sign-off                   PASS
Sign-off errors                           0
```

Cross-version regression against critical V0.9 components:

```text
Owned Axie candidates                  PASS
Recommendation Axie candidates         PASS
Recommendation vs actual               PASS

Overall                                PASS
```

This confirms that the V0.10 marketplace implementation did not break the critical V0.9 owned-Axie / Bounty Optimizer candidate and recommendation pipeline.

### V0.10 Engineering Status

Core V0.10 engineering tasks:

```text
110  Inventory definition                         COMPLETE
111  Canonical inventory model                    COMPLETE
112  Acquisition cost + ownership state           COMPLETE
113  Listing / sale status                        COMPLETE
114  Realized / unrealized metrics                COMPLETE
115  Holding-period analytics                     COMPLETE
116  Resale / break-even analytics                COMPLETE
117  Release-candidate economics                  COMPLETE
118  Capital-utilization analytics                COMPLETE
119  Marketplace strategy scoring                 COMPLETE
120  Integration / production validation          COMPLETE
```

Remaining V0.10 closeout:

```text
121  LLM_Project_Context.md update
122  CHANGELOG.md update
123  Engineering Journal completion record
```

Do not commit the V0.10 implementation until Tasks 121-123 are complete.

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
