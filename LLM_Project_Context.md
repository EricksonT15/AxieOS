# AxieOS — LLM Project Context

Last updated: **2026-10-26**

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

1. Complete V0.12 Staking & Reward Analytics release documentation, final validation, commit, and push.
2. Begin V0.13 Inventory Optimization & ForRel Farming Analytics planning after V0.12 release.
3. Preserve canonical blockchain, marketplace, gameplay, staking, and Terrarium evidence.
4. Continue reconciling acquisition history, cost basis, and capital recovery without double-counting internal transfers.
5. Preserve original Ronin data and distinguish user-owned wallets from external counterparties.
6. Keep operational recommendations separate from accounting evidence and realized financial outcomes.
7. Do not invent missing timestamps, transactions, balances, acquisition costs, listing status, or gameplay metrics.
8. Keep this project context synchronized with the engineering roadmap and validated release status.

### Current Development Checkpoint

AxieOS has completed and released **V0.11 — Terrarium Analytics**.

**V0.12 — Staking & Reward Analytics** has completed implementation and analytical regression validation. Documentation closeout, selective Git staging, commit, and push remain pending.

#### Engineering Release Status

```text
V0.1   Ronin API Sync                         COMPLETE
V0.2   Transaction Classification             COMPLETE
V0.3   Transaction Economics                  COMPLETE
V0.4   Historical + Incremental Sync          COMPLETE
V0.5   Asset & Wallet Intelligence            COMPLETE
V0.6   Automated Accounting Pipeline          COMPLETE
V0.7   Accounting Review & Reporting          COMPLETE
V0.8   Gameplay Data Model + Owned Axies      COMPLETE
V0.9   Bounty Optimizer Integration           COMPLETE
V0.10  Marketplace Strategy Analytics        COMPLETE
V0.11  Terrarium Analytics                    RELEASED
V0.12  Staking & Reward Analytics             VALIDATED / RELEASE PENDING
V0.13  Inventory Optimization & ForRel        PLANNED
V0.14  Unified Finance                        PLANNED
V0.15  Dashboards                             PLANNED
```

#### Historical Database Reference

Previously recorded production foundation:

```text
blockchain_transactions              565 rows
blockchain_accounting_records        405 rows
gameplay_owned_axies                 137 rows
canonical marketplace inventory      171 Axies
```

These figures are historical engineering checkpoints, not verified current database totals. They must be refreshed before use in current inventory, accounting, or wallet reports.

The latest independently audited blockchain/accounting timestamps during V0.12 development were:

```text
blockchain_transactions         2026-08-22 11:10:29
blockchain_accounting_records   2026-08-22 11:10:29
staking_reward_events           2026-08-14 11:53:17
```

The normalized V0.12 staking reward data currently extends through August 19, 2026. The reports are historical rather than live.

#### Upcoming Inventory Optimization

V0.13 planning baseline as reported October 26, 2026:

```text
Axies not currently listed for sale       132
Terrarium operating requirement           120
Potential flexible inventory               12
```

These figures require database and current-listing reconciliation. The potential 12-Axie flexibility is not an automatic sale, release, or liquidation target.

V0.13 begins with Task 135A: feasibility assessment, schema and data-quality audit, database coverage review, and a phased implementation plan before coding.

V0.10 remains the validated canonical marketplace-strategy layer.

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

Marketplace strategy remains advisory:

```text
STRATEGY_HOLD_PROTECTED                 65
STRATEGY_HOLD_INSUFFICIENT_DATA         65
STRATEGY_REVIEW_EXIT_OPTIONS             6
STRATEGY_NOT_APPLICABLE                 35

Automatic SELL decisions                 0
Automatic RELEASE decisions              0
```

V0.11 established the Terrarium evidence, analytics, projection, and ROI layer.

Canonical Terrarium production coverage:

```text
Terrarium snapshots                      17
Plot snapshot rows                       51
Group-ranking rows                       34
```

Partial historical evidence:

```text
Evidence observations                    13
Evidence plot rows                       29
Evidence ranking rows                    12
```

