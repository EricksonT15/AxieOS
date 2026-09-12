# AxieOS Engineering Journal

---

## Journal Entry 001

**Date**

2026-07-18

---

### Decision

The project was officially named **AxieOS**.

---

### Context

The original objective was to optimize the Axie Infinity Bounty Board.

During project planning, the scope expanded to include multiple interconnected systems within the Axie Infinity ecosystem.

Rather than optimizing a single feature, the project evolved into an AI-assisted decision support platform for GameFi.

---

### Why this decision was made

Many gameplay systems influence one another:

- Bounty Board
- Terrariums
- Staking
- Wallet Transactions
- NFT Investments
- Axie Progression

Optimizing each system independently may produce suboptimal long-term outcomes.

AxieOS will instead model the entire player economy.

---

### Design Principles

- Data before AI
- Measure before Optimize
- Build reusable tools
- Explain every recommendation
- Validate ideas using real gameplay data

---

### Initial Modules

- Bounty Board
- Staking
- Terrariums
- Wallet Analytics
- NFT Portfolio
- Strategy Lab

---

### Future Vision

Develop AxieOS into an open-source GameFi analytics platform combining:

- Data Engineering
- Probability
- Operations Research
- Machine Learning
- Blockchain Analytics

---

### Version

v0.1.0

---

## Journal Entry 002

**Date**

2026-08-30

---

### Decision

Complete **AxieOS V0.9 — Bounty Optimizer Integration** as the first fully integrated gameplay decision-support release.

V0.9 connects the existing gameplay and owned-Axie data model to the Bounty Optimizer and adds structured inventory, Fortune Slip accounting, economics, recommendation tracking, and optimizer decision persistence.

---

### Context

Earlier AxieOS releases established the blockchain, accounting, wallet, and gameplay data foundations.

V0.8 completed the structured owned-Axie gameplay layer, including:

- 136 current owned Axies
- 136 / 136 gameplay metadata coverage
- 816 / 816 named Axie parts
- 16 collectible Axies
- 65 evolved Axies
- 124 Axies with exact ownership-start provenance
- 12 legacy-history unresolved ownership cases

V0.9 was designed to make that gameplay data directly useful to the Bounty Optimizer.

---

### Major V0.9 Capabilities

The V0.9 Bounty Optimizer now integrates:

- Bounty requirement modeling
- Task-name and historical task resolution
- Parameterized Axie qualification
- Exact eligible Axie IDs
- Structured CocoChoco inventory
- Gameplay-database inventory
- Fortune Slip state and reserves
- Reserve-aware optimization
- Bounty economics
- KEEP / REROLL / COMBO recommendations
- Recommendation-vs-actual tracking
- Gameplay DB actual-outcome reconstruction
- Optimizer decision persistence
- Persisted-outcome reconciliation
- Explicit live recommendation saving

---

### Architecture

The principal V0.9 decision flow is:

```text
Daily Bounty Board
        ↓
Task Resolution
        ↓
Owned-Axie Qualification
        ↓
Exact Eligible Axie IDs
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

---

### Inventory Decision

Optimizer inventory can come from:

```text
manual
gameplay_db
```

Gameplay inventory is derived from:

```text
latest verified inventory snapshot
+
inventory events strictly after that snapshot
=
current derived inventory
```

A missing verified snapshot must not be interpreted as a zero balance.

CocoChoco inventory tracks:

```text
on_hand
reserved
available
```

This prevents recommendations from consuming protected reserves.

---

### Fortune Slip Decision

Fortune Slips are modeled as structured state rather than only as a raw balance.

The optimizer can account for:

- starting balance
- protected reserve
- projected reroll spend
- projected remaining balance

Reroll recommendations therefore remain reserve-aware.

---

### Economics Decision

Economic inputs are explicit.

Supported inputs include:

```text
gross_cost_weth
expected_recovery_weth
basis
confidence
non_weth_costs
```

Missing cost evidence does not default to zero.

When required evidence is missing, the economics model can return:

```text
INPUT_REQUIRED
```

COMBO recommendations require an explicit combined economic profile instead of automatically summing individual task profiles.

This avoids double-counting shared execution costs.

---

### Recommendation Tracking

V0.9 tracks recommendation types:

```text
KEEP
REROLL
COMBO
```

Planned-versus-actual tracking includes:

- BP
- Fortune Slip spend
- net WETH cost
- recommendation-followed status

Actual states include:

```text
PENDING
COMPLETED
REROLLED
SKIPPED
PARTIAL
```

Missing actual evidence remains `PENDING`.

---

### Historical Task Compatibility

Historical Bounty records contain inconsistent wording from earlier manual logging.

V0.9 resolves historical tasks using:

```text
1. Current V0.9 resolver
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

