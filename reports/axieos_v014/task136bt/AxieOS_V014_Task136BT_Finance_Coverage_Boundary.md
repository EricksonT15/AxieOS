# AxieOS V0.14 — Task136BT Finance Coverage Boundary

**Decision status:** Scoped finance evidence may be used with explicit coverage and unknown-value labels. Unified Finance and Checkpoint 96 remain **OPEN**. This is an evidence decision, not an accepted P&L or an authorization to run accounting writers.

## Evidence reviewed

| Source | Supported observation | Limit |
| --- | --- | --- |
| `Ronin_Gamer_Transactions(1).csv` and Task136BS crosswalk | 9,526 rows, 7,935 unique hashes, 2021-06-29 through 2026-03-03 UTC; 116 hashes with consumables in and WETH out | Generic consumable name, no token ID or log index; payment routes and lots need review |
| Task136BO consumable purchase history | 26 newer Regular/Premium purchase hashes corroborated with explorer evidence | Corroboration does not establish all-time opening inventory or consumed-lot basis |
| Task136F cached ACI token transfers | 691 rows, starting 2026-05-13 UTC | No hash overlap with the historical CSV; does not bridge March–May |
| Task136BM finance resolution queue | 24 sale-basis conflicts retained for review | No direct sale-hash overlap with the historical CSV; lot provenance remains unresolved |
| `Ronin_Gamer_2026_Refresh.csv(1).csv` | 598 rows beginning 2026-05-13 UTC | The historical export ends 2026-03-03; intervening wallet history is unobserved in these exports |

## Treatment boundary

1. Preserve all 116 historical hashes as **purchase-shaped candidates**. Keep token ID, Regular/Premium allocation, paid basis, and inventory lot **UNKNOWN** until event-level evidence supports them. WETH-out row sums are observations, not accepted cost.
2. Preserve the 26 corroborated newer purchases with their own transaction and token-ID references. Do not fold them into the historical candidate count or treat them as proof of opening inventory.
3. Retain the 24 sale-basis conflicts. Do not use inferred FIFO results as realized profit while opening lots or token identities are unresolved.
4. Mark 2026-03-04 through the start of the 2026-05-13 refresh as an **unobserved export interval**. This is not evidence of zero activity. No further user purchase records are assumed to exist.
5. Maintain separate source coverage, candidate amounts, corroborated transaction evidence, and accepted financial values. Accepted all-time income, expenses, profit, PHP outlays, and recovered capital remain **UNKNOWN**.

## Release decision

The four V0.14 finance evidence views can remain available as **coverage views** with visible unknown values and links to source references. Full Unified Finance release requires independent closure of missing wallet history and the relevant inventory lots or an explicit product scope that excludes those totals. No historical CSV rows should be added to production accounting solely from this review.

**Validation:** Read-only offline comparison. Database opened: NO. Database writes: 0. Network calls: 0. Git commit or push: NO.