Evidence-aware analytical coverage:

```text
Total observations                       30
Represented calendar dates               18
Historical range             2026-08-07 → 2026-08-27
```

Observed cumulative bAXS increase:

```text
Forest #1                    +19.6300 bAXS
Savannah #1                   +1.6200 bAXS
Savannah #2                   +1.9800 bAXS
Combined                     +23.2300 bAXS
```

Observed endpoint calendar-date span:

```text
20 days
```

Combined nominal accumulation pace:

```text
1.1615 bAXS / calendar day
```

This is a **calendar-date-span average**, not a precise normalized 24-hour yield.

V0.11 projection sensitivity assumptions are:

```text
Conservative          75% of observed pace
Base                 100% of observed pace
Upside               125% of observed pace
```

These are sensitivity scenarios, not probability forecasts.

Forest ROI reference:

```text
Coordinates                      (-123, 9)
Purchase date                    2025-11-18
Purchase price                   0.06841 ETH
Historical RON reference         871.81 RON
bAXS → AXS conversion            70%
Conversion haircut               30%
```

The historical `871.81` reference is **RON, not USD**.

AXS market price is not hard-coded into Terrarium history. `scripts/terrarium_roi.py` requires the current AXS price in RON as a runtime assumption.

Primary V0.11 scripts:

```text
scripts/add_terrarium_evidence.py
scripts/terrarium_summary.py
scripts/terrarium_projection.py
scripts/terrarium_roi.py
```

Historical evidence safety rules established in V0.11 include:

```text
unknown buff state                    -> NULL
unknown estimated_unbuffed_hours      -> NULL
missing partial-observation metrics   -> NULL
legacy historical zero values         -> preserved, not reinterpreted
```

V0.11 does not infer exact historical timestamps, buff states, unbuffed hours, or missing Terrarium metrics from neighboring observations.

### Current Release Closeout Status — October 26, 2026

V0.11 — Terrarium Analytics was committed and pushed successfully.

V0.12 — Staking & Reward Analytics has completed implementation and analytical validation.

Current engineering progress:

- Task 132 — Staking and reward foundation audit: COMPLETE
- Task 133 — Normalized staking event resolver and source attribution: COMPLETE
- Task 134A — Staking summary: COMPLETE
- Task 134B — Historical reward reporting and aggregation regression: COMPLETE
- Task 134C1 — Repository and compilation validation: COMPLETE
- Task 134C2 — Documentation closeout: IN PROGRESS
- Task 134C3 — Final regression and selective staging: PENDING
- Task 134C4 — Commit and push: PENDING

V0.12 reports 34 normalized staking events, including 18 reward events. Historical APR remains unavailable without verified staking-principal history.

The next planned engineering release is V0.13 — Inventory Optimization & ForRel Farming Analytics, beginning with Task 135A.

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

### Owned-Axie Inventory Foundation

The owned-Axie inventory and qualification layer was completed in V0.8 and is already integrated into the V0.9 Bounty Optimizer.

Current production checkpoint:

```text
Owned Axies                         136
Gameplay metadata                   136 / 136
Named parts                         816 / 816
Collectibles                        16
Evolved Axies                       65
Exact ownership provenance          124
Legacy-history unresolved           12
```

Canonical Axie identity uses:

```text
asset_id
```

Owned-Axie qualification supports:

```text
class
level
breed_count
collectible status / collection
evolved status
required parts
minimum ownership days
```

Qualification results use:

```text
QUALIFIED
DISQUALIFIED
UNKNOWN
```

`UNKNOWN` is retained when source evidence is insufficient for an exact determination.

The Bounty Optimizer should use this existing inventory before recommending that another Axie be purchased.

Typical questions include:

- Do I already own an Axie that satisfies the requirement?
- Which exact Axie IDs qualify?
- Can one Axie satisfy multiple simultaneous tasks?
- Is a qualifying Axie collectible or evolved and therefore economically protected?
- Is ownership history sufficient for a minimum-holding requirement?
- Would using or releasing an owned Axie create a larger economic cost than another execution path?

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

