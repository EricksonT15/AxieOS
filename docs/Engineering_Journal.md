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