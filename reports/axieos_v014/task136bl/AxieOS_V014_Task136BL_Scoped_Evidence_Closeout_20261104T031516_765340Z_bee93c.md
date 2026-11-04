# AxieOS V0.14 — Scoped finance evidence closeout review

**Release state:** Scoped evidence ready for review. Full finance closeout remains open.

Raw transaction rows before/after: **1171/1193**; exact inserted: **22**. Ledger preserved: **1532** rows. Raw transfers and **6** protected tables unchanged.

Source references: **1339** = **517** historical + **707** prior cached + **115** recent. The same hash can occur in several report views.

| View | Historical primary | Prior cached context | Recent unresolved |
|---|---:|---:|---:|
| Capital | 112 | 707 | 115 |
| Expense | 53 | 163 | 115 |
| Income | 93 | 214 | 115 |
| Portfolio | 517 | 707 | 115 |

## Unresolved for full financial closeout

- Verified income, expense, profit, portfolio value and PHP recovery are UNKNOWN
- Checkpoint 96 remains OPEN
- Stored fees and raw fees do not establish who paid gas or accepted expense
- Historical cost basis conflicts and unhashed capital references remain unresolved
- Candidate marketplace routes do not establish verified trades

Verified financial totals: **UNKNOWN**. Checkpoint 96: **OPEN**. No financial values accepted.

Production and backup opened read only | Writes: 0 | Network: 0
