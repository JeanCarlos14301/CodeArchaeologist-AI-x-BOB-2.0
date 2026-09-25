---
name: code-archaeology
description: Mine version control history with PyDriller to uncover hotspots, churn, and author bus factor.
metadata:
  user-invocable: true
  disable-model-invocation: true
  argument-hint: '[--since <date>] [--top <number>] [--author-risk]'
---

> Subagente principal: `git-archaeologist` (ver `.bob/agents/git-archaeologist.md`).

# Code Archaeology Command (Git History & Churn Mining)

Performs deep archaeological mining on the git history of the repository using PyDriller and commit defect analysis.

## Usage

```bash
/code-archaeology --since 2023-01-01 --top 10
/code-archaeology --author-risk
```

## What This Command Does

1. **Commit Log Extraction**: Analyzes commit frequency, churn volume (insertions + deletions), and commit messages.
2. **Defect Hotspot Detection**: Flags files with high churn and recurring bug-fix commits.
3. **Temporal Coupling Identification**: Discovers unlinked files that co-change across commits, revealing hidden architectural entanglements.
4. **Knowledge Ownership & Bus Factor**: Measures author concentration across critical modules to identify orphaned systems.

## Agents Used

- `git-archaeologist` (Lead Mining Agent)
- `ast-cartographer`
- `telemetry-bridge`

## Associated Skills & Rules

- Skill: `git-archaeology`
- Skill: `ast-analysis`
- Rules: `.bob/rules/code-legacy-treatment.md`