V0.11 established structured canonical and evidence-aware Terrarium analytics.

### Canonical Architecture

```text
gameplay_daily_sessions
        ↓
terrarium_snapshots
        ↓
terrarium_plot_snapshots
        ↓
terrarium_group_rankings
```

Canonical production coverage:

```text
Terrarium snapshots                      17
Plot snapshot rows                       51
Group-ranking rows                       34
```

### Historical Evidence Layer

Incomplete historical observations are preserved separately through:

```text
terrarium_snapshot_evidence
terrarium_plot_evidence
terrarium_group_ranking_evidence
```

Current evidence coverage:

```text
Partial evidence observations             13
Evidence plot rows                        29
Evidence ranking rows                     12

Evidence-aware observations               30
Represented calendar dates                18
Historical range              2026-08-07 → 2026-08-27
```

Partial evidence retains only metrics supported by the source.

Missing metrics remain:

```text
NULL
```

AxieOS does not fill missing Terrarium observations from neighboring rows.

### Current Metrics

Terrarium analytics can use observed:

```text
Global Lunium
Claimable bAXS
Plot Flame
Next Distribution
Total acquired bAXS
Group rank
Global group Flame
```

Evidence-aware cumulative increase across the available Aug 7 → Aug 27 endpoint period:

```text
Forest #1                    +19.6300 bAXS
Savannah #1                   +1.6200 bAXS
Savannah #2                   +1.9800 bAXS
Combined                     +23.2300 bAXS
```

Calendar-date span:

```text
20 days
```

Combined nominal pace:

```text
1.1615 bAXS / calendar day
```

This is a calendar-date-span average and is not treated as precise normalized 24-hour yield.

### Buff and Timing Safety

Future unknown buff state stores:

```text
buff_active = NULL
```

Future omitted:

```text
estimated_unbuffed_hours
```

also stores:

```text
NULL
```

Existing legacy zero values are preserved as historical records but are not interpreted as independently observed zero unbuffed hours.

Approximate historical times remain descriptive source evidence rather than being converted into invented exact timestamps.

### Projection and ROI

Primary scripts:

```text
scripts/terrarium_summary.py
scripts/add_terrarium_evidence.py
scripts/terrarium_projection.py
scripts/terrarium_roi.py
```

Projection sensitivity scenarios are:

```text
Conservative          75% of observed pace
Base                 100% of observed pace
Upside               125% of observed pace
```

These are assumptions, not probability forecasts.

Forest financial reference:

```text
Coordinates                      (-123, 9)
Purchase date                    2025-11-18
Purchase price                   0.06841 ETH
Historical RON reference         871.81 RON
bAXS → AXS conversion            70%
Conversion haircut               30%
```

AXS market price is supplied at runtime rather than stored as a fixed historical Terrarium value.

Raw operational Terrarium observations may originate in:

```text
04 — AxieOS Wallet, Staking & Terrariums
```

Canonical and engineering records belong in the structured data layer and:

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

### V0.12 Implementation Status

V0.12 provides a validated read-only analytics layer for historical AXS and bAXS staking activity.

Primary scripts:

```text
scripts/staking_event_resolver.py
scripts/staking_summary.py
scripts/reward_history.py
```

### Data Architecture

V0.12 reuses existing evidence rather than introducing a separate authoritative staking transaction ledger.

```text
blockchain_transactions
    |
    +-- transaction hashes
    +-- blockchain methods
    +-- transfer directions and addresses

blockchain_accounting_records
    |
    +-- exact token quantities
    +-- accounting classifications
    +-- asset and direction evidence

ronin_wallet_registry
    |
    +-- USER_OWNED wallet identification
    +-- STAKING contract-role evidence

staking_reward_events
    |
    +-- manual operational records
    +-- historical source attribution evidence

            |
            v

staking_event_resolver.py
            |
            +-- event type
            +-- token
            +-- exact quantity
            +-- economic source
            +-- confidence
            +-- evidence provenance

            |
            +--> staking_summary.py
            |
            +--> reward_history.py
```

No V0.12 production schema migration was required.

