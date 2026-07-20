# AO-017 — Terrariums Data Model

## Purpose

This document defines the data model used by the Terrariums module in AxieOS.

The objective is to standardize how plots, Atia Flame, Lunium, bAXS earnings, and Axie assignments are recorded and analyzed.

---

# Scope

This document covers:

- Plot Registry
- Axie Assignment
- Shrine
- Dojo
- Atia Flame
- Lunium
- bAXS Production
- Daily & Hourly Analytics

Future versions will include:

- Land Items
- Fortune Slip Buffs
- Automatic Atia Flame Calculator
- ROI Optimization Engine

---

# Design Principles

Terrariums is modeled as a passive resource optimization system.

Each plot converts:

Axies
→ Atia Flame
→ Share of Biome Reward Pool
→ bAXS

while consuming Lunium every hourly tick.

---

# Module Structure

Terrariums

├── Plot Registry

├── Axie Assignment

├── Lunium

├── Earnings

├── Dojo

└── Analytics

---

# 1. Plot Registry

One record per land plot.

| Field | Type | Description |
|------|------|-------------|
| PlotID | Text | Unique Plot Identifier |
| WalletID | Text | Owner Wallet |
| Plot Name | Text | User-defined Plot Name |
| Biome | Enum | Forest, Savannah, Arctic, Mystic |
| Land NFT | Boolean | NFT Plot or Free Plot |
| Max Axies | Integer | Maximum assigned Axies |
| Shrine Axies | Integer | Axies currently praying |
| Dojo Axies | Integer | Axies currently training |
| Atia Flame | Integer | Current Flame |
| Hourly bAXS | Decimal | Current production |
| Current Lunium | Integer | Plot Lunium Buffer |
| Lunium Capacity | Integer | Maximum Plot Capacity |
| Lunium Mode | Enum | Global / Local |
| Active | Boolean | Plot Active |

---

# 2. Axie Assignment

Tracks where every Axie is assigned.

| Field | Type | Description |
|------|------|-------------|
| AxieID | Integer | NFT ID |
| PlotID | Text | Assigned Plot |
| Building | Enum | Shrine / Dojo |
| Assigned Date | DateTime | Assignment Timestamp |
| Cooldown End | DateTime | Production Resume Time |

Notes

An Axie assigned to the Dojo:

• continues to be playable in Origins

• continues to be playable in Classic

• continues to be playable in Axie Quests

Only Terrariums production changes.

---

# 3. Lunium

Two Lunium pools exist.

## Global Lunium

Account-wide reserve.

Purchased using:

- bAXS
- Supported cryptocurrencies

Shared across plots.

---

## Local Lunium

Generated automatically by each plot.

Characteristics:

- Capacity depends on biome.
- Regenerates over time.
- Stops generating while the Shrine consumes it.
- Used only when Local Mode is selected.

---

# Lunium Fields

| Field | Type |
|------|------|
| Global Balance | Integer |
| Local Balance | Integer |
| Capacity | Integer |
| Mode | Enum |
| Consumption per Tick | Decimal |
| Regeneration Rate | Decimal |

---

# 4. Atia Flame

Atia Flame determines the percentage of the biome reward pool earned.

Higher Flame

↓

Larger share

↓

Higher bAXS

Current contributors include:

- Base Axie Flame
- Evolution
- Accessories
- Future Land Item bonuses

---

# Reward Formula

Hourly Reward

=

(Plot Flame ÷ Total Biome Flame)

×

Hourly Biome Reward Pool

Total Biome Flame changes continuously as other players enter, leave, or upgrade their plots.

---

# 5. Earnings

Hourly production.

| Field | Type |
|------|------|
| Timestamp | DateTime |
| PlotID | Text |
| Atia Flame | Integer |
| Hourly Reward | Decimal |

---

Daily production.

| Field | Type |
|------|------|
| Date | Date |
| PlotID | Text |
| Daily bAXS | Decimal |

---

# 6. Dojo

Tracks passive AXP generation.

| Field | Type |
|------|------|
| AxieID | Integer |
| Start Time | DateTime |
| End Time | DateTime |
| Total AXP Earned | Integer |

Important

An Axie earning AXP in the Dojo may simultaneously earn additional AXP from:

- Axie Infinity Origins
- Axie Infinity Classic
- Axie Quests

Gameplay does not remove the Axie from Terrariums.

---

# 7. Cooldown Rules

Changing:

- Shrine ↔ Dojo
- Global ↔ Local Lunium

initiates a one-hour cooldown.

During this cooldown:

- No bAXS is earned.
- No Dojo AXP is earned.

Production resumes on the next hourly tick.

---

# 8. Analytics

Future KPIs

- Average Daily bAXS
- Average Hourly bAXS
- Atia Flame Growth
- bAXS per Flame
- Earnings Stability
- Dojo Opportunity Cost
- Lunium Consumption
- Downtime Percentage

---

# Future Features

AO-018

Atia Flame Calculator

Automatically computes total flame from:

- Axies
- Evolution
- Accessories
- Land Items

---

AO-019

Terrarium Optimizer

Provides recommendations such as:

- Best Axie to move into Dojo
- Lowest opportunity-cost training
- Best upgrade ROI
- Predicted increase in bAXS
- Lunium optimization strategy

---

# Revision History

Version: 0.1

Status: Draft

Author: AxieOS Engineering

Last Updated: July 2026