Some non-final reroll rows may remain semantically unresolved, but they are retained as slot, roll, and Fortune Slip evidence rather than blocking unrelated reconciliation.

---

### Optimizer Decision Persistence

Two new tables were added:

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

A daily gameplay session can contain multiple optimizer runs because the Bounty Board can change after rerolls.

Recommendations are initially stored as:

```text
PENDING
```

and later reconciled against actual gameplay evidence.

Persistence is atomic.

If one decision fails to persist, the entire optimizer run is rolled back.

---

### Historical Recommendation Integrity

Historical gameplay evidence must not be misrepresented as historical AxieOS recommendations.

Gameplay history can show what happened, but it does not prove what the optimizer recommended at the time unless the recommendation itself was recorded.

Therefore:

```text
historical LIVE_OPTIMIZER attribution is blocked
exact duplicate optimizer plans are blocked
normal optimizer execution remains read-only
```

At the final V0.9 validation checkpoint:

```text
bounty_optimizer_runs          0 rows
bounty_optimizer_decisions     0 rows
```

This is intentional.

Synthetic persistence tests used in-memory SQLite databases only.

No fabricated optimizer recommendation history was written to production.

---

### Issues Encountered

Several implementation issues were found and corrected during V0.9:

- Historical Bounty wording initially resolved only 46 of 72 final tasks.
- A historical compatibility layer increased final-task resolution to 72 / 72.
- An unresolved non-final task (`Reach Floor 3`) initially caused the actual-outcome adapter to abort an otherwise valid session.
- The adapter was changed so unresolved unrelated historical rolls are retained as evidence instead of blocking reconciliation.
- During persistence development, `build_recommendation_actual_tracking()` was accidentally displaced by a code insertion.
- The function was restored and Task 107 regression tests were rerun successfully.
- The first explicit-save integration block was not inserted successfully.
- The integration was re-added in smaller verified steps before testing.

---

### Validation

The final V0.9 integration validator executed all V0.9 subsystems.

Results:

```text
V0.9 tests                     25 / 25 PASS
Historical task resolution            PASS
Current daily plan                    PASS
Production history safety             PASS

V0.9 Integration Validation           PASS
```

Production optimizer-history counts remained unchanged during validation:

```text
Optimizer runs                  0 -> 0
Optimizer decisions             0 -> 0
```

---

### Regression Fixture

The current `bounty_daily_input.py` fixture remains the historical August 18, 2026 dataset.

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

The `REVIEW` state is expected because the observed total contains 675 additional / unattributed BP.

It is not a V0.9 regression failure.

The historical fixture is intentionally blocked from being saved as a current `LIVE_OPTIMIZER` recommendation.

---

### Documentation

V0.9 release documentation was updated in:

- `LLM_Project_Context.md`
- `CHANGELOG.md`
- `docs/Engineering_Journal.md`

---

### Next Step

```text
Finish V0.9 documentation
        ↓
Review Git changes
        ↓
Commit
        ↓
Push
        ↓
Begin next AxieOS roadmap release
```

---

### Version