### Event Resolution

Recognized event types:

```text
CLAIM
STAKE
UNSTAKE
RESTAKE_REWARD
UNRESOLVED
```

Resolution precedence:

1. Recognized explicit blockchain method: `HIGH / EXPLICIT_METHOD`.
2. Conservative token-flow pattern using wallet-registry evidence: `MEDIUM / FLOW_PATTERN`.
3. Insufficient evidence: `UNRESOLVED`.

Transactions with multiple blockchain transfer legs are not automatically counted as multiple economic events.

`TOKEN_BURN` accounting events remain outside the staking/reward candidate universe.

### Reward-Source Attribution

Known sources:

```text
BOUNTY
TERRARIUMS
AXS_STAKING
BAXS_STAKING
```

Bounty and Terrarium reward-source assignments are supported by known contract addresses and independently corroborated historical claims.

AXS staking uses generic staking-contract role evidence where a more specific economic source is not proven.

The general `ronin_wallet_registry` remains authoritative for wallet ownership and broad contract roles. Its automatically discovered contract labels must not be manually changed for reward attribution because subsequent discovery can overwrite those labels.

### Validated Normalized Activity

```text
Candidate accounting events             34
Explicit-method HIGH                    12
Flow-pattern MEDIUM                     22
Unresolved                               0
Multi-leg transaction hashes             4

CLAIM                                   14
RESTAKE_REWARD                           4
STAKE                                    6
UNSTAKE                                 10
```

### Validated Historical Rewards

Reward events: **18**, including 6 HIGH-confidence and 12 MEDIUM-confidence events.

```text
Bounty Board           60.310335038216979400 bAXS
Terrariums             42.624047319087398186 bAXS
Total bAXS            102.934382357304377586 bAXS

AXS claims              0.646876807361839655 AXS
AXS immediate restakes  0.597635044539543860 AXS
Total AXS rewards       1.244511851901383515 AXS
```

Reward coverage: July 20 through August 19, 2026, using stored database timestamps.

### Available Reports

`staking_summary.py` provides event counts, staking flows, reward totals, source attribution, and evidence-quality summaries.

`reward_history.py` supports:

```text
Daily aggregation
ISO-weekly aggregation
Monthly aggregation
Transaction-level details
```

All three calendar aggregations reconcile to the same reward totals.

Immediate reward restakes are counted once for reward recognition, not as separate CLAIM and STAKE reward events.

All token aggregation uses `Decimal` arithmetic.

### APR and Balance Limitations

The current database does not contain a validated historical staked-principal snapshot series.

Therefore:

- Reliable historical APR is not available.
- Staking flows are not equivalent to opening or closing staking balances.
- No annualized yield is reported without defensible principal and elapsed-time evidence.
- AXS and bAXS are reported separately without an assumed exchange rate.
- Missing dates are not interpreted as zero rewards.
- Older method-null transaction interpretations retain MEDIUM confidence.
- Reports are historical, not live balances or lifetime earnings.
- Stored timestamps are used without timezone normalization.

Historical principal reconstruction, APR calculations, claiming-frequency analysis, and idle-capital optimization remain potential future enhancements.

### Operational Ownership

Operational staking and reward claims belong in:

```text
04 — AxieOS Wallet, Staking & Terrariums
```

