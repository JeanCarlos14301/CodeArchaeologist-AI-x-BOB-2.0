---
name: board-memo-writing
description: >
  Guidelines, structure, and tone for authoring executive memorandums and 
  board-level modernization reports from technical audit data.
metadata:
  origin: CodeArchaeologist
---

# Board Memorandum Authoring Guide

A strategic writing and communication skill for crafting executive-level modernization memos for corporate boards, executive committees, and non-technical technology leaders.

## When to Use

- When drafting reports for the Board of Directors or C-suite executives.
- When transforming pipeline findings into narrative sections for DOCX generation (Task F-08 / D-08).
- When running the `/legacy-report --audience board` command.
- When communicating technical risk, regulatory liabilities, and investment roadmaps.

## Core Writing Principles

### 1. Zero Number Fabrication
- **Rule of Law**: Every percentage, dollar figure, line count, and timeline hour must trace directly to a verified pipeline artifact. If the pipeline reports 3 critical findings, the memo states 3. If test coverage was unmeasured, state "unmeasured," never "approximately 10%".

### 2. Business Impact Translation
Translate technical jargon into strategic business risk:
- *Instead of:* "Cyclomatic complexity in orders.py is 34 with high afferent coupling."
- *Write:* "The core order processing module is highly interconnected, meaning small updates currently carry a high probability of inducing unexpected system outages."
- *Instead of:* "SQL injection via f-string on line 42."
- *Write:* "A critical vulnerability allows unauthorized access to customer database records, presenting immediate regulatory and reputational liability."

### 3. Clear, Structured Hierarchy
- **The BLUF Principle (Bottom Line Up Front)**: State the core finding, risk level, and required decision in the very first paragraph.
- Use bold lead-in bullets for rapid visual scanning.
- Keep paragraphs under 4 sentences.

## Standard Memorandum Structure

1. **Executive Summary**: The strategic situation in brief. Why action is required now.
2. **Current State & Exposure**: Validated vulnerabilities, maintenance overhead, and operational fragility.
3. **The Recommended Path (Strangler Fig)**: Explain the incremental migration approach and how it avoids the catastrophic failure rates of big-bang rewrites.
4. **Verifiable Progress (The First Cut)**: Evidence that the first migration step is already tested, verified, and operational.
5. **Timeline & Resourcing (PERT Range)**: Probabilistic schedule with confidence bounds.
6. **Requested Board Action**: Explicit decision or authorization requested.

## Vocabulary & Tone Guide

| Avoid (Informal / Emotional) | Prefer (Executive / Strategic) |
|---|---|
| "Terrible spaghetti code" | "Tightly coupled legacy architecture" |
| "Total rewrite needed" | "Phased incremental modernization" |
| "It will take 2 months" | "PERT projected window of 6 to 10 engineer-weeks" |
| "We fixed the bug" | "Eliminated the high-severity security liability" |
| "Trust us, it works" | "Behavioral parity verified via automated test suite" |
