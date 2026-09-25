---
name: adversarial-tribunal
description: >
  Protocol for multi-agent adversarial debate (Architect vs. Skeptic). Pits proposed
  migration plans, architecture designs, or critical PRs against a hostile reviewer agent
  to uncover hidden technical debt, unhandled failure modes, and false assumptions.
metadata:
  origin: CodeArchaeologist
---

# Adversarial Multi-Agent Tribunal Workflow

A formal dialectical evaluation protocol where an Architect agent (proposer) and a Skeptic agent (challenger) debate technical proposals under explicit evidentiary rules until consensus or a clear risk veto is reached.

## When to Use

- Before approving major refactorings, framework migrations, or database schema cuts.
- When an agent proposes a high-blast-radius change (>50% blast radius).
- When validating that automated code changes do not introduce subtle race conditions, data corruption, or security regressions.
- When executing the `/code-tribunal` slash command.

## Tribunal Mechanics & Protocol

```
┌────────────────────────────────────────┐
│ Round 1: Thesis (Architect)            │ ── Migration proposal, assumptions, test plan
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Round 2: Antithesis (Skeptic)          │ ── Cites line numbers, unhandled exceptions, debt
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Round 3: Rebuttal & Defense            │ ── Architect presents proofs or amends proposal
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Round 4: Verdict & Final Adjudication  │ ── Consensus score, concessions, verdict (APPROVE/REJECT)
└────────────────────────────────────────┘
```

### Skeptic Interrogation Rubric

The Skeptic must challenge across 5 non-negotiable vectors:
1. **Concurrency & Race Conditions**: Does the solution assume single-threaded execution? What happens under simultaneous requests?
2. **State & Mutation Leaks**: Are global state variables, connection singletons, or uncommitted transactions left dangling?
3. **Data Loss & Rollback Viability**: If the new service crashes midway through an operation, can the legacy database safely rollback?
4. **Error Boundary Completeness**: Are all HTTP 4xx and 5xx cases accounted for, or does it silently fail with 200 OK?
5. **Observability & Debuggability**: If this breaks at 3 AM in production, can an engineer diagnose it without code changes?

### Adjudication Verdicts

- **UNANIMOUS_PASS**: Architect adequately addressed all skeptic challenges with test evidence or architectural guards.
- **CONDITIONAL_APPROVAL**: Approved subject to mandatory addition of specified characterization test cases.
- **VETOED_REJECTED**: Critical vulnerability, data loss risk, or unverifiable assumption identified; proposal sent back for redesign.
