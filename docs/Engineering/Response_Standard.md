# AxieOS Response Standard

Version: 1.0

---

# Purpose

This document defines the communication standard between the User and ChatGPT during the development of AxieOS.

The objective is to make every response predictable, reusable, and easy to copy into the GitHub repository.

Every response should clearly indicate whether it is:

- Discussion
- Repository content
- Design proposal
- Development task
- Analysis

This prevents confusion and reduces editing time.

---

# General Principles

1. Repository-ready content should always be separated from discussion.

2. A single response may contain multiple sections.

3. Every section must have an explicit header.

4. Repository content should never contain explanations.

5. Discussion should never be mixed inside repository content.

---

# Response Types

---

## 1. Discussion

Purpose

General conversation, brainstorming, clarifications, and decision making.

Header

```
## DISCUSSION
```

Contains

- opinions
- explanations
- reasoning
- trade-offs
- recommendations

Never intended to be copied into GitHub.

---

## 2. Analysis

Purpose

Evaluate a problem before making a decision.

Header

```
## ANALYSIS
```

Typical contents

- Cost analysis
- ROI analysis
- Strategy comparison
- Risk assessment
- Market observations

Example

```
## ANALYSIS

Pros

Cons

Recommendation
```

---

## 3. Markdown Output

Purpose

Repository-ready markdown.

Header

```
## MARKDOWN OUTPUT
```

Must include

Destination

```
Destination:
docs/example.md
```

Only markdown follows.

No discussion.

No explanations.

No comments.

Example

````markdown
# Title

Content