v0.9

---

## 2026-09-01 — V0.10 Marketplace Strategy Analytics

### Objective

V0.10 extended AxieOS from Bounty Board decision support into canonical Axie marketplace inventory, position tracking, economics, capital analysis, and rule-based marketplace strategy.

Primary implementation:

```text
scripts/inventory_report.py
```

The implementation is intentionally read-only against:

```text
data/blockchain/database/axieos.db
```

No production database writes are performed by the marketplace inventory report.

---

### Source Audit

The V0.10 marketplace model uses Axie evidence from:

```text
gameplay_owned_axies
marketplace_events
blockchain_accounting_records
blockchain_transactions
```

Primary responsibilities:

```text
gameplay_owned_axies
    Current ownership and gameplay metadata

blockchain_accounting_records
    Purchase, sale, fee, cost-basis, realized P/L, and accounting evidence

marketplace_events
    Historical marketplace activity and Bounty-linked events

blockchain_transactions
    Blockchain provenance, transfers, burns, and transaction evidence
```

A major design decision was to avoid treating `marketplace_events` as a live marketplace source.

Historical LIST events do not prove that an Axie remains listed today.

---

### Canonical Marketplace Inventory

The original marketplace model contained only a small subset of historical Axies.

V0.10 replaced that approach with a canonical union across gameplay, marketplace, and accounting evidence.

Production source coverage:

```text
gameplay_owned_axies rows              137
marketplace distinct Axies              11
accounting distinct Axies               42

canonical inventory                    171
canonical unique Axies                 171
```

Final position states:

```text
OPEN_OWNED                             136
CLOSED_SOLD                             27
CLOSED_RELEASED                          8
                                      ----
TOTAL                                   171
```

The inventory therefore represents both:

```text
current owned Axies
+
legitimate historical sold / released Axies
```

instead of limiting analytics to currently owned gameplay inventory.

---

### Ownership Start vs Economic Acquisition

V0.10 separates two concepts that were previously easy to conflate:

```text
ownership_start
economic_acquisition
```

`ownership_start` represents evidence that the Axie entered user ownership.

`economic_acquisition` requires defensible purchase or cost evidence.

This prevents:

```text
internal transfers
legacy ownership
incomplete provenance
```

from being treated automatically as purchases.

Final ownership-start coverage:

```text
Known ownership-start datetime          157
Ownership-start READY                   154
Ownership-start REVIEW                   17
```

Final economic-acquisition coverage:

```text
Known acquisition cost                   34
Known acquisition datetime               34
Known acquisition txhash                 27
```

For current open positions:

```text
Open Axies                              136
Open Axies with proven cost               7
```

Only those seven open positions currently have sufficient acquisition basis for READY resale and capital analytics.

---

### Listing and Sale Status

Historical marketplace activity is retained without overstating certainty.

Final listing states:

```text
CLOSED_POSITION                         35
LISTING_RECORDED_UNVERIFIED              1
UNKNOWN                                135
```

No source currently proves live marketplace listing state.

Therefore AxieOS does not report historical LIST activity as a confirmed current listing.

Final sale states:

```text
SOLD_CONFIRMED                          25
SALE_RECORDED_UNVERIFIED                 2
NO_SALE_EVIDENCE                       136
NOT_APPLICABLE_RELEASED                  8
```

Accounting-backed sale evidence is preferred over weaker legacy marketplace evidence.

---

### Datetime Policy

Canonical blockchain and accounting timestamps are treated as UTC.

Legacy manually recorded marketplace timestamps may reflect Philippine local time.

These records are retained as REVIEW evidence rather than being silently converted.

Example:

```text
Axie #2788135 accounting burn
2026-08-14 03:57:05 UTC

Legacy marketplace release
2026-08-14 11:57:05
```

The eight-hour difference is consistent with Asia/Manila time, but the model does not rewrite the historical timestamp without explicit proof of its original timezone.

