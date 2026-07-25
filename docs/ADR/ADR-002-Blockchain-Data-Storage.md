# ADR-002: Blockchain Data Storage

## Status

Accepted

## Date

2026-07-25

---

# Context

Blockchain transaction history is publicly accessible but represents a complete financial history when exported as CSV.

Publishing these datasets inside the GitHub repository would unnecessarily expose years of trading activity.

---

# Decision

Raw blockchain exports will remain outside Git.

Users will manually place exported CSV files into:

```text
data/raw/legacy/
data/raw/op_chain/
```

Import scripts will automatically discover and import every CSV.

No filenames are hardcoded.

---

# Sample Data

The repository may contain anonymized sample datasets.

These are intended only for demonstrating the software.

---

# Consequences

Benefits

- Protects user financial history.
- Keeps repository lightweight.
- Supports any wallet.

Trade-offs

- Initial setup requires manual file placement.
