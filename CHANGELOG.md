## 2026-10-26 — V0.12 Staking & Reward Analytics

### Added

- Added `scripts/staking_event_resolver.py` for normalized AXS and bAXS staking events.
- Added `scripts/staking_summary.py` for staking activity, reward totals, and net staking-flow reporting.
- Added `scripts/reward_history.py` for daily, ISO-weekly, and monthly historical reward reporting.
- Added evidence-based identification of CLAIM, STAKE, UNSTAKE, and RESTAKE_REWARD events.
- Added reward-source attribution for Bounty Board, Terrariums, and AXS staking.
- Added explicit-method and inferred-flow confidence classification.
- Added multi-leg transaction handling to prevent reward double-counting.

### Architecture and Methodology

- Reused existing blockchain transactions, accounting records, and wallet-registry intelligence.
- Preserved the generic STAKING contract role in `ronin_wallet_registry`.
- Applied HIGH confidence to recognized explicit blockchain methods.
- Applied MEDIUM confidence to conservative transaction-flow inferences.
- Used `Decimal` arithmetic for token quantities and reward aggregation.
- Kept AXS and bAXS rewards separate without assuming a conversion rate.
- Counted immediate reward restaking as one economic operation.
- Preserved stored blockchain timestamps without timezone conversion.
- Implemented read-only reporting without modifying production records.

### Validated Historical Coverage

- Normalized staking events: **34**
- Explicit-method HIGH-confidence events: **12**
- Inferred MEDIUM-confidence events: **22**
- Unresolved events: **0**
- Multi-leg staking transaction hashes: **4**
- Reward events: **18**
- Reward events HIGH / MEDIUM: **6 / 12**
- Reward coverage: **July 20–August 19, 2026**

### Validated Reward Totals

- Bounty Board rewards: **60.310335038216979400 bAXS**
- Terrarium rewards: **42.624047319087398186 bAXS**
- Combined bAXS rewards: **102.934382357304377586 bAXS**
- Claimed AXS rewards: **0.646876807361839655 AXS**
- Immediately restaked AXS rewards: **0.597635044539543860 AXS**
- Combined AXS staking rewards: **1.244511851901383515 AXS**

### Validation

- Python compilation: PASS
- Normalized event classification: PASS
- Reward-source attribution: PASS
- Multi-leg transaction handling: PASS
- Staking summary reconciliation: PASS
- Daily reward reporting: PASS
- Weekly reward reconciliation: PASS
- Monthly reward reconciliation: PASS
- Repository whitespace check: PASS

### Known Limitations

- Imported blockchain and accounting records currently extend through August 22, 2026.
- Historical staking principal snapshots are not yet established.
- Historical APR calculations remain deferred until suitable principal and time-weighted balance evidence are available.
- Older transactions without explicit methods remain MEDIUM-confidence inferences.
- Reports do not represent live staking balances or lifetime rewards.
- Missing dates are not interpreted as zero rewards.
- Net staking flows are not equivalent to opening or closing staked balances.

### Release Status

Implementation and analytics validation completed. Final documentation review, selective Git staging, commit, and push pending.

---

## 2026-09-08 — V0.11 Terrarium Analytics

### Added

- Added `scripts/terrarium_summary.py` for canonical and evidence-aware Terrarium analytics.
- Added `scripts/add_terrarium_evidence.py` for preserving partial historical observations without inventing missing fields.
- Added dedicated Terrarium snapshot, plot, and ranking evidence tables.
- Added metric-aware adjacent-versus-bridged change analysis.
- Added cumulative bAXS composition, competitive Flame-share, and Next Distribution analytics.
- Added `scripts/terrarium_projection.py`.
- Added calendar-date-span accumulation projections.
- Added conservative / base / upside scenarios at 75%, 100%, and 125% of observed pace.
- Added `scripts/terrarium_roi.py`.
- Added required runtime `--axs-price-ron` input.
- Added ROI financial-input guardrails.

### Changed

- Changed unknown Terrarium buff state to remain `NULL`.
- Removed the false default from `estimated_unbuffed_hours`.
- Preserved all 17 historical legacy zero values without rewriting historical evidence.
- Changed partial-observation analytics to operate metric-by-metric.
- Changed yield terminology to **calendar-date-span average** where exact timestamps are unavailable.
- Separated historical accumulation from financial assumptions.
- Applied the corrected Forest acquisition reference of 871.81 RON.
- Applied the 70% bAXS → AXS conversion assumption with its 30% haircut explicit.

### Historical Coverage

```text
Canonical snapshots                        17
Canonical plot rows                        51
Canonical ranking rows                     34

Partial evidence observations              13
Evidence plot rows                         29
Evidence ranking rows                      12

Evidence-aware observations                30
Represented dates                          18
Historical range             2026-08-07 → 2026-08-27
```