---

### Realized Economics

V0.10 calculates realized marketplace economics only when sufficient accounting evidence exists.

Final states:

```text
REALIZED_READY                          14
REALIZED_REVIEW                         11
REALIZED_UNAVAILABLE                     2
REALIZED_NOT_APPLICABLE                144
```

READY realized economics can contain:

```text
gross sale
marketplace fee
net proceeds
cost basis
realized P/L
realized ROI
```

Historical accounting values are preserved directly rather than replacing them with reconstructed estimates.

---

### Unrealized Economics

No live Axie marketplace-price source is currently connected.

Therefore V0.10 intentionally leaves:

```text
current_market_value
unrealized_pl
unrealized_roi
```

unavailable for open positions.

The system does not fabricate present market value from stale listings or historical prices.

---

### Marketplace Fee Audit

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

as an explicit historical marketplace-fee assumption for future resale break-even analysis.

This is an assumption supported by the observed accounting history, not a hard-coded claim that the marketplace fee can never change.

---

### Resale Break-Even

For an open Axie with proven acquisition basis:

```text
break-even gross sale price
=
acquisition cost / (1 - 0.0425)
```

Final resale states:

```text
RESALE_READY                              7
RESALE_UNAVAILABLE_NO_COST              129
RESALE_NOT_APPLICABLE                    35
```

Current break-even analysis does not include:

```text
purchase gas in RON
future sale gas in RON
```

because no timestamp-specific RON/WETH conversion model has been established.

The model therefore avoids mixing token-denominated costs through an unsupported conversion assumption.

---

### Holding-Period Analytics

Holding periods use canonical ownership-start evidence.

For open positions:

```text
ownership start -> current UTC report time
```

For closed positions:

```text
ownership start -> sale or release
```

Final states:

```text
HOLDING_READY                           153
HOLDING_REVIEW                            4
HOLDING_UNAVAILABLE                      14
```

The four REVIEW cases contain legacy timestamp or provenance uncertainty.

The 14 unavailable cases lack a defensible ownership-start datetime.

Very short holding periods are legitimate.

Some historical release candidates were purchased and released within minutes.

---

### Release-Candidate Analysis

V0.10 added release-candidate analysis using:

```text
ownership state
acquisition basis
level
breed count
collectible status
evolved status
```

All 136 currently owned Axies have:

```text
level
breed_count
```

available from `gameplay_owned_axies`.

Current protected-attribute coverage:

```text
Collectible Axies                        16
Evolved Axies                            65
Protected collectible/evolved set        65
```

Collectible or evolved Axies are protected from automatic release consideration.

Final release-analysis states:

```text
RELEASE_ANALYSIS_READY                    6
RELEASE_REVIEW_NO_COST_BASIS             65
RELEASE_REVIEW_PROTECTED_ATTRIBUTE       65
RELEASE_NOT_APPLICABLE                   35
```

Seven open Axies have proven acquisition basis.

Six are non-protected and eligible for READY release analysis.

One is evolved and remains protected.

---

### Release-Economics Limitation

Historical production evidence currently contains:

```text
7 accounting-backed Axie burns
2 legacy marketplace release records
recorded material quantities for 2 releases
```

Recorded examples include:

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

No defensible production Memento / release-material valuation model currently exists.

Therefore:

```text
release_expected_recovery_weth = unavailable
release_expected_pl_weth       = unavailable
```

No synthetic material value is inserted.

Historical `ascendLevel` transactions were also found near several releases.

However, those transaction rows do not provide a sufficiently reliable Axie ID relationship.

They are therefore not automatically assigned to individual release economics.

---

### Capital Utilization

Capital analytics are intentionally labeled:

```text
PARTIAL_COVERAGE
```

because proven cost basis exists for only a small portion of the current owned inventory.

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

The `0.0037736775 WETH` value represents only the seven open positions with proven acquisition basis.

