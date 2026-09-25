---
description: Shift-Left pre-PR risk simulator. Predicts cascade failures and blast radius before human review.
argument-hint: "[--diff <git-diff-ref>] [--path <file/module>]"
agent: blast-radius-simulator
---

# Risk Simulate Command (Shift-Left Blast Radius Gate)

Simulates the impact of proposed changes on the entire codebase without applying them, mapping hidden dependencies and calculating cascade failure probabilities.

## Usage

```bash
/risk-simulate [--diff HEAD~1]
/risk-simulate [--path backend/legacy/db_pool.py]
```

## What This Command Does

1. **Diff & Touchpoint Extraction**: Pinpoints exactly which functions, classes, and database schemas are modified.
2. **Transitive Call Graph Traversal**: Reconstructs caller-callee chains to discover all upstream systems exposed to the change.
3. **Database Mutation Conflict Analysis**: Flags concurrent writes, schema alterations, or shared locks that could trigger outages.
4. **Shift-Left PR Gate Scoring**: Computes the Composite Blast Radius Score ($CBRS$) from 0 to 100 and outputs a gate verdict (GREEN: PASS, YELLOW: REVIEW, RED: BLOCK).

## Agents Used

- `blast-radius-simulator` (Lead Risk Assessor)
- `ast-cartographer`
- `legacy-dependency-tracer`
- `code-skeptic`

## Associated Skills & Rules

- Skill: `blast-radius-simulation`
- Skill: `legacy-risk-assessment`
- Rules: `rules/legacy-migration/risk-calculation.md`