### Accumulation Basis

```text
Forest observed increase             +19.6300 bAXS
Savannah #1 observed increase         +1.6200 bAXS
Savannah #2 observed increase         +1.9800 bAXS
Combined observed increase           +23.2300 bAXS

Calendar-date span                          20 days
Base nominal pace                      1.1615 bAXS/day
```

### Financial References

```text
Forest plot                      (-123, 9)
Forest purchase                  0.06841 ETH
Historical RON reference         871.81 RON
bAXS → AXS conversion            70%
Explicit haircut                 30%
```

AXS market price remains a runtime assumption rather than a fixed historical value.

### Validation

- Production Terrarium schema migration: PASS
- Historical rows preserved: PASS
- Foreign-key validation: PASS
- SQLite integrity validation: PASS
- Future NULL ingestion test: PASS
- Evidence-aware analytics regression: PASS
- Projection regression: PASS
- ROI formula validation: PASS
- ROI input guardrails: PASS
- Python compile regression: PASS

---

## 2026-09-01 — V0.10 Marketplace Strategy Analytics

### Added

- Added `scripts/inventory_report.py` as the canonical read-only marketplace inventory and strategy-analysis report.
- Added a canonical Axie inventory built from the union of:
  - `gameplay_owned_axies`
  - `marketplace_events`
  - `blockchain_accounting_records`
- Added canonical marketplace position states:
  - `OPEN_OWNED`
  - `CLOSED_SOLD`
  - `CLOSED_RELEASED`
- Added separate ownership-start and economic-acquisition models.
- Added acquisition evidence tracking for:
  - acquisition datetime
  - acquisition cost
  - acquisition transaction hash
  - source
  - quality state
- Added listing-status analysis that distinguishes historical listing evidence from confirmed live listings.
- Added sale-status analysis with accounting-confirmed and legacy unverified sale states.
- Added realized marketplace economics using exact accounting evidence where available.
- Added unrealized-economics placeholders that explicitly remain unavailable without a live marketplace-price source.
- Added canonical holding-period analytics for open, sold, and released Axies.
- Added resale break-even analysis using the historically validated 4.25% Axie marketplace fee assumption.
- Added release-candidate analysis using:
  - ownership state
  - acquisition basis
  - level
  - breed count
  - collectible status
  - evolved status
- Added capital-utilization analytics for open Axie positions with proven acquisition basis.
- Added rule-based marketplace strategy states:
  - `STRATEGY_HOLD_PROTECTED`
  - `STRATEGY_HOLD_INSUFFICIENT_DATA`
  - `STRATEGY_REVIEW_EXIT_OPTIONS`
  - `STRATEGY_NOT_APPLICABLE`
- Added explicit marketplace safety guardrails preventing automatic SELL or RELEASE decisions.
- Added V0.10 production validation and cross-version V0.9 regression checks.

### Changed

- Expanded marketplace analysis from isolated historical marketplace events into a canonical 171-Axie inventory covering current and historical ownership states.
- Separated ownership evidence from economic acquisition evidence so transfers and incomplete provenance are not automatically treated as purchases.
- Changed historical listing records so they no longer imply that an Axie is currently listed.
- Changed missing market-price behavior so current market value, unrealized P/L, and unrealized ROI remain unavailable instead of being estimated.
- Changed resale analysis to use an explicit 4.25% marketplace-fee assumption derived from historical accounting evidence.
- Changed release analysis so collectible or evolved Axies are protected from automatic release consideration.
- Changed strategy output from a proposed numeric score into explainable rule-based HOLD / REVIEW / NONE states.
- Preserved marketplace strategy as advisory decision support rather than automatic trade execution.

### Production Inventory

Final production inventory:

```text
Canonical inventory                    171
Unique Axies                           171

OPEN_OWNED                             136
CLOSED_SOLD                             27
CLOSED_RELEASED                          8
```

Source coverage:

```text
gameplay_owned_axies rows              137
marketplace distinct Axies              11
accounting distinct Axies               42
```

### Ownership and Acquisition

Final ownership-start coverage:

```text
Known ownership-start datetime          157
Ownership-start READY                   154
Ownership-start REVIEW                   17
```

Economic-acquisition coverage:

```text
Known economic acquisition cost          34
Known acquisition datetime               34
Known acquisition txhash                 27
```

Only 7 of 136 current open positions have proven acquisition cost suitable for READY capital and resale analytics.

### Realized and Unrealized Economics

Final realized-economics state:

```text
REALIZED_READY                           14
REALIZED_REVIEW                          11
REALIZED_UNAVAILABLE                      2
REALIZED_NOT_APPLICABLE                 144
```