It must not be interpreted as the acquisition cost of the full 136-Axie owned inventory.

Capital-days exposure and capital-weighted holding age remain dynamic because open positions continue aging.

---

### Marketplace Strategy Layer

V0.10 uses explainable rule-based strategy states rather than an artificial numeric score.

Final strategy states:

```text
STRATEGY_HOLD_INSUFFICIENT_DATA         65
STRATEGY_HOLD_PROTECTED                 65
STRATEGY_REVIEW_EXIT_OPTIONS             6
STRATEGY_NOT_APPLICABLE                 35
```

Final strategy actions:

```text
HOLD                                    130
REVIEW                                    6
NONE                                     35
```

`STRATEGY_HOLD_PROTECTED` prevents collectible or evolved Axies from being automatically considered release candidates.

`STRATEGY_HOLD_INSUFFICIENT_DATA` prevents the system from making unsupported economic conclusions.

`STRATEGY_REVIEW_EXIT_OPTIONS` identifies positions where enough evidence exists to justify further comparison.

It does not mean:

```text
SELL
RELEASE
```

The six review positions still require additional evidence.

For resale:

```text
live or user-supplied market price required
```

For release:

```text
defensible release-recovery valuation required
```

---

### Safety Guardrails

V0.10 explicitly avoids automatic destructive or market actions.

Production result:

```text
Automatic SELL decisions                  0
Automatic RELEASE decisions               0
```

Marketplace strategy remains advisory.

AxieOS does not automatically infer an exit decision when required economic evidence is unavailable.

---

### Issues Encountered

Several implementation and validation issues were found and corrected during V0.10:

- The previous marketplace model was too narrow because it depended primarily on historical marketplace events and did not represent the full Axie ownership history.
- Historical LIST events were initially unsuitable as evidence of current listing state, so listing semantics were redesigned around verified versus unverified evidence.
- Acquisition cost and ownership start had to be separated to avoid treating transfers or incomplete provenance as purchases.
- During holding-period integration, `ownership_start` was referenced before assignment in the inventory builder. The build order was corrected and the holding validator was rerun successfully.
- Initial write-safety scanning produced false positives from ordinary Python `.replace()` calls. The validation was narrowed to actual SQL write statements.
- The first V0.9 regression harness called two tests without their required production database path. The harness was corrected and all selected cross-version regression tests passed.
- Release-reward material quantities were available for too few historical releases to support a defensible expected-recovery model. The model therefore preserves those values as unavailable instead of inventing estimates.
- No live marketplace-price source currently exists, so unrealized economics and automatic resale decisions remain intentionally unavailable.

---

### Production Validation

Task 120 performed final V0.10 integration and production validation.

Canonical inventory:

```text
Inventory rows                           171
Unique Axies                             171
```

Position states:

```text
CLOSED_RELEASED                            8
CLOSED_SOLD                               27
OPEN_OWNED                               136
```

Marketplace strategy states:

```text
STRATEGY_HOLD_INSUFFICIENT_DATA           65
STRATEGY_HOLD_PROTECTED                   65
STRATEGY_NOT_APPLICABLE                   35
STRATEGY_REVIEW_EXIT_OPTIONS               6
```

Capital coverage:

```text
Coverage status              PARTIAL_COVERAGE
Open positions                           136
Open positions with proven cost            7
Proven open capital             0.0037736775 WETH
```

Safety guardrails:

```text
Automatic SELL decisions                  0
Automatic RELEASE decisions               0
```

Final validator:

```text
Inventory validator                     PASS
Inventory errors                           0
Production sign-off                     PASS
Sign-off errors                             0
```

---

### Cross-Version Regression

Critical V0.9 functionality was rerun against the production database after the V0.10 implementation.

Results:

```text
Owned Axie candidates                  PASS
Recommendation Axie candidates         PASS
Recommendation vs actual               PASS

Overall                                PASS
```

