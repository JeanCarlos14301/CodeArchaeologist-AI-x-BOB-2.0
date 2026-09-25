---
name: legacy-risk
description: Calculate risk matrix and PERT effort estimates from audit findings.
metadata:
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '[--format text|json|markdown]'
---

> Subagente principal: `migration-architect` (ver `.bob/agents/migration-architect.md`).

# Legacy Risk Command

Computes quantitative risk matrices, module blast radiuses, and three-point PERT effort estimates from audit findings.

## Usage

```bash
/legacy-risk [--format text|json|markdown]
```

## What This Command Does

1. **Gathers Audit Evidence**: Reads the validated technical dossier produced by `/legacy-audit`.
2. **Blast Radius Analysis**: Dispatches `legacy-dependency-tracer` to compute direct and transitive dependency blast radiuses across all modules.
3. **PERT Effort Estimation**:
   - Calculates Optimistic ($O$), Most Likely ($M$), and Pessimistic ($P$) effort estimates for each identified modernization phase.
   - Computes expected duration $E = \frac{O + 4M + P}{6}$ and standard deviation $\sigma = \frac{P - O}{6}$.
4. **Risk Matrix Formulation**: Categorizes candidate cuts into Low, Medium, High, and Critical risk quadrants based on $Impact \times Uncertainty$.
5. **Output**: Renders the risk matrix and PERT schedule in the requested format.

## Agents & Skills Used

- Agent: `migration-architect`
- Agent: `legacy-dependency-tracer`
- Skill: `legacy-risk-assessment`
- Rule: `.bob/rules/risk-calculation.md`
