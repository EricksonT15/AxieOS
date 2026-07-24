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