Engineering implementation and canonical analytics belong in the AxieOS development and data workstreams.

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
V0.1   Ronin API Sync                         COMPLETE
V0.2   Transaction Classification             COMPLETE
V0.3   Transaction Economics                  COMPLETE
V0.4   Historical + Incremental Sync          COMPLETE
V0.5   Asset & Wallet Intelligence            COMPLETE
V0.6   Automated Accounting Pipeline          COMPLETE
V0.7   Accounting Review & Reporting          COMPLETE
V0.8   Gameplay Data Model + Owned Axies      COMPLETE
V0.9   Bounty Optimizer Integration           COMPLETE
V0.10  Marketplace Strategy Analytics        COMPLETE
V0.11  Terrarium Analytics                   CORE ENGINEERING COMPLETE
```

V0.10 implementation, production validation, documentation, commit, and push are complete.

V0.11 core engineering and production validation are complete.

### Release Status — October 26, 2026

V0.11 — Terrarium Analytics was completed, committed, and pushed to main. Task 131 is COMPLETE.

V0.12 — Staking & Reward Analytics has completed implementation and analytical validation.

Current development status:

```text
Task 132    Foundation audit                     COMPLETE
Task 133    Event resolver and source attribution COMPLETE
Task 134A   Staking summary                      COMPLETE
Task 134B   Historical reward analytics          COMPLETE
Task 134C1  Code and repository validation       COMPLETE
Task 134C2  Release documentation                IN PROGRESS
Task 134C3  Final regression / selective staging PENDING
Task 134C4  Commit and push                      PENDING
```

The next planned engineering release is V0.13 — Inventory Optimization & ForRel Farming Analytics, beginning with Task 135A.

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




### Immediate Engineering Sequence — October 26, 2026

```text
Complete V0.12 documentation
    ↓
Run final V0.12 regression
    ↓
Review intended Git changes
    ↓
Exclude database backups and unrelated capital-recovery files
    ↓
Selectively stage V0.12 scripts and documentation
    ↓
Commit V0.12
    ↓
Push to main
    ↓
Begin V0.13 Task 135A feasibility audit
```

V0.11 Task 131 is already complete and must not be repeated.


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

V0.10 documentation closeout:

```text
121  LLM_Project_Context.md update                COMPLETE
122  CHANGELOG.md update                          COMPLETE
123  Engineering Journal completion record        COMPLETE
```

V0.10 was subsequently committed and pushed successfully.

Following V0.10, V0.11 Terrarium Analytics was completed, committed, and pushed. As of October 26, 2026, V0.12 Staking & Reward Analytics is validated and awaiting release closeout.

---

## 29B. V0.11 Terrarium Analytics — Released

V0.11 Terrarium Analytics was completed, validated, committed, and pushed to main.

Final release status:

```text
Core engineering             COMPLETE
Production validation        PASS
Documentation closeout       COMPLETE
Final regression             PASS
Commit                       COMPLETE
Push to main                 COMPLETE
Task 131                     COMPLETE
```

V0.11 remains the canonical historical Terrarium analytics, projection, and ROI foundation.

V0.12 — Staking & Reward Analytics is the current validated release awaiting final documentation and Git closeout.

---

### Nightmare Historical Acquisition-Cost Audit

Before V0.11 Terrarium implementation, a follow-up historical acquisition-cost audit was completed for the 11 currently owned Nightmare Axies.

Primary script:

```text
python/nightmare_cost_check.py
```

Final local evidence result:

```text
Nightmare Axies checked                 11
Acquisition costs recovered              0
Cost evidence requiring review           0
Cost not recovered                      10
Ownership history unresolved             1
```

Ten Nightmare Axies have ownership-start evidence but no defensible acquisition cost in the current local AxieOS data.

Axie:

```text
#8724306
```

remains:

```text
HISTORY_UNRESOLVED
```

with neither a defensible acquisition cost nor ownership-start datetime in the current local evidence.

The audit checked:

```text
gameplay_owned_axies
blockchain_accounting_records
marketplace_events
blockchain_transactions
repository files
Git history
```

No defensible historical purchase price was recovered.

Do not infer acquisition cost from:

```text
ownership-start timestamps
Axie progression expenses
ascension / evolution spending
accessory purchases
unrelated marketplace activity
```

Further acquisition-cost recovery requires external historical Ronin / Sky Mavis transaction or marketplace evidence.

---

### V0.11 Objective

V0.11 builds an evidence-preserving Terrarium analytics layer capable of:

```text
historical observation recovery
canonical Terrarium analytics
evidence-aware analytics
cumulative bAXS measurement
competitive Flame / rank analysis
calendar-span projections
financial ROI scenarios
```

The implementation is intentionally conservative when historical source evidence is incomplete.

Missing values remain missing rather than being fabricated.

---

### Canonical Terrarium Architecture

The canonical Terrarium data flow is:

```text
gameplay_daily_sessions
        ↓