V0.10 therefore did not break the critical V0.9 owned-Axie qualification and Bounty Optimizer recommendation pipeline.

---

### V0.10 Task Completion

Core engineering:

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

Documentation closeout:

```text
121  LLM_Project_Context.md update                COMPLETE
122  CHANGELOG.md update                          COMPLETE
123  Engineering Journal completion record        COMPLETE
```

---

### Documentation

V0.10 release documentation was updated in:

- `LLM_Project_Context.md`
- `CHANGELOG.md`
- `docs/Engineering_Journal.md`

---

### Next Step

```text
Review Git changes
        ->
Confirm production database remains untracked
        ->
Commit V0.10
        ->
Push to main
        ->
Begin next AxieOS roadmap release
```

---

### Version

v0.10

---

## 2026-09-08 — V0.11 Terrarium Analytics

### Objective

V0.11 extended AxieOS into evidence-aware Terrarium analytics, historical reconstruction, accumulation measurement, scenario projection, and financial ROI analysis.

The release was designed around one core constraint:

> Missing historical Terrarium evidence must remain missing rather than being reconstructed from unsupported assumptions.

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

The canonical historical range is:

```text
2026-08-07 → 2026-08-26
```

---

### Historical Evidence Layer

V0.11 added dedicated evidence tables for incomplete historical observations:

```text
terrarium_snapshot_evidence
terrarium_plot_evidence
terrarium_group_ranking_evidence
```

Evidence observations support:

```text
COMPLETE
PARTIAL
UNRESOLVED
```

The evidence layer preserves:

- observed date
- observed or approximate time text when available
- source
- source reference
- completeness status
- only the metrics actually supported by the source

Missing metrics remain `NULL`.

No value is filled merely because a nearby observation exists.

Final partial-evidence coverage:

```text
Partial evidence observations             13
Evidence plot rows                        29
Evidence ranking rows                     12
```

Combined evidence-aware coverage:

```text
Total observations                        30
Represented calendar dates                18
Historical range             2026-08-07 → 2026-08-27
```

---

### Buff-State Safety

Historical Terrarium buff evidence was found to be incomplete.

The previous ingestion model could store default values that looked more certain than the underlying source evidence justified.

V0.11 changed future ingestion so:

```text
buff_active = NULL
```

when buff state is unknown.

Existing historical values were preserved rather than rewritten without source evidence.

The model does not infer historical buff state solely from surrounding observations.

---

### Unbuffed-Hours Safety

The previous schema contained a default value for:

```text
estimated_unbuffed_hours
```

This default could incorrectly imply that zero unbuffed hours had been observed.

V0.11 removed the default.

Future omission now stores:

```text
NULL
```

All 17 existing legacy values of:

```text
'0'
```

were preserved as historical records rather than rewritten.

Those legacy zero values are not treated as independently observed zero-hour measurements.

---

### Evidence-Aware Analytics

Primary implementation:

```text
scripts/terrarium_summary.py
```

Canonical analytics remain the default report mode.

Evidence-aware mode is optional and combines canonical and partial evidence while evaluating each metric independently.

The model does not require a partial observation to contain every metric before using the metrics that are actually present.

Implemented analytics include:

- cumulative bAXS history
- plot-level accumulation
- observation-to-observation change
- adjacent versus bridged metric change
- Flame history
- group-rank history
- competitive Flame share
- Next Distribution composition
- distribution-mix comparison

---

### Observed Accumulation

Evidence-aware cumulative bAXS endpoints produced:

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

This value is explicitly treated as a:

```text
calendar-date-span average
```

and not as a precise normalized 24-hour yield.

---

### Yield and Projection Model

Primary implementation:

```text
scripts/terrarium_projection.py
```

Because exact historical observation timestamps are incomplete, V0.11 does not calculate:

```text
exact hourly yield
precise timestamp-normalized daily yield
buff-adjusted yield
unbuffed yield
```

