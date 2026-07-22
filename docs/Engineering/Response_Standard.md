# AxieOS Response Standard

Version: 1.0

---

# Purpose

This document defines how ChatGPT should structure responses while assisting with the development of AxieOS.

The goal is to make every response predictable, easy to understand, and easy to integrate into the repository.

---

# General Principles

1. Every response must clearly indicate its purpose.
2. Repository content must always be separated from discussion.
3. Multiple response sections may be used in a single reply.
4. Repository-ready content must not include explanations.
5. Discussion and analysis should never be mixed into repository content.

---

# Response Types

## DISCUSSION

Purpose

General conversation, brainstorming, clarifications, recommendations, and explanations.

This section is **not** intended for the repository.

---

## ANALYSIS

Purpose

Evaluate alternatives before making a decision.

Typical contents include:

- Cost analysis
- ROI analysis
- Risk assessment
- Strategy comparison
- Trade-offs

This section is **not** intended for the repository.

---

## MARKDOWN OUTPUT

Purpose

Generate repository-ready Markdown.

Requirements

- Must begin with:

```
## MARKDOWN OUTPUT
```

- Must specify the destination file.

Example

```
Destination:
logs/daily/2026-07-22.md
```

- After the destination, only Markdown content should follow.

No explanations.

No discussion.

No comments.

---

## REPOSITORY UPDATE

Purpose

Modify an existing repository file.

Requirements

- Must begin with:

```
## REPOSITORY UPDATE
```

- Must specify:

- File
- Action

Valid Actions

- Create
- Append
- Replace
- Rename
- Delete

Only the repository content should follow.

---

## DESIGN PROPOSAL

Purpose

Present ideas that have **not yet been accepted**.

Typical contents

- Reason
- Benefits
- Drawbacks
- Recommendation

This section is for discussion only.

---

## IMPLEMENTATION TASK

Purpose

Create work items for future development.

Typical contents

- Priority
- Module
- Status
- Description
- Acceptance Criteria

This section is intended for project planning.

---

# Default Response Order

When multiple sections are used, they should appear in the following order.

1. Discussion
2. Analysis
3. Markdown Output
4. Repository Update
5. Design Proposal
6. Implementation Task

---

# Repository Philosophy

The repository is the permanent source of truth.

Chat conversations are temporary.

Whenever a decision becomes permanent, it should eventually be documented inside the repository.

---

End of Document

---

# Data Management Rules

These rules apply to all datasets used by AxieOS.

## Rule 1 — Immutable Raw Data

Raw imported data must never be modified.

Examples

- Blockchain transaction exports
- Marketplace exports
- Wallet exports
- API responses

If an error is discovered, correct it in the processed data or classification layer—not in the original source.

---

## Rule 2 — Separation of Data

AxieOS data is divided into three layers.

### Raw

Original data from external sources.

Never edited.

### Processed

Data cleaned, classified, or transformed by AxieOS.

May be regenerated from Raw at any time.

### Reference

Master data maintained by the user.

Examples

- Axie collection
- Land collection
- Accessories
- Collectibles
- Categories

---

## Rule 3 — Naming Convention

Files should use predictable names.

Examples

wallet_transactions_001.csv

wallet_transactions_002.csv

wallet_transactions_003.csv

marketplace_transactions_001.csv

nft_transactions_001.csv

staking_transactions_001.csv

This allows future automation without renaming files.

---

## Rule 4 — Source of Truth

Only one source of truth exists for each type of information.

Examples

Blockchain
→ Financial transactions

Manual Logs
→ Gameplay and decisions

Marketplace
→ Current market prices

Reference Files
→ Portfolio assets

Processed Data
→ Analytics

---

## Rule 5 — Reproducibility

AxieOS should always be able to rebuild the processed datasets from the raw datasets.

Nothing in the analytics layer should depend on manually edited transaction history.

This ensures the database remains accurate, auditable, and reproducible.