terrarium_snapshots
        ↓
terrarium_plot_snapshots
        ↓
terrarium_group_rankings
```

Canonical production coverage:

```text
Terrarium snapshots                      17
Plot snapshot rows                       51
Group-ranking rows                       34
```

Canonical historical range:

```text
2026-08-07 → 2026-08-26
```

---

### Historical Evidence Architecture

V0.11 added dedicated tables for incomplete historical observations:

```text
terrarium_snapshot_evidence
terrarium_plot_evidence
terrarium_group_ranking_evidence
```

Evidence completeness states support:

```text
COMPLETE
PARTIAL
UNRESOLVED
```

Partial observations retain only the metrics actually supported by source evidence.

Missing fields remain:

```text
NULL
```

Final evidence coverage:

```text
Partial evidence observations             13
Evidence plot rows                        29
Evidence ranking rows                     12
```

Evidence-aware analytical coverage:

```text
Total observations                        30
Represented calendar dates                18
Historical range             2026-08-07 → 2026-08-27
```

---

### Historical Evidence Safety

V0.11 does not invent missing:

```text
snapshot time
Flame
rank
global Flame
Next Distribution
total acquired bAXS
buff state
estimated unbuffed hours
```

from nearby observations.

Historical metric gaps remain explicit.

Approximate historical time descriptions remain descriptive evidence rather than being converted into invented exact timestamps.

---

### Buff-State Safety

Future unknown buff state stores:

```text
buff_active = NULL
```

rather than defaulting to an observed-looking value.

Existing historical buff values were preserved instead of rewritten without source evidence.

Historical buff state is not inferred solely from neighboring snapshots or from the July 24 Shrine Buff experiment.

---

### Unbuffed-Hours Safety

The previous schema default for:

```text
estimated_unbuffed_hours
```

was removed.

Future omission stores:

```text
NULL
```

instead of zero.

All 17 existing legacy values of:

```text
'0'
```

were preserved as historical records.

Those legacy zero values are not treated as independently observed zero-hour measurements.

---

### Primary V0.11 Scripts

```text
scripts/add_terrarium_evidence.py
scripts/terrarium_summary.py
scripts/terrarium_projection.py
scripts/terrarium_roi.py
```

Supporting ingestion/schema changes were made in:

```text
scripts/add_gameplay_day.py
scripts/add_terrarium_snapshot.py
scripts/create_gameplay_schema.py
```

---

### Terrarium Summary Analytics

Primary implementation:

```text
scripts/terrarium_summary.py
```

Canonical data remains the default reporting mode.

Evidence-aware analytics are enabled explicitly.

Implemented capabilities include:

```text
canonical validation
plot-level history
observation-to-observation changes
adjacent versus bridged metric changes
cumulative bAXS accumulation
accumulation composition
Flame history
competitive Flame share
rank history
Next Distribution composition
distribution-mix comparison
```

Evidence-aware calculations evaluate metrics independently.

A partial observation does not need to contain every Terrarium metric before the supported metrics can be used.

---

### Observed bAXS Accumulation

Evidence-aware cumulative endpoints produce:

```text
Forest #1                    +19.6300 bAXS
Savannah #1                   +1.6200 bAXS
Savannah #2                   +1.9800 bAXS
Combined                     +23.2300 bAXS
```

Observed endpoint period:

```text
2026-08-07 → 2026-08-27
```

Calendar-date difference:

```text
20 days
```

Combined nominal accumulation pace:

```text
1.1615 bAXS / calendar day
```

This value is explicitly a:

```text
calendar-date-span average
```

and not a precise normalized 24-hour yield.

---

### Yield and Projection Model

Primary implementation:

```text
scripts/terrarium_projection.py
```

Because exact historical observation timestamps are incomplete, the model does not calculate:

```text
exact hourly yield
precise timestamp-normalized daily yield
buff-adjusted yield
unbuffed yield
```

The projection model instead uses the first-to-latest observed calendar-date span.

Base combined pace:

```text
1.1615 bAXS / calendar day
```

Nominal continuation:

```text
7 days        8.1305 bAXS
30 days      34.8450 bAXS
365 days    423.9475 bAXS
```

Sensitivity assumptions:

```text
Conservative          75% of observed pace
Base                 100% of observed pace
Upside               125% of observed pace
```

These scenarios are modeling assumptions.

They are not confidence intervals or probability forecasts.

---

### Financial ROI Model

Primary implementation:

```text
scripts/terrarium_roi.py
```

Historical Terrarium accumulation is kept separate from financial assumptions.

Forest acquisition reference:

```text
Coordinates                      (-123, 9)
Purchase date                    2025-11-18
Purchase price                   0.06841 ETH
Historical RON reference         871.81 RON
```

The previously recorded interpretation:

```text
$871.81
```

is incorrect.

The supported historical reference is:

```text
871.81 RON
```

Current conversion assumption:

```text
bAXS → AXS                       70%
Conversion haircut               30%
```

AXS market price is not hard-coded.

The ROI script requires:

```text
--axs-price-ron
```

at runtime.

---

### ROI Scope

The V0.11 ROI model uses:

```text
combined bAXS accumulation from all owned Terrarium plots
```

to evaluate recovery of the Forest acquisition reference.

Current payback interpretation:

```text
full acquisition-cost payback from zero recovery
```

Prior realized Terrarium income is not deducted from the Forest acquisition reference.

Current ROI modeling excludes:

```text
gas
taxes
transaction fees
staking yield
future changes to Terrarium economics
future changes to bAXS conversion rules
```

These limitations remain explicit.

---

### Synthetic ROI Validation

A synthetic price of:

```text
10 RON / AXS
```

was used only for formula validation.

It is not a market-price fact.

Synthetic validation result:

```text
Effective value per bAXS                7 RON

AXS required for break-even       87.1810 AXS
Gross bAXS required              124.5443 bAXS

Conservative break-even          142.9695 days
Base break-even                  107.2271 days
Upside break-even                 85.7817 days
```

---

### V0.11 Production and Regression Validation

Validated V0.11 state:

```text
Canonical snapshots                      17
Canonical plot rows                      51
Canonical ranking rows                   34

Evidence observations                    13
Evidence plot rows                       29
Evidence ranking rows                    12

Evidence-aware observations              30
Represented calendar dates               18
```

Core validation:

```text
Canonical analytics                     PASS
Evidence-aware analytics                PASS
Historical evidence integrity           PASS
Metric-specific change analysis         PASS
Projection regression                   PASS
ROI formula validation                  PASS
ROI input guardrails                    PASS
Future NULL ingestion                   PASS
Foreign-key validation                  PASS
SQLite integrity                        PASS
Python compile regression               PASS
```

The disposable future-ingestion test confirmed:

```text
omitted buff state                 -> NULL
omitted unbuffed hours             -> NULL
production historical rows         -> unchanged
```

The production database remains local / untracked and must not be committed to Git.

---

### V0.11 Task Status

```text
124   Terrarium foundation audit                     COMPLETE
125   Canonical summary and validation               COMPLETE
126   Trend / delta / accumulation analytics         COMPLETE
127   Next Distribution analytics                    COMPLETE
128   Historical coverage + evidence layer           COMPLETE
129   Evidence-aware analytics                       COMPLETE
130A  Yield prerequisite audit                       COMPLETE
130B  NULL/default ingestion safety                  COMPLETE
130C  Projection + sensitivity scenarios             COMPLETE
130D  Financial ROI model + validation               COMPLETE
131   Release closeout / final regression / commit   COMPLETE
```

---

### V0.11 Release Closeout — Historical Record

V0.11 completed its release process, including:

- Documentation updates
- Final regression and validation
- Database integrity verification
- Historical evidence preservation
- Git review
- Commit and push to main

Task 131 is COMPLETE.

This section is retained as a historical engineering record. Its release procedures do not need to be repeated for V0.12.

Current engineering work continues under Task 134C — V0.12 release closeout.

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
