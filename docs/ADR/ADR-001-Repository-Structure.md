# ADR-001: Repository Structure

## Status

Accepted

## Date

2026-07-25

---

# Context

AxieOS is evolving from a personal collection of scripts into a reusable analytics platform.

The repository should:

- remain clean and professional
- be easy to clone
- protect personal data
- support future modules

---

# Decision

The project will separate:

- Source Code
- Documentation
- Specifications
- Research
- User Data

User data will never be committed to the public repository.

---

# Repository Structure

```text
AxieOS/

docs/
scripts/
database/
sample_data/
data/
notebooks/
```

The `data/` folder exists locally but is ignored by Git.

---

# Consequences

Benefits

- Cleaner repository
- Reproducible project
- Easier onboarding
- Supports multiple wallets

Trade-offs

- Users must manually provide blockchain exports.
