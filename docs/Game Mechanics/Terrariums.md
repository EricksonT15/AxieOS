---

# Fortune Slips Shrine Buff

## Overview

Players can spend Fortune Slips to temporarily increase Atia's Flame production on an individual land plot.

### Effect

+10% Atia's Flame

Duration:

- 24 hours

Stacking:

- Purchasing additional buffs extends the duration by another 24 hours.
- The +10% effect does **not** stack.

---

## Fortune Slip Costs

| Land Type | Fortune Slips |
|-----------|--------------:|
| Savannah | 3 |
| Forest | 8 |
| Arctic | 22 |
| Mystic | 48 |
| Genesis | 960 |
| Luna's Landing | 2880 |

Each purchase applies to one land plot.

---

## Flame Formula

```
Round Down(
    Total Individual Axies' Flame
    × (1 + Land Item Boost)
    × (1 + Fortune Slips Buff)
)
```

The Fortune Slips Buff is applied after Land Item Boosts.

---

## AxieOS Notes

Future analytics should calculate:

- Additional Flame generated
- Additional bAXS earned
- Fortune Slip ROI
- Break-even point
- Best land type for using Shrine Buffs
- Buff efficiency compared across land rarities

---

# Experiment: Shrine Buff Validation

Date

- 2026-07-24

Objective

Validate the effectiveness of the +10% Fortune Slips Shrine Buff under identical global conditions.

## Experimental Conditions

The following variables remained constant before and after activation:

- Global Lunium: 688,490
- Forest Global Atia Flame: 888,712
- Savannah Global Atia Flame: 396,316
- Forest Rank: 169
- Savannah Rank: 246

Only the Shrine Buff was activated.

## Results

| Plot | Flame Before | Flame After | Next Distribution Before | Next Distribution After |
|------|-------------:|------------:|-------------------------:|------------------------:|
| Forest | 1416 | 1557 | 0.0384 | 0.0422 |
| Savannah #1 | 161 | 177 | 0.0031 | 0.0034 |
| Savannah #2 | 191 | 210 | 0.0037 | 0.0040 |

## Cost

- Forest: 8 Fortune Slips
- Savannah #1: 3 Fortune Slips
- Savannah #2: 3 Fortune Slips

Total Cost

- 14 Fortune Slips

## Observations

- Effective Atia Flame increased by approximately 10%.
- Expected bAXS distribution increased by approximately 10%.
- Global rankings remained unchanged.
- Results closely match the game's documented Shrine Buff mechanics.

## Next Phase

Perform an economic ROI analysis by comparing:

- Additional bAXS earned
- Fortune Slip expenditure
- Alternative Fortune Slip usage (Bounty Board rerolls)

This experiment validates the mechanical behavior of the Shrine Buff. Future experiments will determine whether activating the buff is economically optimal.

---

## Experiment Update: Post-Distribution Observation

### Distribution Snapshot

#### Global

| Metric | Value |
|--------|------:|
| Global Lunium | 688,365 |
| Forest Global Flame | 894,449 |
| Savannah Global Flame | 397,475 |

---

### Forest

| Metric | Value |
|--------|------:|
| Atia Flame | 1,557 |
| Rank | 153 |
| Next Distribution | 0.0420 |
| Total Acquired | 34.26 bAXS |

---

### Savannah #1

| Metric | Value |
|--------|------:|
| Atia Flame | 177 |
| Next Distribution | 0.0034 |
| Total Acquired | 3.04 bAXS |

---

### Savannah #2

| Metric | Value |
|--------|------:|
| Atia Flame | 210 |
| Next Distribution | 0.0040 |
| Total Acquired | 3.15 bAXS |

Combined Savannah Rank

- 225

---

## Findings

Despite changes in the global environment after the distribution:

- Forest rank improved from **169 → 153**.
- Combined Savannah rank improved from **246 → 225**.
- The +10% Shrine Buff maintained a higher competitive position even as total global flame increased.

## Research Direction

Future evaluations should measure the **economic value** of the Shrine Buff rather than only its direct ROI.

Evaluation metrics will include:

- Additional bAXS earned
- Rank improvement
- Global Atia Flame changes
- Global Lunium changes
- Fortune Slips spent
- Competitive positioning

---