Current unrealized economics remain unavailable for all open positions because no live Axie marketplace-price source is connected.

AxieOS does not fabricate:

```text
current_market_value
unrealized_pl
unrealized_roi
```

### Holding Analytics

Final holding-period state:

```text
HOLDING_READY                           153
HOLDING_REVIEW                            4
HOLDING_UNAVAILABLE                      14
```

Open-position holding periods continue to age dynamically using the current UTC report timestamp.

### Resale Break-Even

A production audit of 25 accounting-backed Axie sales confirmed:

```text
Observed marketplace fee rate: 4.2500%
Minimum observed rate:          4.2500%
Maximum observed rate:          4.2500%
```

Final resale-analysis state:

```text
RESALE_READY                              7
RESALE_UNAVAILABLE_NO_COST              129
RESALE_NOT_APPLICABLE                    35
```

Break-even currently includes acquisition basis and the assumed future marketplace fee.

Purchase gas and future sale gas are not converted into WETH because no timestamp-specific RON/WETH conversion model has been established.

### Release Analysis

Final release-analysis state:

```text
RELEASE_ANALYSIS_READY                    6
RELEASE_REVIEW_NO_COST_BASIS             65
RELEASE_REVIEW_PROTECTED_ATTRIBUTE       65
RELEASE_NOT_APPLICABLE                   35
```

Current owned-Axie protection coverage:

```text
Collectible Axies                        16
Evolved Axies                            65
Protected collectible/evolved set        65
```

Production release data does not yet contain a defensible Memento / release-material valuation model.

Therefore:

```text
release_expected_recovery_weth = unavailable
release_expected_pl_weth       = unavailable
```

No synthetic release recovery value is inserted.

### Capital Utilization

Final capital-coverage state:

```text
Coverage status                  PARTIAL_COVERAGE

Open positions                           136
Open positions with proven cost            7
Cost-basis coverage                  5.1471%

Proven open capital             0.0037736775 WETH
Protected-attribute capital     0.0008300000 WETH
Release-analysis-ready capital  0.0029436775 WETH
```

The proven open-capital value represents only the seven open Axies with defensible acquisition basis and must not be interpreted as the cost of the full owned inventory.

### Marketplace Strategy

Final strategy states:

```text
STRATEGY_HOLD_PROTECTED                 65
STRATEGY_HOLD_INSUFFICIENT_DATA         65
STRATEGY_REVIEW_EXIT_OPTIONS             6
STRATEGY_NOT_APPLICABLE                 35
```

Final strategy actions:

```text
HOLD                                    130
REVIEW                                    6
NONE                                     35
```

Safety guardrails:

```text
Automatic SELL decisions                  0
Automatic RELEASE decisions               0
```

The six `STRATEGY_REVIEW_EXIT_OPTIONS` positions require additional evidence before an exit decision can be made.

Resale decisions require a live or user-supplied market price.

Release decisions require a defensible release-recovery valuation model.

### Validated

- Passed Python compile validation.
- Confirmed `scripts/inventory_report.py` contains no SQL write statements.
- Reconciled all 171 canonical inventory rows to 171 unique Axie IDs.
- Validated all canonical position states.
- Validated ownership-start and economic-acquisition separation.
- Validated listing and sale states.
- Validated realized and unrealized-economics safeguards.
- Validated holding-period analytics.
- Validated resale break-even calculations.
- Validated release-candidate safeguards.
- Validated capital-utilization reconciliation.
- Validated marketplace strategy semantics.
- Confirmed no automatic SELL recommendations.
- Confirmed no automatic RELEASE recommendations.
- Passed critical V0.9 cross-version regressions:
  - owned-Axie candidates
  - recommendation Axie candidates
  - recommendation-vs-actual tracking

### Final Validation

```text
Python compile check                   PASS
SQL write-safety scan                  PASS

Canonical inventory                    171
Unique Axies                           171

Inventory validator                   PASS
Inventory errors                         0

Owned Axie candidates                  PASS
Recommendation Axie candidates         PASS
Recommendation vs actual               PASS

Production sign-off                   PASS
Sign-off errors                           0
```

---

## 2026-08-30 — V0.9 Bounty Optimizer Integration

### Added

- Added structured V0.9 Bounty requirement and task-resolution models.
- Connected Bounty requirements to the V0.8 owned-Axie qualification system.
- Added exact eligible Axie ID output for optimizer recommendations.
- Added parameterized Bounty resolution for class, collection, part, level, breed, evolved, and other Axie requirements.
- Added structured CocoChoco inventory state:
  - `on_hand`
  - `reserved`
  - `available`
