# AxieOS — LLM Project Context

Last updated: **2026-08-08**

---

## 1. Project Overview

**AxieOS** is an AI-assisted decision-support and analytics system for the Axie Infinity / GameFi ecosystem.

The project is intended to turn blockchain history, gameplay activity, marketplace transactions, staking activity, Terrarium data, and Bounty Board decisions into structured data that can later support:

- portfolio analytics
- wallet analytics
- profitability analysis
- Bounty Board optimization
- Terrarium optimization
- staking analysis
- marketplace ROI tracking
- NFT / Axie inventory analysis
- explainable recommendations
- future machine-learning models

The project should prioritize reliable data and analytics before introducing AI or machine learning.

---

## 2. Core Design Principles

AxieOS follows these principles:

1. **Data before AI**
2. **Measure before optimize**
3. **Reusable tools**
4. **Explain recommendations**
5. **Validate using real player data**

The system should avoid making recommendations based only on assumptions when historical data can be collected and measured.

---

## 3. Development Environment

Primary development environment:

- Windows
- Visual Studio Code
- Python
- SQLite
- Git
- GitHub
- GitHub Desktop

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

Blockchain data is stored under:

```text
data/blockchain/
```

---

## 4. Blockchain Data Layer

### Canonical SQLite Database

The primary populated AxieOS database is:

```text
data/blockchain/database/axieos.db
```

Current database size after initial import:

```text
40,960 bytes
```

### Current Imported Dataset

The current legacy blockchain dataset contains:

- **37 blockchain transactions**
- Date range: **2021-06-29 to 2021-12-15**
- **10 unique wallet / contract addresses**

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

when executed from the `scripts` directory convention currently used by the project.

The goal is to prevent individual scripts from defining inconsistent database paths.

---

## 7. Blockchain Import Pipeline

### create_database_schema.py

Location:

```text
scripts/create_database_schema.py
```

Purpose:

- creates the SQLite schema
- creates the `blockchain_transactions` table
- prepares the canonical blockchain database

---

### import_blockchain_csv.py

Location:

```text
scripts/import_blockchain_csv.py
```

Current capabilities include:

- CSV import
- header normalization
- idempotent imports
- SHA-256 row hashing
- duplicate-row prevention
- consistent database insertion

Each imported source row receives a deterministic hash stored in:

```text
source_row_hash
```

This allows repeated imports without duplicating existing blockchain records.

---

### verify_dataset_equivalence.py

Location:

```text
scripts/verify_dataset_equivalence.py
```

Purpose:

- verify equivalent blockchain datasets
- support migration and import validation

---

### inspect_database.py

Location:

```text
scripts/inspect_database.py
```

Purpose:

- inspect SQLite database contents
- verify imported rows and schema

---

### validate_import.py

Location:

```text
scripts/validate_import.py
```

Purpose:

- validate imported blockchain data
- compare database state with expected source data

---

## 8. Wallet Analytics

### wallet_summary.py v1.0

Location:

```text
scripts/wallet_summary.py
```

Version 1.0 provides:

- total transaction count
- first transaction date
- latest transaction date
- unique wallet / contract address count
- transaction method counts
- token / collectible counts
- recorded RON network fees

Verified results:

```text
Total transactions: 37
Unique addresses: 10
```

Transaction methods:

| Method | Count |
|---|---:|
| transfer | 16 |
| checkpoint | 12 |
| swapExactTokensForTokens | 4 |
| safeTransferFrom | 3 |
| approve | 1 |
| 0xbec24050 | 1 |

Source-data investigation confirmed that all 37 rows contain:

```text
TxnFee(RON) = 0.0
```

Therefore the zero network-fee result produced by the analytics scripts is consistent with the source dataset.

---

## 9. Transaction Analytics

### transaction_summary.py v1.0

Location:

```text
scripts/transaction_summary.py
```

Version 1.0 provides:

- transaction status summary
- transaction method summary
- monthly transaction activity
- wallet direction analysis
- latest five transactions
- duplicate transaction hash detection

The script has been tested against the current 37-row blockchain dataset.

---

## 10. Token Analytics

### token_summary.py v1.0

Location:

```text
scripts/token_summary.py
```

Completed and committed on **2026-08-08**.