# V0.11 Terrarium Analytics Notes

## Evidence Policy

V0.11 separates canonical Terrarium observations from incomplete historical evidence.

Canonical observations are stored through:

```text
gameplay_daily_sessions
        ↓
terrarium_snapshots
        ↓
terrarium_plot_snapshots
        ↓
terrarium_group_rankings
```

Incomplete historical observations are preserved separately through:

```text
terrarium_snapshot_evidence
terrarium_plot_evidence
terrarium_group_ranking_evidence
```

Partial observations retain only the metrics actually supported by the source.

Missing values remain `NULL`.

AxieOS does not infer missing:

- snapshot times
- Flame values
- ranks
- global Flame
- Next Distribution
- acquired bAXS
- buff state
- unbuffed hours

from neighboring observations.

---

## V0.11 Historical Coverage

Canonical production coverage:

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

Evidence-aware analytics therefore use:

```text
Total observations                       30
Represented calendar dates               18
Historical range             2026-08-07 → 2026-08-27
```

---

## Observed bAXS Accumulation

Evidence-aware cumulative endpoints produce:

```text
Forest #1                    +19.6300 bAXS
Savannah #1                   +1.6200 bAXS
Savannah #2                   +1.9800 bAXS
Combined                     +23.2300 bAXS
```

Endpoint period:

```text
2026-08-07 → 2026-08-27
```

Calendar-date difference:

```text
20 days
```

Combined nominal pace:

```text
1.1615 bAXS / calendar day
```

This is a **calendar-date-span average**.

It must not be described as:

```text
exact hourly yield
precise 24-hour normalized daily yield
buff-adjusted yield
unbuffed yield
```

because the historical observation times and buff-state evidence are not complete enough to support those calculations.

---

## Projection Scenarios

V0.11 uses three explicit sensitivity assumptions:

```text
Conservative          75% of observed pace
Base                 100% of observed pace
Upside               125% of observed pace
```

The base observed calendar-span pace is:

```text
1.1615 bAXS / calendar day
```

Nominal base continuation:

```text
7 days        8.1305 bAXS
30 days      34.8450 bAXS
365 days    423.9475 bAXS
```

These scenarios are sensitivity assumptions.

They are not confidence intervals or probability forecasts.

---

## Buff-State Interpretation

The July 24 Shrine Buff experiment remains useful evidence that the documented +10% Flame mechanic behaved approximately as expected under the observed experimental conditions.

However, V0.11 does not use that experiment to infer historical buff state for unrelated Terrarium snapshots.

When historical buff state is unknown:

```text
buff_active = NULL
```

Future omitted buff state also stores `NULL`.

Likewise, omitted:

```text
estimated_unbuffed_hours
```

stores `NULL`.

Existing legacy zero values are preserved as historical records but are not treated as independently observed zero-hour measurements.

---

## Financial ROI References

Forest acquisition reference:

```text
Plot coordinates                 (-123, 9)
Purchase date                    2025-11-18
Purchase price                   0.06841 ETH
Historical RON reference         871.81 RON
```

The historical reference is:

```text
871.81 RON
```

not USD.

Current bAXS conversion assumption:

```text
bAXS → AXS                       70%
Conversion haircut               30%
```

AXS market price is not stored as a fixed Terrarium historical value.

`scripts/terrarium_roi.py` requires the AXS price in RON at runtime.

---

## Current ROI Scope

The V0.11 ROI model uses:

```text
combined bAXS accumulation from all owned Terrarium plots
```

to evaluate recovery of the Forest acquisition reference.

The calculation currently represents:

```text
full acquisition-cost payback from zero recovery
```

Prior realized Terrarium income is not deducted from the Forest acquisition reference.

The model does not currently include:

- gas
- taxes
- transaction fees
- staking yield
- future Terrarium economy changes
- future bAXS conversion-rule changes

These limitations are reported explicitly rather than estimated without evidence.

---

## V0.11 Implementation

Primary scripts:

```text
scripts/terrarium_summary.py
scripts/add_terrarium_evidence.py
scripts/terrarium_projection.py
scripts/terrarium_roi.py
```

V0.11 preserves the distinction between:

```text
observed historical evidence
        vs
projection assumptions
        vs
financial assumptions
```

This distinction is required for all future Terrarium analytics.