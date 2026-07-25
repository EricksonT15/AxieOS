# Repository Audit Checklist

## Purpose

This checklist is used to verify that the AxieOS repository remains organized, complete, and consistent with the project's architecture.

Repository audits should be performed:

- After major milestones.
- Before creating releases.
- Monthly during active development.

---

# 1. Documentation

## Vision

- [ ] README is current.
- [ ] Decision Log updated.
- [ ] Domain Model updated.
- [ ] Data Dictionary updated.

## ADR

- [ ] ADR index updated.
- [ ] New architectural decisions documented.
- [ ] ADR references remain valid.

## Specifications

- [ ] Specifications reflect current implementation.
- [ ] Missing specifications identified.

---

# 2. Repository Structure

- [ ] Folder structure follows ADR-001.
- [ ] Naming conventions are consistent.
- [ ] Temporary files removed.
- [ ] No duplicate documentation.

---

# 3. Git Repository

- [ ] .gitignore reviewed.
- [ ] Personal blockchain data excluded.
- [ ] SQLite database excluded.
- [ ] Cache files excluded.

---

# 4. Source Code

- [ ] Every implemented module has documentation.
- [ ] Code matches specifications.
- [ ] Dead scripts identified.
- [ ] Import paths verified.

---

# 5. Data

- [ ] Sample datasets available.
- [ ] Personal datasets remain local.
- [ ] Data folder structure unchanged.

---

# 6. Database

- [ ] Schema matches SPEC-002.
- [ ] Migration scripts documented.
- [ ] No orphan tables.

---

# 7. Analytics

- [ ] EDA notebooks organized.
- [ ] Research notebooks separated from production code.
- [ ] Machine learning experiments documented.

---

# Audit Summary

Date:

Version:

Reviewer:

Findings:

Actions:
