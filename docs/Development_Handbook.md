# AxieOS Development Handbook

## Purpose

This handbook defines how AxieOS is developed.

It establishes the engineering workflow, documentation standards, sprint process, and project philosophy.

This document should be followed before adding new features or making significant architectural changes.

---

# Development Philosophy

AxieOS is developed using an iterative engineering process.

The goal is not to build features quickly.

The goal is to build a reliable, explainable, and maintainable GameFi decision support platform.

Our philosophy is:

> Measure → Simulate → Optimize

---

# Core Principles

1. Data before AI.
2. Documentation before implementation.
3. One sprint at a time.
4. Build reusable modules.
5. Every recommendation should be explainable.
6. Never sacrifice maintainability for speed.

---

# Development Workflow

Every feature follows the same lifecycle.

Idea

↓

Discussion

↓

Architecture

↓

Documentation

↓

Implementation

↓

Testing

↓

Review

↓

Release

---

No implementation should begin before documentation is complete.

---

# Sprint Workflow

Each sprint has:

- One goal
- Several small tasks
- One milestone
- One review

A sprint is complete only after documentation and implementation have both been reviewed.

---

# Documentation Hierarchy

README

Public introduction.

Project Charter

Defines the mission and scope.

Roadmap

Defines future development.

Engineering Journal

Records the evolution of the project.

Decision Log

Records architectural decisions.

Data Dictionary

Defines every field used by the system.

Development Handbook

Defines how the project is built.

---

# GitHub Workflow

Small commits are preferred.

Commit messages should describe one logical change.

Examples:

docs: complete Project Charter

feat: add Daily Log worksheet

fix: correct bounty point calculation

---

# Design Philosophy

Whenever possible:

Measure first.

Collect data second.

Analyze third.

Automate last.

Avoid building automation before understanding the underlying process.

---

# AI Collaboration

AxieOS is designed to support collaboration with multiple AI assistants.

Any AI contributing to the project should:

- Read the README first.
- Review the Project Charter.
- Check the Roadmap.
- Respect previous architectural decisions.
- Update documentation when necessary.
- Explain recommendations clearly.

---

# Project Success

AxieOS succeeds when it helps players make better decisions.

Not when it contains more features.

Quality is more important than quantity.

Evidence is more important than opinion.