- Added structured Fortune Slip state with reserve-aware projected spending.
- Added gameplay-database inventory support using verified snapshots plus later inventory events.
- Added explicit Bounty economics modeling for:
  - capital-required actions
  - inventory consumption
  - Fortune Slip / pouch activity
  - asset-destroying actions
  - resource spending
  - gameplay-time actions
- Added KEEP and COMBO economic evaluation with explicit cost profiles.
- Added recommendation-vs-actual tracking for:
  - KEEP
  - REROLL
  - COMBO
- Added planned-versus-actual tracking for:
  - BP
  - Fortune Slip spend
  - net WETH cost
  - recommendation-followed status
- Added historical Bounty task compatibility resolution for older manually logged wording.
- Added gameplay DB actual-outcome reconstruction for recorded Bounty sessions.
- Added optimizer recommendation persistence tables:
  - `bounty_optimizer_runs`
  - `bounty_optimizer_decisions`
- Added atomic optimizer-run persistence with rollback protection.
- Added reconciliation of initially `PENDING` recommendations with later gameplay outcomes.
- Added explicit live optimizer-run saving with duplicate and historical-attribution guardrails.
- Added `run_v09_integration_validation()` as the authoritative V0.9 integration validator.

### Changed

- Extended the Bounty Optimizer from manual task analysis into integrated gameplay decision support using:
  - owned-Axie metadata
  - exact qualification
  - inventory state
  - Fortune Slip state
  - economic inputs
  - historical gameplay evidence
- Added inventory provenance to optimizer execution plans.
- Preserved normal `python bounty_optimizer.py` execution as read-only with respect to optimizer recommendation history.
- Kept historical-only task identifiers outside the active `BOUNTY_TASK_CATALOG`.
- Changed missing economic evidence behavior so unknown cost is not treated as zero; applicable tasks may return `INPUT_REQUIRED`.
- Required explicit COMBO economic profiles instead of automatically summing individual task costs.
- Preserved unresolved non-final historical reroll rows as execution evidence without allowing unrelated unresolved rows to block session reconciliation.

### Validated

- Passed all 25 V0.9 test suites.
- Validated production owned-Axie qualification and optimizer integration.
- Validated structured inventory and Fortune Slip accounting.
- Validated KEEP and COMBO economic integration.
- Validated recommendation-vs-actual tracking.
- Validated gameplay DB actual-outcome reconstruction.
- Validated optimizer persistence and atomic rollback.
- Validated persisted-outcome reconciliation.
- Validated explicit-save duplicate protection.
- Validated historical live-attribution protection.
- Resolved all 72 production final-selected historical Bounty tasks:
  - 72 resolved
  - 0 unresolved
  - 100% resolution rate
- Confirmed current daily regression fixture remains:
  - `Plan Status: READY`
  - `Data Quality: REVIEW`
- Confirmed the existing `REVIEW` state is expected because the August 18 fixture contains 675 additional / unattributed BP.

### Data Integrity

- Historical gameplay outcomes are not treated as proof of historical AxieOS recommendations.
- Retroactive `LIVE_OPTIMIZER` recommendation history is blocked unless explicitly authorized.
- Exact duplicate optimizer plans are blocked from being persisted twice.
- Synthetic persistence tests use in-memory SQLite databases.
- Final production optimizer-history counts remained unchanged during V0.9 validation:
  - `bounty_optimizer_runs`: 0 → 0
  - `bounty_optimizer_decisions`: 0 → 0

### Final Validation

```text
V0.9 tests                     25 / 25 PASS
Historical task resolution            PASS
Current daily plan                    PASS
Production history safety             PASS

V0.9 Integration Validation           PASS
```

---


## 2026-08-08

### Added
- Added `scripts/token_summary.py` v1.0.
- Added per-token transaction analytics:
  - total transaction count
  - incoming transaction count
  - outgoing transaction count
  - zero-movement transaction count
  - total received
  - total sent
  - net token movement
- Added safe numeric handling using Python `Decimal`.
- Validated token summary against all 37 imported blockchain transactions.

### Validated
- Confirmed one zero-movement RON `approve` transaction.
- Confirmed one zero-movement Smooth Love Potion `checkpoint` transaction.
- Verified token transaction counts reconcile to the full 37-row blockchain dataset.

### Documentation
- Created `LLM_Project_Context.md` as the central project context file for AxieOS.
- Documented the current blockchain analytics architecture, completed scripts, validated results, and next development priorities.

### Maintenance
- Verified that `data/axieos.db` was an unused 0-byte database.
- Confirmed no project scripts depend on the unused database.
- Deleted `data/axieos.db`.
- Confirmed `data/blockchain/database/axieos.db` as the canonical AxieOS database.