The report calculates, per token or collectible:

- total transaction count
- incoming transaction count
- outgoing transaction count
- zero-movement transaction count
- total amount received
- total amount sent
- net token movement

Python `Decimal` is used instead of floating-point arithmetic for safer token-value calculations.

### Validated Token Results

| Token / Collectible | Transactions |
|---|---:|
| Axie | 3 |
| RON | 1 |
| Ronin Wrapped Ether | 3 |
| Smooth Love Potion | 30 |
| **Total** | **37** |

### Axie

```text
Transactions: 3
Incoming transactions: 3
Outgoing transactions: 0
Zero-movement transactions: 0
Total received: 3
Total sent: 0
Net movement: 3
```

### RON

```text
Transactions: 1
Incoming transactions: 0
Outgoing transactions: 0
Zero-movement transactions: 1
Total received: 0
Total sent: 0
Net movement: 0
```

The RON transaction is an:

```text
approve
```

transaction with no token movement.

### Ronin Wrapped Ether

```text
Transactions: 3
Incoming transactions: 3
Outgoing transactions: 0
Zero-movement transactions: 0
Total received: 0.0260107944
Total sent: 0
Net movement: 0.0260107944
```

### Smooth Love Potion

```text
Transactions: 30
Incoming transactions: 14
Outgoing transactions: 15
Zero-movement transactions: 1
Total received: 21866
Total sent: 21866
Net movement: 0
```

The zero-movement SLP transaction is a:

```text
checkpoint
```

transaction.

All token transaction counts reconcile to the full:

```text
37 transactions
```

---

## 11. Current Analytics Development Status

### Completed

- [x] Blockchain dataset preparation
- [x] Database schema
- [x] CSV blockchain importer
- [x] Idempotent import logic
- [x] SHA-256 row hashing
- [x] Import validation
- [x] Database inspection utility
- [x] Shared database connection module
- [x] `wallet_summary.py` v1.0
- [x] `transaction_summary.py` v1.0
- [x] `token_summary.py` v1.0
- [x] Database path cleanup
- [x] Remove accidental empty `data/axieos.db`

---

## 12. Next Development Priorities

The next phase moves from basic blockchain analytics toward structured gameplay and economic analytics.

Priority order:

1. **Design the gameplay data model**
2. Convert Bounty Board daily logs into structured data
3. Add Terrarium activity and reward tracking
4. Add marketplace purchase / listing / sale tracking
5. Add consumable inventory tracking
6. Add staking and reward tracking
7. Build Bounty Board reroll analytics
8. Build profitability calculations
9. Build recommendation rules
10. Consider machine learning only after enough structured gameplay data exists

---

## 13. Gameplay Data Model — Planned Scope

The future gameplay database should be able to represent daily Axie activities including:

### Daily Session

Possible fields:

```text
date
player_id
shrine_streak
starting_fortune_slips
claimed_fortune_slips
ending_fortune_slips
notes
```

---

### Bounty Board

Each Bounty Board task should eventually track:

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
time_required
notes
```

This will allow analysis such as:

- BP per Fortune Slip
- reroll success rate
- average value of each task category
- task completion cost
- task combinations
- expected task profitability

---

## 14. Bounty Board Optimization Goals

Future AxieOS logic should help answer questions such as:

- Should this task be completed or rerolled?
- How many Fortune Slips should be spent rerolling?
- Which tasks can be completed together?
- What is the cheapest combination of actions?
- Should a marketplace item be purchased and relisted?
- What is the expected recoverable capital?
- How much gameplay time is required?
- Is a theoretically good task realistically completable today?

An important future variable is:

```text
available_play_time
```

A task worth 100 BP may be inferior to a lower-cost reroll if the player has no time to complete the original task.

---

## 15. Marketplace Analytics — Planned Scope

Marketplace records should eventually track:

```text
asset_id
asset_type
class
breed_count
level
purchase_date
purchase_price
purchase_currency
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

This is important because many Bounty Board purchases can be relisted and capital may be recovered.

AxieOS should distinguish between:

```text
Bounty reward
+
Marketplace result
-
Fees
-
Consumable cost
-
Opportunity cost
=
True economic result
```

---

## 16. Consumable Inventory — Planned Scope

Track inventory such as:

