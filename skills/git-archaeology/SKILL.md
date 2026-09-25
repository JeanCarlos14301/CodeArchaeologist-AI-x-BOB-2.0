---
name: git-archaeology
description: >
  Historical git repository mining using PyDriller, commit frequency metrics,
  and change churn analysis. Uncovers hot-spots, bug-prone modules, author bus factor,
  and historical bug clusters in legacy repositories.
metadata:
  origin: CodeArchaeologist
---

# Git Archaeology & Commit Mining Workflow

A quantitative, evidence-grounded workflow for analyzing the version control history of legacy codebases. Identifies implicit organizational knowledge, architectural erosion, and defect-prone hotspots.

## When to Use

- When auditing an undocumented repository to determine which components fail most frequently.
- When calculating the "Bus Factor" and identifying key subject matter experts.
- When identifying temporal coupling (files that always change together but share no code imports).
- When executing the `/code-archaeology` slash command.

## Methodology & Metrics

```
┌────────────────────────────────────────┐
│ Phase 1: Git Repository Mining         │ ── PyDriller extraction of commits, diffs, messages
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Phase 2: Churn vs. Defect Density Map  │ ── Crossing commit frequency with bug-fix keywords
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Phase 3: Temporal Coupling Analysis    │ ── Co-change probability across file pairs
└──────────────────┬─────────────────────┘
                   │
┌──────────────────▼─────────────────────┐
│ Phase 4: Hotspot & Bus Factor Report   │ ── Synthesis of priority refactoring zones
└────────────────────────────────────────┘
```

### Key Metrics Formulations

1. **Code Churn**:
   $$\text{Churn}(F) = \sum_{c \in \text{Commits}(F)} (\text{Added Lines}(c) + \text{Deleted Lines}(c))$$

2. **Defect Density ($DD$)**:
   Percentage of commits mentioning `fix`, `bug`, `patch`, `issue`, or `revert` in commit messages:
   $$DD(F) = \frac{|\{c \in \text{Commits}(F) : c \text{ is bugfix}\}|}{|\text{Commits}(F)|} \times 100\%$$

3. **Temporal Coupling ($TC$)**:
   Degree to which file $A$ and file $B$ commit together:
   $$TC(A, B) = \frac{|\text{Commits}(A \cap B)|}{|\text{Commits}(A \cup B)|}$$
   High $TC$ without import relationships indicates hidden architecture coupling.

4. **Bus Factor Risk**:
   If $>80\%$ of commits in a high-churn module belong to an author no longer with the team, module is flagged as **ORPHANED_CRITICAL_CORE**.
