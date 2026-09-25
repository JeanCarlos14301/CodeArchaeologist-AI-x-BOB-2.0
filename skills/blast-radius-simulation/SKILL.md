---
name: blast-radius-simulation
description: >
  Shift-Left pre-PR risk simulation and cascade failure prediction. Evaluates proposed
  code diffs or architectural modifications before human review, computing transitive call
  graphs, shared database mutations, and contract breakage risk.
metadata:
  origin: CodeArchaeologist
---

# Blast Radius Simulation & Shift-Left Review

A deterministic, static risk assessment workflow that predicts systemic failure modes caused by code modifications before a Pull Request is submitted or merged.

## When to Use

- When an autonomous agent or developer prepares a Pull Request in a legacy or high-stakes system.
- To prevent reviewer fatigue and alert teams to high-risk, cascading side-effects.
- When evaluating structural modifications to shared core modules (auth, database, telemetry).
- When executing the `/risk-simulate` slash command.

## Calculation Methodology

```
┌────────────────────────────────────────┐
│ Phase 1: Diff Parsing & Touch Points   │ ── Modified symbols, files, and schemas
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Phase 2: Transitive Call Graph Traversal│ ── Callers, callers-of-callers, sink paths
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Phase 3: Data Mutation Conflict Matrix │ ── Tables/indexes touched by modified paths
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Phase 4: Risk Scoring & PR Gate Verdict│ ── Blast Index (0-100), PASS / WARN / BLOCK
└────────────────────────────────────────┘
```

### Risk Dimension Equations

1. **Direct Impact Ratio ($DIR$)**:
   $$DIR = \frac{\text{Direct Callers of Changed Functions}}{\text{Total Repository Functions}}$$

2. **Transitive Blast Radius ($TBR$)**:
   $$TBR = \frac{\text{Unique Transitive Downstream Callers}}{\text{Total Repository Functions}} \times 100\%$$

3. **Database Mutation Vulnerability ($DMV$)**:
   - $DMV = 0$: Read-only queries or no schema touch.
   - $DMV = 0.5$: Unindexed column filters or updates to non-foreign-key columns.
   - $DMV = 1.0$: Column drops, type alterations, shared table mutations without transactions.

4. **Composite Blast Radius Score ($CBRS$)**:
   $$CBRS = (0.4 \times TBR) + (0.3 \times DMV \times 100) + (0.3 \times \text{Test Deficit Factor} \times 100)$$

### Decision Gates

- **CBRS < 25 (Low Risk / Green Gate)**: Safe for standard automated CI/CD and single-reviewer approval.
- **25 <= CBRS < 60 (Moderate Risk / Yellow Gate)**: Requires additional characterization tests and architectural review.
- **CBRS >= 60 (Critical Risk / Red Gate)**: Automated BLOCK. Mandates multi-agent adversarial tribunal and dual principal engineer sign-off.
