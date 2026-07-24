# Daily Financial Snapshot

Version: 1.0

Status: Active

---

# Purpose

The Daily Financial Snapshot records the state of the AxieOS ecosystem at the end of each operating day.

It serves as the primary operational dataset for tracking:

- Portfolio growth
- Passive income
- Liquidity
- Marketplace activity
- Terrarium performance
- Staking performance

Unlike blockchain transactions, this dataset represents a point-in-time snapshot rather than individual events.

---

# Snapshot Frequency

- Once per day
- Recorded after gameplay is complete
- Preferably before ending the work session

---

# Wallet

| Field | Unit | Description |
|--------|------|-------------|
| WETH | WETH | Available wallet balance |
| RON | RON | Available wallet balance |
| AXS | AXS | Liquid AXS balance |
| bAXS | bAXS | Liquid bAXS balance |
| SLP | SLP | Liquid SLP balance |
| USDC | USDC | Stablecoin balance (if applicable) |

---

# Staking

| Field | Unit | Description |
|--------|------|-------------|
| Staked AXS | AXS | Total AXS currently staked |
| Staked bAXS | bAXS | Total bAXS currently staked |
| Claimable AXS (AXS Stake) | AXS | Rewards generated from AXS staking |
| Claimable AXS (bAXS Stake) | AXS | Rewards generated from bAXS staking |
| APR | % | Current staking APR |
| Daily Reward Pool | AXS | Total network rewards distributed daily |
| Network Total Staked | AXS | Total AXS staked across the network |
| AXS Price | USD | Reference market price |

---

# Terrariums

| Field | Unit | Description |
|--------|------|-------------|
| Claimable bAXS | bAXS | Current claimable Terrarium rewards |
| Global Lunium | Points | Total Lunium in the ecosystem |
| Forest Flame | Flame | Player's Forest flame |
| Savannah #1 Flame | Flame | Player's Savannah #1 flame |
| Savannah #2 Flame | Flame | Player's Savannah #2 flame |
| Forest Rank | Rank | Hourly ranking |
| Savannah Rank | Rank | Combined Savannah hourly ranking |
| Active Shrine Buff | Yes/No | Whether the Shrine Buff is active |

---

# Marketplace

| Field | Unit | Description |
|--------|------|-------------|
| Purchases Today | Count | Assets purchased |
| Sales Today | Count | Assets sold |
| Marketplace Revenue | WETH | Gross sales value |
| Marketplace Spending | WETH | Purchase cost |

---

# Bounty Board

| Field | Unit | Description |
|--------|------|-------------|
| BP Earned | BP | Total bounty points earned |
| Tasks Completed | Count | Number of completed tasks |
| Fortune Slips | Count | Current Fortune Slip balance |

---

# Notes

This document defines the standard schema for daily operational snapshots.

Historical snapshots will be stored in the Daily Logs and later imported into the AxieOS SQLite database for analytics and dashboard visualization.

---

# Design Principle

Daily snapshots describe the **state** of the account.

Blockchain transactions describe the **events** that changed that state.

Both datasets complement each other and together provide a complete financial history.
