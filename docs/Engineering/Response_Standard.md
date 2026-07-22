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