```text
Regular CocoChoco
Premium CocoChoco
Lucky Pouches
SLP
RON
bAXS
AXS
```

Inventory changes should ideally be event-based:

```text
purchase
sale
feed
pouch reward
craft
release
stake
unstake
claim
swap
```

This will eventually eliminate manual inventory reconciliation.

---

## 17. Terrarium Analytics — Planned Scope

Terrarium data currently being recorded manually includes:

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

For each Savannah plot:

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

Future records should include:

```text
buff_activation_time
buff_duration
buff_expiry_time
fortune_slip_cost
unbuffed_hours
buff_active_at_snapshot
```

This is important because delayed buff activation can distort rank and reward comparisons.

---

## 18. Terrarium Buff Strategy

Current daily buff cost:

```text
Forest:       8 Fortune Slips
Savannah #1:  3 Fortune Slips
Savannah #2:  3 Fortune Slips
Total:       14 Fortune Slips / day
```

Buff duration is stackable.

A future operational strategy being evaluated is adding approximately **7 days of buff duration at once** instead of manually renewing every day.

Advantages may include:

- less repetitive work
- lower risk of forgotten activation
- fewer unbuffed hours
- cleaner analytics data
- easier weekly scheduling

The likely weekly anchor being considered is:

```text
Monday
```

---

## 19. Reward and Staking Analytics — Planned Scope

AxieOS should eventually track:

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
```

Relevant reward sources include:

```text
Bounty Board
Terrariums
AXS staking
bAXS staking
```

The objective is to measure:

- reward accumulation
- idle capital
- claiming frequency
- compounding frequency
- staking yield
- opportunity cost

---

## 20. Current Player Data Collection Phase

Detailed gameplay logs are currently being collected during **August 2026**.

The purpose of the daily logs is to create a reliable baseline dataset before gameplay decisions are automated.

The logs contain examples of:

- initial Bounty Boards
- rerolls
- Fortune Slip consumption
- task combinations
- marketplace purchases
- marketplace sales
- consumable usage
- Axie evolution
- Axie ascension
- Axie release
- staking
- reward claims
- Terrarium snapshots
- Terrarium buff timing

The detailed manual logging phase is intended to become less necessary once AxieOS can store and summarize these activities automatically.

---

## 21. Future AI / ML Direction

Machine learning is **not the immediate priority**.

The expected progression is:

```text
Raw Data
→ Structured Database
→ Descriptive Analytics
→ Rule-Based Recommendations
→ Statistical Models
→ Machine Learning
→ Explainable AI
```

Potential future models could include:

- Bounty task expected-value model
- reroll recommendation model
- marketplace sale probability model
- Axie holding-period model
- Terrarium reward forecasting
- player strategy simulation
- NFT ROI estimation

Explainability should remain important.

Possible future use:

```text
SHAP
```

for explaining recommendation or prediction drivers.

---

## 22. Documentation

Important project documentation includes:

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

Architecture and specification documents also exist under:

```text
docs/Architecture/
docs/Specifications/
```

`CHANGELOG.md` was previously empty and received its first formal development entry on **2026-08-08**.

---

## 23. Git Workflow

The repository is maintained using GitHub and GitHub Desktop.

Typical workflow:

```text
Edit
→ Test
→ Validate
→ Commit
→ Push
```

Analytics scripts should not be committed until their outputs have been verified against the source data.

Recent completed commit:

```text
Add token summary analytics report
```

---

## 24. Current Project Position

AxieOS has completed its first basic blockchain analytics layer.

Current state:

```text
Blockchain Import             ✅
Database Schema               ✅
Import Validation             ✅
Shared Database Connection    ✅
Wallet Analytics              ✅
Transaction Analytics         ✅
Token Analytics               ✅
Gameplay Data Model           ⏭️ NEXT
Gameplay Data Import          Pending
Bounty Optimization           Pending
Terrarium Analytics           Pending
Marketplace Analytics         Pending
Staking Analytics             Pending
AI Recommendations            Future
Machine Learning              Future
```

The immediate next engineering task is:

```text
Design the AxieOS gameplay data model.
```

This model will convert the manually collected August gameplay logs into structured, queryable data that can later power the Bounty Board, Terrarium, marketplace, staking, and strategy-analysis modules.