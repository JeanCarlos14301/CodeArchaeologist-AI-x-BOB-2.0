---
description: Convene an adversarial multi-agent tribunal (Architect vs Skeptic) to stress-test designs and PRs.
argument-hint: "[--proposal <file>] [--diff <git-diff>]"
agent: code-skeptic
---

# Code Tribunal Command (Adversarial Multi-Agent Review)

Pits an Architect agent (proposing solutions) against a Skeptic agent (actively finding flaws) in a structured 4-round debate to ensure zero hidden debt.

## Usage

```bash
/code-tribunal --proposal docs/decisions.md
/code-tribunal --diff origin/main...feature-branch
```

## What This Command Does

1. **Thesis Presentation**: The Architect presents the design, rationale, and test coverage claims.
2. **Adversarial Interrogation**: The Skeptic attacks the design for race conditions, unhandled failure modes, missing edge cases, and rollback viability.
3. **Rebuttal & Hardening**: The Architect must provide mathematical proofs, AST call graphs, or characterization tests to defeat the Skeptic's objections.
4. **Adjudication**: Issues a binding verdict: UNANIMOUS_PASS, CONDITIONAL_APPROVAL, or VETOED_REJECTED.

## Agents Used

- `code-skeptic` (Adversarial Prosecutor)
- `migration-architect` / `polyglot-migration-planner` (Defense)
- `contract-keeper` (Witness / Test Verifier)

## Associated Skills & Rules

- Skill: `adversarial-tribunal`
- Skill: `characterization-testing`
- Rules: `rules/legacy-migration/evidence-standards.md`