Instead, the projection model uses the observed first-to-latest calendar-date span.

Base combined pace:

```text
1.1615 bAXS / calendar day
```

Nominal continuation examples:

```text
7 days        8.1305 bAXS
30 days      34.8450 bAXS
365 days    423.9475 bAXS
```

Sensitivity scenarios:

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

The ROI layer intentionally separates:

```text
historical Terrarium accumulation
```

from:

```text
financial assumptions
```

Forest acquisition reference:

```text
Plot coordinates                 (-123, 9)
Purchase date                    2025-11-18
Purchase price                   0.06841 ETH
Historical RON reference         871.81 RON
```

The previously recorded interpretation of:

```text
$871.81
```

was rejected.

The corrected historical reference is:

```text
871.81 RON
```

Current conversion assumption used by the model:

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

This keeps current market-price assumptions separate from canonical Terrarium history.

---

### ROI Scope

The current ROI model uses:

```text
combined income from all owned Terrarium plots
```

to evaluate recovery of the Forest acquisition reference.

The calculation is:

```text
full acquisition-cost payback from zero recovery
```

Prior realized Terrarium earnings are not deducted from the historical Forest acquisition cost.

The current model also excludes unsupported or separately modeled factors such as:

- gas
- taxes
- transaction fees
- staking yield
- future changes to Terrarium economics
- future changes to bAXS conversion rules

---

### Synthetic ROI Validation

A synthetic AXS-price input of:

```text
10 RON / AXS
```

was used only to validate formulas.

It was not recorded as a current market fact.

Synthetic validation produced:

```text
Effective value per bAXS                7 RON

AXS required for break-even       87.1810 AXS
Gross bAXS required              124.5443 bAXS

Conservative break-even          142.9695 days
Base break-even                  107.2271 days
Upside break-even                 85.7817 days
```

---

### Schema and Ingestion Validation

V0.11 validated:

```text
Future unknown buff state              NULL
Future unknown unbuffed hours          NULL
Historical canonical rows              preserved
Historical evidence rows               preserved
Foreign-key validation                 PASS
SQLite integrity check                 PASS
```

Disposable database-copy testing confirmed that omitted future fields do not silently recreate false zero/default values.

The production database remained untouched by the synthetic ingestion test.

---

### V0.11 Task Completion

```text
124  Terrarium foundation audit                      COMPLETE
125  Canonical Terrarium summary and validation      COMPLETE
126  Trend / delta / accumulation analytics          COMPLETE
127  Next Distribution analytics                     COMPLETE
128  Historical coverage + evidence layer            COMPLETE
129  Evidence-aware analytics                        COMPLETE
130A Yield prerequisite audit                        COMPLETE
130B NULL/default ingestion safety                   COMPLETE
130C Projection + sensitivity scenarios              COMPLETE
130D Financial ROI model + validation                COMPLETE
131  Release closeout / regression / commit          COMPLETE
```

---

### Validation

V0.11 core engineering validation passed:

```text
Canonical analytics                     PASS
Evidence-aware analytics                PASS
Historical evidence integrity           PASS
Metric-specific change analysis         PASS
Projection regression                   PASS
ROI formula validation                  PASS
ROI input guardrails                    PASS
Future NULL ingestion                    PASS
Foreign-key validation                  PASS
SQLite integrity                        PASS
Python compile regression               PASS
```

---

### Documentation

V0.11 release documentation is being finalized in:

- `docs/Engineering/ROADMAP.md`
- `CHANGELOG.md`
- `docs/Engineering_Journal.md`
- `docs/Game Mechanics/Terrariums.md`
- `LLM_Project_Context.md`

---

### Next Step

```text
Complete remaining V0.11 documentation
        ↓
Remove temporary validation artifacts
        ↓
Run final regression
        ↓
Confirm production database remains untracked
        ↓
Review Git changes
        ↓
Commit V0.11
        ↓
Push to main
```

---

### Version

v0.11